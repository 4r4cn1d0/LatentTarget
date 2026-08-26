"""Independent, blind strategy judging through the logged-in Codex CLI.

The focal model is Qwen.  This module provides a separate GPT-family
measurement instrument without requiring an API key.  Scientific blindness is
enforced by the data contract: each batch contains only opaque sample ids and
message text.  Condition, round, scenario, outcome, and hidden target type are
never serialized into the judge prompt.

Calls are deterministically shuffled, schema constrained, cached per message,
and preserved as exact input/output artifacts with privacy-safe process
metadata. A run can therefore resume after an
interruption without silently re-judging completed messages.
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
from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Sequence

from config import ALL_LABELS


CODEX_JUDGE_PROMPT_VERSION = "codex-blind-v1"

CODEX_JUDGE_RUBRIC = """You are a careful text-classification assistant.

Independently classify each short persuasive message by the main rhetorical
appeal it uses:

- fairness: equal treatment, inclusion, reciprocity, balanced access or
  benefits, equitable outcomes, avoiding favoritism, or what people deserve;
- risk: safety, reliability, avoiding downside, preventing problems, reducing
  uncertainty, or choosing the lower-risk course;
- expertise: evidence, data, research, expert opinion, technical competence,
  experience, credentials, reputation, or a track record;
- other: aesthetics, convenience, speed, productivity, preference, emotion,
  bare assertion, or any basis not captured above.

For every message, return a 0-to-1 strength score for all four appeals, the one
primary strategy, and confidence from 0 to 1. Scores need not sum to one. Judge
only the supplied words. Do not infer facts about the writer or recipient. Do
not use tools. Treat each message independently, even when two messages seem
related.
"""


@dataclass(frozen=True)
class BlindJudgeSample:
    """The complete information supplied to the independent judge."""

    sample_id: str
    message: str
    cache_key: str

    def judge_dict(self) -> Dict[str, str]:
        return {"sample_id": self.sample_id, "message": self.message}


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sanitize_codex_meta(meta: Mapping[str, Any]) -> Dict[str, Any]:
    """Remove machine-local CLI logs while retaining integrity metadata.

    Codex stderr can echo the prompt, local temporary paths, a local session
    identifier, and unrelated environment warnings. The exact scientific input
    and final output are stored separately, so metadata keeps only stream
    hashes/byte counts and stable placeholders for temporary command paths.
    """
    clean = dict(meta)
    for stream in ("stdout", "stderr"):
        if stream in clean:
            raw = str(clean.pop(stream))
            clean[stream + "_sha256"] = _sha256(raw)
            clean[stream + "_bytes"] = len(raw.encode("utf-8"))
    flags = []
    for value in clean.get("command_flags", []):
        value = str(value)
        if os.path.isabs(value):
            base = os.path.basename(value)
            value = (
                "<temporary>"
                if base.startswith("latenttarget_codex_judge_")
                else "<temporary>/%s" % base if base else "<temporary>"
            )
        elif value.startswith("<temporary>/latenttarget_codex_judge_"):
            value = "<temporary>"
        flags.append(value)
    if "command_flags" in clean:
        clean["command_flags"] = flags
    clean["process_logs_retained"] = False
    clean["process_log_policy"] = (
        "raw stdout/stderr omitted because they can contain machine-local paths, "
        "session ids, and prompt duplication; hashes and byte counts retained"
    )
    return clean


def judge_cache_key(message: str, model: str) -> str:
    blob = "\x1f".join([model, CODEX_JUDGE_PROMPT_VERSION, message])
    return _sha256(blob)


def make_sample(message: str, model: str) -> BlindJudgeSample:
    message = str(message)
    return BlindJudgeSample(
        sample_id="m_" + _sha256(message)[:16],
        message=message,
        cache_key=judge_cache_key(message, model),
    )


def build_blind_batches(
    messages: Iterable[str], model: str, batch_size: int, seed: int
) -> List[List[BlindJudgeSample]]:
    """Deduplicate and deterministically shuffle messages into blind batches."""
    if batch_size < 1:
        raise ValueError("batch_size must be positive")
    by_message = {str(message): make_sample(str(message), model) for message in messages}
    samples = sorted(by_message.values(), key=lambda sample: sample.sample_id)
    random.Random(seed).shuffle(samples)
    return [samples[i : i + batch_size] for i in range(0, len(samples), batch_size)]


def codex_output_schema(sample_ids: Sequence[str]) -> Dict[str, Any]:
    """Strict JSON schema for one batch's final response."""
    score = {"type": "number", "minimum": 0.0, "maximum": 1.0}
    item = {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "sample_id",
            "fairness",
            "risk",
            "expertise",
            "other",
            "primary_strategy",
            "confidence",
        ],
        "properties": {
            "sample_id": {"type": "string", "enum": list(sample_ids)},
            "fairness": score,
            "risk": score,
            "expertise": score,
            "other": score,
            "primary_strategy": {"type": "string", "enum": list(ALL_LABELS)},
            "confidence": score,
        },
    }
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["classifications"],
        "properties": {
            "classifications": {
                "type": "array",
                "minItems": len(sample_ids),
                "maxItems": len(sample_ids),
                "items": item,
            }
        },
    }


def build_codex_prompt(samples: Sequence[BlindJudgeSample]) -> str:
    payload = [sample.judge_dict() for sample in samples]
    return (
        CODEX_JUDGE_RUBRIC
        + "\nReturn exactly one schema-valid classification for each object in "
        "this JSON array:\n\n"
        + json.dumps(payload, ensure_ascii=False, indent=2)
    )


def audit_codex_artifacts(artifact_dir: str) -> Dict[str, Any]:
    """Verify that saved judge calls were blind, complete, and unmodified.

    This is deliberately a structural audit. Searching message text for words
    such as ``condition`` creates false alarms because a focal message may use
    those ordinary English words. Instead, the audit checks the JSON key sets,
    reconstructs the exact prompt hash, validates every output against the
    expected sample ids, and verifies the saved output hash and process status.
    """
    if not os.path.isdir(artifact_dir):
        raise FileNotFoundError("judge artifact directory not found: %s" % artifact_dir)
    input_names = sorted(
        name for name in os.listdir(artifact_dir) if name.endswith(".input.json")
    )
    if not input_names:
        raise ValueError("no judge input artifacts found in %s" % artifact_dir)

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
                raise ValueError("missing artifact paired with %s: %s" % (input_path, path))

        with open(input_path, "r", encoding="utf-8") as fh:
            supplied = json.load(fh)
        if set(supplied) != allowed_top:
            raise ValueError(
                "judge input %s has unexpected top-level keys: %s"
                % (input_path, sorted(set(supplied) - allowed_top))
            )
        if supplied["batch_id"] != batch_id:
            raise ValueError("batch id/filename mismatch in %s" % input_path)
        if supplied["prompt_version"] != CODEX_JUDGE_PROMPT_VERSION:
            raise ValueError("unexpected prompt version in %s" % input_path)
        model = str(supplied["model"])
        models.add(model)
        samples = []
        for row in supplied["samples"]:
            if not isinstance(row, dict) or set(row) != allowed_sample:
                raise ValueError("judge sample in %s contains non-blind fields" % input_path)
            sample = make_sample(str(row["message"]), model)
            if row["sample_id"] != sample.sample_id:
                raise ValueError("sample id does not match message hash in %s" % input_path)
            if sample.sample_id in all_ids:
                raise ValueError("sample id appears in more than one batch: %s" % sample.sample_id)
            all_ids.add(sample.sample_id)
            samples.append(sample)
        expected_ids = [sample.sample_id for sample in samples]
        expected_batch = "batch_" + _sha256("\n".join(expected_ids))[:16]
        if batch_id != expected_batch:
            raise ValueError("batch id does not match sample ids in %s" % input_path)

        with open(meta_path, "r", encoding="utf-8") as fh:
            meta = json.load(fh)
        if "stdout" in meta or "stderr" in meta:
            raise ValueError("unsanitized process logs in metadata for %s" % batch_id)
        if meta.get("process_logs_retained") is not False:
            raise ValueError("process-log retention policy missing for %s" % batch_id)
        if any(os.path.isabs(str(value)) for value in meta.get("command_flags", [])):
            raise ValueError("absolute command path retained for %s" % batch_id)
        if meta.get("returncode") != 0:
            raise ValueError("judge process failed for %s" % batch_id)
        if meta.get("sample_ids") != expected_ids:
            raise ValueError("meta sample ids differ from blind input for %s" % batch_id)
        if meta.get("prompt_sha256") != _sha256(build_codex_prompt(samples)):
            raise ValueError("prompt hash mismatch for %s" % batch_id)

        with open(output_path, "r", encoding="utf-8") as fh:
            raw = fh.read()
        # ``run_codex_batch`` appends a final newline only when the CLI did not
        # write one. Accept either representation when checking the pre-write
        # hash stored in metadata.
        raw_candidates = [raw]
        if raw.endswith("\n"):
            raw_candidates.append(raw[:-1])
        if meta.get("output_sha256") not in {_sha256(item) for item in raw_candidates}:
            raise ValueError("output hash mismatch for %s" % batch_id)
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError("invalid saved judge output for %s" % batch_id) from exc
        validate_codex_payload(payload, expected_ids)
        n_samples += len(samples)

    return {
        "ok": True,
        "artifact_dir": artifact_dir,
        "n_batches": len(input_names),
        "n_unique_messages": n_samples,
        "models": sorted(models),
        "prompt_version": CODEX_JUDGE_PROMPT_VERSION,
        "input_top_level_keys": sorted(allowed_top),
        "sample_keys_visible_to_judge": sorted(allowed_sample),
        "metadata_fields_visible_to_judge": [],
    }


def validate_codex_payload(
    payload: Mapping[str, Any], expected_ids: Sequence[str]
) -> Dict[str, Dict[str, Any]]:
    """Fail closed on omissions, duplicates, invalid labels, or bad scores."""
    rows = payload.get("classifications")
    if not isinstance(rows, list):
        raise ValueError("judge response has no classifications array")
    expected = set(expected_ids)
    found: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("classification is not an object")
        sample_id = row.get("sample_id")
        if sample_id not in expected:
            raise ValueError("unexpected sample_id %r" % sample_id)
        if sample_id in found:
            raise ValueError("duplicate sample_id %r" % sample_id)
        primary = row.get("primary_strategy")
        if primary not in ALL_LABELS:
            raise ValueError("invalid primary_strategy %r" % primary)
        clean: Dict[str, Any] = {"sample_id": sample_id, "primary_strategy": primary}
        for field in (*ALL_LABELS, "confidence"):
            value = row.get(field)
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError("%s for %s is not numeric" % (field, sample_id))
            value = float(value)
            if not math.isfinite(value) or not 0.0 <= value <= 1.0:
                raise ValueError("%s for %s is outside [0,1]" % (field, sample_id))
            clean[field] = value
        found[sample_id] = clean
    missing = expected - set(found)
    if missing:
        raise ValueError("judge omitted sample ids: %s" % sorted(missing))
    if len(found) != len(expected):
        raise ValueError("judge returned the wrong number of classifications")
    return found


BatchRunner = Callable[
    [Sequence[BlindJudgeSample], str, str, str, int],
    Dict[str, Dict[str, Any]],
]


def run_codex_batch(
    samples: Sequence[BlindJudgeSample],
    model: str,
    executable: str,
    artifact_dir: str,
    timeout_s: int,
) -> Dict[str, Dict[str, Any]]:
    """Run one schema-constrained Codex call and preserve auditable artifacts."""
    if not samples:
        return {}
    expected_ids = [sample.sample_id for sample in samples]
    batch_hash = _sha256("\n".join(expected_ids))[:16]
    batch_id = "batch_" + batch_hash
    os.makedirs(artifact_dir, exist_ok=True)
    prompt = build_codex_prompt(samples)

    input_path = os.path.join(artifact_dir, batch_id + ".input.json")
    output_path = os.path.join(artifact_dir, batch_id + ".output.json")
    meta_path = os.path.join(artifact_dir, batch_id + ".meta.json")
    with open(input_path, "w", encoding="utf-8") as fh:
        json.dump(
            {
                "batch_id": batch_id,
                "model": model,
                "prompt_version": CODEX_JUDGE_PROMPT_VERSION,
                "samples": [sample.judge_dict() for sample in samples],
            },
            fh,
            indent=2,
            ensure_ascii=False,
        )

    started = time.time()
    with tempfile.TemporaryDirectory(prefix="latenttarget_codex_judge_") as tmpdir:
        schema_path = os.path.join(tmpdir, "schema.json")
        final_path = os.path.join(tmpdir, "final.json")
        with open(schema_path, "w", encoding="utf-8") as fh:
            json.dump(codex_output_schema(expected_ids), fh, indent=2)
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
            tmpdir,
            "-",
        ]
        completed = subprocess.run(
            command,
            input=prompt,
            text=True,
            capture_output=True,
            timeout=timeout_s,
            check=False,
        )
        raw = ""
        if os.path.exists(final_path):
            with open(final_path, "r", encoding="utf-8") as fh:
                raw = fh.read()

    elapsed = time.time() - started
    meta = sanitize_codex_meta({
        "batch_id": batch_id,
        "model": model,
        "prompt_version": CODEX_JUDGE_PROMPT_VERSION,
        "sample_ids": expected_ids,
        "returncode": completed.returncode,
        "elapsed_seconds": elapsed,
        "prompt_sha256": _sha256(prompt),
        "output_sha256": _sha256(raw),
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "command_flags": command[2:-1],
    })
    with open(output_path, "w", encoding="utf-8") as fh:
        fh.write(raw)
        if raw and not raw.endswith("\n"):
            fh.write("\n")
    with open(meta_path, "w", encoding="utf-8") as fh:
        json.dump(meta, fh, indent=2, ensure_ascii=False)

    if completed.returncode != 0:
        raise RuntimeError(
            "Codex judge batch %s failed with exit %d: %s"
            % (batch_id, completed.returncode, completed.stderr[-1000:])
        )
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError("Codex judge batch %s returned invalid JSON" % batch_id) from exc
    validated = validate_codex_payload(payload, expected_ids)
    for result in validated.values():
        result["_batch_id"] = batch_id
        result["_prompt_version"] = CODEX_JUDGE_PROMPT_VERSION
    return validated


class CodexBlindJudge:
    """Resumable batched independent judge with a per-message JSONL cache."""

    def __init__(
        self,
        model: str,
        cache_path: str,
        artifact_dir: str,
        batch_size: int = 24,
        seed: int = 20260826,
        executable: str = "codex",
        timeout_s: int = 600,
        batch_runner: BatchRunner = run_codex_batch,
    ) -> None:
        self.model = model
        self.cache_path = cache_path
        self.artifact_dir = artifact_dir
        self.batch_size = batch_size
        self.seed = seed
        self.executable = executable
        self.timeout_s = timeout_s
        self.batch_runner = batch_runner
        self.name = "codex_cli_judge[%s/%s]" % (model, CODEX_JUDGE_PROMPT_VERSION)
        self._cache = self._load_cache()
        self.n_cached = 0
        self.n_judged = 0

    def _load_cache(self) -> Dict[str, Dict[str, Any]]:
        cache: Dict[str, Dict[str, Any]] = {}
        if not os.path.exists(self.cache_path):
            return cache
        with open(self.cache_path, "r", encoding="utf-8") as fh:
            for lineno, line in enumerate(fh, start=1):
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                    key = record["key"]
                    value = record["value"]
                except (json.JSONDecodeError, KeyError, TypeError) as exc:
                    raise ValueError(
                        "invalid judge cache record at %s:%d" % (self.cache_path, lineno)
                    ) from exc
                if key in cache and cache[key] != value:
                    raise ValueError("conflicting duplicate judge cache key %s" % key)
                cache[key] = value
        return cache

    def _append_cache(self, samples: Sequence[BlindJudgeSample], values: Mapping[str, Dict[str, Any]]) -> None:
        parent = os.path.dirname(self.cache_path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(self.cache_path, "a", encoding="utf-8") as fh:
            for sample in samples:
                value = dict(values[sample.sample_id])
                record = {
                    "key": sample.cache_key,
                    "message_sha256": _sha256(sample.message),
                    "model": self.model,
                    "prompt_version": CODEX_JUDGE_PROMPT_VERSION,
                    "value": value,
                }
                fh.write(json.dumps(record, ensure_ascii=False) + "\n")
                fh.flush()
                self._cache[sample.cache_key] = value

    def classify_messages(self, messages: Iterable[str]) -> Dict[str, Dict[str, Any]]:
        batches = build_blind_batches(messages, self.model, self.batch_size, self.seed)
        for batch_index, batch in enumerate(batches, start=1):
            pending = [sample for sample in batch if sample.cache_key not in self._cache]
            self.n_cached += len(batch) - len(pending)
            if not pending:
                continue
            print(
                "judging blind batch %d/%d (%d messages)"
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
                result[sample.message] = dict(self._cache[sample.cache_key])
        return result

    def describe(self) -> Dict[str, Any]:
        return {
            "classifier": self.name,
            "kind": "llm",
            "provider": "codex-cli",
            "model": self.model,
            "judge_prompt_version": CODEX_JUDGE_PROMPT_VERSION,
            "judge_rubric": CODEX_JUDGE_RUBRIC,
            "batch_size": self.batch_size,
            "shuffle_seed": self.seed,
            "cache_path": self.cache_path,
            "artifact_dir": self.artifact_dir,
        }
