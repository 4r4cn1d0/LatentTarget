"""Blind, two-judge semantic gate for flattened V6 triad candidates."""

from __future__ import annotations

import hashlib
import json
import math
from collections import Counter, defaultdict
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from config import (
    ALL_LABELS,
    CONTROLLED_V6_SEMANTIC_THRESHOLDS,
    STRATEGIES,
)
from .blind_judge import (
    canonical_json_sha256,
    codex_judge_contract,
    replay_codex_judge_run_from_manifest,
)
from .controlled_v6_messages import audit_v6_bank_payload
from .measurement_audit import cohens_kappa


def _pool_payload(pool: Any) -> Mapping[str, Any]:
    payload = pool if isinstance(pool, Mapping) else getattr(pool, "payload", None)
    if not isinstance(payload, Mapping):
        raise ValueError("V6 semantic pool must be a mapping or bank-like object")
    return payload


def _canonical_hash(payload: Mapping[str, Any]) -> str:
    canonical = json.dumps(
        payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def load_v6_semantic_pool(path: str) -> Dict[str, Any]:
    """Load a pool only after the canonical full V6 structural audit passes."""
    with open(path, "r", encoding="utf-8") as handle:
        payload = json.load(handle)
    audit = audit_v6_bank_payload(payload)
    if not audit["pass"]:
        failed = sorted(
            name for name, passed in audit["checks"].items() if not passed
        )
        raise ValueError("invalid V6 semantic pool: %s" % ", ".join(failed))
    semantic_candidate_rows(payload)
    return payload


def semantic_candidate_rows(pool: Any) -> List[Dict[str, str]]:
    """Flatten immutable triads into one target-free rendered message each.

    The returned intended frame and triad metadata are for the post-judging
    join only.  Callers must pass only ``message`` values to a blind judge.
    """
    rows: List[Dict[str, str]] = []
    triad_ids: List[str] = []
    payload = _pool_payload(pool)
    splits = payload.get("splits", {})
    if not isinstance(splits, Mapping):
        raise ValueError("V6 semantic pool has no splits mapping")
    if set(splits) != {"development", "heldout"}:
        raise ValueError("V6 semantic pool must contain exactly two registered splits")
    for split in ("development", "heldout"):
        triads = splits.get(split)
        if not isinstance(triads, list) or not triads:
            raise ValueError("V6 semantic pool has no %s triads" % split)
        for triad in triads:
            if not isinstance(triad, Mapping):
                raise ValueError("V6 semantic pool contains a malformed triad")
            triad_id = str(triad.get("triad_id", ""))
            if not triad_id:
                raise ValueError("V6 semantic pool contains an empty triad ID")
            candidates = triad.get("candidates")
            if not isinstance(candidates, Mapping) or set(candidates) != set(
                STRATEGIES
            ):
                raise ValueError(
                    "V6 semantic triad %s does not contain exactly one candidate "
                    "per intended frame" % triad_id
                )
            triad_ids.append(triad_id)
            for intended_frame in STRATEGIES:
                entry = candidates[intended_frame]
                if not isinstance(entry, Mapping):
                    raise ValueError(
                        "V6 semantic triad %s contains a malformed candidate"
                        % triad_id
                    )
                candidate_id = str(entry.get("candidate_id", ""))
                template = str(entry.get("template", ""))
                if not candidate_id or not template:
                    raise ValueError(
                        "V6 semantic triad %s contains an empty candidate ID or text"
                        % triad_id
                    )
                try:
                    rendered = template.format(a="Option A")
                except (IndexError, KeyError, ValueError) as exc:
                    raise ValueError(
                        "V6 semantic candidate %s could not be rendered"
                        % candidate_id
                    ) from exc
                rows.append(
                    {
                        "candidate_id": candidate_id,
                        "split": split,
                        "triad_id": triad_id,
                        "intended_frame": intended_frame,
                        "message": " ".join(rendered.split()),
                    }
                )
    if len(set(triad_ids)) != len(triad_ids):
        raise ValueError("V6 semantic triads contain duplicate IDs")
    if len({row["candidate_id"] for row in rows}) != len(rows):
        raise ValueError("V6 semantic candidates contain duplicate IDs")
    if len({row["message"] for row in rows}) != len(rows):
        raise ValueError("V6 semantic candidates contain duplicate rendered messages")
    return rows


def _validated_result(result: Mapping[str, Any]) -> Dict[str, Any]:
    primary = str(result.get("primary_strategy", ""))
    if primary not in ALL_LABELS:
        raise ValueError("semantic judge returned an invalid primary strategy")
    clean: Dict[str, Any] = {"primary_strategy": primary}
    for field in (*ALL_LABELS, "confidence"):
        value = result.get(field)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("semantic judge field %s is not numeric" % field)
        value = float(value)
        if not math.isfinite(value) or not 0.0 <= value <= 1.0:
            raise ValueError("semantic judge field %s is outside [0,1]" % field)
        clean[field] = value
    return clean


def _judge_metrics(
    rows: Sequence[Mapping[str, str]],
    results: Mapping[str, Mapping[str, Any]],
) -> Tuple[Dict[str, Any], Dict[str, Dict[str, Any]]]:
    expected_messages = {row["message"] for row in rows}
    if set(results) != expected_messages:
        raise ValueError("semantic judge results do not exactly cover the V6 pool")
    clean = {
        message: _validated_result(result) for message, result in results.items()
    }
    labels = [clean[row["message"]]["primary_strategy"] for row in rows]
    intended = [row["intended_frame"] for row in rows]
    recalls: Dict[str, float] = {}
    for frame in STRATEGIES:
        indices = [index for index, value in enumerate(intended) if value == frame]
        if not indices:
            raise ValueError("V6 semantic pool has no %s candidates" % frame)
        recalls[frame] = sum(labels[index] == frame for index in indices) / float(
            len(indices)
        )
    return (
        {
            "accuracy": sum(a == b for a, b in zip(intended, labels))
            / float(len(rows)),
            "recall_by_intended_frame": recalls,
            "predicted_distribution": dict(Counter(labels)),
        },
        clean,
    )


def _artifact_results_match(
    evaluator_results: Mapping[str, Mapping[str, Any]],
    artifact_audit: Mapping[str, Any],
) -> bool:
    """Require the audited canonical map/hash to equal evaluator inputs."""
    artifact_results = artifact_audit.get("result_map")
    if not isinstance(artifact_results, Mapping):
        return False
    try:
        clean_artifact = {
            str(message): _validated_result(result)
            for message, result in artifact_results.items()
            if isinstance(result, Mapping)
        }
    except (TypeError, ValueError):
        return False
    if len(clean_artifact) != len(artifact_results):
        return False
    if artifact_audit.get("result_map_sha256") != canonical_json_sha256(
        clean_artifact
    ):
        return False
    return clean_artifact == dict(evaluator_results)


def _artifact_contract_matches(
    description: Mapping[str, Any], artifact_audit: Mapping[str, Any]
) -> bool:
    """Bind an audited artifact directory to the described judge contract."""
    model = str(description.get("model", ""))
    prompt_version = str(description.get("judge_prompt_version", ""))
    if not model or artifact_audit.get("models") != [model]:
        return False
    if not prompt_version or artifact_audit.get("prompt_version") != prompt_version:
        return False
    optional_hashes = {
        "judge_prompt_sha256": "prompt_sha256",
        "judge_rubric_sha256": "rubric_sha256",
    }
    return all(
        not description.get(description_key)
        or artifact_audit.get(audit_key) == description.get(description_key)
        for description_key, audit_key in optional_hashes.items()
    )


def _candidate_pass(
    result: Mapping[str, Any],
    intended: str,
    thresholds: Mapping[str, float],
) -> Tuple[bool, Dict[str, bool], float]:
    other_scores = [float(result[label]) for label in ALL_LABELS if label != intended]
    margin = float(result[intended]) - max(other_scores)
    checks = {
        "primary_label": result["primary_strategy"] == intended,
        "confidence": float(result["confidence"])
        >= thresholds["minimum_candidate_confidence"],
        "intended_score": float(result[intended])
        >= thresholds["minimum_candidate_intended_score"],
        "score_margin": margin >= thresholds["minimum_candidate_margin"],
    }
    return all(checks.values()), checks, margin


def evaluate_v6_semantic_validation(
    pool: Any,
    primary_results: Mapping[str, Mapping[str, Any]],
    sensitivity_results: Mapping[str, Mapping[str, Any]],
    primary_description: Mapping[str, Any],
    sensitivity_description: Mapping[str, Any],
    primary_artifact_audit: Mapping[str, Any],
    sensitivity_artifact_audit: Mapping[str, Any],
    thresholds: Optional[Mapping[str, float]] = None,
) -> Dict[str, Any]:
    """Join intended frames and triad IDs after both blind calls have finished."""
    thresholds = dict(thresholds or CONTROLLED_V6_SEMANTIC_THRESHOLDS)
    payload = _pool_payload(pool)
    pool_audit = audit_v6_bank_payload(payload)
    rows = semantic_candidate_rows(payload)
    primary_metrics, primary_clean = _judge_metrics(rows, primary_results)
    sensitivity_metrics, sensitivity_clean = _judge_metrics(
        rows, sensitivity_results
    )
    primary_labels = [
        primary_clean[row["message"]]["primary_strategy"] for row in rows
    ]
    sensitivity_labels = [
        sensitivity_clean[row["message"]]["primary_strategy"] for row in rows
    ]
    raw_kappa = cohens_kappa(primary_labels, sensitivity_labels)
    kappa = raw_kappa if math.isfinite(raw_kappa) else None

    candidate_rows: List[Dict[str, Any]] = []
    by_triad: Dict[Tuple[str, str], List[Dict[str, Any]]] = defaultdict(list)
    for row in rows:
        primary = primary_clean[row["message"]]
        sensitivity = sensitivity_clean[row["message"]]
        primary_pass, primary_checks, primary_margin = _candidate_pass(
            primary, row["intended_frame"], thresholds
        )
        sensitivity_pass, sensitivity_checks, sensitivity_margin = _candidate_pass(
            sensitivity, row["intended_frame"], thresholds
        )
        result_row: Dict[str, Any] = {
            **row,
            "primary_judge": primary,
            "sensitivity_judge": sensitivity,
            "primary_checks": primary_checks,
            "sensitivity_checks": sensitivity_checks,
            "primary_margin": primary_margin,
            "sensitivity_margin": sensitivity_margin,
            "passes_both_judges": primary_pass and sensitivity_pass,
            "eligible": primary_pass and sensitivity_pass,
        }
        candidate_rows.append(result_row)
        by_triad[(row["split"], row["triad_id"])].append(result_row)

    eligible_candidate_ids = [
        row["candidate_id"] for row in candidate_rows if row["eligible"]
    ]
    eligible_triad_ids: List[str] = []
    eligible_triad_candidate_ids: List[str] = []
    eligible_counts: Counter = Counter()
    triad_rows: List[Dict[str, Any]] = []
    for (split, triad_id), members in by_triad.items():
        intended_frames = {row["intended_frame"] for row in members}
        complete = len(members) == len(STRATEGIES) and intended_frames == set(
            STRATEGIES
        )
        candidates_pass = complete and all(
            row["passes_both_judges"] for row in members
        )
        eligible = candidates_pass
        if eligible:
            eligible_triad_ids.append(triad_id)
            eligible_triad_candidate_ids.extend(
                row["candidate_id"] for row in members
            )
            eligible_counts[split] += 1
        for row in members:
            row["triad_eligible"] = eligible
        triad_rows.append(
            {
                "triad_id": triad_id,
                "split": split,
                "candidate_ids": [row["candidate_id"] for row in members],
                "complete_three_frame_triad": complete,
                "all_candidates_pass_both_judges": candidates_pass,
                "eligible": eligible,
            }
        )

    primary_model = str(primary_description.get("model", ""))
    sensitivity_model = str(sensitivity_description.get("model", ""))
    primary_artifact_results_match = _artifact_results_match(
        primary_clean, primary_artifact_audit
    )
    sensitivity_artifact_results_match = _artifact_results_match(
        sensitivity_clean, sensitivity_artifact_audit
    )
    primary_artifact_contract_match = _artifact_contract_matches(
        primary_description, primary_artifact_audit
    )
    sensitivity_artifact_contract_match = _artifact_contract_matches(
        sensitivity_description, sensitivity_artifact_audit
    )
    gates = {
        "pool_structurally_valid": bool(pool_audit.get("pass")),
        "judge_models_distinct": bool(primary_model)
        and bool(sensitivity_model)
        and primary_model != sensitivity_model,
        "both_artifact_audits_pass": bool(primary_artifact_audit.get("ok"))
        and bool(sensitivity_artifact_audit.get("ok")),
        "primary_frozen_schedule_replayed": bool(
            primary_artifact_audit.get("frozen_schedule_enforced")
        ),
        "sensitivity_frozen_schedule_replayed": bool(
            sensitivity_artifact_audit.get("frozen_schedule_enforced")
        ),
        "primary_cache_reconciled_to_raw_artifacts": bool(
            primary_artifact_audit.get("cache_reconciled")
        ),
        "sensitivity_cache_reconciled_to_raw_artifacts": bool(
            sensitivity_artifact_audit.get("cache_reconciled")
        ),
        "primary_raw_run_manifest_recorded": isinstance(
            primary_artifact_audit.get("judge_run_manifest"), Mapping
        ),
        "sensitivity_raw_run_manifest_recorded": isinstance(
            sensitivity_artifact_audit.get("judge_run_manifest"), Mapping
        ),
        "primary_artifact_contract_matches_judge": primary_artifact_contract_match,
        "sensitivity_artifact_contract_matches_judge": (
            sensitivity_artifact_contract_match
        ),
        "primary_artifact_results_match_evaluator": (
            primary_artifact_results_match
        ),
        "sensitivity_artifact_results_match_evaluator": (
            sensitivity_artifact_results_match
        ),
        "primary_accuracy": primary_metrics["accuracy"]
        >= thresholds["minimum_judge_accuracy"],
        "primary_all_class_recall": min(
            primary_metrics["recall_by_intended_frame"].values()
        )
        >= thresholds["minimum_judge_class_recall"],
        "sensitivity_accuracy": sensitivity_metrics["accuracy"]
        >= thresholds["minimum_judge_accuracy"],
        "sensitivity_all_class_recall": min(
            sensitivity_metrics["recall_by_intended_frame"].values()
        )
        >= thresholds["minimum_judge_class_recall"],
        "interjudge_kappa": kappa is not None
        and kappa >= thresholds["minimum_interjudge_kappa"],
        "enough_development_triads": eligible_counts["development"]
        >= int(thresholds["minimum_eligible_development_triads"]),
        "enough_heldout_triads": eligible_counts["heldout"]
        >= int(thresholds["minimum_eligible_heldout_triads"]),
    }
    return {
        "pass": all(gates.values()),
        "scientific_status": (
            "machine-only blind semantic manipulation gate; not human validation"
        ),
        "pool_id": str(payload.get("pool_id", "")),
        "pool_sha256": str(pool_audit.get("sha256") or _canonical_hash(payload)),
        "pool_audit": pool_audit,
        "n_triads": len(by_triad),
        "n_candidates": len(rows),
        "judge_visible_fields": ["sample_id", "message"],
        "intended_metadata_fields": ["intended_frame", "triad_id", "split"],
        "intended_metadata_supplied_to_judges": False,
        "metadata_joined_after_both_judge_calls": True,
        "intended_labels_supplied_to_judges": False,
        "intended_frames_supplied_to_judges": False,
        "triad_ids_supplied_to_judges": False,
        "thresholds_frozen_before_judging": thresholds,
        "primary_judge": dict(primary_description),
        "sensitivity_judge": dict(sensitivity_description),
        "primary_metrics": primary_metrics,
        "sensitivity_metrics": sensitivity_metrics,
        "interjudge_agreement": sum(
            a == b for a, b in zip(primary_labels, sensitivity_labels)
        )
        / float(len(rows)),
        "interjudge_kappa": kappa,
        "interjudge_kappa_defined": kappa is not None,
        "eligible_counts": {
            split: eligible_counts[split]
            for split in ("development", "heldout")
        },
        "eligible_candidate_ids": eligible_candidate_ids,
        "eligible_triad_candidate_ids": eligible_triad_candidate_ids,
        "eligible_triad_ids": eligible_triad_ids,
        "triad_results": triad_rows,
        "candidate_results": candidate_rows,
        "primary_artifact_audit": dict(primary_artifact_audit),
        "sensitivity_artifact_audit": dict(sensitivity_artifact_audit),
        "gates": gates,
    }


def audit_v6_semantic_validation_summary(
    summary: Mapping[str, Any], pool: Any, repository_root: str
) -> Dict[str, Any]:
    """Recompute the semantic gate from raw batches/caches, ignoring ``pass``.

    This is the checkpoint-facing verifier: a hand-edited summary cannot pass
    unless its two repository-local raw run manifests replay exactly and the
    complete deterministic evaluator output matches byte-independent canonical
    JSON.
    """
    if not isinstance(summary, Mapping):
        raise ValueError("semantic validation summary is not an object")
    contract = summary.get("judge_contract")
    manifests = summary.get("raw_judge_run_manifests")
    if not isinstance(contract, Mapping) or not isinstance(manifests, Mapping):
        raise ValueError("semantic summary lacks contract/raw run manifests")
    if set(manifests) != {"primary", "sensitivity"}:
        raise ValueError("semantic summary must contain exactly two run manifests")
    frozen = {
        key: contract.get(key)
        for key in (
            "models",
            "seeds",
            "batch_size",
            "prompt_version",
            "prompt_sha256",
            "rubric_sha256",
        )
    }
    if contract.get("contract_sha256") != canonical_json_sha256(frozen):
        raise ValueError("semantic summary judge contract hash mismatch")
    prompt = codex_judge_contract()
    if any(frozen.get(key) != prompt[key] for key in prompt):
        raise ValueError("semantic summary prompt contract mismatch")
    models = frozen.get("models")
    seeds = frozen.get("seeds")
    batch_size = frozen.get("batch_size")
    if (
        not isinstance(models, list)
        or len(models) != 2
        or not isinstance(seeds, list)
        or len(seeds) != 2
        or isinstance(batch_size, bool)
        or not isinstance(batch_size, int)
        or batch_size < 1
    ):
        raise ValueError("semantic summary judge contract is malformed")

    rows = semantic_candidate_rows(pool)
    messages = [row["message"] for row in rows]
    primary_replay = replay_codex_judge_run_from_manifest(
        messages, manifests["primary"], repository_root
    )
    sensitivity_replay = replay_codex_judge_run_from_manifest(
        messages, manifests["sensitivity"], repository_root
    )
    for index, (name, replay) in enumerate(
        (("primary", primary_replay), ("sensitivity", sensitivity_replay))
    ):
        manifest = replay["judge_run_manifest"]
        if (
            manifest.get("model") != models[index]
            or manifest.get("seed") != seeds[index]
            or manifest.get("batch_size") != batch_size
        ):
            raise ValueError(
                "semantic %s run differs from frozen judge contract" % name
            )

    primary_description = summary.get("primary_judge")
    sensitivity_description = summary.get("sensitivity_judge")
    if not isinstance(primary_description, Mapping) or not isinstance(
        sensitivity_description, Mapping
    ):
        raise ValueError("semantic summary judge descriptions are missing")
    recomputed = evaluate_v6_semantic_validation(
        pool,
        primary_replay["result_map"],
        sensitivity_replay["result_map"],
        primary_description,
        sensitivity_description,
        primary_replay,
        sensitivity_replay,
    )
    supplied_evaluation = {
        key: summary.get(key) for key in recomputed
    }
    if supplied_evaluation != recomputed:
        raise ValueError("semantic summary differs from raw-file recomputation")
    recomputed_sha256 = canonical_json_sha256(recomputed)
    if summary.get("recomputed_evaluation_sha256") != recomputed_sha256:
        raise ValueError("semantic recomputed evaluation hash mismatch")
    return {
        "ok": True,
        "pass": bool(recomputed["pass"]),
        "recomputed_evaluation_sha256": recomputed_sha256,
        "primary_judge_run_manifest": primary_replay["judge_run_manifest"],
        "sensitivity_judge_run_manifest": sensitivity_replay[
            "judge_run_manifest"
        ],
        "recomputed_summary": recomputed,
    }
