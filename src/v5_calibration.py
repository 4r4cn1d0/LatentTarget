"""Target-free focal calibration and deterministic V5 bank selection."""

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
    CONTROLLED_V5_CALIBRATION_THRESHOLDS,
    CONTROLLED_V5_VERSION,
    STRATEGIES,
)
from .controlled_focal_agent import (
    build_controlled_prompt,
    parse_controlled_choice,
)
from .controlled_analysis import _mean
from .controlled_messages import MessageCandidate, candidate_for_slot
from .controlled_v5_messages import V5MessageBank, audit_v5_bank_payload
from .focal_agent import BaseProvider, ProviderError
from .logging_utils import JsonlWriter, write_manifest
from .scenarios import scenario_sequence
from .seeding import derive_seed, rng


V5_CALIBRATION_VERSION = "v5-bank-calibration-1.0"


def _canonical_sha256(payload: Any) -> str:
    canonical = json.dumps(
        payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _file_sha256(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def bank_content_sha256(payload: Mapping[str, Any]) -> str:
    """Hash candidate IDs/text only, stable across validation metadata updates."""
    return _canonical_sha256(payload.get("splits", {}))


def _calibration_coordinates(
    n_episode_blocks: int, n_rounds: int, heldout_start_round: int
) -> Dict[str, List[Tuple[int, int]]]:
    coordinates = {"development": [], "heldout": []}
    for episode_index in range(n_episode_blocks):
        for round_index in range(1, n_rounds + 1):
            split = "heldout" if round_index >= heldout_start_round else "development"
            coordinates[split].append((episode_index, round_index))
    return coordinates


def build_v5_calibration_schedule(
    bank: V5MessageBank,
    n_episode_blocks: int = 24,
    n_rounds: int = 24,
    heldout_start_round: int = 19,
    seed: int = 20261001,
) -> List[Dict[str, Any]]:
    """Create equal candidate exposure and exact candidate-by-slot balance."""
    if n_episode_blocks < 1 or n_rounds < 2:
        raise ValueError("calibration episode blocks and rounds must be positive")
    if not 1 < heldout_start_round <= n_rounds:
        raise ValueError("heldout_start_round must be inside calibration episodes")
    coordinates = _calibration_coordinates(
        n_episode_blocks, n_rounds, heldout_start_round
    )
    assignments: Dict[Tuple[str, str, int, int], Mapping[str, str]] = {}
    slot_assignments: Dict[Tuple[str, str, int, int], int] = {}
    for split, split_coordinates in coordinates.items():
        n_split = len(split_coordinates)
        bank_split = bank.payload["splits"][split]
        for frame_index, frame in enumerate(STRATEGIES):
            entries: Sequence[Mapping[str, str]] = bank_split[frame]
            if n_split % len(entries) != 0:
                raise ValueError(
                    "%s calibration rounds (%d) must divide evenly across %s candidates (%d)"
                    % (split, n_split, frame, len(entries))
                )
            exposures = n_split // len(entries)
            if exposures % len(STRATEGIES) != 0:
                raise ValueError(
                    "each calibration candidate exposure count must divide across three slots"
                )

            positions_by_slot: Dict[int, List[int]] = defaultdict(list)
            base = list(
                rng("v5_calibration_slot_base", seed, split).permutation(
                    len(STRATEGIES)
                )
            )
            for position in range(n_split):
                rotation = position % len(STRATEGIES)
                order = base[rotation:] + base[:rotation]
                frame_order = [STRATEGIES[int(index)] for index in order]
                positions_by_slot[frame_order.index(frame) + 1].append(position)

            for slot, positions in positions_by_slot.items():
                template_indices = list(
                    itertools.chain.from_iterable(
                        [index] * (exposures // len(STRATEGIES))
                        for index in range(len(entries))
                    )
                )
                generator = rng(
                    "v5_calibration_template_order", seed, split, frame, slot
                )
                template_indices = list(generator.permutation(template_indices))
                if len(template_indices) != len(positions):
                    raise RuntimeError("internal V5 calibration balance error")
                for position, template_index in zip(positions, template_indices):
                    episode_index, round_index = split_coordinates[position]
                    key = (split, frame, episode_index, round_index)
                    assignments[key] = entries[int(template_index)]
                    slot_assignments[key] = slot

    scenarios = {
        episode_index: scenario_sequence(episode_index, n_rounds, seed)
        for episode_index in range(n_episode_blocks)
    }
    rows: List[Dict[str, Any]] = []
    pool_hash = bank.sha256()
    for episode_index in range(n_episode_blocks):
        for round_index in range(1, n_rounds + 1):
            split = "heldout" if round_index >= heldout_start_round else "development"
            scenario = scenarios[episode_index][round_index - 1]
            candidates: List[Dict[str, Any]] = []
            for frame in STRATEGIES:
                key = (split, frame, episode_index, round_index)
                entry = assignments[key]
                slot = slot_assignments[key]
                text = str(entry["template"]).format(a=scenario.option_a)
                candidates.append(
                    {
                        "slot": slot,
                        "pool_candidate_id": str(entry["candidate_id"]),
                        "candidate_id": "%s-%s" % (entry["candidate_id"], scenario.id),
                        "message": " ".join(text.split()),
                        "frame": frame,
                        "split": split,
                    }
                )
            candidates.sort(key=lambda candidate: int(candidate["slot"]))
            rows.append(
                {
                    "calibration_version": V5_CALIBRATION_VERSION,
                    "pool_sha256": pool_hash,
                    "episode_index": episode_index,
                    "round": round_index,
                    "n_rounds": n_rounds,
                    "heldout_start_round": heldout_start_round,
                    "split": split,
                    "scenario": scenario.as_dict(),
                    "candidates": candidates,
                    "generation_seed": derive_seed(
                        V5_CALIBRATION_VERSION,
                        seed,
                        episode_index,
                        round_index,
                    ),
                }
            )
    audit = audit_v5_calibration_schedule(rows, bank)
    if not audit["pass"]:
        failed = sorted(name for name, passed in audit["checks"].items() if not passed)
        raise RuntimeError("generated V5 calibration schedule failed: %s" % ", ".join(failed))
    return rows


def audit_v5_calibration_schedule(
    rows: Sequence[Mapping[str, Any]], bank: V5MessageBank
) -> Dict[str, Any]:
    rows = list(rows)
    pool_ids = {
        str(entry["candidate_id"])
        for split in bank.payload["splits"].values()
        for entries in split.values()
        for entry in entries
    }
    exposure: Counter = Counter()
    candidate_slots: Dict[str, Counter] = defaultdict(Counter)
    coordinate_keys = set()
    complete = True
    for row in rows:
        key = (int(row["episode_index"]), int(row["round"]))
        if key in coordinate_keys:
            complete = False
        coordinate_keys.add(key)
        candidates = row.get("candidates", [])
        complete &= (
            len(candidates) == 3
            and {str(candidate["frame"]) for candidate in candidates} == set(STRATEGIES)
            and {int(candidate["slot"]) for candidate in candidates} == {1, 2, 3}
        )
        for candidate in candidates:
            candidate_id = str(candidate["pool_candidate_id"])
            exposure[candidate_id] += 1
            candidate_slots[candidate_id][int(candidate["slot"])] += 1
    exposure_values = [exposure[candidate_id] for candidate_id in sorted(pool_ids)]
    checks = {
        "nonempty": bool(rows),
        "unique_coordinates": len(coordinate_keys) == len(rows),
        "complete_candidate_sets": complete,
        "exact_pool_membership": set(exposure) == pool_ids,
        "equal_candidate_exposure_within_split": all(
            len(
                {
                    exposure[str(entry["candidate_id"])]
                    for frame in STRATEGIES
                    for entry in bank.payload["splits"][split][frame]
                }
            )
            == 1
            for split in ("development", "heldout")
        ),
        "candidate_slot_balance": all(
            set(candidate_slots[candidate_id]) == {1, 2, 3}
            and len(set(candidate_slots[candidate_id].values())) == 1
            for candidate_id in pool_ids
        ),
        "pool_hash": all(row.get("pool_sha256") == bank.sha256() for row in rows),
    }
    return {
        "pass": all(checks.values()),
        "checks": checks,
        "n_rows": len(rows),
        "candidate_exposures": dict(exposure),
        "minimum_candidate_exposure": min(exposure_values) if exposure_values else 0,
        "candidate_slot_counts": {
            candidate_id: dict(counts) for candidate_id, counts in candidate_slots.items()
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


def run_v5_no_history_calibration(
    bank: V5MessageBank,
    provider: BaseProvider,
    run_id: str,
    out_dir: str,
    n_episode_blocks: int = 24,
    n_rounds: int = 24,
    heldout_start_round: int = 19,
    seed: int = 20261001,
    mode: str = "pool_calibration",
    provenance: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    """Run target-free no-history prompts; no simulator or feedback is present."""
    if mode not in {"pool_calibration", "selected_bank_validation"}:
        raise ValueError("unknown V5 calibration mode %r" % mode)
    schedule = build_v5_calibration_schedule(
        bank,
        n_episode_blocks=n_episode_blocks,
        n_rounds=n_rounds,
        heldout_start_round=heldout_start_round,
        seed=seed,
    )
    os.makedirs(out_dir, exist_ok=True)
    log_path = os.path.join(out_dir, run_id + ".jsonl")
    manifest_path = os.path.join(out_dir, run_id + ".manifest.json")
    if os.path.exists(log_path) or os.path.exists(manifest_path):
        raise FileExistsError("refusing to overwrite V5 calibration run %r" % run_id)
    manifest = {
        "calibration_version": V5_CALIBRATION_VERSION,
        "task_version": CONTROLLED_V5_VERSION,
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
            "n_episode_blocks": n_episode_blocks,
            "n_rounds": n_rounds,
            "heldout_start_round": heldout_start_round,
            "seed": seed,
            "n_records": len(schedule),
        },
        "schedule_audit": audit_v5_calibration_schedule(schedule, bank),
    }
    if provenance is not None:
        manifest["frozen_protocol"] = json.loads(json.dumps(provenance))
    write_manifest(manifest_path, manifest)
    records: List[Dict[str, Any]] = []
    with JsonlWriter(log_path, validate=False) as writer:
        for schedule_row in schedule:
            candidates = _message_candidates(schedule_row)
            scenario_dict = schedule_row["scenario"]

            class _Scenario:
                id = scenario_dict["id"]
                title = scenario_dict["title"]
                context = scenario_dict["context"]
                option_a = scenario_dict["option_a"]
                option_b = scenario_dict["option_b"]

                @classmethod
                def render(cls):
                    return (
                        "Decision: %s\n%s\nOption A: %s\nOption B: %s"
                        % (cls.title, cls.context, cls.option_a, cls.option_b)
                    )

            prompt = build_controlled_prompt(
                scenario=_Scenario,
                candidates=candidates,
                history=[],
                round_index=int(schedule_row["round"]),
                n_rounds=n_rounds,
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
                    "V5 calibration requires an exact constrained choice; got %r" % raw
                )
            selected = candidate_for_slot(candidates, parsed.selected_slot)
            source = next(
                candidate for candidate in schedule_row["candidates"]
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
    manifest["log_file_sha256"] = _file_sha256(log_path)
    write_manifest(manifest_path, manifest)
    return {
        "records": records,
        "manifest": manifest,
        "log_path": log_path,
        "manifest_path": manifest_path,
    }


def audit_v5_calibration_run(
    records: Sequence[Mapping[str, Any]],
    manifest: Mapping[str, Any],
    bank: V5MessageBank,
    expected_mode: str,
) -> Dict[str, Any]:
    """Verify a completed calibration/validation artifact before consuming it."""
    records = list(records)
    schedule_audit = audit_v5_calibration_schedule(records, bank)
    frozen = manifest.get("frozen_protocol", {})
    checks = {
        "nonempty": bool(records),
        "completed": manifest.get("run_status") == "completed",
        "task_version": manifest.get("task_version") == CONTROLLED_V5_VERSION,
        "calibration_version": manifest.get("calibration_version")
        == V5_CALIBRATION_VERSION,
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
        "provider_constrained": manifest.get("provider", {}).get(
            "constrained_choices"
        )
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


def build_blind_semantic_samples(
    bank: V5MessageBank, seed: int = 20261001
) -> Tuple[List[Dict[str, str]], Dict[str, Dict[str, str]]]:
    visible: List[Dict[str, str]] = []
    key: Dict[str, Dict[str, str]] = {}
    for split, split_bank in bank.payload["splits"].items():
        for frame, entries in split_bank.items():
            for entry in entries:
                sample_id = hashlib.sha256(
                    (bank.sha256() + str(entry["candidate_id"])).encode("utf-8")
                ).hexdigest()[:16]
                visible.append(
                    {
                        "sample_id": sample_id,
                        "message": str(entry["template"]).format(a="Option A"),
                    }
                )
                key[sample_id] = {
                    "candidate_id": str(entry["candidate_id"]),
                    "intended_frame": str(frame),
                    "split": str(split),
                }
    order = rng("v5_blind_semantic_order", seed, bank.sha256()).permutation(len(visible))
    return [visible[int(index)] for index in order], key


def _semantic_eligible_ids(
    semantic_validation: Mapping[str, Any], bank: V5MessageBank
) -> set:
    if semantic_validation.get("pass") is not True:
        raise ValueError("V5 semantic validation did not pass")
    if semantic_validation.get("pool_sha256") != bank.sha256():
        raise ValueError("semantic validation pool hash mismatch")
    eligible = {str(value) for value in semantic_validation.get("eligible_candidate_ids", [])}
    if not eligible:
        raise ValueError("semantic validation contains no eligible candidates")
    return eligible


def _candidate_rates(
    records: Sequence[Mapping[str, Any]], bank: V5MessageBank
) -> Dict[str, Dict[str, Any]]:
    exposures: Counter = Counter()
    selections: Counter = Counter()
    metadata: Dict[str, Tuple[str, str]] = {}
    for split, split_bank in bank.payload["splits"].items():
        for frame, entries in split_bank.items():
            for entry in entries:
                metadata[str(entry["candidate_id"])] = (split, frame)
    for row in records:
        if row.get("pool_sha256") != bank.sha256():
            raise ValueError("calibration record pool hash mismatch")
        if not row.get("selection_valid") or row.get("fallback_used"):
            raise ValueError("calibration records must contain only strict valid choices")
        for candidate in row["candidates"]:
            exposures[str(candidate["pool_candidate_id"])] += 1
        selections[str(row["selected_pool_candidate_id"])] += 1
    return {
        candidate_id: {
            "candidate_id": candidate_id,
            "split": metadata[candidate_id][0],
            "frame": metadata[candidate_id][1],
            "exposures": exposures[candidate_id],
            "selections": selections[candidate_id],
            "selection_rate": (
                selections[candidate_id] / float(exposures[candidate_id])
                if exposures[candidate_id] else float("nan")
            ),
        }
        for candidate_id in metadata
    }


def _select_balanced_entries(
    entries_by_frame: Mapping[str, Sequence[Mapping[str, Any]]], n_select: int
) -> Tuple[Dict[str, List[Mapping[str, Any]]], Dict[str, Any]]:
    combinations = {
        frame: list(itertools.combinations(entries_by_frame[frame], n_select))
        for frame in STRATEGIES
    }
    if any(not values for values in combinations.values()):
        raise ValueError("not enough semantically eligible candidates for V5 selection")
    best = None
    best_selection = None
    for fairness, risk, expertise in itertools.product(
        combinations["fairness"], combinations["risk"], combinations["expertise"]
    ):
        selected = {
            "fairness": fairness,
            "risk": risk,
            "expertise": expertise,
        }
        means = {
            frame: _mean(entry["selection_rate"] for entry in selected[frame])
            for frame in STRATEGIES
        }
        objective = (
            max(means.values()) - min(means.values()),
            max(abs(value - 1.0 / 3.0) for value in means.values()),
            sum(abs(value - 1.0 / 3.0) for value in means.values()),
            tuple(
                tuple(entry["candidate_id"] for entry in selected[frame])
                for frame in STRATEGIES
            ),
        )
        if best is None or objective < best:
            best = objective
            best_selection = selected
    assert best_selection is not None
    return (
        {frame: list(best_selection[frame]) for frame in STRATEGIES},
        {
            "predicted_frame_means": {
                frame: _mean(
                    entry["selection_rate"] for entry in best_selection[frame]
                )
                for frame in STRATEGIES
            },
            "objective": {
                "predicted_frame_gap": float(best[0]),
                "maximum_distance_from_one_third": float(best[1]),
                "sum_distance_from_one_third": float(best[2]),
            },
        },
    )


def select_v5_bank(
    bank: V5MessageBank,
    calibration_records: Sequence[Mapping[str, Any]],
    semantic_validation: Mapping[str, Any],
    thresholds: Optional[Mapping[str, float]] = None,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    thresholds = dict(thresholds or CONTROLLED_V5_CALIBRATION_THRESHOLDS)
    eligible = _semantic_eligible_ids(semantic_validation, bank)
    rates = _candidate_rates(calibration_records, bank)
    minimum_exposures = int(thresholds["minimum_candidate_exposures"])
    insufficient = [
        candidate_id for candidate_id, row in rates.items()
        if candidate_id in eligible and int(row["exposures"]) < minimum_exposures
    ]
    if insufficient:
        raise ValueError("insufficient candidate calibration exposure: %s" % insufficient)

    selected_payload: Dict[str, Dict[str, List[Dict[str, str]]]] = {
        "development": {}, "heldout": {}
    }
    selection_metrics: Dict[str, Any] = {}
    for split in ("development", "heldout"):
        eligible_by_frame: Dict[str, List[Dict[str, Any]]] = {}
        for frame in STRATEGIES:
            eligible_by_frame[frame] = [
                rates[str(entry["candidate_id"])]
                for entry in bank.payload["splits"][split][frame]
                if str(entry["candidate_id"]) in eligible
            ]
        n_select = int(
            thresholds[
                "%s_templates_selected_per_frame"
                % ("development" if split == "development" else "heldout")
            ]
        )
        chosen, metrics = _select_balanced_entries(eligible_by_frame, n_select)
        selection_metrics[split] = metrics
        for frame in STRATEGIES:
            chosen_ids = {entry["candidate_id"] for entry in chosen[frame]}
            selected_payload[split][frame] = [
                dict(entry)
                for entry in bank.payload["splits"][split][frame]
                if str(entry["candidate_id"]) in chosen_ids
            ]

    semantic_hash = _canonical_sha256(semantic_validation)
    output = {
        "pool_id": "%s-selected" % bank.payload["pool_id"],
        "status": "selected_bank_pending_no_history_validation",
        "created_before_v5_focal_calibration": True,
        "source_pool_sha256": bank.sha256(),
        "source_pool_content_sha256": bank_content_sha256(bank.payload),
        "semantic_validation_sha256": semantic_hash,
        "selection_method": (
            "exhaustive subset search minimizing empirical frame-rate gap, then "
            "distance from one third; lexical candidate ID tie-break"
        ),
        "selection_thresholds": thresholds,
        "splits": selected_payload,
    }
    bank_audit = audit_v5_bank_payload(output)
    if not bank_audit["pass"]:
        raise RuntimeError("selected V5 bank failed structural audit")
    report = {
        "status": "selected bank requires a separate no-history validation run",
        "source_pool_sha256": bank.sha256(),
        "selected_bank_sha256": _canonical_sha256(output),
        "selected_bank_content_sha256": bank_content_sha256(output),
        "semantic_validation_sha256": semantic_hash,
        "candidate_rates": rates,
        "selection_metrics": selection_metrics,
        "thresholds": thresholds,
    }
    return output, report


def evaluate_v5_bank_validation(
    records: Sequence[Mapping[str, Any]],
    bank: V5MessageBank,
    thresholds: Optional[Mapping[str, float]] = None,
) -> Dict[str, Any]:
    thresholds = dict(thresholds or CONTROLLED_V5_CALIBRATION_THRESHOLDS)
    records = list(records)
    if not records:
        raise ValueError("selected-bank validation records are empty")
    if any(row.get("pool_sha256") != bank.sha256() for row in records):
        raise ValueError("selected-bank validation hash mismatch")
    if any(not row.get("selection_valid") or row.get("fallback_used") for row in records):
        raise ValueError("selected-bank validation contains invalid or fallback choices")

    def summarize(part: Iterable[Mapping[str, Any]]) -> Dict[str, Any]:
        part = list(part)
        counts = Counter(str(row["selected_frame"]) for row in part)
        shares = {
            frame: counts.get(frame, 0) / float(len(part)) if part else float("nan")
            for frame in STRATEGIES
        }
        gap = max(shares.values()) - min(shares.values()) if part else float("nan")
        passed = bool(part) and all(
            thresholds["minimum_frame_share"] <= value
            <= thresholds["maximum_frame_share"]
            for value in shares.values()
        ) and gap <= thresholds["maximum_frame_gap"]
        return {"n": len(part), "counts": dict(counts), "shares": shares, "gap": gap, "pass": passed}

    sections = {
        "overall": summarize(records),
        "development": summarize(
            row for row in records if row["split"] == "development"
        ),
        "heldout": summarize(row for row in records if row["split"] == "heldout"),
    }
    return {
        "pass": all(section["pass"] for section in sections.values()),
        "status": "selected-bank no-history validation",
        "bank_sha256": bank.sha256(),
        "bank_content_sha256": bank_content_sha256(bank.payload),
        "thresholds": thresholds,
        "sections": sections,
    }


def finalize_validated_v5_bank(
    pending_payload: Mapping[str, Any], validation: Mapping[str, Any]
) -> Dict[str, Any]:
    pending = json.loads(json.dumps(pending_payload))
    pending_bank_hash = _canonical_sha256(pending)
    if validation.get("pass") is not True:
        raise ValueError("cannot finalize a V5 bank whose validation failed")
    if validation.get("bank_sha256") != pending_bank_hash:
        raise ValueError("V5 validation does not refer to this pending bank")
    if validation.get("bank_content_sha256") != bank_content_sha256(pending):
        raise ValueError("V5 validation candidate content hash mismatch")
    pending["status"] = "selected_bank_validated"
    pending["no_history_validation"] = {
        "pending_bank_sha256": pending_bank_hash,
        "validation_sha256": _canonical_sha256(validation),
        "sections": validation["sections"],
        "thresholds": validation["thresholds"],
    }
    audit = audit_v5_bank_payload(pending)
    if not audit["pass"]:
        raise RuntimeError("finalized V5 bank failed structural audit")
    return pending
