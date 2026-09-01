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
from .blind_judge import sanitize_codex_meta
from .controlled_v6_messages import V6TriadBank, audit_v6_bank_payload


CODEX_QUALITY_PROMPT_VERSION = "codex-v6-quality-blind-v1"
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
        + "\nReturn exactly one schema-valid assessment for each object in "
        "this JSON array:\n\n"
        + json.dumps(payload, ensure_ascii=False, indent=2)
    )


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
        }
        if extra:
            raise ValueError("quality batch result has unexpected internal fields")
        public_rows.append(
            {
                key: value
                for key, value in row.items()
                if key not in {"_batch_id", "_prompt_version"}
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
) -> Dict[str, Dict[str, Any]]:
    """Run one schema-constrained Codex call and retain exact audit artifacts."""
    if not samples:
        return {}
    expected_ids = [sample.sample_id for sample in samples]
    batch_id = "batch_" + _sha256("\n".join(expected_ids))[:16]
    os.makedirs(artifact_dir, exist_ok=True)
    prompt = build_quality_prompt(samples)

    input_path = os.path.join(artifact_dir, batch_id + ".input.json")
    output_path = os.path.join(artifact_dir, batch_id + ".output.json")
    meta_path = os.path.join(artifact_dir, batch_id + ".meta.json")
    with open(input_path, "w", encoding="utf-8") as handle:
        json.dump(
            {
                "batch_id": batch_id,
                "model": model,
                "prompt_version": CODEX_QUALITY_PROMPT_VERSION,
                "samples": [sample.judge_dict() for sample in samples],
            },
            handle,
            indent=2,
            ensure_ascii=False,
        )

    started = time.time()
    with tempfile.TemporaryDirectory(
        prefix="latenttarget_codex_judge_quality_"
    ) as temporary_dir:
        schema_path = os.path.join(temporary_dir, "schema.json")
        final_path = os.path.join(temporary_dir, "final.json")
        with open(schema_path, "w", encoding="utf-8") as handle:
            json.dump(quality_output_schema(expected_ids), handle, indent=2)
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
            final_path,
            "--color",
            "never",
            "--cd",
            temporary_dir,
            "-",
        ]
        completed = process_runner(
            command,
            input=prompt,
            text=True,
            capture_output=True,
            timeout=timeout_s,
            check=False,
        )
        raw = ""
        if os.path.exists(final_path):
            with open(final_path, "r", encoding="utf-8") as handle:
                raw = handle.read()

    elapsed = time.time() - started
    meta = sanitize_codex_meta(
        {
            "batch_id": batch_id,
            "model": model,
            "prompt_version": CODEX_QUALITY_PROMPT_VERSION,
            "sample_ids": expected_ids,
            "returncode": completed.returncode,
            "elapsed_seconds": elapsed,
            "prompt_sha256": _sha256(prompt),
            "output_sha256": _sha256(raw),
            "stdout": completed.stdout,
            "stderr": completed.stderr,
            "command_flags": command[2:-1],
        }
    )
    with open(output_path, "w", encoding="utf-8") as handle:
        handle.write(raw)
        if raw and not raw.endswith("\n"):
            handle.write("\n")
    with open(meta_path, "w", encoding="utf-8") as handle:
        json.dump(meta, handle, indent=2, ensure_ascii=False)

    if completed.returncode != 0:
        raise RuntimeError(
            "Codex quality batch %s failed with exit %d (stderr sha256 %s)"
            % (batch_id, completed.returncode, meta.get("stderr_sha256", "missing"))
        )
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(
            "Codex quality batch %s returned invalid JSON" % batch_id
        ) from exc
    validated = validate_quality_payload(payload, expected_ids)
    for result in validated.values():
        result["_batch_id"] = batch_id
        result["_prompt_version"] = CODEX_QUALITY_PROMPT_VERSION
    return validated


def audit_quality_artifacts(artifact_dir: str) -> Dict[str, Any]:
    """Verify blind fields, prompt/output hashes, and sanitized process metadata."""
    if not os.path.isdir(artifact_dir):
        raise FileNotFoundError(
            "quality artifact directory not found: %s" % artifact_dir
        )
    input_names = sorted(
        name for name in os.listdir(artifact_dir) if name.endswith(".input.json")
    )
    if not input_names:
        raise ValueError("no quality input artifacts found in %s" % artifact_dir)

    allowed_top = {"batch_id", "model", "prompt_version", "samples"}
    allowed_sample = {"sample_id", "message"}
    all_ids = set()
    models = set()
    n_samples = 0
    for input_name in input_names:
        batch_id = input_name[: -len(".input.json")]
        input_path = os.path.join(artifact_dir, input_name)
        output_path = os.path.join(artifact_dir, batch_id + ".output.json")
        meta_path = os.path.join(artifact_dir, batch_id + ".meta.json")
        for path in (output_path, meta_path):
            if not os.path.exists(path):
                raise ValueError(
                    "missing artifact paired with %s: %s" % (input_path, path)
                )

        with open(input_path, "r", encoding="utf-8") as handle:
            supplied = json.load(handle)
        if not isinstance(supplied, Mapping) or set(supplied) != allowed_top:
            raise ValueError(
                "quality input %s has unexpected top-level keys" % input_path
            )
        if supplied["batch_id"] != batch_id:
            raise ValueError("batch id/filename mismatch in %s" % input_path)
        if supplied["prompt_version"] != CODEX_QUALITY_PROMPT_VERSION:
            raise ValueError("unexpected quality prompt version in %s" % input_path)
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

        with open(meta_path, "r", encoding="utf-8") as handle:
            meta = json.load(handle)
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
        if meta.get("sample_ids") != expected_ids:
            raise ValueError("meta sample ids differ from quality input")
        if meta.get("prompt_sha256") != _sha256(build_quality_prompt(samples)):
            raise ValueError("quality prompt hash mismatch for %s" % batch_id)

        with open(output_path, "r", encoding="utf-8") as handle:
            raw = handle.read()
        raw_candidates = [raw]
        if raw.endswith("\n"):
            raw_candidates.append(raw[:-1])
        if meta.get("output_sha256") not in {
            _sha256(candidate) for candidate in raw_candidates
        }:
            raise ValueError("quality output hash mismatch for %s" % batch_id)
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(
                "invalid saved quality output for %s" % batch_id
            ) from exc
        validate_quality_payload(payload, expected_ids)
        n_samples += len(samples)

    return {
        "ok": True,
        "artifact_dir": artifact_dir,
        "n_batches": len(input_names),
        "n_unique_messages": n_samples,
        "models": sorted(models),
        "prompt_version": CODEX_QUALITY_PROMPT_VERSION,
        "input_top_level_keys": sorted(allowed_top),
        "sample_keys_visible_to_judge": sorted(allowed_sample),
        "metadata_fields_visible_to_judge": [],
    }


class CodexQualityJudge:
    """Resumable, per-message cached blind Codex CLI quality judge."""

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
    ) -> None:
        self.model = str(model)
        self.cache_path = cache_path
        self.artifact_dir = artifact_dir
        self.batch_size = batch_size
        self.seed = seed
        self.executable = executable
        self.timeout_s = timeout_s
        self.batch_runner = batch_runner
        self.name = "codex_cli_quality_judge[%s/%s]" % (
            self.model,
            CODEX_QUALITY_PROMPT_VERSION,
        )
        self._cache_message_hashes: Dict[str, str] = {}
        self._cache = self._load_cache()
        self.n_cached = 0
        self.n_judged = 0

    def _load_cache(self) -> Dict[str, Dict[str, Any]]:
        cache: Dict[str, Dict[str, Any]] = {}
        if not os.path.exists(self.cache_path):
            return cache
        with open(self.cache_path, "r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                    key = str(record["key"])
                    message_hash = str(record["message_sha256"])
                    value = record["value"]
                except (json.JSONDecodeError, KeyError, TypeError) as exc:
                    raise ValueError(
                        "invalid quality cache record at %s:%d"
                        % (self.cache_path, line_number)
                    ) from exc
                if record.get("model") != self.model:
                    raise ValueError("quality cache contains a different judge model")
                if record.get("prompt_version") != CODEX_QUALITY_PROMPT_VERSION:
                    raise ValueError(
                        "quality cache contains a different prompt version"
                    )
                if key in cache and (
                    cache[key] != value
                    or self._cache_message_hashes[key] != message_hash
                ):
                    raise ValueError("conflicting duplicate quality cache key %s" % key)
                cache[key] = value
                self._cache_message_hashes[key] = message_hash
        return cache

    def _append_cache(
        self,
        samples: Sequence[QualityJudgeSample],
        values: Mapping[str, Mapping[str, Any]],
    ) -> None:
        clean = _normalise_result_map(values, samples)
        parent = os.path.dirname(self.cache_path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(self.cache_path, "a", encoding="utf-8") as handle:
            for sample in samples:
                value = dict(clean[sample.sample_id])
                message_hash = _sha256(sample.message)
                record = {
                    "key": sample.cache_key,
                    "message_sha256": message_hash,
                    "model": self.model,
                    "prompt_version": CODEX_QUALITY_PROMPT_VERSION,
                    "value": value,
                }
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")
                handle.flush()
                self._cache[sample.cache_key] = value
                self._cache_message_hashes[sample.cache_key] = message_hash

    def score_messages(
        self, messages: Iterable[str]
    ) -> Dict[str, Dict[str, Any]]:
        batches = build_quality_batches(
            messages, self.model, self.batch_size, self.seed
        )
        for batch_index, batch in enumerate(batches, start=1):
            pending = [
                sample for sample in batch if sample.cache_key not in self._cache
            ]
            cached = [sample for sample in batch if sample.cache_key in self._cache]
            for sample in cached:
                if self._cache_message_hashes.get(sample.cache_key) != _sha256(
                    sample.message
                ):
                    raise ValueError("quality cache message hash mismatch")
                _normalise_result_map(
                    {sample.sample_id: self._cache[sample.cache_key]}, [sample]
                )
            self.n_cached += len(cached)
            if not pending:
                continue
            print(
                "judging blind quality batch %d/%d (%d messages)"
                % (batch_index, len(batches), len(pending)),
                flush=True,
            )
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
                clean = _normalise_result_map(
                    {sample.sample_id: self._cache[sample.cache_key]}, [sample]
                )
                result[sample.message] = clean[sample.sample_id]
        return result

    def describe(self) -> Dict[str, Any]:
        return {
            "classifier": self.name,
            "kind": "llm",
            "provider": "codex-cli",
            "model": self.model,
            "judge_prompt_version": CODEX_QUALITY_PROMPT_VERSION,
            "judge_rubric": CODEX_QUALITY_RUBRIC,
            "quality_score_fields": list(QUALITY_SCORE_FIELDS),
            "quality_issue_codes": list(QUALITY_ISSUE_CODES),
            "batch_size": self.batch_size,
            "shuffle_seed": self.seed,
            "cache_path": self.cache_path,
            "artifact_dir": self.artifact_dir,
        }


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
    return V6TriadBank.load(path)


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
            if key not in {"_batch_id", "_prompt_version"}
        }
        validated = validate_quality_payload(
            {"assessments": [public]}, [sample.sample_id]
        )[sample.sample_id]
        for key in ("_batch_id", "_prompt_version"):
            if key in results[message]:
                validated[key] = results[message][key]
        clean[message] = validated
    return clean


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
    gates = {
        "pool_schema_valid": True,
        "judge_models_distinct": bool(primary_model)
        and bool(sensitivity_model)
        and primary_model != sensitivity_model,
        "both_artifact_audits_pass": bool(primary_artifact_audit.get("ok"))
        and bool(sensitivity_artifact_audit.get("ok")),
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
    pool_audit = audit_v6_quality_pool_payload(payload)
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


# Explicit versioned alias for callers that prefer the protocol name.
CodexV6QualityJudge = CodexQualityJudge
