"""Blind, auditable two-judge quality gate for the V6 triad pool.

This instrument is deliberately separate from the semantic judge.  Its prompt,
schema, cache keys, artifacts, and evaluation concern message quality only.  A
judge receives an opaque hash-derived sample id and rendered message text; the
registered frame, triad, and split are joined to both completed result sets only
inside :func:`evaluate_v6_quality_validation`.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import random
import subprocess
import tempfile
import time
from collections import Counter
from dataclasses import dataclass
from typing import (
    Any,
    Callable,
    Dict,
    Iterable,
    List,
    Mapping,
    Optional,
    Sequence,
    Tuple,
)

from config import CONTROLLED_V6_QUALITY_THRESHOLDS, STRATEGIES
from .blind_judge import (
    FROZEN_JUDGE_BATCH_SCHEDULE_VERSION,
    PaidBatchReconciliationError,
    _audit_paid_batch_evidence,
    _atomic_write_json,
    _atomic_write_jsonl,
    _atomic_write_text,
    _json_file_manifest,
    _jsonl_file_manifest,
    _repository_local_path,
    _read_regular_text,
    _resolve_repository_path,
    _strict_json_file,
    _strict_jsonl_file,
    _validate_official_run_coordinates,
    _paid_batch_claim_payload,
    _paid_batch_paths,
    _paid_batch_reconciliation_error,
    _paid_batch_state_payload,
    _paid_state_meta_fields,
    _prepare_paid_batch_claim,
    _publish_paid_batch_state,
    _read_durable_provider_output,
    _validated_existing_paid_output,
    _validated_official_judge_contract,
    _verify_official_executable_for_dispatch,
    _write_or_verify_exact_json_artifact,
    _write_or_verify_exact_text_artifact,
    canonical_json_sha256,
    sanitize_codex_meta,
    strict_json_file_identity,
)
from .controlled_v6_messages import V6TriadBank, audit_v6_bank_payload
from .file_lock import require_directory_nonsymlink, require_regular_nonsymlink
from .logging_utils import strict_json_loads


CODEX_QUALITY_PROMPT_VERSION = "codex-v6-quality-blind-v1"
CODEX_QUALITY_PROMPT_INSTRUCTION = (
    "\nReturn exactly one schema-valid assessment for each object in "
    "this JSON array:\n\n"
)
QUALITY_SCORE_FIELDS: Tuple[str, ...] = (
    "grammar",
    "clarity",
    "generic_applicability",
    "persuasive_strength",
    "overall_quality",
    "confidence",
)
QUALITY_ISSUE_CODES: Tuple[str, ...] = (
    "none",
    "grammar",
    "clarity",
    "genericity",
    "persuasion",
    "overall",
    "other",
)

CODEX_QUALITY_RUBRIC = """You are a careful message-quality evaluator.

Score each supplied short persuasive message independently on these dimensions:

- grammar: grammatical correctness, mechanics, and sentence completeness;
- clarity: immediate readability and an unambiguous reason for the choice;
- generic_applicability: suitability across varied neutral two-option decision
  scenarios, without unsupported assumptions about a particular situation;
- persuasive_strength: how plausibly compelling the stated reason would be;
- overall_quality: holistic readiness as a polished, usable short message;
- confidence: your confidence in this assessment.

Every score must be from 0 to 1, where 1 is strongest. Do not normalize scores
within the batch and do not compare messages with one another. Judge only the
supplied words, do not infer missing context, and do not use tools.

Also return exactly one predominant issue_code from this fixed set:
- none: no notable quality issue;
- grammar: a grammar, mechanics, or sentence-completeness problem;
- clarity: unclear, awkward, or ambiguous wording;
- genericity: depends too strongly on unstated or narrow scenario details;
- persuasion: the reason is weak or unconvincing;
- overall: a broader quality problem not captured by one dimension;
- other: another material quality issue.
"""


@dataclass(frozen=True)
class QualityJudgeSample:
    """The complete per-sample information exposed to a quality judge."""

    sample_id: str
    message: str
    cache_key: str

    def judge_dict(self) -> Dict[str, str]:
        return {"sample_id": self.sample_id, "message": self.message}


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


CODEX_QUALITY_RUBRIC_SHA256 = _sha256(CODEX_QUALITY_RUBRIC)
CODEX_QUALITY_PROMPT_SHA256 = _sha256(
    CODEX_QUALITY_RUBRIC
    + CODEX_QUALITY_PROMPT_INSTRUCTION
    + "<SAMPLES_JSON>"
)


def quality_judge_contract() -> Dict[str, str]:
    """Return the stable quality-judge prompt contract frozen by V6."""
    return {
        "prompt_version": CODEX_QUALITY_PROMPT_VERSION,
        "prompt_sha256": CODEX_QUALITY_PROMPT_SHA256,
        "rubric_sha256": CODEX_QUALITY_RUBRIC_SHA256,
    }


def quality_judge_cache_key(message: str, model: str) -> str:
    """Return a cache key isolated by quality prompt version and model."""
    return _sha256(
        "\x1f".join([str(model), CODEX_QUALITY_PROMPT_VERSION, str(message)])
    )


def make_quality_sample(message: str, model: str) -> QualityJudgeSample:
    message = str(message)
    return QualityJudgeSample(
        sample_id="q_" + _sha256(message)[:16],
        message=message,
        cache_key=quality_judge_cache_key(message, model),
    )


def build_quality_batches(
    messages: Iterable[str], model: str, batch_size: int, seed: int
) -> List[List[QualityJudgeSample]]:
    """Deduplicate and deterministically shuffle message-only samples."""
    if batch_size < 1:
        raise ValueError("batch_size must be positive")
    by_message = {
        str(message): make_quality_sample(str(message), model) for message in messages
    }
    samples = sorted(by_message.values(), key=lambda sample: sample.sample_id)
    random.Random(seed).shuffle(samples)
    return [
        samples[index : index + batch_size]
        for index in range(0, len(samples), batch_size)
    ]


def quality_output_schema(sample_ids: Sequence[str]) -> Dict[str, Any]:
    """Return the strict JSON schema for one quality-judge response."""
    expected_ids = list(sample_ids)
    if len(expected_ids) != len(set(expected_ids)):
        raise ValueError("quality schema sample ids must be unique")
    score = {"type": "number", "minimum": 0.0, "maximum": 1.0}
    required = ["sample_id", *QUALITY_SCORE_FIELDS, "issue_code"]
    properties: Dict[str, Any] = {
        "sample_id": {"type": "string", "enum": expected_ids},
        **{field: score for field in QUALITY_SCORE_FIELDS},
        "issue_code": {"type": "string", "enum": list(QUALITY_ISSUE_CODES)},
    }
    item = {
        "type": "object",
        "additionalProperties": False,
        "required": required,
        "properties": properties,
    }
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["assessments"],
        "properties": {
            "assessments": {
                "type": "array",
                "minItems": len(expected_ids),
                "maxItems": len(expected_ids),
                "items": item,
            }
        },
    }


def build_quality_prompt(samples: Sequence[QualityJudgeSample]) -> str:
    """Build a prompt whose only sample fields are opaque id and message."""
    payload = [sample.judge_dict() for sample in samples]
    return (
        CODEX_QUALITY_RUBRIC
        + CODEX_QUALITY_PROMPT_INSTRUCTION
        + json.dumps(payload, ensure_ascii=False, indent=2)
    )


def _unique_quality_messages(messages: Iterable[str]) -> List[str]:
    values = [str(message) for message in messages]
    if not values:
        raise ValueError("frozen quality judge message set must not be empty")
    if len(values) != len(set(values)):
        raise ValueError(
            "frozen quality judge message set must contain unique messages"
        )
    return values


def _quality_message_set_sha256(messages: Iterable[str]) -> str:
    return canonical_json_sha256(sorted(_unique_quality_messages(messages)))


def _quality_batch_id(samples: Sequence[QualityJudgeSample]) -> str:
    return "batch_" + _sha256(
        "\n".join(sample.sample_id for sample in samples)
    )[:16]


def build_quality_batch_plan(
    messages: Iterable[str], model: str, batch_size: int, seed: int
) -> List[Dict[str, Any]]:
    """Reconstruct the only quality-judge partition permitted by contract."""
    canonical_messages = _unique_quality_messages(messages)
    batches = build_quality_batches(canonical_messages, model, batch_size, seed)
    message_set_sha256 = _quality_message_set_sha256(canonical_messages)
    n_batches = len(batches)
    plan: List[Dict[str, Any]] = []
    for batch_index, samples in enumerate(batches, start=1):
        batch_id = _quality_batch_id(samples)
        schedule = {
            "schedule_version": FROZEN_JUDGE_BATCH_SCHEDULE_VERSION,
            "batch_id": batch_id,
            "batch_index": batch_index,
            "n_batches": n_batches,
            "model": str(model),
            "seed": int(seed),
            "batch_size": int(batch_size),
            "message_set_sha256": message_set_sha256,
        }
        input_payload = {
            **schedule,
            "prompt_version": CODEX_QUALITY_PROMPT_VERSION,
            "prompt_template_sha256": CODEX_QUALITY_PROMPT_SHA256,
            "rubric_sha256": CODEX_QUALITY_RUBRIC_SHA256,
            "samples": [sample.judge_dict() for sample in samples],
        }
        plan.append(
            {
                **schedule,
                "sample_ids": [sample.sample_id for sample in samples],
                "samples": list(samples),
                "input_filename": batch_id + ".input.json",
                "output_filename": batch_id + ".output.json",
                "meta_filename": batch_id + ".meta.json",
                "input_payload": input_payload,
                "input_payload_sha256": canonical_json_sha256(input_payload),
                "prompt_sha256": _sha256(build_quality_prompt(samples)),
            }
        )
    return plan


def validate_quality_payload(
    payload: Mapping[str, Any], expected_ids: Sequence[str]
) -> Dict[str, Dict[str, Any]]:
    """Fail closed on extra fields, omissions, duplicates, or invalid values."""
    expected_list = list(expected_ids)
    if len(expected_list) != len(set(expected_list)):
        raise ValueError("expected quality sample ids must be unique")
    if not isinstance(payload, Mapping) or set(payload) != {"assessments"}:
        raise ValueError("quality response must contain only the assessments array")
    rows = payload.get("assessments")
    if not isinstance(rows, list):
        raise ValueError("quality response has no assessments array")

    expected = set(expected_list)
    required = {"sample_id", *QUALITY_SCORE_FIELDS, "issue_code"}
    found: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, Mapping):
            raise ValueError("quality assessment is not an object")
        if set(row) != required:
            raise ValueError("quality assessment has missing or unexpected fields")
        sample_id = row.get("sample_id")
        if sample_id not in expected:
            raise ValueError("unexpected sample_id %r" % sample_id)
        if sample_id in found:
            raise ValueError("duplicate sample_id %r" % sample_id)
        issue_code = row.get("issue_code")
        if issue_code not in QUALITY_ISSUE_CODES:
            raise ValueError("invalid issue_code %r" % issue_code)
        clean: Dict[str, Any] = {
            "sample_id": sample_id,
            "issue_code": issue_code,
        }
        for field in QUALITY_SCORE_FIELDS:
            value = row.get(field)
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError("%s for %s is not numeric" % (field, sample_id))
            value = float(value)
            if not math.isfinite(value) or not 0.0 <= value <= 1.0:
                raise ValueError("%s for %s is outside [0,1]" % (field, sample_id))
            clean[field] = value
        found[str(sample_id)] = clean

    missing = expected - set(found)
    if missing:
        raise ValueError("quality judge omitted sample ids: %s" % sorted(missing))
    if len(found) != len(expected):
        raise ValueError("quality judge returned the wrong number of assessments")
    return found


def _quality_public_result(
    result: Mapping[str, Any], expected_sample_id: str
) -> Dict[str, Any]:
    """Validate one result and strip identifiers/internal audit metadata."""
    if not isinstance(result, Mapping):
        raise ValueError("quality judge result is not an object")
    extra = set(result) - {
        "sample_id",
        *QUALITY_SCORE_FIELDS,
        "issue_code",
        "_artifact_binding",
        "_batch_id",
        "_prompt_version",
    }
    if extra:
        raise ValueError("quality judge result has unexpected internal fields")
    sample_id = result.get("sample_id", expected_sample_id)
    if sample_id != expected_sample_id:
        raise ValueError("quality result sample id does not match its message")
    public = {
        key: value
        for key, value in result.items()
        if key not in {"_artifact_binding", "_batch_id", "_prompt_version"}
    }
    public["sample_id"] = expected_sample_id
    clean = validate_quality_payload(
        {"assessments": [public]}, [expected_sample_id]
    )[expected_sample_id]
    return {
        key: clean[key] for key in (*QUALITY_SCORE_FIELDS, "issue_code")
    }


def canonical_quality_result_map(
    results: Mapping[str, Mapping[str, Any]],
    expected_messages: Optional[Iterable[str]] = None,
) -> Dict[str, Dict[str, Any]]:
    """Return the canonical, message-keyed public quality result map."""
    if not isinstance(results, Mapping):
        raise ValueError("quality judge results are not a mapping")
    if expected_messages is not None:
        expected = {str(message) for message in expected_messages}
        if set(results) != expected:
            raise ValueError("quality judge results do not exactly cover messages")
    clean: Dict[str, Dict[str, Any]] = {}
    for message, result in results.items():
        message = str(message)
        clean[message] = _quality_public_result(
            result, make_quality_sample(message, "sample-id-only").sample_id
        )
    return clean


def _quality_artifact_binding(
    sample: QualityJudgeSample,
    model: str,
    batch_id: str,
    prompt_sha256: str,
    output_sha256: str,
    result: Mapping[str, Any],
) -> Dict[str, str]:
    return {
        "batch_id": batch_id,
        "model": str(model),
        "prompt_version": CODEX_QUALITY_PROMPT_VERSION,
        "prompt_sha256": prompt_sha256,
        "prompt_template_sha256": CODEX_QUALITY_PROMPT_SHA256,
        "rubric_sha256": CODEX_QUALITY_RUBRIC_SHA256,
        "message_sha256": _sha256(sample.message),
        "output_sha256": output_sha256,
        "result_sha256": canonical_json_sha256(result),
    }


def _validated_quality_artifact_binding(
    binding: Mapping[str, Any],
    sample: QualityJudgeSample,
    model: str,
    result: Mapping[str, Any],
) -> Dict[str, str]:
    expected_keys = {
        "batch_id",
        "model",
        "prompt_version",
        "prompt_sha256",
        "prompt_template_sha256",
        "rubric_sha256",
        "message_sha256",
        "output_sha256",
        "result_sha256",
    }
    if set(binding) != expected_keys:
        raise ValueError("quality cache artifact binding has unexpected fields")
    expected = {
        "model": str(model),
        "prompt_version": CODEX_QUALITY_PROMPT_VERSION,
        "prompt_template_sha256": CODEX_QUALITY_PROMPT_SHA256,
        "rubric_sha256": CODEX_QUALITY_RUBRIC_SHA256,
        "message_sha256": _sha256(sample.message),
        "result_sha256": canonical_json_sha256(result),
    }
    for key, value in expected.items():
        if binding.get(key) != value:
            raise ValueError("quality cache artifact binding mismatch for %s" % key)
    for key in ("prompt_sha256", "output_sha256"):
        value = binding.get(key)
        if (
            not isinstance(value, str)
            or len(value) != 64
            or any(character not in "0123456789abcdef" for character in value)
        ):
            raise ValueError("quality cache artifact binding has invalid %s" % key)
    if not isinstance(binding.get("batch_id"), str) or not str(
        binding["batch_id"]
    ).startswith("batch_"):
        raise ValueError("quality cache artifact binding has invalid batch_id")
    return {key: str(binding[key]) for key in expected_keys}


QUALITY_BATCH_RECOVERY_VERSION = "v6-quality-batch-recovery-v1"


def _quality_recovery_path(artifact_dir: str, batch_id: str) -> str:
    return os.path.join(artifact_dir, ".%s.recovery.json" % batch_id)


def _quality_batch_artifact_paths(
    artifact_dir: str, batch_id: str
) -> Tuple[str, str, str]:
    return (
        os.path.join(artifact_dir, batch_id + ".input.json"),
        os.path.join(artifact_dir, batch_id + ".output.json"),
        os.path.join(artifact_dir, batch_id + ".meta.json"),
    )


def _quality_recovery_payload(
    input_payload: Mapping[str, Any],
    output_text: str,
    meta: Mapping[str, Any],
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "recovery_version": QUALITY_BATCH_RECOVERY_VERSION,
        "input_payload": dict(input_payload),
        "output_text": str(output_text),
        "meta": dict(meta),
    }
    payload["recovery_sha256"] = canonical_json_sha256(payload)
    return payload


def _validate_quality_batch_artifacts(
    input_payload: Mapping[str, Any],
    output_text: str,
    meta: Mapping[str, Any],
    plan_row: Mapping[str, Any],
    model: str,
) -> Dict[str, Dict[str, Any]]:
    if dict(input_payload) != plan_row["input_payload"]:
        raise ValueError(
            "quality recovery input differs from frozen seed/batch schedule"
        )
    if not isinstance(meta, Mapping):
        raise ValueError("quality recovery metadata is not an object")
    if "stdout" in meta or "stderr" in meta:
        raise ValueError("quality recovery metadata contains raw process logs")
    if meta.get("process_logs_retained") is not False:
        raise ValueError("quality recovery process-log policy is missing")
    if meta.get("returncode") != 0:
        raise ValueError("quality recovery batch was not successful")
    if meta.get("batch_id") != plan_row["batch_id"]:
        raise ValueError("quality recovery batch id differs from frozen schedule")
    if meta.get("model") != str(model):
        raise ValueError("quality recovery model differs from frozen schedule")
    if meta.get("prompt_version") != CODEX_QUALITY_PROMPT_VERSION:
        raise ValueError("quality recovery prompt version differs from contract")
    if meta.get("prompt_template_sha256") != CODEX_QUALITY_PROMPT_SHA256:
        raise ValueError("quality recovery prompt hash differs from contract")
    if meta.get("rubric_sha256") != CODEX_QUALITY_RUBRIC_SHA256:
        raise ValueError("quality recovery rubric hash differs from contract")
    if meta.get("sample_ids") != list(plan_row["sample_ids"]):
        raise ValueError("quality recovery sample order differs from schedule")
    if meta.get("prompt_sha256") != plan_row["prompt_sha256"]:
        raise ValueError("quality recovery exact prompt hash mismatch")
    for field in (
        "schedule_version",
        "batch_index",
        "n_batches",
        "seed",
        "batch_size",
        "message_set_sha256",
    ):
        if meta.get(field) != plan_row[field]:
            raise ValueError(
                "quality recovery %s differs from frozen schedule" % field
            )
    if any(os.path.isabs(str(value)) for value in meta.get("command_flags", [])):
        raise ValueError("quality recovery metadata retains an absolute path")
    output_hashes = {_sha256(output_text)}
    if output_text.endswith("\n"):
        output_hashes.add(_sha256(output_text[:-1]))
    if meta.get("output_sha256") not in output_hashes:
        raise ValueError("quality recovery output hash mismatch")
    try:
        output_payload = strict_json_loads(output_text)
    except ValueError as exc:
        raise ValueError("quality recovery output is invalid JSON") from exc
    validated = validate_quality_payload(output_payload, plan_row["sample_ids"])
    samples = list(plan_row["samples"])
    by_id = {sample.sample_id: sample for sample in samples}
    prompt_sha256 = str(plan_row["prompt_sha256"])
    output_sha256 = str(meta["output_sha256"])
    for sample_id, result in validated.items():
        public = _quality_public_result(result, sample_id)
        result["_batch_id"] = str(plan_row["batch_id"])
        result["_prompt_version"] = CODEX_QUALITY_PROMPT_VERSION
        result["_artifact_binding"] = _quality_artifact_binding(
            by_id[sample_id],
            model,
            str(plan_row["batch_id"]),
            prompt_sha256,
            output_sha256,
            public,
        )
    return validated


def _load_quality_recovery(
    path: str, plan_row: Mapping[str, Any], model: str
) -> Tuple[Dict[str, Any], Dict[str, Dict[str, Any]]]:
    try:
        supplied, _ = _strict_json_file(
            path,
            root=os.path.dirname(path) or os.curdir,
            label="quality batch recovery journal",
        )
    except (OSError, ValueError) as exc:
        raise ValueError("quality batch recovery journal is unreadable") from exc
    required = {
        "recovery_version",
        "input_payload",
        "output_text",
        "meta",
        "recovery_sha256",
    }
    if not isinstance(supplied, Mapping) or set(supplied) != required:
        raise ValueError("quality batch recovery journal schema mismatch")
    payload = dict(supplied)
    supplied_hash = payload.pop("recovery_sha256")
    if supplied_hash != canonical_json_sha256(payload):
        raise ValueError("quality batch recovery journal hash mismatch")
    if payload.get("recovery_version") != QUALITY_BATCH_RECOVERY_VERSION:
        raise ValueError("quality batch recovery journal version mismatch")
    if not isinstance(payload.get("input_payload"), Mapping) or not isinstance(
        payload.get("meta"), Mapping
    ):
        raise ValueError("quality batch recovery journal payload is malformed")
    if not isinstance(payload.get("output_text"), str):
        raise ValueError("quality batch recovery output is not text")
    values = _validate_quality_batch_artifacts(
        payload["input_payload"],
        payload["output_text"],
        payload["meta"],
        plan_row,
        model,
    )
    return dict(supplied), values


def _recover_quality_batch_from_artifacts(
    artifact_dir: str,
    plan_row: Mapping[str, Any],
    model: str,
) -> Optional[Dict[str, Dict[str, Any]]]:
    batch_id = str(plan_row["batch_id"])
    input_path, output_path, meta_path = _quality_batch_artifact_paths(
        artifact_dir, batch_id
    )
    recovery_path = _quality_recovery_path(artifact_dir, batch_id)
    flat_paths = (input_path, output_path, meta_path)
    flat_exists = [os.path.exists(path) for path in flat_paths]

    if os.path.exists(recovery_path):
        recovery, values = _load_quality_recovery(
            recovery_path, plan_row, model
        )
        expected_values: Tuple[Any, ...] = (
            recovery["input_payload"],
            recovery["output_text"],
            recovery["meta"],
        )
        for path, expected_value, exists in zip(
            flat_paths, expected_values, flat_exists
        ):
            if exists:
                if path == output_path:
                    actual_value: Any = _read_regular_text(
                        path,
                        root=artifact_dir,
                        label="quality recovered output artifact",
                    )
                else:
                    actual_value, _ = _strict_json_file(
                        path,
                        root=artifact_dir,
                        label="quality recovered JSON artifact",
                    )
                if actual_value != expected_value:
                    raise ValueError(
                        "quality recovery journal/triplet divergence for %s"
                        % batch_id
                    )
            elif path == output_path:
                _atomic_write_text(path, str(expected_value))
            else:
                _atomic_write_json(path, expected_value)
        return values

    if not any(flat_exists):
        return None
    if not all(flat_exists):
        raise ValueError(
            "quality batch has an incomplete artifact triplet; refusing to "
            "repeat a possibly paid call"
        )
    try:
        input_payload, _ = _strict_json_file(
            input_path, root=artifact_dir, label="quality input artifact"
        )
        output_text = _read_regular_text(
            output_path, root=artifact_dir, label="quality output artifact"
        )
        meta, _ = _strict_json_file(
            meta_path, root=artifact_dir, label="quality metadata artifact"
        )
    except (OSError, ValueError) as exc:
        raise ValueError("quality artifact triplet is unreadable") from exc
    return _validate_quality_batch_artifacts(
        input_payload, output_text, meta, plan_row, model
    )


def _normalise_result_map(
    values: Mapping[str, Mapping[str, Any]], samples: Sequence[QualityJudgeSample]
) -> Dict[str, Dict[str, Any]]:
    """Validate a batch-runner/cache result, allowing two internal audit fields."""
    expected_ids = [sample.sample_id for sample in samples]
    if set(values) != set(expected_ids):
        raise ValueError("quality batch results do not exactly cover pending samples")
    public_rows = []
    internal: Dict[str, Dict[str, Any]] = {}
    for sample_id in expected_ids:
        row = values[sample_id]
        if not isinstance(row, Mapping):
            raise ValueError("quality batch result is not an object")
        extra = set(row) - {
            "sample_id",
            *QUALITY_SCORE_FIELDS,
            "issue_code",
            "_batch_id",
            "_prompt_version",
            "_artifact_binding",
        }
        if extra:
            raise ValueError("quality batch result has unexpected internal fields")
        if row.get("_prompt_version", CODEX_QUALITY_PROMPT_VERSION) != (
            CODEX_QUALITY_PROMPT_VERSION
        ):
            raise ValueError("quality result has a different prompt version")
        if "_batch_id" in row and (
            not isinstance(row["_batch_id"], str)
            or not row["_batch_id"].startswith("batch_")
        ):
            raise ValueError("quality result has an invalid batch id")
        public_rows.append(
            {
                key: value
                for key, value in row.items()
                if key
                not in {"_artifact_binding", "_batch_id", "_prompt_version"}
            }
        )
        internal[sample_id] = {
            key: row[key]
            for key in ("_batch_id", "_prompt_version")
            if key in row
        }
    clean = validate_quality_payload({"assessments": public_rows}, expected_ids)
    for sample_id in expected_ids:
        clean[sample_id].update(internal[sample_id])
    return clean


QualityBatchRunner = Callable[
    [Sequence[QualityJudgeSample], str, str, str, int],
    Dict[str, Dict[str, Any]],
]


def run_quality_codex_batch(
    samples: Sequence[QualityJudgeSample],
    model: str,
    executable: str,
    artifact_dir: str,
    timeout_s: int,
    process_runner: Callable[..., Any] = subprocess.run,
    batch_context: Optional[Mapping[str, Any]] = None,
    official_contract: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Dict[str, Any]]:
    """Run one schema-constrained Codex call and retain exact audit artifacts."""
    if not samples:
        return {}
    expected_ids = [sample.sample_id for sample in samples]
    batch_id = _quality_batch_id(samples)
    validated_official = (
        _verify_official_executable_for_dispatch(
            executable,
            official_contract,
            kind="quality",
            model=model,
        )
        if official_contract is not None
        else None
    )
    os.makedirs(artifact_dir, exist_ok=True)
    prompt = build_quality_prompt(samples)

    schedule_payload: Dict[str, Any] = {}
    if batch_context is not None:
        required_context = {
            "schedule_version",
            "batch_id",
            "batch_index",
            "n_batches",
            "model",
            "seed",
            "batch_size",
            "message_set_sha256",
            "sample_ids",
            "prompt_sha256",
        }
        if not isinstance(batch_context, Mapping) or not required_context.issubset(
            batch_context
        ):
            raise ValueError("quality judge batch context is incomplete")
        if batch_context["batch_id"] != batch_id:
            raise ValueError("quality judge batch context has wrong batch id")
        if batch_context["model"] != str(model):
            raise ValueError("quality judge batch context has wrong model")
        if list(batch_context["sample_ids"]) != expected_ids:
            raise ValueError("quality judge batch context has wrong sample order")
        if batch_context["prompt_sha256"] != _sha256(prompt):
            raise ValueError("quality judge batch context has wrong prompt hash")
        schedule_payload = {
            key: batch_context[key]
            for key in (
                "schedule_version",
                "batch_index",
                "n_batches",
                "seed",
                "batch_size",
                "message_set_sha256",
            )
        }

    input_path = os.path.join(artifact_dir, batch_id + ".input.json")
    output_path = os.path.join(artifact_dir, batch_id + ".output.json")
    meta_path = os.path.join(artifact_dir, batch_id + ".meta.json")
    input_payload = {
        **schedule_payload,
        "batch_id": batch_id,
        "model": model,
        "prompt_version": CODEX_QUALITY_PROMPT_VERSION,
        "prompt_template_sha256": CODEX_QUALITY_PROMPT_SHA256,
        "rubric_sha256": CODEX_QUALITY_RUBRIC_SHA256,
        "samples": [sample.judge_dict() for sample in samples],
    }

    output_schema = quality_output_schema(expected_ids)
    _, claimed_provider_output_path, _ = _paid_batch_paths(
        artifact_dir, batch_id
    )
    claim = _paid_batch_claim_payload(
        kind="quality",
        batch_id=batch_id,
        model=model,
        executable=executable,
        prompt_version=CODEX_QUALITY_PROMPT_VERSION,
        prompt_template_sha256=CODEX_QUALITY_PROMPT_SHA256,
        rubric_sha256=CODEX_QUALITY_RUBRIC_SHA256,
        prompt=prompt,
        input_payload=input_payload,
        output_schema=output_schema,
        sample_ids=expected_ids,
        provider_output_filename=os.path.basename(claimed_provider_output_path),
        official_contract=validated_official,
    )

    def build_meta(
        state: Mapping[str, Any], command: Sequence[str]
    ) -> Dict[str, Any]:
        return sanitize_codex_meta(
            {
                **schedule_payload,
                "batch_id": batch_id,
                "model": model,
                "prompt_version": CODEX_QUALITY_PROMPT_VERSION,
                "prompt_template_sha256": CODEX_QUALITY_PROMPT_SHA256,
                "rubric_sha256": CODEX_QUALITY_RUBRIC_SHA256,
                "sample_ids": expected_ids,
                **_paid_state_meta_fields(state),
                "prompt_sha256": _sha256(prompt),
                "output_sha256": state["output_sha256"],
                "command_flags": list(command[2:-1]),
                "provider_claim_sha256": claim["claim_sha256"],
                "provider_state_sha256": state["state_sha256"],
                "provider_output_filename": claim["provider_output_filename"],
                "provider_output_recovered": state[
                    "recovered_from_durable_output"
                ],
            }
        )

    def persist_failed_triplet(
        raw_output: str,
        state: Mapping[str, Any],
        command: Sequence[str],
    ) -> Dict[str, Any]:
        failed_meta = build_meta(state, command)
        failed_output = raw_output + (
            "\n" if raw_output and not raw_output.endswith("\n") else ""
        )
        _write_or_verify_exact_json_artifact(
            input_path, input_payload, kind="quality", batch_id=batch_id
        )
        _write_or_verify_exact_text_artifact(
            output_path, failed_output, kind="quality", batch_id=batch_id
        )
        _write_or_verify_exact_json_artifact(
            meta_path, failed_meta, kind="quality", batch_id=batch_id
        )
        return failed_meta

    with tempfile.TemporaryDirectory(
        prefix="latenttarget_codex_judge_quality_"
    ) as temporary_dir:
        schema_path = os.path.join(temporary_dir, "schema.json")
        with open(schema_path, "w", encoding="utf-8") as handle:
            json.dump(output_schema, handle, indent=2)
            handle.flush()
            os.fsync(handle.fileno())
        first_dispatch, _, provider_output_path, state_path = (
            _prepare_paid_batch_claim(
                artifact_dir,
                claim,
                kind="quality",
                batch_id=batch_id,
            )
        )
        provider_output_path = os.path.abspath(provider_output_path)
        command = [
            executable,
            "exec",
            "--ephemeral",
            "--ignore-user-config",
            "--ignore-rules",
            "--skip-git-repo-check",
            "--sandbox",
            "read-only",
            "--model",
            model,
            "--output-schema",
            schema_path,
            "--output-last-message",
            provider_output_path,
            "--color",
            "never",
            "--cd",
            temporary_dir,
            "-",
        ]

        if first_dispatch:
            started = time.time()
            try:
                completed = process_runner(
                    command,
                    input=prompt,
                    text=True,
                    capture_output=True,
                    timeout=timeout_s,
                    check=False,
                )
            except BaseException as exc:
                raw_after_exception = ""
                output_is_complete = False
                if os.path.lexists(provider_output_path):
                    try:
                        raw_after_exception = _read_durable_provider_output(
                            provider_output_path,
                            kind="quality",
                            batch_id=batch_id,
                        )
                        exception_payload = strict_json_loads(raw_after_exception)
                        validate_quality_payload(exception_payload, expected_ids)
                        output_is_complete = True
                    except (PaidBatchReconciliationError, ValueError):
                        output_is_complete = False
                if not output_is_complete:
                    failed_state = _paid_batch_state_payload(
                        claim,
                        status="failed",
                        raw_output=raw_after_exception,
                        returncode=None,
                        elapsed_seconds=time.time() - started,
                        stdout=None,
                        stderr=None,
                        failure_kind=type(exc).__name__,
                        recovered_from_durable_output=False,
                    )
                    _publish_paid_batch_state(
                        state_path,
                        failed_state,
                        kind="quality",
                        batch_id=batch_id,
                    )
                if isinstance(exc, subprocess.TimeoutExpired):
                    raise RuntimeError(
                        "Codex quality batch %s timed out after %d seconds"
                        % (batch_id, timeout_s)
                    ) from None
                raise

            elapsed = time.time() - started
            raw = ""
            if os.path.lexists(provider_output_path):
                try:
                    raw = _read_durable_provider_output(
                        provider_output_path,
                        kind="quality",
                        batch_id=batch_id,
                    )
                except PaidBatchReconciliationError:
                    _publish_paid_batch_state(
                        state_path,
                        _paid_batch_state_payload(
                            claim,
                            status="failed",
                            raw_output="",
                            returncode=completed.returncode,
                            elapsed_seconds=elapsed,
                            stdout=completed.stdout,
                            stderr=completed.stderr,
                            failure_kind="unreadable_provider_output",
                            recovered_from_durable_output=False,
                        ),
                        kind="quality",
                        batch_id=batch_id,
                    )
                    raise
            if completed.returncode != 0:
                state = _publish_paid_batch_state(
                    state_path,
                    _paid_batch_state_payload(
                        claim,
                        status="failed",
                        raw_output=raw,
                        returncode=completed.returncode,
                        elapsed_seconds=elapsed,
                        stdout=completed.stdout,
                        stderr=completed.stderr,
                        failure_kind="nonzero_exit",
                        recovered_from_durable_output=False,
                    ),
                    kind="quality",
                    batch_id=batch_id,
                )
                meta = persist_failed_triplet(raw, state, command)
                raise RuntimeError(
                    "Codex quality batch %s failed with exit %d (stderr sha256 %s)"
                    % (
                        batch_id,
                        completed.returncode,
                        meta.get("stderr_sha256", "missing"),
                    )
                )
            if not os.path.lexists(provider_output_path):
                state = _publish_paid_batch_state(
                    state_path,
                    _paid_batch_state_payload(
                        claim,
                        status="failed",
                        raw_output="",
                        returncode=completed.returncode,
                        elapsed_seconds=elapsed,
                        stdout=completed.stdout,
                        stderr=completed.stderr,
                        failure_kind="missing_provider_output",
                        recovered_from_durable_output=False,
                    ),
                    kind="quality",
                    batch_id=batch_id,
                )
                persist_failed_triplet("", state, command)
                raise RuntimeError(
                    "Codex quality batch %s produced no durable provider output"
                    % batch_id
                )
            try:
                payload = strict_json_loads(raw)
                validated = validate_quality_payload(payload, expected_ids)
            except ValueError as exc:
                state = _publish_paid_batch_state(
                    state_path,
                    _paid_batch_state_payload(
                        claim,
                        status="failed",
                        raw_output=raw,
                        returncode=completed.returncode,
                        elapsed_seconds=elapsed,
                        stdout=completed.stdout,
                        stderr=completed.stderr,
                        failure_kind=(
                            "invalid_json_or_schema"
                        ),
                        recovered_from_durable_output=False,
                    ),
                    kind="quality",
                    batch_id=batch_id,
                )
                persist_failed_triplet(raw, state, command)
                raise ValueError(
                    "Codex quality batch %s returned invalid strict JSON or schema"
                    % batch_id
                ) from exc
            state = _publish_paid_batch_state(
                state_path,
                _paid_batch_state_payload(
                    claim,
                    status="succeeded",
                    raw_output=raw,
                    returncode=completed.returncode,
                    elapsed_seconds=elapsed,
                    stdout=completed.stdout,
                    stderr=completed.stderr,
                    failure_kind=None,
                    recovered_from_durable_output=False,
                ),
                kind="quality",
                batch_id=batch_id,
            )
        else:
            raw, state = _validated_existing_paid_output(
                claim=claim,
                provider_output_path=provider_output_path,
                state_path=state_path,
                kind="quality",
                batch_id=batch_id,
            )
            try:
                payload = strict_json_loads(raw)
                validated = validate_quality_payload(payload, expected_ids)
            except ValueError as exc:
                raise _paid_batch_reconciliation_error(
                    "quality",
                    batch_id,
                    "the claimed durable provider output is not schema-valid",
                ) from exc
            if state is None:
                state = _publish_paid_batch_state(
                    state_path,
                    _paid_batch_state_payload(
                        claim,
                        status="succeeded",
                        raw_output=raw,
                        returncode=0,
                        elapsed_seconds=None,
                        stdout=None,
                        stderr=None,
                        failure_kind=None,
                        recovered_from_durable_output=True,
                    ),
                    kind="quality",
                    batch_id=batch_id,
                )

    meta = build_meta(state, command)
    output_text = raw + ("\n" if raw and not raw.endswith("\n") else "")
    prompt_sha256 = _sha256(prompt)
    output_sha256 = _sha256(raw)
    by_id = {sample.sample_id: sample for sample in samples}
    for sample_id, result in validated.items():
        public = _quality_public_result(result, sample_id)
        result["_batch_id"] = batch_id
        result["_prompt_version"] = CODEX_QUALITY_PROMPT_VERSION
        result["_artifact_binding"] = _quality_artifact_binding(
            by_id[sample_id],
            model,
            batch_id,
            prompt_sha256,
            output_sha256,
            public,
        )
    recovery_path = _quality_recovery_path(artifact_dir, batch_id)
    _write_or_verify_exact_json_artifact(
        recovery_path,
        _quality_recovery_payload(input_payload, output_text, meta),
        kind="quality",
        batch_id=batch_id,
    )
    _write_or_verify_exact_json_artifact(
        input_path, input_payload, kind="quality", batch_id=batch_id
    )
    _write_or_verify_exact_text_artifact(
        output_path, output_text, kind="quality", batch_id=batch_id
    )
    _write_or_verify_exact_json_artifact(
        meta_path, meta, kind="quality", batch_id=batch_id
    )
    return validated


def audit_quality_artifacts(
    artifact_dir: str,
    *,
    expected_messages: Optional[Iterable[str]] = None,
    model: Optional[str] = None,
    batch_size: Optional[int] = None,
    seed: Optional[int] = None,
    repository_root: Optional[str] = None,
    official_contract: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    """Verify blind fields, prompt/output hashes, and sanitized process metadata."""
    if not os.path.isdir(artifact_dir):
        raise FileNotFoundError(
            "quality artifact directory not found: %s" % artifact_dir
        )
    require_directory_nonsymlink(
        artifact_dir, label="quality judge artifact directory"
    )
    directory_entries = sorted(os.listdir(artifact_dir))
    operational_lock_filenames = [".quality-validation.lock"]
    operational_excluded_files = sorted(
        name for name in directory_entries if name in operational_lock_filenames
    )
    for name in operational_excluded_files:
        require_regular_nonsymlink(
            os.path.join(artifact_dir, name),
            label="quality operational run lock",
        )
    actual_file_names = sorted(
        name
        for name in directory_entries
        if not name.startswith(".") and os.path.isfile(os.path.join(artifact_dir, name))
    )
    input_names = sorted(
        name for name in directory_entries if name.endswith(".input.json")
    )
    if not input_names:
        raise ValueError("no quality input artifacts found in %s" % artifact_dir)

    strict_schedule = expected_messages is not None
    validated_official = (
        _validated_official_judge_contract(
            official_contract, kind="quality"
        )
        if official_contract is not None
        else None
    )
    expected_plan: List[Dict[str, Any]] = []
    expected_by_input: Dict[str, Dict[str, Any]] = {}
    if strict_schedule:
        if model is None or batch_size is None or seed is None:
            raise ValueError(
                "strict quality artifact audit requires model, batch_size, and seed"
            )
        expected_plan = build_quality_batch_plan(
            expected_messages or [], str(model), int(batch_size), int(seed)
        )
        expected_by_input = {
            str(row["input_filename"]): row for row in expected_plan
        }
        expected_files = {
            str(row[field])
            for row in expected_plan
            for field in ("input_filename", "output_filename", "meta_filename")
        }
        for row in expected_plan:
            batch_id = str(row["batch_id"])
            expected_files.update(
                {
                    ".%s.provider-claim.json" % batch_id,
                    ".%s.provider-output.json" % batch_id,
                    ".%s.provider-state.json" % batch_id,
                    ".%s.recovery.json" % batch_id,
                }
            )
        strict_entries = set(directory_entries) - set(operational_excluded_files)
        if strict_entries != expected_files:
            missing = sorted(expected_files - strict_entries)
            extra = sorted(strict_entries - expected_files)
            raise ValueError(
                "quality artifact file set differs from frozen schedule "
                "(missing=%s, extra=%s)" % (missing, extra)
            )
        input_names = [str(row["input_filename"]) for row in expected_plan]

    allowed_top = {"batch_id", "model", "prompt_version", "samples"}
    contract_fields = {"prompt_template_sha256", "rubric_sha256"}
    allowed_sample = {"sample_id", "message"}
    all_ids = set()
    models = set()
    n_samples = 0
    result_map: Dict[str, Dict[str, Any]] = {}
    result_binding_map: Dict[str, Dict[str, str]] = {}
    file_manifest: List[Dict[str, str]] = []
    batch_manifest: List[Dict[str, Any]] = []
    for input_name in input_names:
        batch_id = input_name[: -len(".input.json")]
        input_path = os.path.join(artifact_dir, input_name)
        output_path = os.path.join(artifact_dir, batch_id + ".output.json")
        meta_path = os.path.join(artifact_dir, batch_id + ".meta.json")
        claim_path, provider_output_path, state_path = _paid_batch_paths(
            artifact_dir, batch_id
        )
        recovery_path = _quality_recovery_path(artifact_dir, batch_id)
        for path in (output_path, meta_path):
            if not os.path.exists(path):
                raise ValueError(
                    "missing artifact paired with %s: %s" % (input_path, path)
                )

        supplied, _ = _strict_json_file(
            input_path,
            root=artifact_dir,
            label="quality visible input artifact",
        )
        supplied_keys = set(supplied) if isinstance(supplied, Mapping) else set()
        if strict_schedule:
            expected_row = expected_by_input[input_name]
            if supplied != expected_row["input_payload"]:
                raise ValueError(
                    "quality input %s differs from the frozen seed/batch schedule"
                    % input_path
                )
        elif supplied_keys not in (allowed_top, allowed_top | contract_fields):
            raise ValueError(
                "quality input %s has unexpected top-level keys" % input_path
            )
        if supplied["batch_id"] != batch_id:
            raise ValueError("batch id/filename mismatch in %s" % input_path)
        if supplied["prompt_version"] != CODEX_QUALITY_PROMPT_VERSION:
            raise ValueError("unexpected quality prompt version in %s" % input_path)
        if supplied_keys & contract_fields:
            if supplied.get("prompt_template_sha256") != CODEX_QUALITY_PROMPT_SHA256:
                raise ValueError(
                    "unexpected quality prompt template hash in %s" % input_path
                )
            if supplied.get("rubric_sha256") != CODEX_QUALITY_RUBRIC_SHA256:
                raise ValueError("unexpected quality rubric hash in %s" % input_path)
        model = str(supplied["model"])
        models.add(model)
        samples = []
        if not isinstance(supplied["samples"], list):
            raise ValueError("quality input samples are not an array")
        for row in supplied["samples"]:
            if not isinstance(row, Mapping) or set(row) != allowed_sample:
                raise ValueError(
                    "quality sample in %s contains non-blind fields" % input_path
                )
            sample = make_quality_sample(str(row["message"]), model)
            if row["sample_id"] != sample.sample_id:
                raise ValueError(
                    "quality sample id does not match message hash in %s" % input_path
                )
            if sample.sample_id in all_ids:
                raise ValueError(
                    "quality sample id appears in more than one batch: %s"
                    % sample.sample_id
                )
            all_ids.add(sample.sample_id)
            samples.append(sample)

        expected_ids = [sample.sample_id for sample in samples]
        expected_batch = "batch_" + _sha256("\n".join(expected_ids))[:16]
        if batch_id != expected_batch:
            raise ValueError("batch id does not match quality sample ids")

        meta, _ = _strict_json_file(
            meta_path,
            root=artifact_dir,
            label="quality visible metadata artifact",
        )
        if not isinstance(meta, Mapping):
            raise ValueError("quality process metadata is not an object")
        if "stdout" in meta or "stderr" in meta:
            raise ValueError("unsanitized process logs in metadata for %s" % batch_id)
        if meta.get("process_logs_retained") is not False:
            raise ValueError("process-log retention policy missing for %s" % batch_id)
        if any(os.path.isabs(str(value)) for value in meta.get("command_flags", [])):
            raise ValueError("absolute command path retained for %s" % batch_id)
        if meta.get("returncode") != 0:
            raise ValueError("quality judge process failed for %s" % batch_id)
        if meta.get("batch_id") != batch_id:
            raise ValueError("meta batch id differs from quality input")
        if meta.get("model") != model:
            raise ValueError("meta model differs from quality input")
        if meta.get("prompt_version") != CODEX_QUALITY_PROMPT_VERSION:
            raise ValueError("meta prompt version differs from quality input")
        if meta.get(
            "prompt_template_sha256", CODEX_QUALITY_PROMPT_SHA256
        ) != CODEX_QUALITY_PROMPT_SHA256:
            raise ValueError("meta prompt template hash differs from quality input")
        if meta.get("rubric_sha256", CODEX_QUALITY_RUBRIC_SHA256) != (
            CODEX_QUALITY_RUBRIC_SHA256
        ):
            raise ValueError("meta rubric hash differs from quality input")
        if meta.get("sample_ids") != expected_ids:
            raise ValueError("meta sample ids differ from quality input")
        if strict_schedule:
            expected_row = expected_by_input[input_name]
            for field in (
                "schedule_version",
                "batch_index",
                "n_batches",
                "seed",
                "batch_size",
                "message_set_sha256",
            ):
                if meta.get(field) != expected_row[field]:
                    raise ValueError(
                        "quality metadata %s differs from frozen schedule for %s"
                        % (field, batch_id)
                    )
        prompt_sha256 = _sha256(build_quality_prompt(samples))
        if meta.get("prompt_sha256") != prompt_sha256:
            raise ValueError("quality prompt hash mismatch for %s" % batch_id)

        raw = _read_regular_text(
            output_path,
            root=artifact_dir,
            label="quality visible output artifact",
        )
        raw_candidates = [raw]
        if raw.endswith("\n"):
            raw_candidates.append(raw[:-1])
        if meta.get("output_sha256") not in {
            _sha256(candidate) for candidate in raw_candidates
        }:
            raise ValueError("quality output hash mismatch for %s" % batch_id)
        try:
            payload = strict_json_loads(raw)
        except ValueError as exc:
            raise ValueError(
                "invalid saved quality output for %s" % batch_id
            ) from exc
        validated = validate_quality_payload(payload, expected_ids)
        evidence: Optional[Dict[str, Any]] = None
        recovery: Optional[Dict[str, Any]] = None
        if strict_schedule:
            evidence = _audit_paid_batch_evidence(
                kind="quality",
                batch_id=batch_id,
                model=model,
                prompt_version=CODEX_QUALITY_PROMPT_VERSION,
                prompt_template_sha256=CODEX_QUALITY_PROMPT_SHA256,
                rubric_sha256=CODEX_QUALITY_RUBRIC_SHA256,
                prompt_sha256=prompt_sha256,
                input_payload=supplied,
                output_schema=quality_output_schema(expected_ids),
                sample_ids=expected_ids,
                meta=meta,
                visible_output_text=raw,
                claim_path=claim_path,
                provider_output_path=provider_output_path,
                state_path=state_path,
                official_contract=validated_official,
            )
            provider_validated = validate_quality_payload(
                evidence["provider_payload"], expected_ids
            )
            if provider_validated != validated:
                raise ValueError(
                    "quality provider output conflicts with visible output"
                )
            require_regular_nonsymlink(
                recovery_path, label="quality recovery journal"
            )
            recovery, _ = _load_quality_recovery(
                recovery_path, expected_by_input[input_name], model
            )
            if (
                recovery["input_payload"] != supplied
                or recovery["output_text"] != raw
                or recovery["meta"] != meta
            ):
                raise ValueError(
                    "quality recovery journal conflicts with visible artifacts"
                )
        output_sha256 = str(meta["output_sha256"])
        for sample in samples:
            public = _quality_public_result(
                validated[sample.sample_id], sample.sample_id
            )
            if sample.message in result_map:
                raise ValueError("message appears in more than one quality batch")
            result_map[sample.message] = public
            result_binding_map[sample.message] = _quality_artifact_binding(
                sample,
                model,
                batch_id,
                prompt_sha256,
                output_sha256,
                public,
            )
        n_samples += len(samples)
        evidence_paths = [input_path, output_path, meta_path]
        if strict_schedule:
            evidence_paths.extend(
                [claim_path, provider_output_path, state_path, recovery_path]
            )
        files = [
            _json_file_manifest(path, repository_root)
            for path in evidence_paths
        ]
        file_manifest.extend(files)
        batch_entry: Dict[str, Any] = {
            "batch_id": batch_id,
            "batch_index": (
                int(expected_by_input[input_name]["batch_index"])
                if strict_schedule
                else len(batch_manifest) + 1
            ),
            "sample_ids": expected_ids,
            "prompt_sha256": prompt_sha256,
            "input_payload_sha256": canonical_json_sha256(supplied),
            "files": files,
        }
        if evidence is not None and recovery is not None:
            batch_entry["hidden_evidence"] = {
                "provider_claim_sha256": evidence["claim"]["claim_sha256"],
                "provider_state_sha256": evidence["state"]["state_sha256"],
                "provider_output_sha256": evidence["state"]["output_sha256"],
                "provider_output_bytes": evidence["state"]["output_bytes"],
                "recovery_sha256": recovery["recovery_sha256"],
            }
        batch_manifest.append(batch_entry)

    audit = {
        "ok": True,
        "artifact_dir": (
            _repository_local_path(artifact_dir, repository_root)
            if repository_root is not None
            else artifact_dir
        ),
        "n_batches": len(input_names),
        "n_unique_messages": n_samples,
        "models": sorted(models),
        "prompt_version": CODEX_QUALITY_PROMPT_VERSION,
        "prompt_sha256": CODEX_QUALITY_PROMPT_SHA256,
        "prompt_template_sha256": CODEX_QUALITY_PROMPT_SHA256,
        "rubric_sha256": CODEX_QUALITY_RUBRIC_SHA256,
        "result_map": result_map,
        "result_map_sha256": canonical_json_sha256(result_map),
        "result_binding_map": result_binding_map,
        "result_binding_map_sha256": canonical_json_sha256(result_binding_map),
        "input_top_level_keys": sorted(allowed_top | contract_fields),
        "sample_keys_visible_to_judge": sorted(allowed_sample),
        "metadata_fields_visible_to_judge": [],
        "frozen_schedule_enforced": strict_schedule,
        "operational_exclusions": {
            "run_lock_filenames": operational_lock_filenames,
            "excluded_from_artifact_manifest": True,
        },
        "artifact_file_manifest": file_manifest,
        "artifact_file_manifest_sha256": canonical_json_sha256(file_manifest),
        "batch_manifest": batch_manifest,
        "batch_manifest_sha256": canonical_json_sha256(batch_manifest),
    }
    if validated_official is not None:
        audit["official_contract"] = validated_official
        audit["official_contract_sha256"] = validated_official[
            "official_contract_sha256"
        ]
    if strict_schedule:
        audit.update(
            {
                "model": str(model),
                "seed": int(seed),
                "batch_size": int(batch_size),
                "message_set_sha256": str(
                    expected_plan[0]["message_set_sha256"]
                ),
                "expected_batch_plan_sha256": canonical_json_sha256(
                    [
                        {
                            key: value
                            for key, value in row.items()
                            if key != "samples"
                        }
                        for row in expected_plan
                    ]
                ),
            }
        )
    return audit


class CodexQualityJudge:
    """Resumable judge whose per-message cache is published whole-batch atomic."""

    def __init__(
        self,
        model: str,
        cache_path: str,
        artifact_dir: str,
        batch_size: int = 24,
        seed: int = 20261002,
        executable: str = "codex",
        timeout_s: int = 600,
        batch_runner: QualityBatchRunner = run_quality_codex_batch,
        official_contract: Optional[Mapping[str, Any]] = None,
    ) -> None:
        self.model = str(model)
        self.cache_path = cache_path
        self.artifact_dir = artifact_dir
        self.batch_size = batch_size
        self.seed = seed
        self.executable = executable
        self.timeout_s = timeout_s
        self.batch_runner = batch_runner
        self.official_contract = (
            _validate_official_run_coordinates(
                official_contract,
                kind="quality",
                model=model,
                seed=seed,
                batch_size=batch_size,
                prompt_version=CODEX_QUALITY_PROMPT_VERSION,
                prompt_sha256=CODEX_QUALITY_PROMPT_SHA256,
                rubric_sha256=CODEX_QUALITY_RUBRIC_SHA256,
            )
            if official_contract is not None
            else None
        )
        self._require_artifact_binding = batch_runner is run_quality_codex_batch
        self.name = "codex_cli_quality_judge[%s/%s]" % (
            self.model,
            CODEX_QUALITY_PROMPT_VERSION,
        )
        self._cache_message_hashes: Dict[str, str] = {}
        self._cache_bindings: Dict[str, Dict[str, str]] = {}
        self._cache_records: List[Dict[str, Any]] = []
        self._cache = self._load_cache()
        self.n_cached = 0
        self.n_judged = 0

    def _load_cache(self) -> Dict[str, Dict[str, Any]]:
        cache: Dict[str, Dict[str, Any]] = {}
        if not os.path.exists(self.cache_path):
            return cache
        records, _ = _strict_jsonl_file(
            self.cache_path, label="quality judge cache"
        )
        for line_number, record in enumerate(records, start=1):
            try:
                key = str(record["key"])
                message_hash = str(record["message_sha256"])
                value = record["value"]
            except (KeyError, TypeError) as exc:
                raise ValueError(
                    "invalid quality cache record at %s:%d"
                    % (self.cache_path, line_number)
                ) from exc
            if record.get("model") != self.model:
                raise ValueError("quality cache contains a different judge model")
            if len(key) != 64 or any(
                character not in "0123456789abcdef" for character in key
            ):
                raise ValueError("quality cache contains an invalid cache key")
            if record.get("prompt_version") != CODEX_QUALITY_PROMPT_VERSION:
                raise ValueError(
                    "quality cache contains a different prompt version"
                )
            if record.get(
                "prompt_template_sha256", CODEX_QUALITY_PROMPT_SHA256
            ) != CODEX_QUALITY_PROMPT_SHA256:
                raise ValueError("quality cache contains a different prompt hash")
            if record.get(
                "rubric_sha256", CODEX_QUALITY_RUBRIC_SHA256
            ) != CODEX_QUALITY_RUBRIC_SHA256:
                raise ValueError("quality cache contains a different rubric hash")
            if len(message_hash) != 64 or any(
                character not in "0123456789abcdef"
                for character in message_hash
            ):
                raise ValueError("quality cache contains an invalid message hash")
            if not isinstance(value, Mapping):
                raise ValueError("quality cache value is not an object")
            sample_id = value.get("sample_id")
            if not isinstance(sample_id, str):
                raise ValueError("quality cache value has no sample id")
            public = _quality_public_result(value, sample_id)
            if record.get(
                "value_sha256", canonical_json_sha256(public)
            ) != canonical_json_sha256(public):
                raise ValueError("quality cache value hash mismatch")
            binding = record.get("artifact_binding")
            if binding is not None and not isinstance(binding, Mapping):
                raise ValueError("quality cache artifact binding is not an object")
            if key in cache and (
                cache[key] != value
                or self._cache_message_hashes[key] != message_hash
                or self._cache_bindings.get(key)
                != (dict(binding) if binding is not None else None)
            ):
                raise ValueError("conflicting duplicate quality cache key %s" % key)
            cache[key] = dict(value)
            self._cache_records.append(dict(record))
            self._cache_message_hashes[key] = message_hash
            if binding is not None:
                self._cache_bindings[key] = {
                    str(name): str(binding[name]) for name in binding
                }
        return cache

    def _append_cache(
        self,
        samples: Sequence[QualityJudgeSample],
        values: Mapping[str, Mapping[str, Any]],
    ) -> None:
        clean = _normalise_result_map(values, samples)
        bindings = {
            sample.sample_id: dict(values[sample.sample_id]["_artifact_binding"])
            for sample in samples
            if "_artifact_binding" in values[sample.sample_id]
        }
        if self._require_artifact_binding and set(bindings) != {
            sample.sample_id for sample in samples
        }:
            raise ValueError("quality runner omitted required artifact binding")
        parent = os.path.dirname(self.cache_path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        pending_records: List[Dict[str, Any]] = []
        pending_state: List[
            Tuple[QualityJudgeSample, Dict[str, Any], Optional[Dict[str, str]]]
        ] = []
        for sample in samples:
            if sample.cache_key in self._cache:
                raise ValueError("quality cache append would duplicate a cache key")
            value = dict(clean[sample.sample_id])
            message_hash = _sha256(sample.message)
            public = _quality_public_result(value, sample.sample_id)
            binding = bindings.get(sample.sample_id)
            validated_binding = None
            if binding is not None:
                validated_binding = _validated_quality_artifact_binding(
                    binding, sample, self.model, public
                )
                if value.get("_batch_id", validated_binding["batch_id"]) != (
                    validated_binding["batch_id"]
                ):
                    raise ValueError("quality cache batch id/binding mismatch")
                if value.get(
                    "_prompt_version", CODEX_QUALITY_PROMPT_VERSION
                ) != CODEX_QUALITY_PROMPT_VERSION:
                    raise ValueError("quality cache prompt version mismatch")
            record: Dict[str, Any] = {
                "cache_record_version": 2 if validated_binding else 1,
                "key": sample.cache_key,
                "message_sha256": message_hash,
                "model": self.model,
                "prompt_version": CODEX_QUALITY_PROMPT_VERSION,
                "prompt_template_sha256": CODEX_QUALITY_PROMPT_SHA256,
                "rubric_sha256": CODEX_QUALITY_RUBRIC_SHA256,
                "value_sha256": canonical_json_sha256(public),
                "value": value,
            }
            if validated_binding is not None:
                record["artifact_binding"] = validated_binding
            pending_records.append(record)
            pending_state.append((sample, value, validated_binding))

        _atomic_write_jsonl(
            self.cache_path, [*self._cache_records, *pending_records]
        )
        self._cache_records.extend(pending_records)
        for sample, value, validated_binding in pending_state:
            self._cache[sample.cache_key] = value
            self._cache_message_hashes[sample.cache_key] = _sha256(sample.message)
            if validated_binding is not None:
                self._cache_bindings[sample.cache_key] = validated_binding

    def _validated_cached_value(
        self, sample: QualityJudgeSample
    ) -> Dict[str, Any]:
        if self._cache_message_hashes.get(sample.cache_key) != _sha256(
            sample.message
        ):
            raise ValueError("quality cache message hash mismatch")
        clean = _normalise_result_map(
            {sample.sample_id: self._cache[sample.cache_key]}, [sample]
        )
        value = clean[sample.sample_id]
        binding = self._cache_bindings.get(sample.cache_key)
        if binding is not None:
            public = _quality_public_result(value, sample.sample_id)
            checked = _validated_quality_artifact_binding(
                binding, sample, self.model, public
            )
            if value.get("_batch_id", checked["batch_id"]) != checked["batch_id"]:
                raise ValueError("quality cache batch id/binding mismatch")
        return value

    def score_messages(
        self, messages: Iterable[str]
    ) -> Dict[str, Dict[str, Any]]:
        message_list = [str(message) for message in messages]
        batches = build_quality_batches(
            message_list, self.model, self.batch_size, self.seed
        )
        batch_plan = build_quality_batch_plan(
            list(dict.fromkeys(message_list)),
            self.model,
            self.batch_size,
            self.seed,
        )
        if self._require_artifact_binding:
            ordered_samples = [
                sample for row in batch_plan for sample in row["samples"]
            ]
            actual_prefix = [
                (
                    str(record.get("key", "")),
                    str(record.get("value", {}).get("sample_id", ""))
                    if isinstance(record.get("value"), Mapping)
                    else "",
                )
                for record in self._cache_records
            ]
            expected_prefix = [
                (sample.cache_key, sample.sample_id)
                for sample in ordered_samples[: len(actual_prefix)]
            ]
            if actual_prefix != expected_prefix:
                raise ValueError(
                    "quality cache is not an exact prefix of the frozen batch "
                    "schedule"
                )
        for batch_index, batch in enumerate(batches, start=1):
            pending = [
                sample for sample in batch if sample.cache_key not in self._cache
            ]
            cached = [sample for sample in batch if sample.cache_key in self._cache]
            for sample in cached:
                self._validated_cached_value(sample)
            recovered = None
            if self._require_artifact_binding:
                recovered = _recover_quality_batch_from_artifacts(
                    self.artifact_dir,
                    batch_plan[batch_index - 1],
                    self.model,
                )
            if recovered is not None:
                recovered_clean = _normalise_result_map(recovered, batch)
                recovered_bindings = {
                    sample.sample_id: dict(
                        recovered[sample.sample_id]["_artifact_binding"]
                    )
                    for sample in batch
                }
                cached_ids = [sample.sample_id for sample in cached]
                expected_prefix = [
                    sample.sample_id for sample in batch[: len(cached)]
                ]
                if cached_ids != expected_prefix:
                    raise ValueError(
                        "quality partial cache is not a frozen-batch prefix"
                    )
                for sample in cached:
                    if self._cache[sample.cache_key] != recovered_clean[
                        sample.sample_id
                    ] or self._cache_bindings.get(sample.cache_key) != (
                        recovered_bindings.get(sample.sample_id)
                    ):
                        raise ValueError(
                            "quality partial cache differs from recovered artifacts"
                        )
                if pending:
                    self._append_cache(
                        pending,
                        {
                            sample.sample_id: recovered[sample.sample_id]
                            for sample in pending
                        },
                    )
                self.n_cached += len(batch)
                continue
            self.n_cached += len(cached)
            if not pending:
                continue
            if cached and self._require_artifact_binding:
                raise ValueError(
                    "quality frozen batch is only partially cached and has no "
                    "recoverable paid artifacts"
                )
            print(
                "judging blind quality batch %d/%d (%d messages)"
                % (batch_index, len(batches), len(pending)),
                flush=True,
            )
            if self.batch_runner is run_quality_codex_batch:
                values = run_quality_codex_batch(
                    pending,
                    self.model,
                    self.executable,
                    self.artifact_dir,
                    self.timeout_s,
                    batch_context=batch_plan[batch_index - 1],
                    official_contract=self.official_contract,
                )
            else:
                values = self.batch_runner(
                    pending,
                    self.model,
                    self.executable,
                    self.artifact_dir,
                    self.timeout_s,
                )
            self._append_cache(pending, values)
            self.n_judged += len(pending)

        result: Dict[str, Dict[str, Any]] = {}
        for batch in batches:
            for sample in batch:
                result[sample.message] = dict(self._validated_cached_value(sample))
        return result

    def describe(self) -> Dict[str, Any]:
        description = {
            "classifier": self.name,
            "kind": "llm",
            "provider": "codex-cli",
            "model": self.model,
            "judge_prompt_version": CODEX_QUALITY_PROMPT_VERSION,
            "judge_prompt_sha256": CODEX_QUALITY_PROMPT_SHA256,
            "judge_rubric": CODEX_QUALITY_RUBRIC,
            "judge_rubric_sha256": CODEX_QUALITY_RUBRIC_SHA256,
            "quality_score_fields": list(QUALITY_SCORE_FIELDS),
            "quality_issue_codes": list(QUALITY_ISSUE_CODES),
            "batch_size": self.batch_size,
            "shuffle_seed": self.seed,
            "cache_path": self.cache_path,
            "artifact_dir": self.artifact_dir,
        }
        if self.official_contract is not None:
            description["official_contract_sha256"] = self.official_contract[
                "official_contract_sha256"
            ]
        return description


def audit_quality_cache(
    cache_path: str,
    messages: Iterable[str],
    model: str,
    batch_size: int,
    seed: int,
    artifact_audit: Mapping[str, Any],
    *,
    repository_root: Optional[str] = None,
) -> Dict[str, Any]:
    """Replay every quality cache row against exact raw batch artifacts."""
    if not os.path.isfile(cache_path):
        raise FileNotFoundError("quality judge cache not found: %s" % cache_path)
    message_list = _unique_quality_messages(messages)
    plan = build_quality_batch_plan(message_list, model, batch_size, seed)
    ordered_samples = [sample for row in plan for sample in row["samples"]]
    expected_ids = [sample.sample_id for sample in ordered_samples]
    records, cache_raw = _strict_jsonl_file(
        cache_path,
        root=repository_root,
        label="quality judge cache",
    )
    actual_ids = [
        str(record.get("value", {}).get("sample_id", ""))
        if isinstance(record.get("value"), Mapping)
        else ""
        for record in records
    ]
    if actual_ids != expected_ids:
        raise ValueError(
            "quality cache order/coverage differs from frozen seed/batch schedule"
        )

    required_keys = {
        "cache_record_version",
        "key",
        "message_sha256",
        "model",
        "prompt_version",
        "prompt_template_sha256",
        "rubric_sha256",
        "value_sha256",
        "value",
        "artifact_binding",
    }
    artifact_results = artifact_audit.get("result_map")
    artifact_bindings = artifact_audit.get("result_binding_map")
    if not isinstance(artifact_results, Mapping) or not isinstance(
        artifact_bindings, Mapping
    ):
        raise ValueError("quality artifact audit has no replayable results")
    cache_results: Dict[str, Dict[str, Any]] = {}
    for record, sample in zip(records, ordered_samples):
        if set(record) != required_keys:
            raise ValueError("quality cache record fields differ from frozen schema")
        if record["cache_record_version"] != 2:
            raise ValueError(
                "quality cache record is not artifact-bound version 2"
            )
        if record["key"] != sample.cache_key:
            raise ValueError("quality cache key differs from frozen message/model")
        if record["message_sha256"] != _sha256(sample.message):
            raise ValueError("quality cache message hash mismatch")
        if record["model"] != str(model):
            raise ValueError("quality cache model differs from frozen contract")
        if record["prompt_version"] != CODEX_QUALITY_PROMPT_VERSION:
            raise ValueError("quality cache prompt version differs from contract")
        if record["prompt_template_sha256"] != CODEX_QUALITY_PROMPT_SHA256:
            raise ValueError("quality cache prompt hash differs from contract")
        if record["rubric_sha256"] != CODEX_QUALITY_RUBRIC_SHA256:
            raise ValueError("quality cache rubric hash differs from contract")
        value = record["value"]
        if not isinstance(value, Mapping):
            raise ValueError("quality cache value is not an object")
        public = _quality_public_result(value, sample.sample_id)
        if record["value_sha256"] != canonical_json_sha256(public):
            raise ValueError("quality cache value hash mismatch")
        expected_binding = artifact_bindings.get(sample.message)
        if record["artifact_binding"] != expected_binding:
            raise ValueError("quality cache/artifact binding divergence")
        checked_binding = _validated_quality_artifact_binding(
            record["artifact_binding"], sample, model, public
        )
        if value.get("_batch_id") != checked_binding["batch_id"]:
            raise ValueError("quality cache batch id differs from artifact")
        if value.get("_prompt_version") != CODEX_QUALITY_PROMPT_VERSION:
            raise ValueError("quality cache value prompt version differs")
        if artifact_results.get(sample.message) != public:
            raise ValueError("quality cache result differs from raw artifact")
        cache_results[sample.message] = public

    if canonical_json_sha256(cache_results) != artifact_audit.get(
        "result_map_sha256"
    ):
        raise ValueError(
            "quality cache result map differs from artifact result map"
        )
    cache_manifest = _jsonl_file_manifest(
        cache_path, records, repository_root, raw_bytes=cache_raw
    )
    return {
        "ok": True,
        "cache_reconciled": True,
        "cache_file": cache_manifest,
        "n_records": len(records),
        "model": str(model),
        "seed": int(seed),
        "batch_size": int(batch_size),
        "message_set_sha256": _quality_message_set_sha256(message_list),
        "result_map": cache_results,
        "result_map_sha256": canonical_json_sha256(cache_results),
    }


def audit_quality_judge_run(
    messages: Iterable[str],
    model: str,
    batch_size: int,
    seed: int,
    artifact_dir: str,
    cache_path: str,
    *,
    repository_root: str,
    official_contract: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    """Replay one complete quality judge run from repository-local raw files."""
    validated_official = (
        _validate_official_run_coordinates(
            official_contract,
            kind="quality",
            model=model,
            seed=seed,
            batch_size=batch_size,
            prompt_version=CODEX_QUALITY_PROMPT_VERSION,
            prompt_sha256=CODEX_QUALITY_PROMPT_SHA256,
            rubric_sha256=CODEX_QUALITY_RUBRIC_SHA256,
        )
        if official_contract is not None
        else None
    )
    message_list = _unique_quality_messages(messages)
    artifact_audit = audit_quality_artifacts(
        artifact_dir,
        expected_messages=message_list,
        model=model,
        batch_size=batch_size,
        seed=seed,
        repository_root=repository_root,
        official_contract=validated_official,
    )
    cache_audit = audit_quality_cache(
        cache_path,
        message_list,
        model,
        batch_size,
        seed,
        artifact_audit,
        repository_root=repository_root,
    )
    manifest: Dict[str, Any] = {
        "manifest_version": (
            "v6-quality-judge-run-v2"
            if validated_official is not None
            else "v6-quality-judge-run-v1"
        ),
        "kind": "quality",
        "model": str(model),
        "seed": int(seed),
        "batch_size": int(batch_size),
        "message_set_sha256": artifact_audit["message_set_sha256"],
        "expected_batch_plan_sha256": artifact_audit[
            "expected_batch_plan_sha256"
        ],
        "artifact_dir": artifact_audit["artifact_dir"],
        "cache_path": cache_audit["cache_file"]["path"],
        "artifact_file_manifest": artifact_audit["artifact_file_manifest"],
        "artifact_file_manifest_sha256": artifact_audit[
            "artifact_file_manifest_sha256"
        ],
        "batch_manifest": artifact_audit["batch_manifest"],
        "batch_manifest_sha256": artifact_audit["batch_manifest_sha256"],
        "operational_exclusions": artifact_audit["operational_exclusions"],
        "cache_file": cache_audit["cache_file"],
        "result_map_sha256": artifact_audit["result_map_sha256"],
        "result_binding_map_sha256": artifact_audit[
            "result_binding_map_sha256"
        ],
        "frozen_schedule_enforced": True,
        "cache_reconciled": True,
    }
    if validated_official is not None:
        manifest["official_contract"] = validated_official
        manifest["official_contract_sha256"] = validated_official[
            "official_contract_sha256"
        ]
    manifest["manifest_sha256"] = canonical_json_sha256(manifest)
    return {
        **artifact_audit,
        "cache_audit": cache_audit,
        "cache_reconciled": True,
        "judge_run_manifest": manifest,
    }


def replay_quality_judge_run_from_manifest(
    messages: Iterable[str],
    manifest: Mapping[str, Any],
    repository_root: str,
) -> Dict[str, Any]:
    """Independently reconstruct a quality run from its repository manifest."""
    if not isinstance(manifest, Mapping):
        raise ValueError("quality judge run manifest is not an object")
    supplied = dict(manifest)
    manifest_sha256 = supplied.pop("manifest_sha256", None)
    if manifest_sha256 != canonical_json_sha256(supplied):
        raise ValueError("quality judge run manifest hash mismatch")
    manifest_version = supplied.get("manifest_version")
    if manifest_version not in {
        "v6-quality-judge-run-v1",
        "v6-quality-judge-run-v2",
    }:
        raise ValueError("unexpected quality judge run manifest version")
    official_contract = None
    if manifest_version == "v6-quality-judge-run-v2":
        official_contract = supplied.get("official_contract")
        validated_official = _validated_official_judge_contract(
            official_contract, kind="quality"
        )
        if supplied.get("official_contract_sha256") != validated_official[
            "official_contract_sha256"
        ]:
            raise ValueError("quality run manifest official contract mismatch")
    elif "official_contract" in supplied or "official_contract_sha256" in supplied:
        raise ValueError("legacy quality manifest cannot claim official identity")
    artifact_dir = _resolve_repository_path(
        str(supplied.get("artifact_dir", "")), repository_root
    )
    cache_path = _resolve_repository_path(
        str(supplied.get("cache_path", "")), repository_root
    )
    replayed = audit_quality_judge_run(
        messages,
        str(supplied.get("model", "")),
        int(supplied.get("batch_size", 0)),
        int(supplied.get("seed", 0)),
        artifact_dir,
        cache_path,
        repository_root=repository_root,
        official_contract=official_contract,
    )
    if replayed["judge_run_manifest"] != dict(manifest):
        raise ValueError("quality judge run manifest differs from raw-file replay")
    return replayed


def _bank_payload(bank: Any) -> Mapping[str, Any]:
    payload = bank.payload if hasattr(bank, "payload") else bank
    if not isinstance(payload, Mapping):
        raise ValueError("V6 quality bank payload is not a mapping")
    return payload


def audit_v6_quality_pool_payload(payload: Mapping[str, Any]) -> Dict[str, Any]:
    """Delegate structural validation to the canonical V6 bank contract."""
    return audit_v6_bank_payload(payload)


def quality_candidate_rows(bank: Any) -> List[Dict[str, str]]:
    """Render V6 candidates; these metadata rows never enter a judge prompt."""
    payload = _bank_payload(bank)
    audit = audit_v6_quality_pool_payload(payload)
    if not audit["pass"]:
        failed = sorted(
            name for name, passed in audit["checks"].items() if not passed
        )
        raise ValueError("invalid V6 triad pool: %s" % ", ".join(failed))

    rows: List[Dict[str, str]] = []
    for split in ("development", "heldout"):
        for triad in payload["splits"][split]:
            for intended_frame in STRATEGIES:
                entry = triad["candidates"][intended_frame]
                rows.append(
                    {
                        "candidate_id": str(entry["candidate_id"]),
                        "triad_id": str(triad["triad_id"]),
                        "split": split,
                        "intended_frame": intended_frame,
                        "message": " ".join(
                            str(entry["template"]).format(a="Option A").split()
                        ),
                    }
                )
    return rows


def load_v6_quality_pool(path: str) -> V6TriadBank:
    """Load through the canonical V6 structural audit."""
    payload, _ = strict_json_file_identity(
        path, label="V6 quality candidate pool"
    )
    if not isinstance(payload, Mapping):
        raise ValueError("V6 quality candidate pool is not an object")
    audit = audit_v6_quality_pool_payload(payload)
    if not audit["pass"]:
        failed = sorted(
            name for name, passed in audit["checks"].items() if not passed
        )
        raise ValueError("invalid V6 triad bank: %s" % ", ".join(failed))
    return V6TriadBank(payload=dict(payload), source_path=path)


def _validated_judge_results(
    rows: Sequence[Mapping[str, str]],
    results: Mapping[str, Mapping[str, Any]],
) -> Dict[str, Dict[str, Any]]:
    expected_messages = {str(row["message"]) for row in rows}
    if set(results) != expected_messages:
        raise ValueError("quality judge results do not exactly cover the V6 pool")
    clean: Dict[str, Dict[str, Any]] = {}
    for message in expected_messages:
        sample = make_quality_sample(message, "evaluation-placeholder")
        row = dict(results[message])
        if "sample_id" in row and row["sample_id"] != sample.sample_id:
            raise ValueError("quality result sample id does not match its message")
        row["sample_id"] = sample.sample_id
        public = {
            key: value
            for key, value in row.items()
            if key not in {"_artifact_binding", "_batch_id", "_prompt_version"}
        }
        validated = validate_quality_payload(
            {"assessments": [public]}, [sample.sample_id]
        )[sample.sample_id]
        for key in ("_batch_id", "_prompt_version"):
            if key in results[message]:
                validated[key] = results[message][key]
        clean[message] = validated
    return clean


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
            str(message): _quality_public_result(
                result,
                make_quality_sample(str(message), "sample-id-only").sample_id,
            )
            for message, result in artifact_results.items()
            if isinstance(result, Mapping)
        }
        clean_evaluator = {
            str(message): _quality_public_result(
                result,
                make_quality_sample(str(message), "sample-id-only").sample_id,
            )
            for message, result in evaluator_results.items()
        }
    except (TypeError, ValueError):
        return False
    if len(clean_artifact) != len(artifact_results):
        return False
    if artifact_audit.get("result_map_sha256") != canonical_json_sha256(
        clean_artifact
    ):
        return False
    return clean_artifact == clean_evaluator


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


def _candidate_checks(
    result: Mapping[str, Any], thresholds: Mapping[str, float]
) -> Dict[str, bool]:
    return {
        field: float(result[field])
        >= float(thresholds["minimum_candidate_%s" % field])
        for field in QUALITY_SCORE_FIELDS
        if field != "confidence"
    }


def _judge_metrics(
    results: Mapping[str, Mapping[str, Any]],
    pass_by_message: Mapping[str, bool],
    triad_gaps: Sequence[float],
) -> Dict[str, Any]:
    n = len(results)
    return {
        "candidate_pass_rate": sum(pass_by_message.values()) / float(n),
        "score_summary": {
            field: {
                "minimum": min(float(row[field]) for row in results.values()),
                "mean": sum(float(row[field]) for row in results.values()) / float(n),
            }
            for field in QUALITY_SCORE_FIELDS
        },
        "issue_code_counts": dict(
            sorted(Counter(str(row["issue_code"]) for row in results.values()).items())
        ),
        "maximum_within_triad_overall_quality_gap": max(triad_gaps),
    }


def evaluate_v6_quality_validation(
    bank: Any,
    primary_results: Mapping[str, Mapping[str, Any]],
    sensitivity_results: Mapping[str, Mapping[str, Any]],
    primary_description: Mapping[str, Any],
    sensitivity_description: Mapping[str, Any],
    primary_artifact_audit: Mapping[str, Any],
    sensitivity_artifact_audit: Mapping[str, Any],
    thresholds: Optional[Mapping[str, float]] = None,
) -> Dict[str, Any]:
    """Join hidden pool metadata after both blind calls and enforce V6 gates."""
    thresholds = dict(thresholds or CONTROLLED_V6_QUALITY_THRESHOLDS)
    payload = _bank_payload(bank)
    pool_audit = audit_v6_quality_pool_payload(payload)
    rows = quality_candidate_rows(bank)
    primary = _validated_judge_results(rows, primary_results)
    sensitivity = _validated_judge_results(rows, sensitivity_results)

    primary_checks: Dict[str, Dict[str, bool]] = {}
    sensitivity_checks: Dict[str, Dict[str, bool]] = {}
    primary_pass: Dict[str, bool] = {}
    sensitivity_pass: Dict[str, bool] = {}
    candidate_results: List[Dict[str, Any]] = []
    for row in rows:
        message = row["message"]
        primary_checks[message] = _candidate_checks(primary[message], thresholds)
        sensitivity_checks[message] = _candidate_checks(
            sensitivity[message], thresholds
        )
        primary_pass[message] = all(primary_checks[message].values())
        sensitivity_pass[message] = all(sensitivity_checks[message].values())
        candidate_results.append(
            {
                **row,
                "primary_judge": primary[message],
                "sensitivity_judge": sensitivity[message],
                "primary_checks": primary_checks[message],
                "sensitivity_checks": sensitivity_checks[message],
                "passes_both_judges": primary_pass[message]
                and sensitivity_pass[message],
            }
        )

    maximum_gap = float(thresholds["maximum_within_triad_overall_quality_gap"])
    primary_gaps: List[float] = []
    sensitivity_gaps: List[float] = []
    triad_results: List[Dict[str, Any]] = []
    eligible_triads: List[str] = []
    eligible_candidates: List[str] = []
    eligible_counts: Counter = Counter()
    for split in ("development", "heldout"):
        for triad in payload["splits"][split]:
            triad_id = str(triad["triad_id"])
            members = [row for row in rows if row["triad_id"] == triad_id]
            primary_scores = [
                float(primary[row["message"]]["overall_quality"]) for row in members
            ]
            sensitivity_scores = [
                float(sensitivity[row["message"]]["overall_quality"])
                for row in members
            ]
            primary_gap = max(primary_scores) - min(primary_scores)
            sensitivity_gap = max(sensitivity_scores) - min(sensitivity_scores)
            primary_gap_pass = primary_gap <= maximum_gap
            sensitivity_gap_pass = sensitivity_gap <= maximum_gap
            candidates_pass = all(
                primary_pass[row["message"]] and sensitivity_pass[row["message"]]
                for row in members
            )
            eligible = candidates_pass and primary_gap_pass and sensitivity_gap_pass
            if eligible:
                eligible_triads.append(triad_id)
                eligible_candidates.extend(row["candidate_id"] for row in members)
                eligible_counts[split] += 1
            for result_row in candidate_results:
                if result_row["triad_id"] == triad_id:
                    result_row["triad_eligible"] = eligible
            primary_gaps.append(primary_gap)
            sensitivity_gaps.append(sensitivity_gap)
            triad_results.append(
                {
                    "triad_id": triad_id,
                    "split": split,
                    "candidate_ids": [row["candidate_id"] for row in members],
                    "all_candidates_pass_both_judges": candidates_pass,
                    "primary_overall_quality_gap": primary_gap,
                    "sensitivity_overall_quality_gap": sensitivity_gap,
                    "primary_gap_pass": primary_gap_pass,
                    "sensitivity_gap_pass": sensitivity_gap_pass,
                    "eligible": eligible,
                }
            )

    both_pass = {
        message: primary_pass[message] and sensitivity_pass[message]
        for message in primary_pass
    }
    both_pass_rate = sum(both_pass.values()) / float(len(both_pass))
    pass_agreement = sum(
        primary_pass[message] == sensitivity_pass[message]
        for message in primary_pass
    ) / float(len(primary_pass))
    primary_metrics = _judge_metrics(primary, primary_pass, primary_gaps)
    sensitivity_metrics = _judge_metrics(
        sensitivity, sensitivity_pass, sensitivity_gaps
    )

    primary_model = str(primary_description.get("model", ""))
    sensitivity_model = str(sensitivity_description.get("model", ""))
    primary_artifact_results_match = _artifact_results_match(
        primary, primary_artifact_audit
    )
    sensitivity_artifact_results_match = _artifact_results_match(
        sensitivity, sensitivity_artifact_audit
    )
    primary_artifact_contract_match = _artifact_contract_matches(
        primary_description, primary_artifact_audit
    )
    sensitivity_artifact_contract_match = _artifact_contract_matches(
        sensitivity_description, sensitivity_artifact_audit
    )
    gates = {
        "pool_schema_valid": bool(pool_audit.get("pass")),
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
        "primary_candidate_pass_rate": primary_metrics["candidate_pass_rate"]
        >= float(thresholds["minimum_interjudge_candidate_pass_rate"]),
        "sensitivity_candidate_pass_rate": sensitivity_metrics[
            "candidate_pass_rate"
        ]
        >= float(thresholds["minimum_interjudge_candidate_pass_rate"]),
        "interjudge_candidate_pass_rate": both_pass_rate
        >= float(thresholds["minimum_interjudge_candidate_pass_rate"]),
        "enough_development_triads": eligible_counts["development"]
        >= int(thresholds["minimum_eligible_development_triads"]),
        "enough_heldout_triads": eligible_counts["heldout"]
        >= int(thresholds["minimum_eligible_heldout_triads"]),
    }
    pool_hash = (
        str(bank.sha256())
        if callable(getattr(bank, "sha256", None))
        else str(pool_audit["sha256"])
    )
    return {
        "pass": all(gates.values()),
        "scientific_status": (
            "machine-only blind quality/usability gate; not human validation"
        ),
        "pool_id": str(payload.get("pool_id", "")),
        "pool_sha256": pool_hash,
        "pool_audit": pool_audit,
        "n_triads": len(triad_results),
        "n_candidates": len(rows),
        "judge_visible_fields": ["sample_id", "message"],
        "intended_metadata_fields": ["intended_frame", "triad_id", "split"],
        "intended_metadata_supplied_to_judges": False,
        "metadata_joined_after_both_judge_calls": True,
        "thresholds_frozen_before_judging": thresholds,
        "quality_score_fields": list(QUALITY_SCORE_FIELDS),
        "quality_issue_codes": list(QUALITY_ISSUE_CODES),
        "primary_judge": dict(primary_description),
        "sensitivity_judge": dict(sensitivity_description),
        "primary_metrics": primary_metrics,
        "sensitivity_metrics": sensitivity_metrics,
        "both_judges_candidate_pass_rate": both_pass_rate,
        "interjudge_candidate_pass_rate": both_pass_rate,
        "interjudge_pass_agreement": pass_agreement,
        "eligible_counts": {
            split: eligible_counts[split]
            for split in ("development", "heldout")
        },
        "eligible_candidate_ids": eligible_candidates,
        "eligible_triad_ids": eligible_triads,
        "candidate_results": candidate_results,
        "triad_results": triad_results,
        "primary_artifact_audit": dict(primary_artifact_audit),
        "sensitivity_artifact_audit": dict(sensitivity_artifact_audit),
        "gates": gates,
    }


def audit_v6_quality_validation_summary(
    summary: Mapping[str, Any], bank: Any, repository_root: str
) -> Dict[str, Any]:
    """Recompute the quality gate from both raw, artifact-bound judge runs."""
    if not isinstance(summary, Mapping):
        raise ValueError("quality validation summary is not an object")
    contract = summary.get("judge_contract")
    manifests = summary.get("raw_judge_run_manifests")
    if not isinstance(contract, Mapping) or not isinstance(manifests, Mapping):
        raise ValueError("quality summary lacks contract/raw run manifests")
    if set(manifests) != {"primary", "sensitivity"}:
        raise ValueError("quality summary must contain exactly two run manifests")
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
        raise ValueError("quality summary judge contract hash mismatch")
    prompt = quality_judge_contract()
    if any(frozen.get(key) != prompt[key] for key in prompt):
        raise ValueError("quality summary prompt contract mismatch")
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
        raise ValueError("quality summary judge contract is malformed")

    official_contract = contract.get("official_contract")
    if contract.get("official") is True and official_contract is None:
        raise ValueError("official quality summary lacks its runtime/pool contract")
    if official_contract is not None:
        checked_official = _validated_official_judge_contract(
            official_contract, kind="quality"
        )
        if contract.get("official_contract_sha256") != checked_official[
            "official_contract_sha256"
        ]:
            raise ValueError("quality summary official contract hash mismatch")
        if any(checked_official[key] != frozen[key] for key in frozen):
            raise ValueError("quality summary official/prompt contracts diverge")
        pool_contract = checked_official["candidate_pool"]
        supplied_pool_identity = {
            "path": summary.get("pool_source_path"),
            "file_sha256": summary.get("pool_source_file_sha256"),
            "canonical_sha256": summary.get("pool_source_canonical_sha256"),
        }
        if supplied_pool_identity != pool_contract:
            raise ValueError("quality summary candidate pool identity mismatch")
    else:
        checked_official = None

    rows = quality_candidate_rows(bank)
    messages = [row["message"] for row in rows]
    primary_replay = replay_quality_judge_run_from_manifest(
        messages, manifests["primary"], repository_root
    )
    sensitivity_replay = replay_quality_judge_run_from_manifest(
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
                "quality %s run differs from frozen judge contract" % name
            )
        if checked_official is not None and manifest.get(
            "official_contract"
        ) != checked_official:
            raise ValueError(
                "quality %s run differs from official runtime/pool contract" % name
            )

    primary_description = summary.get("primary_judge")
    sensitivity_description = summary.get("sensitivity_judge")
    if not isinstance(primary_description, Mapping) or not isinstance(
        sensitivity_description, Mapping
    ):
        raise ValueError("quality summary judge descriptions are missing")
    recomputed = evaluate_v6_quality_validation(
        bank,
        primary_replay["result_map"],
        sensitivity_replay["result_map"],
        primary_description,
        sensitivity_description,
        primary_replay,
        sensitivity_replay,
    )
    supplied_evaluation = {key: summary.get(key) for key in recomputed}
    if supplied_evaluation != recomputed:
        raise ValueError("quality summary differs from raw-file recomputation")
    recomputed_sha256 = canonical_json_sha256(recomputed)
    if summary.get("recomputed_evaluation_sha256") != recomputed_sha256:
        raise ValueError("quality recomputed evaluation hash mismatch")
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


# Explicit versioned alias for callers that prefer the protocol name.
CodexV6QualityJudge = CodexQualityJudge
