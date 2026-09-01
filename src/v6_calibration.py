"""Target-free whole-triad calibration and final V6 bank selection."""

from __future__ import annotations

import hashlib
import itertools
import json
import os
import time
from collections import Counter, defaultdict
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

import numpy as np

from config import (
    CONTROLLED_V6_CALIBRATION_THRESHOLDS,
    CONTROLLED_V6_VERSION,
    STRATEGIES,
)
from .controlled_focal_agent import build_controlled_prompt, parse_controlled_choice
from .controlled_messages import MessageCandidate, candidate_for_slot
from .controlled_v6_messages import V6TriadBank, audit_v6_bank_payload
from .focal_agent import BaseProvider, ProviderError
from .logging_utils import JsonlWriter, write_manifest
from .scenarios import (
    V6_CALIBRATION_SCENARIOS,
    V6_VALIDATION_SCENARIOS,
)
from .seeding import derive_seed


V6_CALIBRATION_VERSION = "v6-triad-calibration-1.0"
V6_POOL_MODE = "pool_screening"
V6_VALIDATION_MODE = "selected_bank_validation"
V6_CALIBRATION_FOLDS: Tuple[Tuple[str, str], ...] = tuple(
    (
        V6_CALIBRATION_SCENARIOS[index].id,
        V6_CALIBRATION_SCENARIOS[index + 1].id,
    )
    for index in range(0, len(V6_CALIBRATION_SCENARIOS), 2)
)
V6_VALIDATION_FOLDS: Tuple[Tuple[str, str], ...] = tuple(
    (
        V6_VALIDATION_SCENARIOS[index].id,
        V6_VALIDATION_SCENARIOS[index + 1].id,
    )
    for index in range(0, len(V6_VALIDATION_SCENARIOS), 2)
)


def canonical_sha256(payload: Any) -> str:
    canonical = json.dumps(
        payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def file_sha256(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def bank_content_sha256(payload: Mapping[str, Any]) -> str:
    return canonical_sha256(payload.get("splits", {}))


def _triads(bank: V6TriadBank, split: Optional[str] = None):
    if split is None:
        for split_name in ("development", "heldout"):
            yield from bank.payload["splits"][split_name]
    else:
        yield from bank.payload["splits"][split]


def _candidate_rows_for_triad(
    triad: Mapping[str, Any], scenario: Any, permutation: Sequence[str], split: str
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for slot, frame in enumerate(permutation, start=1):
        entry = triad["candidates"][frame]
        text = " ".join(str(entry["template"]).format(a=scenario.option_a).split())
        rows.append(
            {
                "slot": slot,
                "triad_id": str(triad["triad_id"]),
                "pool_candidate_id": str(entry["candidate_id"]),
                "candidate_id": "%s-%s" % (entry["candidate_id"], scenario.id),
                "message": text,
                "frame": frame,
                "split": split,
            }
        )
    return rows


def build_v6_pool_schedule(
    bank: V6TriadBank, seed: int = 20262001
) -> List[Dict[str, Any]]:
    """Evaluate every triad on all scenarios and all six slot permutations."""
    permutations = list(itertools.permutations(STRATEGIES))
    rows: List[Dict[str, Any]] = []
    pool_hash = bank.sha256()
    global_index = 0
    for split in ("development", "heldout"):
        triads = list(_triads(bank, split))
        for triad_index, triad in enumerate(triads):
            for scenario_index, scenario in enumerate(V6_CALIBRATION_SCENARIOS):
                # Rotate which lexical permutation receives each permutation index
                # without changing the complete six-permutation set.
                offset = derive_seed(
                    "v6_pool_permutation_offset",
                    seed,
                    split,
                    triad["triad_id"],
                    scenario.id,
                ) % len(permutations)
                ordered = permutations[offset:] + permutations[:offset]
                for local_index, permutation in enumerate(ordered):
                    if split == "development":
                        round_index = (
                            scenario_index * len(permutations)
                            + local_index
                            + triad_index
                        ) % 18 + 1
                    else:
                        round_index = 19 + (
                            scenario_index + local_index + triad_index
                        ) % 6
                    rows.append(
                        {
                            "calibration_version": V6_CALIBRATION_VERSION,
                            "pool_sha256": pool_hash,
                            "split": split,
                            "triad_id": str(triad["triad_id"]),
                            "triad_index": triad_index,
                            "scenario_index": scenario_index,
                            "permutation_index": local_index,
                            "frame_order": list(permutation),
                            "episode_index": global_index // 24,
                            "round": round_index,
                            "n_rounds": 24,
                            "heldout_start_round": 19,
                            "scenario": scenario.as_dict(),
                            "candidates": _candidate_rows_for_triad(
                                triad, scenario, permutation, split
                            ),
                            "generation_seed": derive_seed(
                                V6_CALIBRATION_VERSION,
                                seed,
                                split,
                                triad["triad_id"],
                                scenario.id,
                                local_index,
                            ),
                        }
                    )
                    global_index += 1
    audit = audit_v6_pool_schedule(rows, bank)
    if not audit["pass"]:
        failed = sorted(name for name, passed in audit["checks"].items() if not passed)
        raise RuntimeError("generated V6 pool schedule failed: %s" % ", ".join(failed))
    return rows


def audit_v6_pool_schedule(
    rows: Sequence[Mapping[str, Any]], bank: V6TriadBank
) -> Dict[str, Any]:
    rows = list(rows)
    expected_triads = {
        str(triad["triad_id"]): split
        for split in ("development", "heldout")
        for triad in _triads(bank, split)
    }
    triad_counts: Counter = Counter()
    scenario_counts: Dict[str, Counter] = defaultdict(Counter)
    frame_slots: Dict[str, Counter] = defaultdict(Counter)
    permutations: Dict[str, set] = defaultdict(set)
    complete = True
    for row in rows:
        triad_id = str(row.get("triad_id", ""))
        triad_counts[triad_id] += 1
        scenario_counts[triad_id][str(row.get("scenario", {}).get("id", ""))] += 1
        candidates = row.get("candidates", [])
        complete &= (
            len(candidates) == 3
            and {str(candidate.get("frame")) for candidate in candidates}
            == set(STRATEGIES)
            and {int(candidate.get("slot", -1)) for candidate in candidates}
            == {1, 2, 3}
            and all(str(candidate.get("triad_id")) == triad_id for candidate in candidates)
        )
        order = tuple(
            str(candidate["frame"])
            for candidate in sorted(candidates, key=lambda item: int(item["slot"]))
        )
        permutations[triad_id].add(order)
        for candidate in candidates:
            frame_slots[triad_id][
                (str(candidate["frame"]), int(candidate["slot"]))
            ] += 1
        split = str(row.get("split", ""))
        round_index = int(row.get("round", -1))
        complete &= split == expected_triads.get(triad_id)
        complete &= (round_index <= 18 if split == "development" else round_index >= 19)
    expected_count = len(expected_triads) * len(V6_CALIBRATION_SCENARIOS) * 6
    checks = {
        "nonempty": bool(rows),
        "record_count": len(rows) == expected_count,
        "exact_triad_membership": set(triad_counts) == set(expected_triads),
        "complete_candidate_sets": complete,
        "triad_exposure": all(
            value == len(V6_CALIBRATION_SCENARIOS) * 6
            for value in triad_counts.values()
        ),
        "all_scenarios_per_triad": all(
            set(counts) == {scenario.id for scenario in V6_CALIBRATION_SCENARIOS}
            and set(counts.values()) == {6}
            for counts in scenario_counts.values()
        ),
        "all_six_permutations": all(len(values) == 6 for values in permutations.values()),
        "frame_slot_balance": all(
            set(counts) == {(frame, slot) for frame in STRATEGIES for slot in (1, 2, 3)}
            and set(counts.values()) == {len(V6_CALIBRATION_SCENARIOS) * 2}
            for counts in frame_slots.values()
        ),
        "pool_hash": all(row.get("pool_sha256") == bank.sha256() for row in rows),
    }
    return {
        "pass": all(checks.values()),
        "checks": checks,
        "n_rows": len(rows),
        "triad_exposures": dict(triad_counts),
        "frame_slot_counts": {
            triad_id: {"%s@%d" % key: value for key, value in counts.items()}
            for triad_id, counts in frame_slots.items()
        },
    }


def _base_candidate_id(candidate_id: str, scenario_id: str) -> str:
    suffix = "-" + scenario_id
    if not candidate_id.endswith(suffix):
        raise ValueError("candidate id does not end with scenario id")
    return candidate_id[: -len(suffix)]


def _triad_lookup(bank: V6TriadBank) -> Dict[str, Tuple[str, str]]:
    lookup: Dict[str, Tuple[str, str]] = {}
    for split in ("development", "heldout"):
        for triad in _triads(bank, split):
            for entry in triad["candidates"].values():
                lookup[str(entry["candidate_id"])] = (str(triad["triad_id"]), split)
    return lookup


def build_v6_validation_schedule(
    bank: V6TriadBank,
    seed: int = 20262002,
) -> List[Dict[str, Any]]:
    """Challenge the locked bank on disjoint scenarios and all permutations."""
    permutations = list(itertools.permutations(STRATEGIES))
    rows: List[Dict[str, Any]] = []
    global_index = 0
    for split in ("development", "heldout"):
        for triad_index, triad in enumerate(_triads(bank, split)):
            for scenario_index, scenario in enumerate(V6_VALIDATION_SCENARIOS):
                offset = derive_seed(
                    "v6_validation_permutation_offset",
                    seed,
                    split,
                    triad["triad_id"],
                    scenario.id,
                ) % len(permutations)
                ordered = permutations[offset:] + permutations[:offset]
                for local_index, permutation in enumerate(ordered):
                    if split == "development":
                        round_index = (
                            scenario_index * len(permutations)
                            + local_index
                            + triad_index
                        ) % 18 + 1
                    else:
                        round_index = 19 + (
                            scenario_index + local_index + triad_index
                        ) % 6
                    rows.append(
                        {
                            "calibration_version": V6_CALIBRATION_VERSION,
                            "pool_sha256": bank.sha256(),
                            "split": split,
                            "triad_id": str(triad["triad_id"]),
                            "triad_index": triad_index,
                            "scenario_index": scenario_index,
                            "permutation_index": local_index,
                            "frame_order": list(permutation),
                            "episode_index": global_index // 24,
                            "round": round_index,
                            "n_rounds": 24,
                            "heldout_start_round": 19,
                            "scenario": scenario.as_dict(),
                            "candidates": _candidate_rows_for_triad(
                                triad, scenario, permutation, split
                            ),
                            "generation_seed": derive_seed(
                                V6_CALIBRATION_VERSION,
                                "independent_validation",
                                seed,
                                split,
                                triad["triad_id"],
                                scenario.id,
                                local_index,
                            ),
                        }
                    )
                    global_index += 1
    audit = audit_v6_validation_schedule(rows, bank)
    if not audit["pass"]:
        failed = sorted(name for name, passed in audit["checks"].items() if not passed)
        raise RuntimeError("generated V6 validation schedule failed: %s" % ", ".join(failed))
    return rows


def audit_v6_validation_schedule(
    rows: Sequence[Mapping[str, Any]], bank: V6TriadBank
) -> Dict[str, Any]:
    rows = list(rows)
    triad_counts: Dict[str, Counter] = defaultdict(Counter)
    scenario_counts: Dict[str, Counter] = defaultdict(Counter)
    frame_slots: Dict[str, Counter] = defaultdict(Counter)
    permutations: Dict[str, set] = defaultdict(set)
    complete = True
    for row in rows:
        split = str(row["split"])
        triad_id = str(row["triad_id"])
        triad_counts[split][triad_id] += 1
        scenario_counts[triad_id][str(row["scenario"]["id"])] += 1
        candidates = row.get("candidates", [])
        complete &= len(candidates) == 3
        complete &= {candidate["frame"] for candidate in candidates} == set(STRATEGIES)
        complete &= {int(candidate["slot"]) for candidate in candidates} == {1, 2, 3}
        complete &= all(candidate["triad_id"] == row["triad_id"] for candidate in candidates)
        order = tuple(
            str(candidate["frame"])
            for candidate in sorted(candidates, key=lambda item: int(item["slot"]))
        )
        permutations[triad_id].add(order)
        for candidate in candidates:
            frame_slots[triad_id][
                (str(candidate["frame"]), int(candidate["slot"]))
            ] += 1
    expected_ids = {
        split: {str(triad["triad_id"]) for triad in _triads(bank, split)}
        for split in ("development", "heldout")
    }
    expected_total = sum(len(values) for values in expected_ids.values()) * len(
        V6_VALIDATION_SCENARIOS
    ) * 6
    checks = {
        "nonempty": bool(rows),
        "record_count": len(rows) == expected_total,
        "complete_candidate_sets": complete,
        "pool_hash": all(row.get("pool_sha256") == bank.sha256() for row in rows),
        "split_membership": all(set(triad_counts[split]) == expected_ids[split] for split in expected_ids),
        "triad_exposure": all(
            value == len(V6_VALIDATION_SCENARIOS) * 6
            for counts in triad_counts.values()
            for value in counts.values()
        ),
        "disjoint_validation_scenarios": all(
            set(counts) == {scenario.id for scenario in V6_VALIDATION_SCENARIOS}
            and set(counts.values()) == {6}
            for counts in scenario_counts.values()
        ),
        "all_six_permutations": all(len(values) == 6 for values in permutations.values()),
        "frame_slot_balance": all(
            set(counts) == {(frame, slot) for frame in STRATEGIES for slot in (1, 2, 3)}
            and set(counts.values()) == {len(V6_VALIDATION_SCENARIOS) * 2}
            for counts in frame_slots.values()
        ),
    }
    return {
        "pass": all(checks.values()),
        "checks": checks,
        "n_rows": len(rows),
        "triad_counts": {split: dict(counts) for split, counts in triad_counts.items()},
        "frame_slot_counts": {
            triad_id: {"%s@%d" % key: value for key, value in counts.items()}
            for triad_id, counts in frame_slots.items()
        },
    }


def _message_candidates(row: Mapping[str, Any]) -> List[MessageCandidate]:
    return [
        MessageCandidate(
            slot=int(candidate["slot"]),
            candidate_id=str(candidate["candidate_id"]),
            message=str(candidate["message"]),
            frame=str(candidate["frame"]),
            split=str(candidate["split"]),
            template_index=-1,
        )
        for candidate in row["candidates"]
    ]


def _scenario_proxy(scenario: Mapping[str, Any]):
    class ScenarioProxy:
        id = scenario["id"]
        title = scenario["title"]
        context = scenario["context"]
        option_a = scenario["option_a"]
        option_b = scenario["option_b"]

        @classmethod
        def render(cls):
            return (
                "Decision: %s\n%s\nOption A: %s\nOption B: %s"
                % (cls.title, cls.context, cls.option_a, cls.option_b)
            )

    return ScenarioProxy


def run_v6_target_free_calibration(
    bank: V6TriadBank,
    provider: BaseProvider,
    run_id: str,
    out_dir: str,
    seed: int,
    mode: str,
    n_episode_blocks: Optional[int] = None,
    provenance: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    if n_episode_blocks is not None:
        raise ValueError(
            "V6 uses a complete triad-by-scenario-by-permutation schedule; "
            "episode-block overrides are not defined"
        )
    if mode == V6_POOL_MODE:
        schedule = build_v6_pool_schedule(bank, seed=seed)
    elif mode == V6_VALIDATION_MODE:
        schedule = build_v6_validation_schedule(bank, seed=seed)
    else:
        raise ValueError("unknown V6 calibration mode %r" % mode)
    os.makedirs(out_dir, exist_ok=True)
    log_path = os.path.join(out_dir, run_id + ".jsonl")
    manifest_path = os.path.join(out_dir, run_id + ".manifest.json")
    if os.path.exists(log_path) or os.path.exists(manifest_path):
        raise FileExistsError("refusing to overwrite V6 calibration run %r" % run_id)
    schedule_audit = (
        audit_v6_pool_schedule(schedule, bank)
        if mode == V6_POOL_MODE
        else audit_v6_validation_schedule(schedule, bank)
    )
    manifest: Dict[str, Any] = {
        "calibration_version": V6_CALIBRATION_VERSION,
        "task_version": CONTROLLED_V6_VERSION,
        "mode": mode,
        "run_id": run_id,
        "run_status": "running",
        "target_simulator_present": False,
        "history_present": False,
        "pool_sha256": bank.sha256(),
        "bank_content_sha256": bank_content_sha256(bank.payload),
        "bank_source": bank.source_path,
        "provider": provider.describe(),
        "schedule": {
            "seed": seed,
            "n_records": len(schedule),
            "n_episode_blocks": None,
            "n_rounds": 24,
            "heldout_start_round": 19,
        },
        "schedule_audit": schedule_audit,
    }
    if provenance is not None:
        manifest["frozen_protocol"] = json.loads(json.dumps(provenance))
    write_manifest(manifest_path, manifest)
    records: List[Dict[str, Any]] = []
    with JsonlWriter(log_path, validate=False) as writer:
        for schedule_row in schedule:
            candidates = _message_candidates(schedule_row)
            prompt = build_controlled_prompt(
                scenario=_scenario_proxy(schedule_row["scenario"]),
                candidates=candidates,
                history=[],
                round_index=int(schedule_row["round"]),
                n_rounds=24,
                show_history=False,
                focal_mode="spontaneous",
                context={},
            )
            set_next_seed = getattr(provider, "set_next_seed", None)
            if callable(set_next_seed):
                set_next_seed(int(schedule_row["generation_seed"]))
            raw = provider.generate(prompt)
            parsed = parse_controlled_choice(
                raw, "spontaneous", int(schedule_row["generation_seed"])
            )
            if not parsed.selection_valid:
                raise ProviderError(
                    "V6 calibration requires an exact constrained choice; got %r" % raw
                )
            selected = candidate_for_slot(candidates, parsed.selected_slot)
            source = next(
                candidate
                for candidate in schedule_row["candidates"]
                if int(candidate["slot"]) == parsed.selected_slot
            )
            record = {
                **schedule_row,
                "run_id": run_id,
                "mode": mode,
                "focal_system_prompt": prompt.system,
                "focal_user_prompt": prompt.user,
                "focal_output_raw": raw,
                "selection_valid": True,
                "fallback_used": False,
                "selected_slot": parsed.selected_slot,
                "selected_frame": selected.frame,
                "selected_candidate_id": selected.candidate_id,
                "selected_pool_candidate_id": source["pool_candidate_id"],
                "provider": provider.name,
                "model_name": getattr(provider, "model_id", None)
                or getattr(provider, "model", None)
                or "unknown",
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            }
            writer.write(record)
            records.append(record)
    manifest["run_status"] = "completed"
    manifest["n_records"] = len(records)
    manifest["valid_selection_rate"] = 1.0
    manifest["log_path"] = os.path.abspath(log_path)
    manifest["log_file_sha256"] = file_sha256(log_path)
    write_manifest(manifest_path, manifest)
    return {
        "records": records,
        "manifest": manifest,
        "log_path": log_path,
        "manifest_path": manifest_path,
    }


def audit_v6_calibration_run(
    records: Sequence[Mapping[str, Any]],
    manifest: Mapping[str, Any],
    bank: V6TriadBank,
    expected_mode: str,
) -> Dict[str, Any]:
    records = list(records)
    schedule_audit = (
        audit_v6_pool_schedule(records, bank)
        if expected_mode == V6_POOL_MODE
        else audit_v6_validation_schedule(records, bank)
    )
    frozen = manifest.get("frozen_protocol", {})
    checks = {
        "nonempty": bool(records),
        "completed": manifest.get("run_status") == "completed",
        "task_version": manifest.get("task_version") == CONTROLLED_V6_VERSION,
        "calibration_version": manifest.get("calibration_version") == V6_CALIBRATION_VERSION,
        "mode": manifest.get("mode") == expected_mode
        and all(row.get("mode") == expected_mode for row in records),
        "target_absent": manifest.get("target_simulator_present") is False,
        "history_absent": manifest.get("history_present") is False,
        "bank_hash": manifest.get("pool_sha256") == bank.sha256()
        and all(row.get("pool_sha256") == bank.sha256() for row in records),
        "record_count": manifest.get("n_records") == len(records)
        == manifest.get("schedule", {}).get("n_records"),
        "strict_outputs": all(
            row.get("selection_valid") is True
            and row.get("fallback_used") is False
            and str(row.get("focal_output_raw", "")) in {"1", "2", "3"}
            for row in records
        ),
        "provider_constrained": manifest.get("provider", {}).get("constrained_choices")
        == ["1", "2", "3"],
        "schedule_audit": schedule_audit["pass"],
        "frozen_protocol_audit": frozen.get("plan_audit", {}).get("pass") is True,
        "run_id_consistent": len({str(row.get("run_id")) for row in records}) == 1
        and next(iter({str(row.get("run_id")) for row in records}), None)
        == str(manifest.get("run_id")),
    }
    return {
        "pass": all(checks.values()),
        "checks": checks,
        "schedule_audit": schedule_audit,
        "n_records": len(records),
        "expected_mode": expected_mode,
    }


def _eligible_triads(
    bank: V6TriadBank,
    semantic_validation: Mapping[str, Any],
    quality_validation: Mapping[str, Any],
) -> set:
    for name, result in (
        ("semantic", semantic_validation),
        ("quality", quality_validation),
    ):
        if result.get("pass") is not True:
            raise ValueError("V6 %s validation did not pass" % name)
        if result.get("pool_sha256") != bank.sha256():
            raise ValueError("V6 %s validation pool hash mismatch" % name)
    semantic = {str(value) for value in semantic_validation.get("eligible_triad_ids", [])}
    quality = {str(value) for value in quality_validation.get("eligible_triad_ids", [])}
    eligible = semantic & quality
    if not eligible:
        raise ValueError("V6 validation contains no jointly eligible triads")
    return eligible


def _frame_summary(rows: Iterable[Mapping[str, Any]]) -> Dict[str, Any]:
    rows = list(rows)
    counts = Counter(str(row["selected_frame"]) for row in rows)
    shares = {
        frame: counts.get(frame, 0) / float(len(rows)) if rows else float("nan")
        for frame in STRATEGIES
    }
    return {
        "n": len(rows),
        "counts": dict(counts),
        "shares": shares,
        "gap": max(shares.values()) - min(shares.values()) if rows else float("nan"),
    }


def _passes(summary: Mapping[str, Any], thresholds: Mapping[str, float], cv: bool) -> bool:
    prefix = "cross_validation_" if cv else ""
    low = float(thresholds[prefix + "minimum_frame_share"])
    high = float(thresholds[prefix + "maximum_frame_share"])
    gap = float(thresholds[prefix + "maximum_frame_gap"])
    return bool(summary["n"]) and all(
        low <= float(value) <= high for value in summary["shares"].values()
    ) and float(summary["gap"]) <= gap


def _best_subset(
    rows: Sequence[Mapping[str, Any]],
    ids: Sequence[str],
    n_select: int,
    thresholds: Mapping[str, float],
    cv_thresholds: bool,
) -> Tuple[Tuple[str, ...], Dict[str, Any]]:
    best_objective = None
    best_choice: Optional[Tuple[str, ...]] = None
    best_summary: Optional[Dict[str, Any]] = None
    for chosen in itertools.combinations(sorted(ids), n_select):
        chosen_set = set(chosen)
        summary = _frame_summary(
            row for row in rows if str(row["triad_id"]) in chosen_set
        )
        passed = _passes(summary, thresholds, cv=cv_thresholds)
        distances = [
            abs(float(value) - 1.0 / 3.0)
            for value in summary["shares"].values()
        ]
        objective = (
            0 if passed else 1,
            float(summary["gap"]),
            max(distances),
            sum(distances),
            chosen,
        )
        if best_objective is None or objective < best_objective:
            best_objective = objective
            best_choice = chosen
            best_summary = {**summary, "pass": passed}
    assert best_choice is not None and best_summary is not None
    return best_choice, {
        "selected_triad_ids": list(best_choice),
        "summary": best_summary,
        "objective": {
            "fail_indicator": int(best_objective[0]),
            "frame_gap": float(best_objective[1]),
            "maximum_distance_from_one_third": float(best_objective[2]),
            "sum_distance_from_one_third": float(best_objective[3]),
            "lexical_tie_break": list(best_choice),
        },
    }


def _select_split(
    records: Sequence[Mapping[str, Any]],
    eligible_ids: set,
    split: str,
    n_select: int,
    thresholds: Mapping[str, float],
) -> Tuple[Optional[Tuple[str, ...]], Dict[str, Any]]:
    rows = [row for row in records if str(row["split"]) == split]
    by_triad: Dict[str, List[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        by_triad[str(row["triad_id"])].append(row)
    ids = sorted(set(by_triad) & eligible_ids)
    if len(ids) < n_select:
        raise ValueError("not enough jointly eligible V6 triads in %s" % split)
    expected_exposures = int(thresholds["minimum_triad_exposures"])
    if any(len(by_triad[triad_id]) < expected_exposures for triad_id in ids):
        raise ValueError("insufficient V6 triad calibration exposure in %s" % split)

    # Genuine cross-validation: each fold selects from the twelve training
    # scenarios, then evaluates that selected subset only on the untouched pair.
    folds: Dict[str, Dict[str, Any]] = {}
    for fold_index, heldout_pair in enumerate(V6_CALIBRATION_FOLDS):
        heldout = set(heldout_pair)
        train_rows = [
            row for row in rows if str(row["scenario"]["id"]) not in heldout
        ]
        test_rows = [
            row for row in rows if str(row["scenario"]["id"]) in heldout
        ]
        fold_choice, training = _best_subset(
            train_rows, ids, n_select, thresholds, cv_thresholds=False
        )
        fold_set = set(fold_choice)
        test_summary = _frame_summary(
            row for row in test_rows if str(row["triad_id"]) in fold_set
        )
        test_summary["pass"] = _passes(test_summary, thresholds, cv=True)
        fold_key = "fold_%02d" % fold_index
        folds[fold_key] = {
            "heldout_scenario_ids": list(heldout_pair),
            "training_scenario_ids": sorted(
                {str(row["scenario"]["id"]) for row in train_rows}
            ),
            "selected_on_training": training,
            "heldout_evaluation": test_summary,
            "no_heldout_rows_in_selection": not any(
                str(row["scenario"]["id"]) in heldout for row in train_rows
            ),
            "pass": bool(test_summary["pass"]),
        }
    cv_pass = all(fold["pass"] for fold in folds.values())
    final_choice, final_selection = _best_subset(
        rows, ids, n_select, thresholds, cv_thresholds=False
    )
    support_pass = bool(final_selection["summary"]["pass"] and cv_pass)
    payload = {
        "selected_triad_ids": list(final_choice),
        "aggregate": final_selection["summary"],
        "selection_objective": final_selection["objective"],
        "cross_validation": folds,
        "cross_validation_pass": cv_pass,
        "worst_heldout_pair_gap": max(
            float(fold["heldout_evaluation"]["gap"]) for fold in folds.values()
        ),
        "support_pass": support_pass,
    }
    return (final_choice if support_pass else None, payload)


def select_v6_bank(
    bank: V6TriadBank,
    calibration_records: Sequence[Mapping[str, Any]],
    semantic_validation: Mapping[str, Any],
    quality_validation: Mapping[str, Any],
    thresholds: Optional[Mapping[str, float]] = None,
) -> Tuple[Optional[Dict[str, Any]], Dict[str, Any]]:
    thresholds = dict(thresholds or CONTROLLED_V6_CALIBRATION_THRESHOLDS)
    eligible = _eligible_triads(bank, semantic_validation, quality_validation)
    selections: Dict[str, Optional[Tuple[str, ...]]] = {}
    metrics: Dict[str, Any] = {}
    for split, count_key in (
        ("development", "development_triads_selected"),
        ("heldout", "heldout_triads_selected"),
    ):
        selection, metric = _select_split(
            calibration_records,
            eligible,
            split,
            int(thresholds[count_key]),
            thresholds,
        )
        selections[split] = selection
        metrics[split] = metric
    semantic_hash = canonical_sha256(semantic_validation)
    quality_hash = canonical_sha256(quality_validation)
    support_pass = all(value is not None for value in selections.values())
    report: Dict[str, Any] = {
        "status": (
            "selected bank requires one separate target-free validation"
            if support_pass
            else "STOP: V6 calibration support gate failed"
        ),
        "support_pass": support_pass,
        "source_pool_sha256": bank.sha256(),
        "source_pool_content_sha256": bank_content_sha256(bank.payload),
        "semantic_validation_sha256": semantic_hash,
        "quality_validation_sha256": quality_hash,
        "jointly_eligible_triad_ids": sorted(eligible),
        "selection_metrics": metrics,
        "thresholds": thresholds,
    }
    if not support_pass:
        return None, report
    selected_splits: Dict[str, List[Dict[str, Any]]] = {}
    for split in ("development", "heldout"):
        wanted = set(selections[split] or ())
        selected_splits[split] = [
            json.loads(json.dumps(triad))
            for triad in _triads(bank, split)
            if str(triad["triad_id"]) in wanted
        ]
    output: Dict[str, Any] = {
        "pool_id": "%s-selected" % bank.payload["pool_id"],
        "status": "selected_bank_pending_no_history_validation",
        "candidate_text_authored_before_v6_focal_calibration": True,
        "source_pool_sha256": bank.sha256(),
        "source_pool_content_sha256": bank_content_sha256(bank.payload),
        "semantic_validation_sha256": semantic_hash,
        "quality_validation_sha256": quality_hash,
        "selection_method": (
            "whole-triad exhaustive subset search with seven two-scenario "
            "cross-validation folds and final selection on all calibration scenarios"
        ),
        "selection_thresholds": thresholds,
        "splits": selected_splits,
    }
    audit = audit_v6_bank_payload(output)
    if not audit["pass"]:
        raise RuntimeError("selected V6 bank failed structural audit")
    report["selected_bank_sha256"] = canonical_sha256(output)
    report["selected_bank_content_sha256"] = bank_content_sha256(output)
    return output, report


def evaluate_v6_bank_validation(
    records: Sequence[Mapping[str, Any]],
    bank: V6TriadBank,
    thresholds: Optional[Mapping[str, float]] = None,
) -> Dict[str, Any]:
    thresholds = dict(thresholds or CONTROLLED_V6_CALIBRATION_THRESHOLDS)
    records = list(records)
    if not records:
        raise ValueError("selected-bank validation records are empty")
    if any(row.get("pool_sha256") != bank.sha256() for row in records):
        raise ValueError("selected-bank validation hash mismatch")
    if any(not row.get("selection_valid") or row.get("fallback_used") for row in records):
        raise ValueError("selected-bank validation contains invalid or fallback choices")
    section_rows = {
        "overall": records,
        "development": [row for row in records if row["split"] == "development"],
        "heldout": [row for row in records if row["split"] == "heldout"],
    }
    sections: Dict[str, Dict[str, Any]] = {}
    for name, part in section_rows.items():
        summary = _frame_summary(part)
        summary["pass"] = _passes(summary, thresholds, cv=False)
        sections[name] = summary

    folds: Dict[str, Dict[str, Any]] = {}
    for fold_index, scenario_pair in enumerate(V6_VALIDATION_FOLDS):
        pair = set(scenario_pair)
        fold_sections: Dict[str, Any] = {}
        for name, part in section_rows.items():
            summary = _frame_summary(
                row for row in part if str(row["scenario"]["id"]) in pair
            )
            summary["pass"] = _passes(summary, thresholds, cv=True)
            fold_sections[name] = summary
        folds["fold_%02d" % fold_index] = {
            "scenario_ids": list(scenario_pair),
            "sections": fold_sections,
            "pass": all(summary["pass"] for summary in fold_sections.values()),
        }

    scenario_ids = sorted({str(row["scenario"]["id"]) for row in records})
    n_boot = int(thresholds["bootstrap_resamples"])
    confidence = float(thresholds["bootstrap_confidence"])
    bootstrap_seed = int(thresholds["bootstrap_seed"])
    generator = np.random.default_rng(
        derive_seed("v6_validation_bootstrap", bootstrap_seed, bank.sha256())
    )
    bootstrap: Dict[str, Any] = {}
    alpha = 1.0 - confidence
    for name, part in section_rows.items():
        by_scenario: Dict[str, List[Mapping[str, Any]]] = defaultdict(list)
        for row in part:
            by_scenario[str(row["scenario"]["id"])].append(row)
        share_draws = {frame: np.empty(n_boot, dtype=float) for frame in STRATEGIES}
        gap_draws = np.empty(n_boot, dtype=float)
        for index in range(n_boot):
            sampled = generator.choice(scenario_ids, size=len(scenario_ids), replace=True)
            summary = _frame_summary(
                row for scenario_id in sampled for row in by_scenario[str(scenario_id)]
            )
            for frame in STRATEGIES:
                share_draws[frame][index] = float(summary["shares"][frame])
            gap_draws[index] = float(summary["gap"])
        intervals = {
            frame: {
                "lo": float(np.quantile(values, alpha / 2.0)),
                "hi": float(np.quantile(values, 1.0 - alpha / 2.0)),
            }
            for frame, values in share_draws.items()
        }
        gap_quantile = float(np.quantile(gap_draws, confidence))
        passed = all(
            interval["lo"] >= float(thresholds["minimum_frame_share"])
            and interval["hi"] <= float(thresholds["maximum_frame_share"])
            for interval in intervals.values()
        ) and gap_quantile <= float(thresholds["maximum_frame_gap"])
        bootstrap[name] = {
            "n_resamples": n_boot,
            "confidence": confidence,
            "bootstrap_seed": bootstrap_seed,
            "cluster": "scenario_id",
            "frame_share_intervals": intervals,
            "gap_confidence_quantile": gap_quantile,
            "pass": bool(passed),
        }

    block_counts: Dict[Tuple[str, str], Counter] = defaultdict(Counter)
    for row in records:
        block_counts[(str(row["scenario"]["id"]), str(row["triad_id"]))][
            str(row["selected_frame"])
        ] += 1
    nontrivial_blocks = sum(
        max(counts.values(), default=0) >= 3 for counts in block_counts.values()
    )
    nontrivial_fraction = nontrivial_blocks / float(len(block_counts))
    anti_triviality = {
        "definition": "a scenario-by-triad block selects one frame in at least three of six slot permutations",
        "n_blocks": len(block_counts),
        "n_nontrivial_blocks": nontrivial_blocks,
        "fraction": nontrivial_fraction,
        "minimum_fraction": float(thresholds["minimum_nontrivial_block_fraction"]),
        "pass": nontrivial_fraction
        >= float(thresholds["minimum_nontrivial_block_fraction"]),
    }
    overall_pass = (
        all(section["pass"] for section in sections.values())
        and all(fold["pass"] for fold in folds.values())
        and all(section["pass"] for section in bootstrap.values())
        and anti_triviality["pass"]
    )
    return {
        "pass": bool(overall_pass),
        "status": "selected-bank target-free independent validation",
        "bank_sha256": bank.sha256(),
        "bank_content_sha256": bank_content_sha256(bank.payload),
        "thresholds": thresholds,
        "sections": sections,
        "validation_scenario_pair_folds": folds,
        "scenario_cluster_bootstrap": bootstrap,
        "anti_triviality": anti_triviality,
    }


def finalize_validated_v6_bank(
    pending_payload: Mapping[str, Any], validation: Mapping[str, Any]
) -> Dict[str, Any]:
    pending = json.loads(json.dumps(pending_payload))
    pending_hash = canonical_sha256(pending)
    if validation.get("pass") is not True:
        raise ValueError("cannot finalize a V6 bank whose validation failed")
    if validation.get("bank_sha256") != pending_hash:
        raise ValueError("V6 validation does not refer to this pending bank")
    if validation.get("bank_content_sha256") != bank_content_sha256(pending):
        raise ValueError("V6 validation candidate content hash mismatch")
    pending["status"] = "selected_bank_validated"
    pending["no_history_validation"] = {
        "pending_bank_sha256": pending_hash,
        "validation_sha256": canonical_sha256(validation),
        "sections": validation["sections"],
        "thresholds": validation["thresholds"],
    }
    audit = audit_v6_bank_payload(pending)
    if not audit["pass"]:
        raise RuntimeError("finalized V6 bank failed structural audit")
    return pending
