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
import shutil
import stat
import subprocess
import tempfile
import time
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

from config import ALL_LABELS
from .file_lock import (
    fsync_directory_best_effort,
    require_directory_nonsymlink,
    require_regular_nonsymlink,
)
from .logging_utils import (
    open_regular_read_descriptor,
    strict_json_loads,
)


CODEX_JUDGE_PROMPT_VERSION = "codex-blind-v1"

CODEX_JUDGE_PROMPT_INSTRUCTION = (
    "\nReturn exactly one schema-valid classification for each object in "
    "this JSON array:\n\n"
)

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


def canonical_json_sha256(value: Any) -> str:
    """Hash a JSON value using the repository's canonical serialization."""
    canonical = json.dumps(
        value,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
        allow_nan=False,
    )
    return _sha256(canonical)


def _read_regular_bytes(
    path: str,
    *,
    root: Optional[str] = None,
    label: str = "artifact",
) -> bytes:
    """Read one descriptor-opened regular file without following symlinks.

    ``open_regular_read_descriptor`` adds both ``O_NOFOLLOW`` and
    ``O_NONBLOCK`` before checking ``fstat``.  In particular, an attacker-owned
    FIFO is rejected without waiting for a writer.
    """
    descriptor = open_regular_read_descriptor(path, root=root, label=label)
    with os.fdopen(descriptor, "rb") as handle:
        return handle.read()


def _read_regular_text(
    path: str,
    *,
    root: Optional[str] = None,
    label: str = "artifact",
) -> str:
    try:
        return _read_regular_bytes(path, root=root, label=label).decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("%s is not valid UTF-8: %s" % (label, path)) from exc


def _strict_json_file(
    path: str,
    *,
    root: Optional[str] = None,
    label: str = "JSON artifact",
) -> Tuple[Any, bytes]:
    raw = _read_regular_bytes(path, root=root, label=label)
    try:
        return strict_json_loads(raw.decode("utf-8")), raw
    except (UnicodeDecodeError, ValueError) as exc:
        raise ValueError("%s is not strict JSON: %s" % (label, path)) from exc


def _strict_jsonl_file(
    path: str,
    *,
    root: Optional[str] = None,
    label: str = "JSONL artifact",
) -> Tuple[List[Dict[str, Any]], bytes]:
    raw = _read_regular_bytes(path, root=root, label=label)
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("%s is not valid UTF-8: %s" % (label, path)) from exc
    records: List[Dict[str, Any]] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            value = strict_json_loads(line)
        except ValueError as exc:
            raise ValueError(
                "%s has invalid strict JSON at %s:%d"
                % (label, path, line_number)
            ) from exc
        if not isinstance(value, Mapping):
            raise ValueError(
                "%s record at %s:%d is not an object"
                % (label, path, line_number)
            )
        records.append(dict(value))
    return records, raw


def strict_json_file_identity(
    path: str,
    *,
    repository_root: Optional[str] = None,
    label: str = "JSON artifact",
) -> Tuple[Any, Dict[str, str]]:
    """Strict-load a regular JSON file and attest the exact bytes and value."""
    payload, raw = _strict_json_file(
        path, root=repository_root, label=label
    )
    display_path = (
        _repository_local_path(path, repository_root)
        if repository_root is not None
        else os.path.basename(path)
    )
    return payload, {
        "path": display_path,
        "file_sha256": hashlib.sha256(raw).hexdigest(),
        "canonical_sha256": canonical_json_sha256(payload),
    }


def _atomic_write_text(path: str, text: str) -> None:
    """Durably replace ``path`` with one complete UTF-8 text payload."""
    parent = os.path.dirname(path) or "."
    os.makedirs(parent, exist_ok=True)
    descriptor, temporary_path = tempfile.mkstemp(
        prefix=".%s.tmp-" % os.path.basename(path), dir=parent
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, path)
        fsync_directory_best_effort(parent)
    except BaseException:
        if os.path.exists(temporary_path):
            os.unlink(temporary_path)
        raise


def _atomic_write_json(path: str, payload: Mapping[str, Any]) -> None:
    _atomic_write_text(
        path,
        json.dumps(
            payload,
            indent=2,
            ensure_ascii=False,
            allow_nan=False,
        ),
    )


def _atomic_write_jsonl(
    path: str, records: Sequence[Mapping[str, Any]]
) -> None:
    """Replace a JSONL cache in one rename, never exposing a partial batch."""
    text = "".join(
        json.dumps(record, ensure_ascii=False, allow_nan=False) + "\n"
        for record in records
    )
    _atomic_write_text(path, text)


def publish_exact_json(path: str, payload: Mapping[str, Any]) -> bool:
    """Atomically publish JSON once, accepting an exact prior publication.

    Returns ``True`` when this call publishes the file and ``False`` when an
    identical JSON value already exists.  A temporary hard link gives us an
    atomic no-overwrite publish, so concurrent or resumed finalization cannot
    silently replace a different result.
    """

    expected = json.dumps(
        payload,
        indent=2,
        ensure_ascii=False,
        allow_nan=False,
    )

    def assert_existing_exact() -> None:
        try:
            existing, _ = _strict_json_file(
                path, label="existing JSON publication"
            )
        except (OSError, ValueError) as exc:
            raise ValueError(
                "existing JSON publication is unreadable: %s" % path
            ) from exc
        if canonical_json_sha256(existing) != canonical_json_sha256(payload):
            raise ValueError(
                "existing JSON publication differs from recomputation: %s" % path
            )

    if os.path.lexists(path):
        assert_existing_exact()
        return False

    parent = os.path.dirname(path) or "."
    os.makedirs(parent, exist_ok=True)
    descriptor, temporary_path = tempfile.mkstemp(
        prefix=".%s.publish-" % os.path.basename(path), dir=parent
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(expected)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temporary_path, path)
        except FileExistsError:
            assert_existing_exact()
            return False
        fsync_directory_best_effort(parent)
        return True
    finally:
        if os.path.exists(temporary_path):
            os.unlink(temporary_path)


PAID_BATCH_CLAIM_VERSION = "v6-paid-codex-claim-v1"
OFFICIAL_PAID_BATCH_CLAIM_VERSION = "v6-paid-codex-claim-v2"
PAID_BATCH_STATE_VERSION = "v6-paid-codex-state-v1"
OFFICIAL_JUDGE_CONTRACT_VERSION = "v6-official-codex-judge-contract-v1"

_CODEX_RUNTIME_FIELDS = (
    "codex_executable",
    "codex_cli_version",
    "codex_executable_sha256",
)
_CANDIDATE_POOL_FIELDS = (
    "path",
    "file_sha256",
    "canonical_sha256",
)


class PaidBatchReconciliationError(RuntimeError):
    """A paid call may have happened and therefore must not be repeated."""


def _paid_batch_reconciliation_error(
    kind: str, batch_id: str, reason: str
) -> PaidBatchReconciliationError:
    return PaidBatchReconciliationError(
        "%s batch %s requires terminal manual reconciliation; refusing to "
        "repeat a possibly paid Codex call: %s" % (kind, batch_id, reason)
    )


def _paid_batch_paths(
    artifact_dir: str, batch_id: str
) -> Tuple[str, str, str]:
    """Return immutable claim, direct provider output, and terminal-state paths."""
    return (
        os.path.join(artifact_dir, ".%s.provider-claim.json" % batch_id),
        os.path.join(artifact_dir, ".%s.provider-output.json" % batch_id),
        os.path.join(artifact_dir, ".%s.provider-state.json" % batch_id),
    )


def _validated_official_judge_contract(
    contract: Mapping[str, Any], *, kind: Optional[str] = None
) -> Dict[str, Any]:
    """Validate the portable identity contract embedded in official evidence."""
    if not isinstance(contract, Mapping):
        raise ValueError("official judge contract is not an object")
    required = {
        "contract_version",
        "kind",
        "models",
        "seeds",
        "batch_size",
        "prompt_version",
        "prompt_sha256",
        "rubric_sha256",
        "candidate_pool",
        "codex_runtime",
        "official_contract_sha256",
    }
    if set(contract) != required:
        raise ValueError("official judge contract schema mismatch")
    payload = dict(contract)
    supplied_hash = payload.pop("official_contract_sha256")
    if not _is_sha256(supplied_hash) or supplied_hash != canonical_json_sha256(
        payload
    ):
        raise ValueError("official judge contract hash mismatch")
    if payload["contract_version"] != OFFICIAL_JUDGE_CONTRACT_VERSION:
        raise ValueError("official judge contract version mismatch")
    if kind is not None and payload["kind"] != kind:
        raise ValueError("official judge contract kind mismatch")
    if payload["kind"] not in {"semantic", "quality"}:
        raise ValueError("official judge contract has invalid kind")
    if (
        not isinstance(payload["models"], list)
        or len(payload["models"]) != 2
        or not all(isinstance(value, str) and value for value in payload["models"])
    ):
        raise ValueError("official judge contract has invalid models")
    if (
        not isinstance(payload["seeds"], list)
        or len(payload["seeds"]) != 2
        or any(isinstance(value, bool) or not isinstance(value, int) for value in payload["seeds"])
    ):
        raise ValueError("official judge contract has invalid seeds")
    if (
        isinstance(payload["batch_size"], bool)
        or not isinstance(payload["batch_size"], int)
        or payload["batch_size"] < 1
    ):
        raise ValueError("official judge contract has invalid batch size")
    if not isinstance(payload["prompt_version"], str) or not payload[
        "prompt_version"
    ]:
        raise ValueError("official judge contract has invalid prompt version")
    for field in ("prompt_sha256", "rubric_sha256"):
        if not _is_sha256(payload[field]):
            raise ValueError("official judge contract has invalid %s" % field)

    candidate_pool = payload["candidate_pool"]
    if not isinstance(candidate_pool, Mapping) or set(candidate_pool) != set(
        _CANDIDATE_POOL_FIELDS
    ):
        raise ValueError("official judge contract candidate pool schema mismatch")
    if (
        not isinstance(candidate_pool["path"], str)
        or not candidate_pool["path"]
        or os.path.isabs(candidate_pool["path"])
        or candidate_pool["path"].replace("\\", "/") != candidate_pool["path"]
        or any(
            part in {"", os.curdir, os.pardir}
            for part in candidate_pool["path"].split("/")
        )
    ):
        raise ValueError("official candidate pool path is not repository-local")
    for field in ("file_sha256", "canonical_sha256"):
        if not _is_sha256(candidate_pool[field]):
            raise ValueError("official candidate pool has invalid %s" % field)

    runtime = payload["codex_runtime"]
    if not isinstance(runtime, Mapping) or set(runtime) != set(
        _CODEX_RUNTIME_FIELDS
    ):
        raise ValueError("official Codex runtime schema mismatch")
    if runtime["codex_executable"] != "codex":
        raise ValueError("official Codex executable token must be exactly 'codex'")
    if not isinstance(runtime["codex_cli_version"], str) or not runtime[
        "codex_cli_version"
    ]:
        raise ValueError("official Codex CLI version is missing")
    if not _is_sha256(runtime["codex_executable_sha256"]):
        raise ValueError("official Codex executable SHA-256 is invalid")
    return dict(contract)


def attest_codex_executable(
    executable: str,
    expected_runtime: Mapping[str, Any],
    *,
    process_runner: Callable[..., Any] = subprocess.run,
    version_timeout_s: int = 15,
) -> Dict[str, str]:
    """Resolve and attest the one frozen Codex executable for official runs."""
    expected = {field: expected_runtime.get(field) for field in _CODEX_RUNTIME_FIELDS}
    if set(expected_runtime) != set(_CODEX_RUNTIME_FIELDS):
        raise ValueError("official Codex runtime schema mismatch")
    if executable != "codex" or expected["codex_executable"] != "codex":
        raise ValueError(
            "official mode forbids --codex-executable overrides; use exactly 'codex'"
        )
    resolved_token = shutil.which("codex")
    if not resolved_token:
        raise FileNotFoundError("official Codex executable was not found on PATH")
    resolved = os.path.realpath(resolved_token)
    try:
        metadata = os.lstat(resolved)
    except OSError as exc:
        raise ValueError("resolved Codex executable is unreadable") from exc
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
        raise ValueError(
            "resolved Codex executable must be a regular nonsymlink file"
        )
    if not os.access(resolved, os.X_OK):
        raise ValueError("resolved Codex executable is not executable")
    executable_bytes = _read_regular_bytes(
        resolved, label="resolved Codex executable"
    )
    executable_sha256 = hashlib.sha256(executable_bytes).hexdigest()
    if executable_sha256 != expected["codex_executable_sha256"]:
        raise ValueError("Codex executable SHA-256 differs from frozen protocol")
    try:
        completed = process_runner(
            [resolved, "--version"],
            text=True,
            capture_output=True,
            timeout=version_timeout_s,
            check=False,
        )
    except BaseException as exc:
        raise ValueError("Codex --version attestation failed") from exc
    if completed.returncode != 0 or not isinstance(completed.stdout, str):
        raise ValueError("Codex --version attestation did not exit successfully")
    version = completed.stdout.rstrip("\r\n")
    if not version or "\n" in version or "\r" in version:
        raise ValueError("Codex --version output is not one exact line")
    if version != expected["codex_cli_version"]:
        raise ValueError("Codex --version differs from frozen protocol")
    return {
        "codex_executable": "codex",
        "codex_cli_version": version,
        "codex_executable_sha256": executable_sha256,
        "resolved_executable": resolved,
    }


def _verify_official_executable_for_dispatch(
    executable: str,
    official_contract: Mapping[str, Any],
    *,
    kind: str,
    model: str,
) -> Dict[str, Any]:
    """Recheck the resolved executable bytes immediately before a paid claim."""
    contract = _validated_official_judge_contract(
        official_contract, kind=kind
    )
    if str(model) not in contract["models"]:
        raise ValueError("official judge model is outside the frozen contract")
    if not os.path.isabs(executable) or os.path.realpath(executable) != executable:
        raise ValueError(
            "official dispatch requires the resolved nonsymlink Codex path"
        )
    metadata = os.lstat(executable)
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
        raise ValueError(
            "official dispatch Codex executable must be a regular nonsymlink file"
        )
    actual_sha256 = hashlib.sha256(
        _read_regular_bytes(executable, label="official Codex executable")
    ).hexdigest()
    if actual_sha256 != contract["codex_runtime"][
        "codex_executable_sha256"
    ]:
        raise ValueError("official dispatch Codex executable hash changed")
    return contract


def _validate_official_run_coordinates(
    official_contract: Mapping[str, Any],
    *,
    kind: str,
    model: str,
    seed: int,
    batch_size: int,
    prompt_version: str,
    prompt_sha256: str,
    rubric_sha256: str,
) -> Dict[str, Any]:
    contract = _validated_official_judge_contract(
        official_contract, kind=kind
    )
    try:
        model_index = contract["models"].index(str(model))
    except ValueError as exc:
        raise ValueError("official judge model is outside the frozen contract") from exc
    expected = {
        "seed": contract["seeds"][model_index],
        "batch_size": contract["batch_size"],
        "prompt_version": contract["prompt_version"],
        "prompt_sha256": contract["prompt_sha256"],
        "rubric_sha256": contract["rubric_sha256"],
    }
    actual = {
        "seed": int(seed),
        "batch_size": int(batch_size),
        "prompt_version": prompt_version,
        "prompt_sha256": prompt_sha256,
        "rubric_sha256": rubric_sha256,
    }
    if actual != expected:
        raise ValueError("official judge run coordinates differ from contract")
    return contract


def _paid_batch_claim_payload(
    *,
    kind: str,
    batch_id: str,
    model: str,
    executable: str,
    prompt_version: str,
    prompt_template_sha256: str,
    rubric_sha256: str,
    prompt: str,
    input_payload: Mapping[str, Any],
    output_schema: Mapping[str, Any],
    sample_ids: Sequence[str],
    provider_output_filename: str,
    official_contract: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    """Build an exact, privacy-safe description of one provider request."""
    schema_sha256 = canonical_json_sha256(output_schema)
    validated_official = (
        _validated_official_judge_contract(official_contract, kind=kind)
        if official_contract is not None
        else None
    )
    stable_request = {
        "provider": "codex-cli",
        "model": str(model),
        "prompt_sha256": _sha256(prompt),
        "output_schema_sha256": schema_sha256,
        "input_payload_sha256": canonical_json_sha256(input_payload),
        "executable_token_sha256": _sha256(str(executable)),
        "command_contract": [
            "exec",
            "--ephemeral",
            "--ignore-user-config",
            "--ignore-rules",
            "--skip-git-repo-check",
            "--sandbox=read-only",
            "--model=%s" % model,
            "--output-schema-sha256=%s" % schema_sha256,
            "--output-last-message=%s" % provider_output_filename,
            "--color=never",
            "--cd=<ephemeral>",
            "stdin=-",
        ],
    }
    if validated_official is not None:
        stable_request["official_contract_sha256"] = validated_official[
            "official_contract_sha256"
        ]
    payload: Dict[str, Any] = {
        "claim_version": (
            OFFICIAL_PAID_BATCH_CLAIM_VERSION
            if validated_official is not None
            else PAID_BATCH_CLAIM_VERSION
        ),
        "kind": str(kind),
        "provider": "codex-cli",
        "batch_id": str(batch_id),
        "model": str(model),
        "prompt_version": str(prompt_version),
        "prompt_template_sha256": str(prompt_template_sha256),
        "rubric_sha256": str(rubric_sha256),
        "prompt_sha256": _sha256(prompt),
        "input_payload_sha256": canonical_json_sha256(input_payload),
        "output_schema_sha256": schema_sha256,
        "sample_ids": [str(sample_id) for sample_id in sample_ids],
        "executable_basename": os.path.basename(str(executable)) or str(executable),
        "executable_token_sha256": _sha256(str(executable)),
        "provider_output_filename": str(provider_output_filename),
        "request_sha256": canonical_json_sha256(stable_request),
    }
    if validated_official is not None:
        payload["official_contract"] = validated_official
        payload["official_contract_sha256"] = validated_official[
            "official_contract_sha256"
        ]
    payload["claim_sha256"] = canonical_json_sha256(payload)
    return payload


def _load_exact_paid_batch_claim(
    path: str,
    expected: Mapping[str, Any],
    *,
    kind: str,
    batch_id: str,
) -> Dict[str, Any]:
    try:
        supplied, _ = _strict_json_file(
            path,
            root=os.path.dirname(path) or os.curdir,
            label=kind + " provider claim",
        )
    except (OSError, ValueError) as exc:
        raise _paid_batch_reconciliation_error(
            kind, batch_id, "the durable request claim is unreadable"
        ) from exc
    if not isinstance(supplied, Mapping):
        raise _paid_batch_reconciliation_error(
            kind, batch_id, "the durable request claim is not an object"
        )
    payload = dict(supplied)
    supplied_hash = payload.pop("claim_sha256", None)
    if supplied_hash != canonical_json_sha256(payload):
        raise _paid_batch_reconciliation_error(
            kind, batch_id, "the durable request claim hash is invalid"
        )
    if dict(supplied) != dict(expected):
        raise _paid_batch_reconciliation_error(
            kind, batch_id, "the durable request claim differs from this request"
        )
    return dict(supplied)


def _prepare_paid_batch_claim(
    artifact_dir: str,
    claim: Mapping[str, Any],
    *,
    kind: str,
    batch_id: str,
) -> Tuple[bool, str, str, str]:
    """Publish a claim once and distinguish first dispatch from reconciliation."""
    require_directory_nonsymlink(
        artifact_dir, label=kind + " artifact directory"
    )
    claim_path, provider_output_path, state_path = _paid_batch_paths(
        artifact_dir, batch_id
    )
    for path, label in (
        (claim_path, "provider claim"),
        (provider_output_path, "provider output"),
        (state_path, "provider state"),
    ):
        require_regular_nonsymlink(
            path,
            label="%s %s" % (kind, label),
            allow_missing=True,
        )

    if os.path.lexists(claim_path):
        _load_exact_paid_batch_claim(
            claim_path, claim, kind=kind, batch_id=batch_id
        )
        return False, claim_path, provider_output_path, state_path
    if os.path.lexists(provider_output_path) or os.path.lexists(state_path):
        raise _paid_batch_reconciliation_error(
            kind,
            batch_id,
            "provider output/state exists without its immutable request claim",
        )
    try:
        published = publish_exact_json(claim_path, claim)
    except ValueError as exc:
        raise _paid_batch_reconciliation_error(
            kind, batch_id, "a conflicting request claim appeared concurrently"
        ) from exc
    if not published:
        _load_exact_paid_batch_claim(
            claim_path, claim, kind=kind, batch_id=batch_id
        )
    return published, claim_path, provider_output_path, state_path


def _paid_batch_state_payload(
    claim: Mapping[str, Any],
    *,
    status: str,
    raw_output: str,
    returncode: Optional[int],
    elapsed_seconds: Optional[float],
    stdout: Optional[str],
    stderr: Optional[str],
    failure_kind: Optional[str],
    recovered_from_durable_output: bool,
) -> Dict[str, Any]:
    if status not in {"succeeded", "failed"}:
        raise ValueError("paid batch state must be succeeded or failed")
    process = {
        "returncode": returncode,
        "elapsed_seconds": elapsed_seconds,
        "stdout_sha256": None if stdout is None else _sha256(str(stdout)),
        "stdout_bytes": (
            None if stdout is None else len(str(stdout).encode("utf-8"))
        ),
        "stderr_sha256": None if stderr is None else _sha256(str(stderr)),
        "stderr_bytes": (
            None if stderr is None else len(str(stderr).encode("utf-8"))
        ),
    }
    payload: Dict[str, Any] = {
        "state_version": PAID_BATCH_STATE_VERSION,
        "claim_sha256": claim["claim_sha256"],
        "status": status,
        "process": process,
        "output_sha256": _sha256(raw_output),
        "output_bytes": len(raw_output.encode("utf-8")),
        "failure_kind": failure_kind,
        "recovered_from_durable_output": bool(recovered_from_durable_output),
    }
    payload["state_sha256"] = canonical_json_sha256(payload)
    return payload


def _load_paid_batch_state(
    path: str,
    claim: Mapping[str, Any],
    *,
    kind: str,
    batch_id: str,
) -> Optional[Dict[str, Any]]:
    if not os.path.lexists(path):
        return None
    try:
        supplied, _ = _strict_json_file(
            path,
            root=os.path.dirname(path) or os.curdir,
            label=kind + " provider state",
        )
    except (OSError, ValueError) as exc:
        raise _paid_batch_reconciliation_error(
            kind, batch_id, "the durable provider state is unreadable"
        ) from exc
    required = {
        "state_version",
        "claim_sha256",
        "status",
        "process",
        "output_sha256",
        "output_bytes",
        "failure_kind",
        "recovered_from_durable_output",
        "state_sha256",
    }
    if not isinstance(supplied, Mapping) or set(supplied) != required:
        raise _paid_batch_reconciliation_error(
            kind, batch_id, "the durable provider state schema is invalid"
        )
    payload = dict(supplied)
    supplied_hash = payload.pop("state_sha256")
    if supplied_hash != canonical_json_sha256(payload):
        raise _paid_batch_reconciliation_error(
            kind, batch_id, "the durable provider state hash is invalid"
        )
    if payload["state_version"] != PAID_BATCH_STATE_VERSION:
        raise _paid_batch_reconciliation_error(
            kind, batch_id, "the durable provider state version is unsupported"
        )
    if payload["claim_sha256"] != claim["claim_sha256"]:
        raise _paid_batch_reconciliation_error(
            kind, batch_id, "the provider state is bound to another request"
        )
    if payload["status"] not in {"succeeded", "failed"} or not isinstance(
        payload["process"], Mapping
    ):
        raise _paid_batch_reconciliation_error(
            kind, batch_id, "the durable provider state is malformed"
        )
    process_keys = {
        "returncode",
        "elapsed_seconds",
        "stdout_sha256",
        "stdout_bytes",
        "stderr_sha256",
        "stderr_bytes",
    }
    if set(payload["process"]) != process_keys:
        raise _paid_batch_reconciliation_error(
            kind, batch_id, "the durable provider process state is malformed"
        )
    if payload["status"] == "succeeded" and payload["process"]["returncode"] != 0:
        raise _paid_batch_reconciliation_error(
            kind, batch_id, "a successful provider state has a nonzero exit"
        )
    return dict(supplied)


def _publish_paid_batch_state(
    path: str,
    payload: Mapping[str, Any],
    *,
    kind: str,
    batch_id: str,
) -> Dict[str, Any]:
    try:
        publish_exact_json(path, payload)
    except ValueError as exc:
        raise _paid_batch_reconciliation_error(
            kind, batch_id, "a conflicting terminal provider state already exists"
        ) from exc
    return dict(payload)


def _read_durable_provider_output(
    path: str, *, kind: str, batch_id: str
) -> str:
    if not os.path.lexists(path):
        raise _paid_batch_reconciliation_error(
            kind, batch_id, "the request claim exists but provider output is missing"
        )
    try:
        raw_bytes = _read_regular_bytes(
            path,
            root=os.path.dirname(path) or os.curdir,
            label=kind + " provider output",
        )
        fsync_directory_best_effort(os.path.dirname(path) or ".")
        return raw_bytes.decode("utf-8")
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        raise _paid_batch_reconciliation_error(
            kind, batch_id, "the direct provider output is unreadable or partial"
        ) from exc


def _validated_existing_paid_output(
    *,
    claim: Mapping[str, Any],
    provider_output_path: str,
    state_path: str,
    kind: str,
    batch_id: str,
) -> Tuple[str, Optional[Dict[str, Any]]]:
    """Read a previously claimed call without ever authorizing a new call."""
    state = _load_paid_batch_state(
        state_path, claim, kind=kind, batch_id=batch_id
    )
    if state is not None and state["status"] == "failed":
        raise _paid_batch_reconciliation_error(
            kind,
            batch_id,
            "the durable provider state records a failed dispatch (%s)"
            % (state.get("failure_kind") or "unknown failure"),
        )
    raw = _read_durable_provider_output(
        provider_output_path, kind=kind, batch_id=batch_id
    )
    if state is not None and (
        state["output_sha256"] != _sha256(raw)
        or state["output_bytes"] != len(raw.encode("utf-8"))
    ):
        raise _paid_batch_reconciliation_error(
            kind, batch_id, "provider output differs from its terminal state"
        )
    return raw, state


def _paid_state_meta_fields(state: Mapping[str, Any]) -> Dict[str, Any]:
    process = dict(state["process"])
    return {
        key: value
        for key, value in process.items()
        if value is not None
    }


def _is_sha256(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _audit_paid_batch_evidence(
    *,
    kind: str,
    batch_id: str,
    model: str,
    prompt_version: str,
    prompt_template_sha256: str,
    rubric_sha256: str,
    prompt_sha256: str,
    input_payload: Mapping[str, Any],
    output_schema: Mapping[str, Any],
    sample_ids: Sequence[str],
    meta: Mapping[str, Any],
    visible_output_text: str,
    claim_path: str,
    provider_output_path: str,
    state_path: str,
    official_contract: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    """Strictly validate and cross-bind one paid call's hidden evidence."""

    def load_json_object(path: str, label: str) -> Dict[str, Any]:
        try:
            value, _ = _strict_json_file(
                path,
                root=os.path.dirname(path) or os.curdir,
                label=label,
            )
        except (OSError, ValueError) as exc:
            raise ValueError("%s is unreadable" % label) from exc
        if not isinstance(value, Mapping):
            raise ValueError("%s is not an object" % label)
        return dict(value)

    claim = load_json_object(claim_path, kind + " provider claim")
    claim_keys = {
        "claim_version",
        "kind",
        "provider",
        "batch_id",
        "model",
        "prompt_version",
        "prompt_template_sha256",
        "rubric_sha256",
        "prompt_sha256",
        "input_payload_sha256",
        "output_schema_sha256",
        "sample_ids",
        "executable_basename",
        "executable_token_sha256",
        "provider_output_filename",
        "request_sha256",
        "claim_sha256",
    }
    validated_official = None
    if official_contract is not None:
        validated_official = _validated_official_judge_contract(
            official_contract, kind=kind
        )
        claim_keys.update(
            {"official_contract", "official_contract_sha256"}
        )
    if set(claim) != claim_keys:
        raise ValueError("%s provider claim schema mismatch" % kind)
    string_claim_fields = claim_keys - {"sample_ids", "official_contract"}
    if any(not isinstance(claim[field], str) for field in string_claim_fields):
        raise ValueError("%s provider claim has invalid field types" % kind)
    if not isinstance(claim["sample_ids"], list) or any(
        not isinstance(sample_id, str) for sample_id in claim["sample_ids"]
    ):
        raise ValueError("%s provider claim has invalid sample_ids" % kind)
    for field in (
        "prompt_template_sha256",
        "rubric_sha256",
        "prompt_sha256",
        "input_payload_sha256",
        "output_schema_sha256",
        "executable_token_sha256",
        "request_sha256",
        "claim_sha256",
    ):
        if not _is_sha256(claim[field]):
            raise ValueError("%s provider claim has invalid %s" % (kind, field))
    claim_without_hash = dict(claim)
    supplied_claim_hash = claim_without_hash.pop("claim_sha256")
    if supplied_claim_hash != canonical_json_sha256(claim_without_hash):
        raise ValueError("%s provider claim hash mismatch" % kind)

    provider_output_filename = os.path.basename(provider_output_path)
    expected_claim_values = {
        "claim_version": (
            OFFICIAL_PAID_BATCH_CLAIM_VERSION
            if validated_official is not None
            else PAID_BATCH_CLAIM_VERSION
        ),
        "kind": kind,
        "provider": "codex-cli",
        "batch_id": batch_id,
        "model": str(model),
        "prompt_version": prompt_version,
        "prompt_template_sha256": prompt_template_sha256,
        "rubric_sha256": rubric_sha256,
        "prompt_sha256": prompt_sha256,
        "input_payload_sha256": canonical_json_sha256(input_payload),
        "output_schema_sha256": canonical_json_sha256(output_schema),
        "sample_ids": list(sample_ids),
        "provider_output_filename": provider_output_filename,
    }
    for field, expected in expected_claim_values.items():
        if claim[field] != expected:
            raise ValueError(
                "%s provider claim differs from batch %s" % (kind, field)
            )
    if validated_official is None:
        if claim["claim_version"] != PAID_BATCH_CLAIM_VERSION:
            raise ValueError("%s provider claim version mismatch" % kind)
    else:
        if claim["claim_version"] != OFFICIAL_PAID_BATCH_CLAIM_VERSION:
            raise ValueError("%s official provider claim version mismatch" % kind)
        if claim["official_contract"] != validated_official or claim[
            "official_contract_sha256"
        ] != validated_official["official_contract_sha256"]:
            raise ValueError("%s provider claim official contract mismatch" % kind)
    if (
        not claim["executable_basename"]
        or os.path.basename(claim["executable_basename"])
        != claim["executable_basename"]
    ):
        raise ValueError("%s provider claim has invalid executable basename" % kind)
    stable_request = {
        "provider": "codex-cli",
        "model": str(model),
        "prompt_sha256": prompt_sha256,
        "output_schema_sha256": canonical_json_sha256(output_schema),
        "input_payload_sha256": canonical_json_sha256(input_payload),
        "executable_token_sha256": claim["executable_token_sha256"],
        "command_contract": [
            "exec",
            "--ephemeral",
            "--ignore-user-config",
            "--ignore-rules",
            "--skip-git-repo-check",
            "--sandbox=read-only",
            "--model=%s" % model,
            "--output-schema-sha256=%s"
            % canonical_json_sha256(output_schema),
            "--output-last-message=%s" % provider_output_filename,
            "--color=never",
            "--cd=<ephemeral>",
            "stdin=-",
        ],
    }
    if validated_official is not None:
        stable_request["official_contract_sha256"] = validated_official[
            "official_contract_sha256"
        ]
    if claim["request_sha256"] != canonical_json_sha256(stable_request):
        raise ValueError("%s provider request hash mismatch" % kind)

    state = load_json_object(state_path, kind + " provider state")
    state_keys = {
        "state_version",
        "claim_sha256",
        "status",
        "process",
        "output_sha256",
        "output_bytes",
        "failure_kind",
        "recovered_from_durable_output",
        "state_sha256",
    }
    if set(state) != state_keys:
        raise ValueError("%s provider state schema mismatch" % kind)
    state_without_hash = dict(state)
    supplied_state_hash = state_without_hash.pop("state_sha256")
    if not _is_sha256(supplied_state_hash) or supplied_state_hash != (
        canonical_json_sha256(state_without_hash)
    ):
        raise ValueError("%s provider state hash mismatch" % kind)
    if state["state_version"] != PAID_BATCH_STATE_VERSION:
        raise ValueError("%s provider state version mismatch" % kind)
    if state["claim_sha256"] != claim["claim_sha256"]:
        raise ValueError("%s provider state/claim hash mismatch" % kind)
    if state["status"] != "succeeded":
        raise ValueError("%s provider state is not successful" % kind)
    if state["failure_kind"] is not None:
        raise ValueError("%s successful provider state records a failure" % kind)
    if not isinstance(state["recovered_from_durable_output"], bool):
        raise ValueError("%s provider recovery flag is not boolean" % kind)
    if not _is_sha256(state["output_sha256"]):
        raise ValueError("%s provider state output hash is invalid" % kind)
    if (
        isinstance(state["output_bytes"], bool)
        or not isinstance(state["output_bytes"], int)
        or state["output_bytes"] < 0
    ):
        raise ValueError("%s provider state output size is invalid" % kind)

    process = state["process"]
    process_keys = {
        "returncode",
        "elapsed_seconds",
        "stdout_sha256",
        "stdout_bytes",
        "stderr_sha256",
        "stderr_bytes",
    }
    if not isinstance(process, Mapping) or set(process) != process_keys:
        raise ValueError("%s provider process state schema mismatch" % kind)
    if (
        isinstance(process["returncode"], bool)
        or not isinstance(process["returncode"], int)
        or process["returncode"] != 0
    ):
        raise ValueError("%s provider process did not exit successfully" % kind)
    elapsed = process["elapsed_seconds"]
    if elapsed is not None and (
        isinstance(elapsed, bool)
        or not isinstance(elapsed, (int, float))
        or not math.isfinite(float(elapsed))
        or float(elapsed) < 0.0
    ):
        raise ValueError("%s provider elapsed time is invalid" % kind)
    for stream in ("stdout", "stderr"):
        stream_hash = process[stream + "_sha256"]
        stream_bytes = process[stream + "_bytes"]
        if (stream_hash is None) != (stream_bytes is None):
            raise ValueError("%s provider %s evidence is incomplete" % (kind, stream))
        if stream_hash is not None and not _is_sha256(stream_hash):
            raise ValueError("%s provider %s hash is invalid" % (kind, stream))
        if stream_bytes is not None and (
            isinstance(stream_bytes, bool)
            or not isinstance(stream_bytes, int)
            or stream_bytes < 0
        ):
            raise ValueError("%s provider %s size is invalid" % (kind, stream))

    try:
        provider_output_bytes = _read_regular_bytes(
            provider_output_path,
            root=os.path.dirname(provider_output_path) or os.curdir,
            label=kind + " provider output",
        )
        provider_output_text = provider_output_bytes.decode("utf-8")
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        raise ValueError("%s provider output is unreadable" % kind) from exc
    if state["output_bytes"] != len(provider_output_bytes):
        raise ValueError("%s provider output byte count mismatch" % kind)
    if state["output_sha256"] != hashlib.sha256(provider_output_bytes).hexdigest():
        raise ValueError("%s provider output hash mismatch" % kind)
    expected_visible_output = provider_output_text + (
        "\n"
        if provider_output_text and not provider_output_text.endswith("\n")
        else ""
    )
    if visible_output_text != expected_visible_output:
        raise ValueError("%s provider/visible output conflict" % kind)
    try:
        provider_payload = strict_json_loads(provider_output_text)
    except ValueError as exc:
        raise ValueError("%s provider output is invalid JSON" % kind) from exc

    provider_meta_fields = {
        "provider_claim_sha256",
        "provider_state_sha256",
        "provider_output_filename",
        "provider_output_recovered",
    }
    if {key for key in meta if key.startswith("provider_")} != (
        provider_meta_fields
    ):
        raise ValueError("%s provider metadata schema mismatch" % kind)
    expected_meta = {
        "provider_claim_sha256": claim["claim_sha256"],
        "provider_state_sha256": state["state_sha256"],
        "provider_output_filename": provider_output_filename,
        "provider_output_recovered": state[
            "recovered_from_durable_output"
        ],
        "output_sha256": state["output_sha256"],
    }
    for field, expected in expected_meta.items():
        if meta.get(field) != expected:
            raise ValueError(
                "%s provider evidence conflicts with metadata %s" % (kind, field)
            )
    for field in process_keys:
        expected = process[field]
        if expected is None:
            if field in meta:
                raise ValueError(
                    "%s metadata unexpectedly records provider %s" % (kind, field)
                )
        elif meta.get(field) != expected:
            raise ValueError(
                "%s provider process conflicts with metadata %s" % (kind, field)
            )

    return {
        "claim": claim,
        "state": state,
        "provider_output_text": provider_output_text,
        "provider_payload": provider_payload,
    }


def _write_or_verify_exact_json_artifact(
    path: str,
    payload: Mapping[str, Any],
    *,
    kind: str,
    batch_id: str,
) -> None:
    """Create one triplet/journal member, never replacing a conflicting one."""
    if os.path.lexists(path):
        try:
            existing, _ = _strict_json_file(
                path,
                root=os.path.dirname(path) or os.curdir,
                label=kind + " batch artifact",
            )
        except (OSError, ValueError) as exc:
            raise _paid_batch_reconciliation_error(
                kind, batch_id, "an existing batch artifact is unreadable"
            ) from exc
        if canonical_json_sha256(existing) != canonical_json_sha256(payload):
            raise _paid_batch_reconciliation_error(
                kind, batch_id, "an existing batch artifact conflicts with recovery"
            )
        return
    _atomic_write_json(path, payload)


def _write_or_verify_exact_text_artifact(
    path: str,
    text: str,
    *,
    kind: str,
    batch_id: str,
) -> None:
    if os.path.lexists(path):
        try:
            existing = _read_regular_text(
                path,
                root=os.path.dirname(path) or os.curdir,
                label=kind + " batch artifact",
            )
        except (OSError, ValueError) as exc:
            raise _paid_batch_reconciliation_error(
                kind, batch_id, "an existing batch artifact is unreadable"
            ) from exc
        if existing != text:
            raise _paid_batch_reconciliation_error(
                kind, batch_id, "an existing batch artifact conflicts with recovery"
            )
        return
    _atomic_write_text(path, text)


CODEX_JUDGE_RUBRIC_SHA256 = _sha256(CODEX_JUDGE_RUBRIC)
CODEX_JUDGE_PROMPT_SHA256 = _sha256(
    CODEX_JUDGE_RUBRIC + CODEX_JUDGE_PROMPT_INSTRUCTION + "<SAMPLES_JSON>"
)


def codex_judge_contract() -> Dict[str, str]:
    """Return the stable semantic-judge prompt contract frozen by V6."""
    return {
        "prompt_version": CODEX_JUDGE_PROMPT_VERSION,
        "prompt_sha256": CODEX_JUDGE_PROMPT_SHA256,
        "rubric_sha256": CODEX_JUDGE_RUBRIC_SHA256,
    }


def load_frozen_judge_contract(
    contract_input: Any,
    *,
    repository_root: Optional[str] = None,
) -> Mapping[str, Any]:
    """Strict-load a contract mapping, inline JSON, or regular JSON file."""
    if isinstance(contract_input, Mapping):
        return dict(contract_input)
    token = str(contract_input)
    if token.lstrip().startswith("{"):
        payload = strict_json_loads(token)
    else:
        path = token
        if repository_root is not None and not os.path.isabs(path):
            path = os.path.join(repository_root, path)
        payload, _ = _strict_json_file(
            path,
            root=repository_root,
            label="frozen judge contract",
        )
    if not isinstance(payload, Mapping):
        raise ValueError("judge contract JSON must contain an object")
    return dict(payload)


V6_JUDGE_AUTHORIZED_STATUS = "READY_FOR_TARGET_FREE_JUDGES"


def require_v6_judge_protocol_open(contract_payload: Mapping[str, Any]) -> None:
    """Require an explicit canonical-protocol authorization state.

    Production CLIs separately require the canonical repository path. Missing,
    unknown, pending, copied-inline, and terminal statuses all fail closed.
    """
    status = contract_payload.get("status")
    if status != V6_JUDGE_AUTHORIZED_STATUS:
        raise RuntimeError(
            "V6 protocol does not authorize judge dispatch (status=%r)" % status
        )
    power = contract_payload.get("power_design")
    result = power.get("result") if isinstance(power, Mapping) else None
    if (
        not isinstance(result, Mapping)
        or result.get("status") != "PASS_V6_PROSPECTIVE_BUNDLE_POWER"
        or result.get("pass") is not True
        or type(result.get("selected_episode_seeds")) is not int
    ):
        raise RuntimeError(
            "V6 judge dispatch requires a canonical passing power result"
        )


def frozen_official_runtime(
    contract_payload: Mapping[str, Any]
) -> Dict[str, str]:
    """Extract the exact official runtime fields needed before attestation."""
    runtime = contract_payload.get("judge_runtime")
    if not isinstance(runtime, Mapping):
        raise ValueError("official judge contract is missing judge_runtime")
    selected = {field: runtime.get(field) for field in _CODEX_RUNTIME_FIELDS}
    if set(runtime).issuperset(_CODEX_RUNTIME_FIELDS):
        pass
    else:
        missing = sorted(set(_CODEX_RUNTIME_FIELDS) - set(runtime))
        raise ValueError(
            "official judge runtime is missing protocol fields: %s"
            % ", ".join(missing)
        )
    if selected["codex_executable"] != "codex":
        raise ValueError("official Codex executable token must be exactly 'codex'")
    if not isinstance(selected["codex_cli_version"], str) or not selected[
        "codex_cli_version"
    ]:
        raise ValueError("official judge runtime has no exact codex_cli_version")
    if not _is_sha256(selected["codex_executable_sha256"]):
        raise ValueError("official judge runtime has no valid executable SHA-256")
    return {field: str(selected[field]) for field in _CODEX_RUNTIME_FIELDS}


def enforce_frozen_judge_contract(
    contract_input: Any,
    kind: str,
    actual: Mapping[str, Any],
    prompt_contract: Mapping[str, str],
) -> Dict[str, Any]:
    """Load and enforce a frozen semantic/quality CLI judge contract.

    ``contract_input`` may be a JSON path or an inline JSON object.  A direct
    contract object is accepted, as are protocol objects containing
    ``semantic_validation``/``quality_validation`` or ``judge_contracts``.
    """
    payload = load_frozen_judge_contract(contract_input)

    section: Any = payload
    validation = payload.get("%s_validation" % kind)
    canonical_out_dir = None
    canonical_cache_dir = None
    if isinstance(validation, Mapping):
        canonical_out_dir = validation.get("canonical_out_dir")
        canonical_cache_dir = validation.get("canonical_cache_dir")
    contracts = payload.get("judge_contracts")
    if isinstance(validation, Mapping) and isinstance(
        validation.get("judge_contract"), Mapping
    ):
        section = validation["judge_contract"]
    elif isinstance(contracts, Mapping):
        section = contracts.get(kind, contracts.get("%s_validation" % kind))
    elif isinstance(validation, Mapping):
        section = validation
    elif isinstance(payload.get("judge_contract"), Mapping):
        section = payload["judge_contract"]
    if not isinstance(section, Mapping):
        raise ValueError("%s judge contract section is missing" % kind)
    if canonical_out_dir is None:
        canonical_out_dir = section.get("canonical_out_dir")
    if canonical_cache_dir is None:
        canonical_cache_dir = section.get("canonical_cache_dir")

    models = section.get(
        "models", section.get("judge_models", section.get("judges"))
    )
    if models is None:
        models = [section.get("primary_model"), section.get("sensitivity_model")]
    seeds = section.get("seeds", section.get("shuffle_seeds"))
    if seeds is None:
        seeds = [
            section.get("primary_seed", section.get("primary_shuffle_seed")),
            section.get(
                "sensitivity_seed", section.get("sensitivity_shuffle_seed")
            ),
        ]
    if (
        not isinstance(models, list)
        or len(models) != 2
        or not all(isinstance(value, str) and value for value in models)
    ):
        raise ValueError("%s judge contract must freeze exactly two models" % kind)
    if (
        not isinstance(seeds, list)
        or len(seeds) != 2
        or any(
            isinstance(value, bool) or not isinstance(value, int)
            for value in seeds
        )
    ):
        raise ValueError(
            "%s judge contract must freeze exactly two integer seeds" % kind
        )

    prompt_sha256 = section.get(
        "prompt_sha256",
        section.get(
            "prompt_template_sha256", section.get("judge_prompt_sha256")
        ),
    )
    frozen = {
        "models": [str(value) for value in models],
        "seeds": [int(value) for value in seeds],
        "batch_size": section.get("batch_size", section.get("judge_batch_size")),
        "prompt_version": section.get(
            "prompt_version", section.get("judge_prompt_version")
        ),
        "prompt_sha256": prompt_sha256,
        "rubric_sha256": section.get(
            "rubric_sha256", section.get("judge_rubric_sha256")
        ),
    }
    if isinstance(frozen["batch_size"], bool) or not isinstance(
        frozen["batch_size"], int
    ):
        raise ValueError("%s judge contract must freeze an integer batch_size" % kind)
    if frozen["batch_size"] < 1:
        raise ValueError("%s judge contract batch_size must be positive" % kind)
    for field in ("prompt_version", "prompt_sha256", "rubric_sha256"):
        if not isinstance(frozen[field], str) or not frozen[field]:
            raise ValueError("%s judge contract is missing %s" % (kind, field))
    declared_contract_sha256 = section.get("contract_sha256")
    if declared_contract_sha256 is not None and declared_contract_sha256 != (
        canonical_json_sha256(frozen)
    ):
        raise ValueError("%s judge contract hash mismatch" % kind)

    expected = {
        "models": [str(actual["primary_model"]), str(actual["sensitivity_model"])],
        "seeds": [int(actual["primary_seed"]), int(actual["sensitivity_seed"])],
        "batch_size": int(actual["batch_size"]),
        "prompt_version": str(prompt_contract["prompt_version"]),
        "prompt_sha256": str(prompt_contract["prompt_sha256"]),
        "rubric_sha256": str(prompt_contract["rubric_sha256"]),
    }
    for field, expected_value in expected.items():
        if frozen[field] != expected_value:
            raise ValueError(
                "%s judge contract mismatch for %s" % (kind, field)
            )
    if "canonical_out_dir" in actual or "canonical_cache_dir" in actual:
        if not isinstance(canonical_out_dir, str) or not canonical_out_dir:
            raise ValueError(
                "%s judge contract is missing canonical_out_dir" % kind
            )
        if not isinstance(canonical_cache_dir, str) or not canonical_cache_dir:
            raise ValueError(
                "%s judge contract is missing canonical_cache_dir" % kind
            )
        if actual.get("canonical_out_dir") != canonical_out_dir:
            raise ValueError(
                "%s judge contract mismatch for canonical_out_dir" % kind
            )
        if actual.get("canonical_cache_dir") != canonical_cache_dir:
            raise ValueError(
                "%s judge contract mismatch for canonical_cache_dir" % kind
            )
    result = {
        **frozen,
        "kind": kind,
        "contract_sha256": canonical_json_sha256(frozen),
        "enforced": True,
    }
    if canonical_out_dir is not None:
        result["canonical_out_dir"] = canonical_out_dir
    if canonical_cache_dir is not None:
        result["canonical_cache_dir"] = canonical_cache_dir

    official_requested = any(
        field in actual for field in ("candidate_pool", "codex_runtime")
    )
    if official_requested:
        actual_pool = actual.get("candidate_pool")
        protocol_pool = payload.get("candidate_pool")
        if not isinstance(actual_pool, Mapping) or not isinstance(
            protocol_pool, Mapping
        ):
            raise ValueError("official judge contract is missing candidate_pool")
        frozen_pool = {
            "path": protocol_pool.get("path"),
            "file_sha256": protocol_pool.get("file_sha256"),
            "canonical_sha256": protocol_pool.get("sha256"),
        }
        if dict(actual_pool) != frozen_pool:
            raise ValueError(
                "%s judge contract candidate pool path/hash mismatch" % kind
            )
        actual_runtime = actual.get("codex_runtime")
        if not isinstance(actual_runtime, Mapping):
            raise ValueError("official judge contract is missing attested runtime")
        selected_runtime = {
            field: actual_runtime.get(field) for field in _CODEX_RUNTIME_FIELDS
        }
        if selected_runtime != frozen_official_runtime(payload):
            raise ValueError("%s judge contract Codex runtime mismatch" % kind)
        official_without_hash: Dict[str, Any] = {
            "contract_version": OFFICIAL_JUDGE_CONTRACT_VERSION,
            "kind": kind,
            **frozen,
            "candidate_pool": frozen_pool,
            "codex_runtime": selected_runtime,
        }
        official_hash = canonical_json_sha256(official_without_hash)
        declared_official_hash = section.get("official_contract_sha256")
        if declared_official_hash != official_hash:
            raise ValueError(
                "%s judge contract official_contract_sha256 mismatch" % kind
            )
        official_contract = {
            **official_without_hash,
            "official_contract_sha256": official_hash,
        }
        _validated_official_judge_contract(official_contract, kind=kind)
        result.update(
            {
                "candidate_pool": frozen_pool,
                "codex_runtime": selected_runtime,
                "official_contract": official_contract,
                "official_contract_sha256": official_hash,
                "official": True,
            }
        )
    else:
        result["official"] = False
    return result


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
        + CODEX_JUDGE_PROMPT_INSTRUCTION
        + json.dumps(payload, ensure_ascii=False, indent=2)
    )


FROZEN_JUDGE_BATCH_SCHEDULE_VERSION = "v6-frozen-judge-batches-v1"


def _unique_messages(messages: Iterable[str]) -> List[str]:
    values = [str(message) for message in messages]
    if not values:
        raise ValueError("frozen judge message set must not be empty")
    if len(values) != len(set(values)):
        raise ValueError("frozen judge message set must contain unique messages")
    return values


def _message_set_sha256(messages: Iterable[str]) -> str:
    """Hash the complete canonical message set independently of input order."""
    return canonical_json_sha256(sorted(_unique_messages(messages)))


def _semantic_batch_id(samples: Sequence[BlindJudgeSample]) -> str:
    return "batch_" + _sha256(
        "\n".join(sample.sample_id for sample in samples)
    )[:16]


def build_codex_batch_plan(
    messages: Iterable[str], model: str, batch_size: int, seed: int
) -> List[Dict[str, Any]]:
    """Reconstruct the one permitted semantic-judge batch schedule.

    The plan is derived only from the complete canonical message set and the
    frozen model/seed/batch-size contract.  Each entry contains the exact
    persisted input payload and the exact prompt hash expected for that batch.
    """
    canonical_messages = _unique_messages(messages)
    batches = build_blind_batches(canonical_messages, model, batch_size, seed)
    message_set_sha256 = _message_set_sha256(canonical_messages)
    n_batches = len(batches)
    plan: List[Dict[str, Any]] = []
    for batch_index, samples in enumerate(batches, start=1):
        batch_id = _semantic_batch_id(samples)
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
            "prompt_version": CODEX_JUDGE_PROMPT_VERSION,
            "prompt_template_sha256": CODEX_JUDGE_PROMPT_SHA256,
            "rubric_sha256": CODEX_JUDGE_RUBRIC_SHA256,
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
                "prompt_sha256": _sha256(build_codex_prompt(samples)),
            }
        )
    return plan


def _repository_local_path(path: str, repository_root: str) -> str:
    root = os.path.realpath(repository_root)
    resolved = os.path.realpath(path)
    try:
        common = os.path.commonpath([root, resolved])
    except ValueError as exc:
        raise ValueError("judge artifact path is outside the repository") from exc
    if common != root:
        raise ValueError("judge artifact path is outside the repository")
    return os.path.relpath(resolved, root).replace(os.sep, "/")


def _raw_file_sha256(path: str) -> str:
    return hashlib.sha256(
        _read_regular_bytes(path, label="artifact hash input")
    ).hexdigest()


def _json_file_manifest(path: str, repository_root: Optional[str]) -> Dict[str, str]:
    payload, raw = _strict_json_file(
        path,
        root=repository_root,
        label="JSON evidence artifact",
    )
    display_path = (
        _repository_local_path(path, repository_root)
        if repository_root is not None
        else os.path.basename(path)
    )
    return {
        "path": display_path,
        "file_sha256": hashlib.sha256(raw).hexdigest(),
        "canonical_sha256": canonical_json_sha256(payload),
    }


def _jsonl_file_manifest(
    path: str,
    records: Sequence[Mapping[str, Any]],
    repository_root: Optional[str],
    *,
    raw_bytes: Optional[bytes] = None,
) -> Dict[str, str]:
    display_path = (
        _repository_local_path(path, repository_root)
        if repository_root is not None
        else os.path.basename(path)
    )
    return {
        "path": display_path,
        "file_sha256": hashlib.sha256(
            raw_bytes
            if raw_bytes is not None
            else _read_regular_bytes(
                path, root=repository_root, label="JSONL evidence artifact"
            )
        ).hexdigest(),
        "canonical_sha256": canonical_json_sha256(list(records)),
    }


def _resolve_repository_path(path: str, repository_root: str) -> str:
    if os.path.isabs(path):
        raise ValueError("judge manifest paths must be repository-local")
    resolved = os.path.realpath(os.path.join(repository_root, path))
    _repository_local_path(resolved, repository_root)
    return resolved


def audit_codex_artifacts(
    artifact_dir: str,
    *,
    expected_messages: Optional[Iterable[str]] = None,
    model: Optional[str] = None,
    batch_size: Optional[int] = None,
    seed: Optional[int] = None,
    repository_root: Optional[str] = None,
    official_contract: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    """Verify that saved judge calls were blind, complete, and unmodified.

    This is deliberately a structural audit. Searching message text for words
    such as ``condition`` creates false alarms because a focal message may use
    those ordinary English words. Instead, the audit checks the JSON key sets,
    reconstructs the exact prompt hash, validates every output against the
    expected sample ids, and verifies the saved output hash and process status.
    """
    if not os.path.isdir(artifact_dir):
        raise FileNotFoundError("judge artifact directory not found: %s" % artifact_dir)
    require_directory_nonsymlink(
        artifact_dir, label="semantic judge artifact directory"
    )
    directory_entries = sorted(os.listdir(artifact_dir))
    operational_lock_filenames = [".semantic-validation.lock"]
    operational_excluded_files = sorted(
        name for name in directory_entries if name in operational_lock_filenames
    )
    for name in operational_excluded_files:
        require_regular_nonsymlink(
            os.path.join(artifact_dir, name),
            label="semantic operational run lock",
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
        raise ValueError("no judge input artifacts found in %s" % artifact_dir)

    strict_schedule = expected_messages is not None
    validated_official = (
        _validated_official_judge_contract(
            official_contract, kind="semantic"
        )
        if official_contract is not None
        else None
    )
    expected_plan: List[Dict[str, Any]] = []
    expected_by_input: Dict[str, Dict[str, Any]] = {}
    if strict_schedule:
        if model is None or batch_size is None or seed is None:
            raise ValueError(
                "strict judge artifact audit requires model, batch_size, and seed"
            )
        expected_plan = build_codex_batch_plan(
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
                "judge artifact file set differs from frozen schedule "
                "(missing=%s, extra=%s)" % (missing, extra)
            )
        input_names = [str(row["input_filename"]) for row in expected_plan]

    allowed_top = {"batch_id", "model", "prompt_version", "samples"}
    contract_fields = {"prompt_template_sha256", "rubric_sha256"}
    schedule_fields = {
        "schedule_version",
        "batch_index",
        "n_batches",
        "seed",
        "batch_size",
        "message_set_sha256",
    }
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
        recovery_path = _semantic_recovery_path(artifact_dir, batch_id)
        for path in (output_path, meta_path):
            if not os.path.exists(path):
                raise ValueError("missing artifact paired with %s: %s" % (input_path, path))

        supplied, _ = _strict_json_file(
            input_path,
            root=artifact_dir,
            label="semantic visible input artifact",
        )
        supplied_keys = set(supplied) if isinstance(supplied, Mapping) else set()
        if strict_schedule:
            expected_row = expected_by_input[input_name]
            if supplied != expected_row["input_payload"]:
                raise ValueError(
                    "judge input %s differs from the frozen seed/batch schedule"
                    % input_path
                )
        elif supplied_keys not in (allowed_top, allowed_top | contract_fields):
            raise ValueError(
                "judge input %s has unexpected top-level keys: %s"
                % (
                    input_path,
                    sorted(
                        supplied_keys
                        - allowed_top
                        - contract_fields
                        - schedule_fields
                    ),
                )
            )
        if supplied["batch_id"] != batch_id:
            raise ValueError("batch id/filename mismatch in %s" % input_path)
        if supplied["prompt_version"] != CODEX_JUDGE_PROMPT_VERSION:
            raise ValueError("unexpected prompt version in %s" % input_path)
        if supplied_keys & contract_fields:
            if supplied.get("prompt_template_sha256") != CODEX_JUDGE_PROMPT_SHA256:
                raise ValueError("unexpected prompt template hash in %s" % input_path)
            if supplied.get("rubric_sha256") != CODEX_JUDGE_RUBRIC_SHA256:
                raise ValueError("unexpected rubric hash in %s" % input_path)
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

        meta, _ = _strict_json_file(
            meta_path,
            root=artifact_dir,
            label="semantic visible metadata artifact",
        )
        if not isinstance(meta, Mapping):
            raise ValueError("judge process metadata is not an object")
        if "stdout" in meta or "stderr" in meta:
            raise ValueError("unsanitized process logs in metadata for %s" % batch_id)
        if meta.get("process_logs_retained") is not False:
            raise ValueError("process-log retention policy missing for %s" % batch_id)
        if any(os.path.isabs(str(value)) for value in meta.get("command_flags", [])):
            raise ValueError("absolute command path retained for %s" % batch_id)
        if meta.get("returncode") != 0:
            raise ValueError("judge process failed for %s" % batch_id)
        if meta.get("batch_id", batch_id) != batch_id:
            raise ValueError("meta batch id differs from blind input for %s" % batch_id)
        if meta.get("model", model) != model:
            raise ValueError("meta model differs from blind input for %s" % batch_id)
        if meta.get("prompt_version", CODEX_JUDGE_PROMPT_VERSION) != (
            CODEX_JUDGE_PROMPT_VERSION
        ):
            raise ValueError("meta prompt version differs for %s" % batch_id)
        if meta.get("prompt_template_sha256", CODEX_JUDGE_PROMPT_SHA256) != (
            CODEX_JUDGE_PROMPT_SHA256
        ):
            raise ValueError("meta prompt template hash differs for %s" % batch_id)
        if meta.get("rubric_sha256", CODEX_JUDGE_RUBRIC_SHA256) != (
            CODEX_JUDGE_RUBRIC_SHA256
        ):
            raise ValueError("meta rubric hash differs for %s" % batch_id)
        if meta.get("sample_ids") != expected_ids:
            raise ValueError("meta sample ids differ from blind input for %s" % batch_id)
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
                        "judge metadata %s differs from frozen schedule for %s"
                        % (field, batch_id)
                    )
        prompt_sha256 = _sha256(build_codex_prompt(samples))
        if meta.get("prompt_sha256") != prompt_sha256:
            raise ValueError("prompt hash mismatch for %s" % batch_id)

        raw = _read_regular_text(
            output_path,
            root=artifact_dir,
            label="semantic visible output artifact",
        )
        # ``run_codex_batch`` appends a final newline only when the CLI did not
        # write one. Accept either representation when checking the pre-write
        # hash stored in metadata.
        raw_candidates = [raw]
        if raw.endswith("\n"):
            raw_candidates.append(raw[:-1])
        if meta.get("output_sha256") not in {_sha256(item) for item in raw_candidates}:
            raise ValueError("output hash mismatch for %s" % batch_id)
        try:
            payload = strict_json_loads(raw)
        except ValueError as exc:
            raise ValueError("invalid saved judge output for %s" % batch_id) from exc
        validated = validate_codex_payload(payload, expected_ids)
        evidence: Optional[Dict[str, Any]] = None
        recovery: Optional[Dict[str, Any]] = None
        if strict_schedule:
            evidence = _audit_paid_batch_evidence(
                kind="semantic",
                batch_id=batch_id,
                model=model,
                prompt_version=CODEX_JUDGE_PROMPT_VERSION,
                prompt_template_sha256=CODEX_JUDGE_PROMPT_SHA256,
                rubric_sha256=CODEX_JUDGE_RUBRIC_SHA256,
                prompt_sha256=prompt_sha256,
                input_payload=supplied,
                output_schema=codex_output_schema(expected_ids),
                sample_ids=expected_ids,
                meta=meta,
                visible_output_text=raw,
                claim_path=claim_path,
                provider_output_path=provider_output_path,
                state_path=state_path,
                official_contract=validated_official,
            )
            provider_validated = validate_codex_payload(
                evidence["provider_payload"], expected_ids
            )
            if provider_validated != validated:
                raise ValueError(
                    "semantic provider output conflicts with visible output"
                )
            require_regular_nonsymlink(
                recovery_path, label="semantic recovery journal"
            )
            recovery, _ = _load_semantic_recovery(
                recovery_path, expected_by_input[input_name], model
            )
            if (
                recovery["input_payload"] != supplied
                or recovery["output_text"] != raw
                or recovery["meta"] != meta
            ):
                raise ValueError(
                    "semantic recovery journal conflicts with visible artifacts"
                )
        output_sha256 = str(meta["output_sha256"])
        for sample in samples:
            public = _semantic_public_result(
                validated[sample.sample_id], sample.sample_id
            )
            if sample.message in result_map:
                raise ValueError("message appears in more than one judge batch")
            result_map[sample.message] = public
            result_binding_map[sample.message] = _semantic_artifact_binding(
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
        "prompt_version": CODEX_JUDGE_PROMPT_VERSION,
        "prompt_sha256": CODEX_JUDGE_PROMPT_SHA256,
        "prompt_template_sha256": CODEX_JUDGE_PROMPT_SHA256,
        "rubric_sha256": CODEX_JUDGE_RUBRIC_SHA256,
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


def validate_codex_payload(
    payload: Mapping[str, Any], expected_ids: Sequence[str]
) -> Dict[str, Dict[str, Any]]:
    """Fail closed on omissions, duplicates, invalid labels, or bad scores."""
    if not isinstance(payload, Mapping) or set(payload) != {"classifications"}:
        raise ValueError(
            "judge response must contain only the classifications array"
        )
    rows = payload.get("classifications")
    if not isinstance(rows, list):
        raise ValueError("judge response has no classifications array")
    expected = set(expected_ids)
    required = {
        "sample_id",
        *ALL_LABELS,
        "primary_strategy",
        "confidence",
    }
    found: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, Mapping):
            raise ValueError("classification is not an object")
        if set(row) != required:
            raise ValueError("classification has missing or unexpected fields")
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


_SEMANTIC_INTERNAL_FIELDS = {
    "_artifact_binding",
    "_batch_id",
    "_prompt_version",
}


def _semantic_public_result(
    result: Mapping[str, Any], expected_sample_id: str
) -> Dict[str, Any]:
    """Validate one result and strip identifiers/internal audit metadata."""
    if not isinstance(result, Mapping):
        raise ValueError("semantic judge result is not an object")
    extra = set(result) - {
        "sample_id",
        *ALL_LABELS,
        "primary_strategy",
        "confidence",
        *_SEMANTIC_INTERNAL_FIELDS,
    }
    if extra:
        raise ValueError("semantic judge result has unexpected internal fields")
    sample_id = result.get("sample_id", expected_sample_id)
    if sample_id != expected_sample_id:
        raise ValueError("semantic result sample id does not match its message")
    public = {
        key: value
        for key, value in result.items()
        if key not in _SEMANTIC_INTERNAL_FIELDS
    }
    public["sample_id"] = expected_sample_id
    clean = validate_codex_payload(
        {"classifications": [public]}, [expected_sample_id]
    )[expected_sample_id]
    return {
        key: clean[key]
        for key in (*ALL_LABELS, "primary_strategy", "confidence")
    }


def canonical_semantic_result_map(
    results: Mapping[str, Mapping[str, Any]],
    expected_messages: Optional[Iterable[str]] = None,
) -> Dict[str, Dict[str, Any]]:
    """Return the canonical, message-keyed public semantic result map."""
    if not isinstance(results, Mapping):
        raise ValueError("semantic judge results are not a mapping")
    if expected_messages is not None:
        expected = {str(message) for message in expected_messages}
        if set(results) != expected:
            raise ValueError("semantic judge results do not exactly cover messages")
    clean: Dict[str, Dict[str, Any]] = {}
    for message, result in results.items():
        message = str(message)
        clean[message] = _semantic_public_result(
            result, make_sample(message, "sample-id-only").sample_id
        )
    return clean


def _normalise_result_map(
    values: Mapping[str, Mapping[str, Any]],
    samples: Sequence[BlindJudgeSample],
) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, Dict[str, Any]]]:
    """Validate runner/cache values and detach artifact-binding metadata."""
    expected_ids = [sample.sample_id for sample in samples]
    if set(values) != set(expected_ids):
        raise ValueError("semantic batch results do not exactly cover pending samples")
    clean: Dict[str, Dict[str, Any]] = {}
    bindings: Dict[str, Dict[str, Any]] = {}
    for sample in samples:
        row = values[sample.sample_id]
        public = _semantic_public_result(row, sample.sample_id)
        if row.get("_prompt_version", CODEX_JUDGE_PROMPT_VERSION) != (
            CODEX_JUDGE_PROMPT_VERSION
        ):
            raise ValueError("semantic result has a different prompt version")
        if "_batch_id" in row and (
            not isinstance(row["_batch_id"], str)
            or not row["_batch_id"].startswith("batch_")
        ):
            raise ValueError("semantic result has an invalid batch id")
        value = {"sample_id": sample.sample_id, **public}
        for key in ("_batch_id", "_prompt_version"):
            if key in row:
                value[key] = row[key]
        clean[sample.sample_id] = value
        if "_artifact_binding" in row:
            binding = row["_artifact_binding"]
            if not isinstance(binding, Mapping):
                raise ValueError("semantic artifact binding is not an object")
            bindings[sample.sample_id] = dict(binding)
    return clean, bindings


def _semantic_artifact_binding(
    sample: BlindJudgeSample,
    model: str,
    batch_id: str,
    prompt_sha256: str,
    output_sha256: str,
    result: Mapping[str, Any],
) -> Dict[str, str]:
    return {
        "batch_id": batch_id,
        "model": str(model),
        "prompt_version": CODEX_JUDGE_PROMPT_VERSION,
        "prompt_sha256": prompt_sha256,
        "prompt_template_sha256": CODEX_JUDGE_PROMPT_SHA256,
        "rubric_sha256": CODEX_JUDGE_RUBRIC_SHA256,
        "message_sha256": _sha256(sample.message),
        "output_sha256": output_sha256,
        "result_sha256": canonical_json_sha256(result),
    }


def _validated_semantic_artifact_binding(
    binding: Mapping[str, Any],
    sample: BlindJudgeSample,
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
        raise ValueError("semantic cache artifact binding has unexpected fields")
    expected = {
        "model": str(model),
        "prompt_version": CODEX_JUDGE_PROMPT_VERSION,
        "prompt_template_sha256": CODEX_JUDGE_PROMPT_SHA256,
        "rubric_sha256": CODEX_JUDGE_RUBRIC_SHA256,
        "message_sha256": _sha256(sample.message),
        "result_sha256": canonical_json_sha256(result),
    }
    for key, value in expected.items():
        if binding.get(key) != value:
            raise ValueError("semantic cache artifact binding mismatch for %s" % key)
    for key in ("prompt_sha256", "output_sha256"):
        value = binding.get(key)
        if (
            not isinstance(value, str)
            or len(value) != 64
            or any(character not in "0123456789abcdef" for character in value)
        ):
            raise ValueError("semantic cache artifact binding has invalid %s" % key)
    if not isinstance(binding.get("batch_id"), str) or not str(
        binding["batch_id"]
    ).startswith("batch_"):
        raise ValueError("semantic cache artifact binding has invalid batch_id")
    return {key: str(binding[key]) for key in expected_keys}


SEMANTIC_BATCH_RECOVERY_VERSION = "v6-semantic-batch-recovery-v1"


def _semantic_recovery_path(artifact_dir: str, batch_id: str) -> str:
    return os.path.join(artifact_dir, ".%s.recovery.json" % batch_id)


def _semantic_batch_artifact_paths(
    artifact_dir: str, batch_id: str
) -> Tuple[str, str, str]:
    return (
        os.path.join(artifact_dir, batch_id + ".input.json"),
        os.path.join(artifact_dir, batch_id + ".output.json"),
        os.path.join(artifact_dir, batch_id + ".meta.json"),
    )


def _semantic_recovery_payload(
    input_payload: Mapping[str, Any],
    output_text: str,
    meta: Mapping[str, Any],
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "recovery_version": SEMANTIC_BATCH_RECOVERY_VERSION,
        "input_payload": dict(input_payload),
        "output_text": str(output_text),
        "meta": dict(meta),
    }
    payload["recovery_sha256"] = canonical_json_sha256(payload)
    return payload


def _validate_semantic_batch_artifacts(
    input_payload: Mapping[str, Any],
    output_text: str,
    meta: Mapping[str, Any],
    plan_row: Mapping[str, Any],
    model: str,
) -> Dict[str, Dict[str, Any]]:
    """Reconstruct one paid batch only after exact frozen-plan validation."""
    if dict(input_payload) != plan_row["input_payload"]:
        raise ValueError(
            "semantic recovery input differs from frozen seed/batch schedule"
        )
    if not isinstance(meta, Mapping):
        raise ValueError("semantic recovery metadata is not an object")
    if "stdout" in meta or "stderr" in meta:
        raise ValueError("semantic recovery metadata contains raw process logs")
    if meta.get("process_logs_retained") is not False:
        raise ValueError("semantic recovery process-log policy is missing")
    if meta.get("returncode") != 0:
        raise ValueError("semantic recovery batch was not successful")
    if meta.get("batch_id") != plan_row["batch_id"]:
        raise ValueError("semantic recovery batch id differs from frozen schedule")
    if meta.get("model") != str(model):
        raise ValueError("semantic recovery model differs from frozen schedule")
    if meta.get("prompt_version") != CODEX_JUDGE_PROMPT_VERSION:
        raise ValueError("semantic recovery prompt version differs from contract")
    if meta.get("prompt_template_sha256") != CODEX_JUDGE_PROMPT_SHA256:
        raise ValueError("semantic recovery prompt hash differs from contract")
    if meta.get("rubric_sha256") != CODEX_JUDGE_RUBRIC_SHA256:
        raise ValueError("semantic recovery rubric hash differs from contract")
    if meta.get("sample_ids") != list(plan_row["sample_ids"]):
        raise ValueError("semantic recovery sample order differs from schedule")
    if meta.get("prompt_sha256") != plan_row["prompt_sha256"]:
        raise ValueError("semantic recovery exact prompt hash mismatch")
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
                "semantic recovery %s differs from frozen schedule" % field
            )
    if any(os.path.isabs(str(value)) for value in meta.get("command_flags", [])):
        raise ValueError("semantic recovery metadata retains an absolute path")
    output_hashes = {_sha256(output_text)}
    if output_text.endswith("\n"):
        output_hashes.add(_sha256(output_text[:-1]))
    if meta.get("output_sha256") not in output_hashes:
        raise ValueError("semantic recovery output hash mismatch")
    try:
        output_payload = strict_json_loads(output_text)
    except ValueError as exc:
        raise ValueError("semantic recovery output is invalid JSON") from exc
    validated = validate_codex_payload(output_payload, plan_row["sample_ids"])
    samples = list(plan_row["samples"])
    by_id = {sample.sample_id: sample for sample in samples}
    prompt_sha256 = str(plan_row["prompt_sha256"])
    output_sha256 = str(meta["output_sha256"])
    for sample_id, result in validated.items():
        public = _semantic_public_result(result, sample_id)
        result["_batch_id"] = str(plan_row["batch_id"])
        result["_prompt_version"] = CODEX_JUDGE_PROMPT_VERSION
        result["_artifact_binding"] = _semantic_artifact_binding(
            by_id[sample_id],
            model,
            str(plan_row["batch_id"]),
            prompt_sha256,
            output_sha256,
            public,
        )
    return validated


def _load_semantic_recovery(
    path: str, plan_row: Mapping[str, Any], model: str
) -> Tuple[Dict[str, Any], Dict[str, Dict[str, Any]]]:
    try:
        supplied, _ = _strict_json_file(
            path,
            root=os.path.dirname(path) or os.curdir,
            label="semantic batch recovery journal",
        )
    except (OSError, ValueError) as exc:
        raise ValueError("semantic batch recovery journal is unreadable") from exc
    required = {
        "recovery_version",
        "input_payload",
        "output_text",
        "meta",
        "recovery_sha256",
    }
    if not isinstance(supplied, Mapping) or set(supplied) != required:
        raise ValueError("semantic batch recovery journal schema mismatch")
    payload = dict(supplied)
    supplied_hash = payload.pop("recovery_sha256")
    if supplied_hash != canonical_json_sha256(payload):
        raise ValueError("semantic batch recovery journal hash mismatch")
    if payload.get("recovery_version") != SEMANTIC_BATCH_RECOVERY_VERSION:
        raise ValueError("semantic batch recovery journal version mismatch")
    if not isinstance(payload.get("input_payload"), Mapping) or not isinstance(
        payload.get("meta"), Mapping
    ):
        raise ValueError("semantic batch recovery journal payload is malformed")
    if not isinstance(payload.get("output_text"), str):
        raise ValueError("semantic batch recovery output is not text")
    values = _validate_semantic_batch_artifacts(
        payload["input_payload"],
        payload["output_text"],
        payload["meta"],
        plan_row,
        model,
    )
    return dict(supplied), values


def _recover_semantic_batch_from_artifacts(
    artifact_dir: str,
    plan_row: Mapping[str, Any],
    model: str,
) -> Optional[Dict[str, Dict[str, Any]]]:
    """Recover a successful call without repeating it, or fail closed."""
    batch_id = str(plan_row["batch_id"])
    input_path, output_path, meta_path = _semantic_batch_artifact_paths(
        artifact_dir, batch_id
    )
    recovery_path = _semantic_recovery_path(artifact_dir, batch_id)
    flat_paths = (input_path, output_path, meta_path)
    flat_exists = [os.path.exists(path) for path in flat_paths]

    if os.path.exists(recovery_path):
        recovery, values = _load_semantic_recovery(
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
                        label="semantic recovered output artifact",
                    )
                else:
                    actual_value, _ = _strict_json_file(
                        path,
                        root=artifact_dir,
                        label="semantic recovered JSON artifact",
                    )
                if actual_value != expected_value:
                    raise ValueError(
                        "semantic recovery journal/triplet divergence for %s"
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
            "semantic batch has an incomplete artifact triplet; refusing to "
            "repeat a possibly paid call"
        )
    try:
        input_payload, _ = _strict_json_file(
            input_path,
            root=artifact_dir,
            label="semantic input artifact",
        )
        output_text = _read_regular_text(
            output_path,
            root=artifact_dir,
            label="semantic output artifact",
        )
        meta, _ = _strict_json_file(
            meta_path,
            root=artifact_dir,
            label="semantic metadata artifact",
        )
    except (OSError, ValueError) as exc:
        raise ValueError("semantic artifact triplet is unreadable") from exc
    return _validate_semantic_batch_artifacts(
        input_payload, output_text, meta, plan_row, model
    )


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
    process_runner: Callable[..., Any] = subprocess.run,
    batch_context: Optional[Mapping[str, Any]] = None,
    official_contract: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Dict[str, Any]]:
    """Run one schema-constrained Codex call and preserve auditable artifacts."""
    if not samples:
        return {}
    expected_ids = [sample.sample_id for sample in samples]
    batch_id = _semantic_batch_id(samples)
    validated_official = (
        _verify_official_executable_for_dispatch(
            executable,
            official_contract,
            kind="semantic",
            model=model,
        )
        if official_contract is not None
        else None
    )
    os.makedirs(artifact_dir, exist_ok=True)
    prompt = build_codex_prompt(samples)

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
            raise ValueError("semantic judge batch context is incomplete")
        if batch_context["batch_id"] != batch_id:
            raise ValueError("semantic judge batch context has wrong batch id")
        if batch_context["model"] != str(model):
            raise ValueError("semantic judge batch context has wrong model")
        if list(batch_context["sample_ids"]) != expected_ids:
            raise ValueError("semantic judge batch context has wrong sample order")
        if batch_context["prompt_sha256"] != _sha256(prompt):
            raise ValueError("semantic judge batch context has wrong prompt hash")
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
        "prompt_version": CODEX_JUDGE_PROMPT_VERSION,
        "prompt_template_sha256": CODEX_JUDGE_PROMPT_SHA256,
        "rubric_sha256": CODEX_JUDGE_RUBRIC_SHA256,
        "samples": [sample.judge_dict() for sample in samples],
    }

    output_schema = codex_output_schema(expected_ids)
    _, claimed_provider_output_path, _ = _paid_batch_paths(
        artifact_dir, batch_id
    )
    claim = _paid_batch_claim_payload(
        kind="semantic",
        batch_id=batch_id,
        model=model,
        executable=executable,
        prompt_version=CODEX_JUDGE_PROMPT_VERSION,
        prompt_template_sha256=CODEX_JUDGE_PROMPT_SHA256,
        rubric_sha256=CODEX_JUDGE_RUBRIC_SHA256,
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
                "prompt_version": CODEX_JUDGE_PROMPT_VERSION,
                "prompt_template_sha256": CODEX_JUDGE_PROMPT_SHA256,
                "rubric_sha256": CODEX_JUDGE_RUBRIC_SHA256,
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
            input_path, input_payload, kind="semantic", batch_id=batch_id
        )
        _write_or_verify_exact_text_artifact(
            output_path, failed_output, kind="semantic", batch_id=batch_id
        )
        _write_or_verify_exact_json_artifact(
            meta_path, failed_meta, kind="semantic", batch_id=batch_id
        )
        return failed_meta

    with tempfile.TemporaryDirectory(prefix="latenttarget_codex_judge_") as tmpdir:
        schema_path = os.path.join(tmpdir, "schema.json")
        with open(schema_path, "w", encoding="utf-8") as fh:
            json.dump(output_schema, fh, indent=2)
            fh.flush()
            os.fsync(fh.fileno())
        first_dispatch, _, provider_output_path, state_path = (
            _prepare_paid_batch_claim(
                artifact_dir,
                claim,
                kind="semantic",
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
            tmpdir,
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
                            kind="semantic",
                            batch_id=batch_id,
                        )
                        exception_payload = strict_json_loads(raw_after_exception)
                        validate_codex_payload(exception_payload, expected_ids)
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
                        kind="semantic",
                        batch_id=batch_id,
                    )
                if isinstance(exc, subprocess.TimeoutExpired):
                    raise RuntimeError(
                        "Codex judge batch %s timed out after %d seconds"
                        % (batch_id, timeout_s)
                    ) from None
                raise

            elapsed = time.time() - started
            raw = ""
            if os.path.lexists(provider_output_path):
                try:
                    raw = _read_durable_provider_output(
                        provider_output_path,
                        kind="semantic",
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
                        kind="semantic",
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
                    kind="semantic",
                    batch_id=batch_id,
                )
                meta = persist_failed_triplet(raw, state, command)
                raise RuntimeError(
                    "Codex judge batch %s failed with exit %d (stderr sha256 %s)"
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
                    kind="semantic",
                    batch_id=batch_id,
                )
                persist_failed_triplet("", state, command)
                raise RuntimeError(
                    "Codex judge batch %s produced no durable provider output"
                    % batch_id
                )
            try:
                payload = strict_json_loads(raw)
                validated = validate_codex_payload(payload, expected_ids)
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
                    kind="semantic",
                    batch_id=batch_id,
                )
                persist_failed_triplet(raw, state, command)
                raise ValueError(
                    "Codex judge batch %s returned invalid strict JSON or schema"
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
                kind="semantic",
                batch_id=batch_id,
            )
        else:
            raw, state = _validated_existing_paid_output(
                claim=claim,
                provider_output_path=provider_output_path,
                state_path=state_path,
                kind="semantic",
                batch_id=batch_id,
            )
            try:
                payload = strict_json_loads(raw)
                validated = validate_codex_payload(payload, expected_ids)
            except ValueError as exc:
                raise _paid_batch_reconciliation_error(
                    "semantic",
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
                    kind="semantic",
                    batch_id=batch_id,
                )

    meta = build_meta(state, command)
    output_text = raw + ("\n" if raw and not raw.endswith("\n") else "")
    prompt_sha256 = _sha256(prompt)
    output_sha256 = _sha256(raw)
    by_id = {sample.sample_id: sample for sample in samples}
    for sample_id, result in validated.items():
        public = _semantic_public_result(result, sample_id)
        result["_batch_id"] = batch_id
        result["_prompt_version"] = CODEX_JUDGE_PROMPT_VERSION
        result["_artifact_binding"] = _semantic_artifact_binding(
            by_id[sample_id],
            model,
            batch_id,
            prompt_sha256,
            output_sha256,
            public,
        )
    recovery_path = _semantic_recovery_path(artifact_dir, batch_id)
    _write_or_verify_exact_json_artifact(
        recovery_path,
        _semantic_recovery_payload(input_payload, output_text, meta),
        kind="semantic",
        batch_id=batch_id,
    )
    _write_or_verify_exact_json_artifact(
        input_path, input_payload, kind="semantic", batch_id=batch_id
    )
    _write_or_verify_exact_text_artifact(
        output_path, output_text, kind="semantic", batch_id=batch_id
    )
    _write_or_verify_exact_json_artifact(
        meta_path, meta, kind="semantic", batch_id=batch_id
    )
    return validated


class CodexBlindJudge:
    """Resumable judge whose per-message cache is published whole-batch atomic."""

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
        official_contract: Optional[Mapping[str, Any]] = None,
    ) -> None:
        self.model = model
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
                kind="semantic",
                model=model,
                seed=seed,
                batch_size=batch_size,
                prompt_version=CODEX_JUDGE_PROMPT_VERSION,
                prompt_sha256=CODEX_JUDGE_PROMPT_SHA256,
                rubric_sha256=CODEX_JUDGE_RUBRIC_SHA256,
            )
            if official_contract is not None
            else None
        )
        self._require_artifact_binding = batch_runner is run_codex_batch
        self.name = "codex_cli_judge[%s/%s]" % (model, CODEX_JUDGE_PROMPT_VERSION)
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
            self.cache_path, label="semantic judge cache"
        )
        for lineno, record in enumerate(records, start=1):
            try:
                key = str(record["key"])
                message_hash = str(record["message_sha256"])
                value = record["value"]
            except (KeyError, TypeError) as exc:
                raise ValueError(
                    "invalid judge cache record at %s:%d"
                    % (self.cache_path, lineno)
                ) from exc
            if record.get("model") != self.model:
                raise ValueError("judge cache contains a different judge model")
            if len(key) != 64 or any(
                character not in "0123456789abcdef" for character in key
            ):
                raise ValueError("judge cache contains an invalid cache key")
            if record.get("prompt_version") != CODEX_JUDGE_PROMPT_VERSION:
                raise ValueError("judge cache contains a different prompt version")
            if record.get(
                "prompt_template_sha256", CODEX_JUDGE_PROMPT_SHA256
            ) != CODEX_JUDGE_PROMPT_SHA256:
                raise ValueError("judge cache contains a different prompt hash")
            if record.get(
                "rubric_sha256", CODEX_JUDGE_RUBRIC_SHA256
            ) != CODEX_JUDGE_RUBRIC_SHA256:
                raise ValueError("judge cache contains a different rubric hash")
            if len(message_hash) != 64 or any(
                character not in "0123456789abcdef"
                for character in message_hash
            ):
                raise ValueError("judge cache contains an invalid message hash")
            if not isinstance(value, Mapping):
                raise ValueError("judge cache value is not an object")
            sample_id = value.get("sample_id")
            if not isinstance(sample_id, str):
                raise ValueError("judge cache value has no sample id")
            public = _semantic_public_result(value, sample_id)
            if record.get(
                "value_sha256", canonical_json_sha256(public)
            ) != canonical_json_sha256(public):
                raise ValueError("judge cache value hash mismatch")
            binding = record.get("artifact_binding")
            if binding is not None and not isinstance(binding, Mapping):
                raise ValueError("judge cache artifact binding is not an object")
            if key in cache and (
                cache[key] != value
                or self._cache_message_hashes[key] != message_hash
                or self._cache_bindings.get(key)
                != (dict(binding) if binding is not None else None)
            ):
                raise ValueError("conflicting duplicate judge cache key %s" % key)
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
        samples: Sequence[BlindJudgeSample],
        values: Mapping[str, Dict[str, Any]],
    ) -> None:
        clean, bindings = _normalise_result_map(values, samples)
        if self._require_artifact_binding and set(bindings) != {
            sample.sample_id for sample in samples
        }:
            raise ValueError("semantic runner omitted required artifact binding")
        parent = os.path.dirname(self.cache_path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        pending_records: List[Dict[str, Any]] = []
        pending_state: List[
            Tuple[BlindJudgeSample, Dict[str, Any], Optional[Dict[str, str]]]
        ] = []
        for sample in samples:
            if sample.cache_key in self._cache:
                raise ValueError("semantic cache append would duplicate a cache key")
            value = dict(clean[sample.sample_id])
            public = _semantic_public_result(value, sample.sample_id)
            binding = bindings.get(sample.sample_id)
            validated_binding = None
            if binding is not None:
                validated_binding = _validated_semantic_artifact_binding(
                    binding, sample, self.model, public
                )
                if value.get("_batch_id", validated_binding["batch_id"]) != (
                    validated_binding["batch_id"]
                ):
                    raise ValueError("semantic cache batch id/binding mismatch")
                if value.get(
                    "_prompt_version", CODEX_JUDGE_PROMPT_VERSION
                ) != CODEX_JUDGE_PROMPT_VERSION:
                    raise ValueError("semantic cache prompt version mismatch")
            record: Dict[str, Any] = {
                "cache_record_version": 2 if validated_binding else 1,
                "key": sample.cache_key,
                "message_sha256": _sha256(sample.message),
                "model": self.model,
                "prompt_version": CODEX_JUDGE_PROMPT_VERSION,
                "prompt_template_sha256": CODEX_JUDGE_PROMPT_SHA256,
                "rubric_sha256": CODEX_JUDGE_RUBRIC_SHA256,
                "value_sha256": canonical_json_sha256(public),
                "value": value,
            }
            if validated_binding is not None:
                record["artifact_binding"] = validated_binding
            pending_records.append(record)
            pending_state.append((sample, value, validated_binding))

        # The only mutation of the on-disk cache is one durable rename.  The
        # in-memory cache changes only after that rename succeeds.
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
        self, sample: BlindJudgeSample
    ) -> Dict[str, Any]:
        if self._cache_message_hashes.get(sample.cache_key) != _sha256(
            sample.message
        ):
            raise ValueError("judge cache message hash mismatch")
        clean, _ = _normalise_result_map(
            {sample.sample_id: self._cache[sample.cache_key]}, [sample]
        )
        value = clean[sample.sample_id]
        binding = self._cache_bindings.get(sample.cache_key)
        if binding is not None:
            public = _semantic_public_result(value, sample.sample_id)
            checked = _validated_semantic_artifact_binding(
                binding, sample, self.model, public
            )
            if value.get("_batch_id", checked["batch_id"]) != checked["batch_id"]:
                raise ValueError("judge cache batch id/binding mismatch")
        return value

    def classify_messages(self, messages: Iterable[str]) -> Dict[str, Dict[str, Any]]:
        message_list = [str(message) for message in messages]
        batches = build_blind_batches(
            message_list, self.model, self.batch_size, self.seed
        )
        batch_plan = build_codex_batch_plan(
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
                    "semantic cache is not an exact prefix of the frozen batch "
                    "schedule"
                )
        for batch_index, batch in enumerate(batches, start=1):
            pending = [sample for sample in batch if sample.cache_key not in self._cache]
            cached = [sample for sample in batch if sample.cache_key in self._cache]
            for sample in cached:
                self._validated_cached_value(sample)
            recovered = None
            if self._require_artifact_binding:
                recovered = _recover_semantic_batch_from_artifacts(
                    self.artifact_dir,
                    batch_plan[batch_index - 1],
                    self.model,
                )
            if recovered is not None:
                recovered_clean, recovered_bindings = _normalise_result_map(
                    recovered, batch
                )
                cached_ids = [sample.sample_id for sample in cached]
                expected_prefix = [
                    sample.sample_id for sample in batch[: len(cached)]
                ]
                if cached_ids != expected_prefix:
                    raise ValueError(
                        "semantic partial cache is not a frozen-batch prefix"
                    )
                for sample in cached:
                    if self._cache[sample.cache_key] != recovered_clean[
                        sample.sample_id
                    ] or self._cache_bindings.get(sample.cache_key) != (
                        recovered_bindings.get(sample.sample_id)
                    ):
                        raise ValueError(
                            "semantic partial cache differs from recovered artifacts"
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
                    "semantic frozen batch is only partially cached and has no "
                    "recoverable paid artifacts"
                )
            print(
                "judging blind batch %d/%d (%d messages)"
                % (batch_index, len(batches), len(pending)),
                flush=True,
            )
            if self.batch_runner is run_codex_batch:
                values = run_codex_batch(
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
            "judge_prompt_version": CODEX_JUDGE_PROMPT_VERSION,
            "judge_prompt_sha256": CODEX_JUDGE_PROMPT_SHA256,
            "judge_rubric": CODEX_JUDGE_RUBRIC,
            "judge_rubric_sha256": CODEX_JUDGE_RUBRIC_SHA256,
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


def audit_codex_cache(
    cache_path: str,
    messages: Iterable[str],
    model: str,
    batch_size: int,
    seed: int,
    artifact_audit: Mapping[str, Any],
    *,
    repository_root: Optional[str] = None,
) -> Dict[str, Any]:
    """Replay every semantic cache record against the frozen batch artifacts."""
    if not os.path.isfile(cache_path):
        raise FileNotFoundError("judge cache not found: %s" % cache_path)
    message_list = _unique_messages(messages)
    plan = build_codex_batch_plan(message_list, model, batch_size, seed)
    ordered_samples = [sample for row in plan for sample in row["samples"]]
    by_sample_id = {sample.sample_id: sample for sample in ordered_samples}
    expected_ids = [sample.sample_id for sample in ordered_samples]
    records, cache_raw = _strict_jsonl_file(
        cache_path,
        root=repository_root,
        label="semantic judge cache",
    )
    actual_ids = [
        str(record.get("value", {}).get("sample_id", ""))
        if isinstance(record.get("value"), Mapping)
        else ""
        for record in records
    ]
    if actual_ids != expected_ids:
        raise ValueError(
            "judge cache order/coverage differs from frozen seed/batch schedule"
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
        raise ValueError("judge artifact audit has no replayable results")
    cache_results: Dict[str, Dict[str, Any]] = {}
    for record, sample in zip(records, ordered_samples):
        if set(record) != required_keys:
            raise ValueError("judge cache record fields differ from frozen schema")
        if record["cache_record_version"] != 2:
            raise ValueError("judge cache record is not artifact-bound version 2")
        if record["key"] != sample.cache_key:
            raise ValueError("judge cache key differs from frozen message/model")
        if record["message_sha256"] != _sha256(sample.message):
            raise ValueError("judge cache message hash mismatch")
        if record["model"] != str(model):
            raise ValueError("judge cache model differs from frozen contract")
        if record["prompt_version"] != CODEX_JUDGE_PROMPT_VERSION:
            raise ValueError("judge cache prompt version differs from contract")
        if record["prompt_template_sha256"] != CODEX_JUDGE_PROMPT_SHA256:
            raise ValueError("judge cache prompt hash differs from contract")
        if record["rubric_sha256"] != CODEX_JUDGE_RUBRIC_SHA256:
            raise ValueError("judge cache rubric hash differs from contract")
        value = record["value"]
        if not isinstance(value, Mapping):
            raise ValueError("judge cache value is not an object")
        public = _semantic_public_result(value, sample.sample_id)
        if record["value_sha256"] != canonical_json_sha256(public):
            raise ValueError("judge cache value hash mismatch")
        expected_binding = artifact_bindings.get(sample.message)
        if record["artifact_binding"] != expected_binding:
            raise ValueError("judge cache/artifact binding divergence")
        checked_binding = _validated_semantic_artifact_binding(
            record["artifact_binding"], sample, model, public
        )
        if value.get("_batch_id") != checked_binding["batch_id"]:
            raise ValueError("judge cache batch id differs from artifact")
        if value.get("_prompt_version") != CODEX_JUDGE_PROMPT_VERSION:
            raise ValueError("judge cache value prompt version differs")
        if artifact_results.get(sample.message) != public:
            raise ValueError("judge cache result differs from raw artifact")
        cache_results[sample.message] = public

    if canonical_json_sha256(cache_results) != artifact_audit.get(
        "result_map_sha256"
    ):
        raise ValueError("judge cache result map differs from artifact result map")
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
        "message_set_sha256": _message_set_sha256(message_list),
        "result_map": cache_results,
        "result_map_sha256": canonical_json_sha256(cache_results),
    }


def audit_codex_judge_run(
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
    """Replay one complete semantic judge run from raw files, fail closed."""
    validated_official = (
        _validate_official_run_coordinates(
            official_contract,
            kind="semantic",
            model=model,
            seed=seed,
            batch_size=batch_size,
            prompt_version=CODEX_JUDGE_PROMPT_VERSION,
            prompt_sha256=CODEX_JUDGE_PROMPT_SHA256,
            rubric_sha256=CODEX_JUDGE_RUBRIC_SHA256,
        )
        if official_contract is not None
        else None
    )
    message_list = _unique_messages(messages)
    artifact_audit = audit_codex_artifacts(
        artifact_dir,
        expected_messages=message_list,
        model=model,
        batch_size=batch_size,
        seed=seed,
        repository_root=repository_root,
        official_contract=validated_official,
    )
    cache_audit = audit_codex_cache(
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
            "v6-semantic-judge-run-v2"
            if validated_official is not None
            else "v6-semantic-judge-run-v1"
        ),
        "kind": "semantic",
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


def replay_codex_judge_run_from_manifest(
    messages: Iterable[str],
    manifest: Mapping[str, Any],
    repository_root: str,
) -> Dict[str, Any]:
    """Resolve repository-local paths and independently replay a saved run."""
    if not isinstance(manifest, Mapping):
        raise ValueError("semantic judge run manifest is not an object")
    supplied = dict(manifest)
    manifest_sha256 = supplied.pop("manifest_sha256", None)
    if manifest_sha256 != canonical_json_sha256(supplied):
        raise ValueError("semantic judge run manifest hash mismatch")
    manifest_version = supplied.get("manifest_version")
    if manifest_version not in {
        "v6-semantic-judge-run-v1",
        "v6-semantic-judge-run-v2",
    }:
        raise ValueError("unexpected semantic judge run manifest version")
    official_contract = None
    if manifest_version == "v6-semantic-judge-run-v2":
        official_contract = supplied.get("official_contract")
        validated_official = _validated_official_judge_contract(
            official_contract, kind="semantic"
        )
        if supplied.get("official_contract_sha256") != validated_official[
            "official_contract_sha256"
        ]:
            raise ValueError("semantic run manifest official contract mismatch")
    elif "official_contract" in supplied or "official_contract_sha256" in supplied:
        raise ValueError("legacy semantic manifest cannot claim official identity")
    artifact_dir = _resolve_repository_path(
        str(supplied.get("artifact_dir", "")), repository_root
    )
    cache_path = _resolve_repository_path(
        str(supplied.get("cache_path", "")), repository_root
    )
    replayed = audit_codex_judge_run(
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
        raise ValueError("semantic judge run manifest differs from raw-file replay")
    return replayed
