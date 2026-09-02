"""Fail-closed audits for the final V6 calibration artifact graph.

The protocol status strings are descriptive only.  V6 authorization comes from
reloading the frozen artifacts, checking their hashes, and replaying the
deterministic selection and validation transitions.
"""

from __future__ import annotations

import hashlib
import json
import os
from typing import Any, Dict, List, Mapping, Optional

from config import (
    CONTROLLED_V6_ANALYSIS_CONFIG,
    CONTROLLED_V6_CALIBRATION_THRESHOLDS,
    CONTROLLED_V6_GATE_THRESHOLDS,
    CONTROLLED_V6_PAID_PREFLIGHT_RECEIPT_PATH,
    CONTROLLED_V6_QUALITY_THRESHOLDS,
    CONTROLLED_V6_RANDOMIZATION_SEED,
    CONTROLLED_V6_SEMANTIC_THRESHOLDS,
    CONTROLLED_V6_VERSION,
    ControlledExperimentConfig,
    ControlledTargetParams,
    ModelConfig,
)
from .controlled_experiment import build_controlled_episode_specs
from .controlled_v6_messages import (
    V6_PROVISIONAL_POOL_STATUS,
    V6_SELECTED_BANK_STATUS,
    V6TriadBank,
)
from .controlled_v6_randomization import v6_allocation_schedule
from .hf_provider import V6_FOCAL_RUNTIME_EVIDENCE_VERSION
from .logging_utils import (
    read_jsonl,
    read_regular_bytes,
    strict_json_load,
    strict_json_loads,
)
from .v6_calibration import (
    V6_CALIBRATION_FOLDS,
    V6_POOL_MODE,
    V6_VALIDATION_MODE,
    audit_v6_calibration_run,
    bank_content_sha256,
    canonical_sha256,
    evaluate_v6_bank_validation,
    file_sha256,
    finalize_validated_v6_bank,
    select_v6_bank,
)
from .scenarios import V6_SCENARIO_SETS, v6_scenario_sequence
from .controlled_v6_power import (
    V6_POWER_CONTRACT_SHA256,
    V6_PROSPECTIVE_POWER_CONTRACT,
    audit_v6_power_payload,
)
from .v6_quality_validation import audit_v6_quality_validation_summary
from .v6_semantic_validation import audit_v6_semantic_validation_summary


V6_CALIBRATION_PROTOCOL_VERSION = "v6-calibration-protocol-1.0"
V6_PREVALIDATION_CHECKPOINT_VERSION = "v6-prevalidation-checkpoint-1.0"
V6_FINAL_CHECKPOINT_VERSION = "v6-final-checkpoint-1.0"
V6_PREVALIDATION_CHECKPOINT_STATUS = "FROZEN_BEFORE_V6_INDEPENDENT_VALIDATION"
V6_FINAL_CHECKPOINT_STATUS = "FROZEN_BEFORE_V6_CONFIRMATORY_OUTCOMES"
V6_CONFIRMATORY_EPISODES_PER_SEED = 24
V6_FOCAL_RUNTIME_CONTRACT_VERSION = "v6-focal-runtime-contract-1.0"
V6_FROZEN_FOCAL_RUNTIME_CONTRACT: Dict[str, Any] = {
    "contract_version": V6_FOCAL_RUNTIME_CONTRACT_VERSION,
    "requirements_file": "requirements-pod.txt",
    "device_argument": "auto",
    "python": {
        "implementation": "CPython",
        "major": 3,
        "minor": 12,
    },
    "exact_packages": {
        "torch": "2.9.1",
        "torchvision": "0.24.1",
        "torchaudio": "2.9.1",
        "transformers": "5.16.1",
        "accelerate": "1.14.0",
    },
    # These versions are intentionally observed at pool screening rather than
    # guessed here, then held equal through validation and confirmation.
    "record_and_match_packages": ["numpy", "sentencepiece"],
    "cuda": {
        "required": True,
        "bfloat16_required": True,
    },
    "hardware": {
        "visible_device_count": 1,
        "vendor_name_fragment": "NVIDIA",
        "product_name_fragment": "A100",
        "memory_class": "80GB",
        "minimum_total_memory_bytes": 80_000_000_000,
        "compute_capability": [8, 0],
    },
    "cross_stage": {
        "stages": [
            "pool_screening",
            "selected_bank_validation",
            "confirmatory",
        ],
        "comparison": "exact_canonical_json",
        "all_evidence_fields": True,
    },
}
V6_CANONICAL_RUN_PATHS = {
    V6_POOL_MODE: {
        "out_dir": "data/calibration/v6_pool_screening",
        "receipt": "results/v6_design/launch_receipts/v6_pool_screening.json",
    },
    V6_VALIDATION_MODE: {
        "out_dir": "data/calibration/v6_bank_validation",
        "receipt": "results/v6_design/launch_receipts/v6_bank_validation.json",
    },
    "confirmatory": {
        "out_dir": "data/raw/v6_confirmatory",
        "receipt": "results/v6_design/launch_receipts/v6_confirmatory.json",
        "preflight": "results/v6_design/confirmatory_paid_preflight.json",
        "preflight_receipt": CONTROLLED_V6_PAID_PREFLIGHT_RECEIPT_PATH,
    },
}
V6_CANONICAL_MEASUREMENT_PATHS = {
    "semantic": {
        "summary": "results/v6_design/semantic_validation/summary.json",
        "out_dir": "results/v6_design/semantic_validation",
        "cache_dir": "data/processed/v6_semantic_validation",
    },
    "quality": {
        "summary": "results/v6_design/quality_validation/summary.json",
        "out_dir": "results/v6_design/quality_validation",
        "cache_dir": "data/processed/v6_quality_validation",
    },
    "power": {
        "out_dir": "results/v6_design/power_prevalidation",
    },
}


def _runtime_mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def audit_v6_focal_runtime(
    contract: Any,
    evidence: Any,
    *,
    expected_evidence: Optional[Mapping[str, Any]] = None,
    device_argument: Any = "auto",
) -> Dict[str, Any]:
    """Audit one model-free focal-runtime observation against the V6 freeze.

    The pool-screening observation is the cross-stage anchor.  Fields whose
    exact pod values were not known at preregistration time (notably NumPy,
    Python patch level, CUDA build/runtime, and the precise A100 device string)
    are still mandatory and must match that anchor exactly thereafter.
    """
    supplied_contract = _runtime_mapping(contract)
    observed = _runtime_mapping(evidence)
    python = _runtime_mapping(observed.get("python"))
    packages = _runtime_mapping(observed.get("packages"))
    module_versions = _runtime_mapping(observed.get("module_versions"))
    cuda = _runtime_mapping(observed.get("cuda"))
    devices = observed.get("devices")
    devices = devices if isinstance(devices, list) else []
    hardware = V6_FROZEN_FOCAL_RUNTIME_CONTRACT["hardware"]
    exact_packages = V6_FROZEN_FOCAL_RUNTIME_CONTRACT["exact_packages"]
    recorded_packages = V6_FROZEN_FOCAL_RUNTIME_CONTRACT[
        "record_and_match_packages"
    ]
    expected_package_names = set(exact_packages) | set(recorded_packages)
    version_info = python.get("version_info")
    version_info_ok = (
        isinstance(version_info, list)
        and len(version_info) == 3
        and all(type(value) is int and value >= 0 for value in version_info)
    )
    python_version_ok = (
        version_info_ok
        and type(python.get("version")) is str
        and python.get("version") == ".".join(str(value) for value in version_info)
    )
    device = devices[0] if len(devices) == 1 and isinstance(devices[0], Mapping) else {}
    memory = device.get("total_memory_bytes")
    name = device.get("name")
    module_keys = {"numpy", "torch", "transformers", "accelerate"}
    torch_module_version = module_versions.get("torch")
    checks: Dict[str, bool] = {
        "contract_exact": _strict_json_equal(
            supplied_contract, V6_FROZEN_FOCAL_RUNTIME_CONTRACT
        ),
        "evidence_schema": set(observed)
        == {
            "evidence_version",
            "requested_device",
            "resolved_device_type",
            "python",
            "packages",
            "module_versions",
            "cuda",
            "devices",
        },
        "evidence_version": observed.get("evidence_version")
        == V6_FOCAL_RUNTIME_EVIDENCE_VERSION,
        "device_argument_auto": device_argument == "auto"
        and observed.get("requested_device") == "auto",
        "resolved_cuda_device": observed.get("resolved_device_type") == "cuda",
        "python_schema": set(python)
        == {"implementation", "version", "version_info"},
        "python_implementation": python.get("implementation") == "CPython",
        "python_family": version_info_ok and version_info[:2] == [3, 12],
        "python_version_exactly_recorded": python_version_ok,
        "package_schema": set(packages) == expected_package_names,
        "exact_package_versions": all(
            type(packages.get(name)) is str
            and (
                packages.get(name) == expected
                or (
                    name in {"torch", "torchvision", "torchaudio"}
                    and packages.get(name).split("+", 1)[0] == expected
                )
            )
            for name, expected in exact_packages.items()
        ),
        "unfrozen_package_versions_recorded": all(
            type(packages.get(name)) is str and bool(packages.get(name))
            for name in recorded_packages
        ),
        "module_version_schema": set(module_versions) == module_keys,
        "module_versions_recorded": all(
            type(module_versions.get(name)) is str
            and bool(module_versions.get(name))
            for name in module_keys
        ),
        "numpy_module_matches_distribution": module_versions.get("numpy")
        == packages.get("numpy"),
        "torch_module_matches_frozen_release": type(torch_module_version) is str
        and torch_module_version.split("+", 1)[0] == exact_packages["torch"],
        "transformers_module_matches_distribution": module_versions.get(
            "transformers"
        )
        == packages.get("transformers"),
        "accelerate_module_matches_distribution": module_versions.get("accelerate")
        == packages.get("accelerate"),
        "cuda_schema": set(cuda)
        == {
            "available",
            "torch_build_version",
            "runtime_version",
            "device_count",
            "bfloat16_supported",
        },
        "cuda_available": cuda.get("available") is True,
        "cuda_build_recorded": type(cuda.get("torch_build_version")) is str
        and bool(cuda.get("torch_build_version")),
        "cuda_runtime_recorded": type(cuda.get("runtime_version")) is int
        and cuda.get("runtime_version", 0) > 0,
        "single_visible_device": type(cuda.get("device_count")) is int
        and cuda.get("device_count") == hardware["visible_device_count"]
        == len(devices),
        "bfloat16_supported": cuda.get("bfloat16_supported") is True,
        "device_schema": set(device)
        == {"index", "name", "compute_capability", "total_memory_bytes"},
        "device_index": type(device.get("index")) is int
        and device.get("index") == 0,
        "nvidia_a100_name": type(name) is str
        and hardware["vendor_name_fragment"].casefold() in name.casefold()
        and hardware["product_name_fragment"].casefold() in name.casefold(),
        "compute_capability": _strict_json_equal(
            device.get("compute_capability"), hardware["compute_capability"]
        ),
        "a100_80gb_memory": type(memory) is int
        and memory >= hardware["minimum_total_memory_bytes"],
        "cross_stage_exact": expected_evidence is None
        or _strict_json_equal(observed, expected_evidence),
    }
    evidence_hash: Optional[str] = None
    if observed:
        try:
            evidence_hash = canonical_sha256(observed)
        except (TypeError, ValueError):
            evidence_hash = None
    return {
        "pass": all(checks.values()),
        "checks": checks,
        "contract_sha256": canonical_sha256(V6_FROZEN_FOCAL_RUNTIME_CONTRACT),
        "evidence_sha256": evidence_hash,
        "evidence": dict(observed),
    }


def require_v6_focal_runtime(
    protocol: Mapping[str, Any],
    evidence: Mapping[str, Any],
    *,
    expected_evidence: Optional[Mapping[str, Any]] = None,
    device_argument: Any = "auto",
) -> Dict[str, Any]:
    """Return a passing audit or raise before an official artifact is written."""
    audit = audit_v6_focal_runtime(
        protocol.get("focal_runtime"),
        evidence,
        expected_evidence=expected_evidence,
        device_argument=device_argument,
    )
    if audit.get("pass") is not True:
        failed = sorted(
            name for name, passed in audit.get("checks", {}).items() if not passed
        )
        raise ValueError("V6 focal runtime contract failed: %s" % ", ".join(failed))
    return audit


def build_v6_focal_runtime_checkpoint(
    protocol: Mapping[str, Any], evidence: Mapping[str, Any]
) -> Dict[str, Any]:
    """Build the exact runtime object carried between all focal stages."""
    audit = require_v6_focal_runtime(protocol, evidence)
    return {
        "contract": json.loads(
            json.dumps(V6_FROZEN_FOCAL_RUNTIME_CONTRACT, allow_nan=False)
        ),
        "contract_sha256": audit["contract_sha256"],
        "evidence": json.loads(json.dumps(evidence, allow_nan=False)),
        "evidence_sha256": audit["evidence_sha256"],
    }


def audit_v6_focal_runtime_checkpoint(
    payload: Any,
    protocol: Mapping[str, Any],
    *,
    expected_evidence: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    """Audit a checkpoint-carried runtime contract and evidence object."""
    runtime = _runtime_mapping(payload)
    evidence = _runtime_mapping(runtime.get("evidence"))
    audit = audit_v6_focal_runtime(
        runtime.get("contract"),
        evidence,
        expected_evidence=expected_evidence,
    )
    checks = dict(audit["checks"])
    checks.update(
        {
            "protocol_contract": _strict_json_equal(
                protocol.get("focal_runtime"),
                V6_FROZEN_FOCAL_RUNTIME_CONTRACT,
            ),
            "contract_hash": runtime.get("contract_sha256")
            == audit["contract_sha256"],
            "evidence_hash": runtime.get("evidence_sha256")
            == audit["evidence_sha256"],
            "checkpoint_schema": set(runtime)
            == {"contract", "contract_sha256", "evidence", "evidence_sha256"},
        }
    )
    return {
        **audit,
        "pass": all(checks.values()),
        "checks": checks,
    }


def _strict_json_equal(observed: Any, expected: Any) -> bool:
    """Compare JSON values without Python's bool/int/float coercions."""
    if type(observed) is not type(expected):
        return False
    if isinstance(expected, dict):
        return set(observed) == set(expected) and all(
            _strict_json_equal(observed[key], expected[key]) for key in expected
        )
    if isinstance(expected, list):
        return len(observed) == len(expected) and all(
            _strict_json_equal(left, right)
            for left, right in zip(observed, expected)
        )
    return observed == expected

def _discover_v6_executable_source_paths(project_root: str) -> tuple[str, ...]:
    """Bind the complete in-repository Python runtime, not a hand-picked list.

    V6 deliberately accepts an over-inclusive source closure.  Every Python
    module under ``src`` and ``scripts`` plus both dependency lock inputs is
    frozen.  This prevents a newly noticed transitive import from escaping the
    checkpoint simply because it was absent from a manually maintained list.
    """
    paths = {"config.py", "requirements.txt", "requirements-pod.txt"}
    for directory in ("src", "scripts"):
        absolute_directory = os.path.join(project_root, directory)
        for current_root, _directories, filenames in os.walk(absolute_directory):
            for filename in filenames:
                if not filename.endswith(".py"):
                    continue
                absolute = os.path.join(current_root, filename)
                paths.add(os.path.relpath(absolute, project_root))
    return tuple(sorted(paths))


_V6_IMPORT_PROJECT_ROOT = os.path.realpath(
    os.path.join(os.path.dirname(__file__), os.pardir)
)
V6_ALL_EXECUTABLE_SOURCE_PATHS = _discover_v6_executable_source_paths(
    _V6_IMPORT_PROJECT_ROOT
)
V6_PREVALIDATION_SOURCE_PATHS = V6_ALL_EXECUTABLE_SOURCE_PATHS
V6_CONFIRMATORY_SOURCE_PATHS = V6_ALL_EXECUTABLE_SOURCE_PATHS


def _resolve(root: str, path: str) -> str:
    return path if os.path.isabs(path) else os.path.join(root, path)


def _inside_root(path: str, root: str) -> bool:
    try:
        return os.path.commonpath(
            [os.path.realpath(path), os.path.realpath(root)]
        ) == os.path.realpath(root)
    except ValueError:
        return False


def v6_artifact_reference(
    path: str, repository_root: str, *, canonical_json: bool = True
) -> Dict[str, Any]:
    """Return a repository-local immutable reference for a checkpoint."""
    absolute = os.path.abspath(path)
    root = os.path.abspath(repository_root)
    if not _inside_root(absolute, root):
        raise ValueError("V6 checkpoint artifacts must be inside the repository root")
    raw = read_regular_bytes(
        absolute, root=root, label="V6 checkpoint artifact"
    )
    reference: Dict[str, Any] = {
        "path": os.path.relpath(absolute, root),
        "file_sha256": hashlib.sha256(raw).hexdigest(),
    }
    if canonical_json:
        reference["canonical_sha256"] = canonical_sha256(
            strict_json_loads(raw.decode("utf-8"))
        )
    return reference


def _source_code_references(
    repository_root: str, relative_paths: tuple[str, ...]
) -> Dict[str, Dict[str, Any]]:
    """Hash every executable source file that can affect a frozen stage."""
    return {
        relative_path: v6_artifact_reference(
            os.path.join(repository_root, relative_path),
            repository_root,
            canonical_json=False,
        )
        for relative_path in relative_paths
    }


def _audit_source_code_references(
    references: Any,
    repository_root: str,
    relative_paths: tuple[str, ...],
) -> Dict[str, bool]:
    expected = set(relative_paths)
    supplied = references if isinstance(references, Mapping) else {}
    checks: Dict[str, bool] = {
        "exact_file_set": set(supplied) == expected,
    }
    for relative_path in relative_paths:
        reference = supplied.get(relative_path, {})
        path, inside = _checkpoint_reference_path(reference, repository_root)
        raw: Optional[bytes] = None
        if inside:
            try:
                raw = read_regular_bytes(
                    path,
                    root=repository_root,
                    label="V6 executable source",
                )
            except (OSError, ValueError):
                raw = None
        exists = raw is not None
        checks["%s_path" % relative_path] = (
            inside and reference.get("path") == relative_path
        )
        checks["%s_hash" % relative_path] = (
            exists
            and isinstance(reference.get("file_sha256"), str)
            and hashlib.sha256(raw).hexdigest() == reference.get("file_sha256")
            and set(reference) == {"path", "file_sha256"}
        )
    return checks


def _checkpoint_reference_path(
    reference: Mapping[str, Any], repository_root: str
) -> tuple[str, bool]:
    raw_path = reference.get("path")
    if not isinstance(raw_path, str) or not raw_path.strip():
        return "", False
    if os.path.isabs(raw_path):
        return "", False
    normalized = os.path.normpath(raw_path)
    if normalized in {"", os.curdir} or normalized.startswith(os.pardir + os.sep):
        return "", False
    path = os.path.abspath(os.path.join(repository_root, normalized))
    try:
        inside = os.path.commonpath(
            [path, os.path.abspath(repository_root)]
        ) == os.path.abspath(repository_root)
    except ValueError:
        inside = False
    return path, inside


def _load_checkpoint_json_reference(
    reference: Mapping[str, Any], repository_root: str
) -> tuple[Dict[str, Any], Dict[str, bool], str]:
    path, inside = _checkpoint_reference_path(reference, repository_root)
    exists = False
    payload: Dict[str, Any] = {}
    parsed = False
    raw = b""
    if inside:
        try:
            raw = read_regular_bytes(
                path,
                root=repository_root,
                label="V6 checkpoint JSON reference",
            )
            exists = True
            loaded = strict_json_loads(raw.decode("utf-8"))
            if isinstance(loaded, dict):
                payload = loaded
                parsed = True
        except (OSError, UnicodeError, ValueError, TypeError):
            pass
    checks = {
        "path_inside_root": inside,
        "exists": exists,
        "json_object": parsed,
        "file_sha256": exists
        and isinstance(reference.get("file_sha256"), str)
        and hashlib.sha256(raw).hexdigest() == reference.get("file_sha256"),
        "canonical_sha256": parsed
        and isinstance(reference.get("canonical_sha256"), str)
        and canonical_sha256(payload) == reference.get("canonical_sha256"),
    }
    return payload, checks, path


def _load_checkpoint_log_reference(
    reference: Mapping[str, Any], repository_root: str
) -> tuple[List[Dict[str, Any]], Dict[str, bool], str]:
    path, inside = _checkpoint_reference_path(reference, repository_root)
    exists = False
    records: List[Dict[str, Any]] = []
    parsed = False
    raw = b""
    if inside:
        try:
            raw = read_regular_bytes(
                path,
                root=repository_root,
                label="V6 checkpoint JSONL reference",
            )
            exists = True
            loaded = [
                strict_json_loads(line)
                for line in raw.decode("utf-8").splitlines()
                if line.strip()
            ]
            if all(isinstance(row, dict) for row in loaded):
                records = loaded
                parsed = True
        except (OSError, UnicodeError, ValueError, TypeError, json.JSONDecodeError):
            pass
    checks = {
        "path_inside_root": inside,
        "exists": exists,
        "jsonl_objects": parsed,
        "file_sha256": exists
        and isinstance(reference.get("file_sha256"), str)
        and hashlib.sha256(raw).hexdigest() == reference.get("file_sha256"),
    }
    return records, checks, path


def _prefix_checks(
    checks: Dict[str, bool], prefix: str, values: Mapping[str, bool]
) -> None:
    checks.update({"%s_%s" % (prefix, name): bool(value) for name, value in values.items()})


def v6_official_run_ids(protocol: Mapping[str, Any]) -> Dict[str, str]:
    """Read the three single-use run IDs and reject an incomplete contract."""
    values = {
        "pool_screening": protocol.get("pool_screening_schedule", {}).get(
            "official_run_id"
        ),
        "selected_bank_validation": protocol.get(
            "selected_bank_validation_schedule", {}
        ).get("official_run_id"),
        "confirmatory": protocol.get("confirmatory_design", {}).get(
            "official_run_id"
        ),
    }
    if any(not isinstance(value, str) or not value.strip() for value in values.values()):
        raise ValueError("V6 protocol must freeze all three official run IDs")
    if len(set(values.values())) != len(values):
        raise ValueError("V6 official run IDs must be distinct")
    return {name: str(value) for name, value in values.items()}


def _safe_v6_official_run_ids(protocol: Mapping[str, Any]) -> Dict[str, str]:
    try:
        return v6_official_run_ids(protocol)
    except (TypeError, ValueError):
        return {}


def build_v6_calibration_launch_receipt(
    *,
    protocol: Mapping[str, Any],
    protocol_path: str,
    bank: V6TriadBank,
    mode: str,
    repository_root: str,
    runtime_evidence: Mapping[str, Any],
    prevalidation_reference: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    """Derive the exact atomic receipt for one paid calibration launch."""
    if mode not in (V6_POOL_MODE, V6_VALIDATION_MODE):
        raise ValueError("unknown V6 calibration mode %r" % mode)
    schedule_key = (
        "pool_screening_schedule"
        if mode == V6_POOL_MODE
        else "selected_bank_validation_schedule"
    )
    schedule = protocol.get(schedule_key, {})
    expected_paths = V6_CANONICAL_RUN_PATHS[mode]
    if schedule.get("canonical_out_dir") != expected_paths["out_dir"] or schedule.get(
        "launch_receipt_path"
    ) != expected_paths["receipt"]:
        raise ValueError("V6 calibration canonical path contract drifted")
    model = protocol.get("primary_model", {})
    root = os.path.realpath(repository_root)
    absolute_protocol = os.path.realpath(protocol_path)
    if not _inside_root(absolute_protocol, root):
        raise ValueError("V6 calibration protocol must remain inside repository root")
    receipt = {
        "receipt_version": "v6-single-launch-receipt-1.0",
        "status": "OFFICIAL_LAUNCH_CLAIMED",
        "mode": mode,
        "official_run_id": schedule.get("official_run_id"),
        "canonical_out_dir": schedule.get("canonical_out_dir"),
        "protocol_path": os.path.relpath(absolute_protocol, root),
        "protocol_file_sha256": file_sha256(absolute_protocol),
        "protocol_canonical_sha256": canonical_sha256(protocol),
        "bank_sha256": bank.sha256(),
        "bank_content_sha256": bank_content_sha256(bank.payload),
        "model": model.get("id"),
        "revision": model.get("revision"),
        "seed": schedule.get("seed"),
        "prevalidation_checkpoint": (
            json.loads(json.dumps(prevalidation_reference))
            if prevalidation_reference is not None
            else None
        ),
    }
    receipt["focal_runtime"] = build_v6_focal_runtime_checkpoint(
        protocol, runtime_evidence
    )
    if any(
        not isinstance(receipt.get(key), str) or not receipt.get(key)
        for key in (
            "official_run_id",
            "canonical_out_dir",
            "protocol_path",
            "model",
            "revision",
        )
    ):
        raise ValueError("V6 calibration launch receipt contract is incomplete")
    return receipt


def build_v6_confirmatory_schedule_metadata(
    protocol: Mapping[str, Any],
    bank: V6TriadBank,
    selected_episode_seeds: Optional[int] = None,
) -> Dict[str, Any]:
    """Hash every allowed full confirmatory scenario/message schedule.

    Power chooses one value from the predeclared episode-seed grid.  Freezing a
    hash for every allowed value keeps that later choice from changing any
    scenario, triad, or slot assignment while avoiding validation-dependent
    schedule generation.
    """
    design = protocol.get("confirmatory_design", {})
    power_design = protocol.get("power_design", {})
    power_contract = power_design.get("contract", {})
    official_run_ids = v6_official_run_ids(protocol)
    scenario_set = design.get("scenario_set")
    if scenario_set != "confirmatory":
        raise ValueError("V6 confirmatory design must use the sealed confirmatory set")
    try:
        master_seed = int(design["master_seed"])
        n_rounds = int(design["n_rounds"])
        heldout_start_round = int(design["heldout_start_round"])
        swap_round = int(design["swap_round"])
        conditions = [str(value) for value in design["conditions"]]
        randomization_seed = int(design["randomization_seed"])
        target = design["target"]
        canonical_out_dir = str(design["canonical_out_dir"])
        launch_receipt_path = str(design["launch_receipt_path"])
        paid_preflight_report_path = str(design["paid_preflight_report_path"])
        paid_preflight_receipt_path = str(design["paid_preflight_receipt_path"])
        episode_seed_grid = sorted(
            {int(value) for value in power_contract["power"]["n_grid"]}
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("V6 confirmatory schedule coordinates are incomplete") from exc
    if n_rounds <= 0 or heldout_start_round < 2:
        raise ValueError("V6 confirmatory round coordinates are invalid")
    if randomization_seed != CONTROLLED_V6_RANDOMIZATION_SEED:
        raise ValueError("V6 confirmatory randomization seed drifted")
    if not episode_seed_grid or episode_seed_grid[0] <= 0:
        raise ValueError("V6 power design has no positive episode-seed grid")
    if (
        canonical_sha256(power_contract) != V6_POWER_CONTRACT_SHA256
        or power_design.get("contract_sha256") != V6_POWER_CONTRACT_SHA256
        or max(episode_seed_grid) != 30
    ):
        raise ValueError("V6 prospective power contract drifted")
    for label, path in (
        ("canonical output directory", canonical_out_dir),
        ("launch receipt", launch_receipt_path),
        ("paid preflight report", paid_preflight_report_path),
        ("paid preflight receipt", paid_preflight_receipt_path),
    ):
        if os.path.isabs(path) or os.path.normpath(path).startswith(os.pardir):
            raise ValueError("V6 %s must be repository-relative" % label)
    expected_confirmatory_paths = V6_CANONICAL_RUN_PATHS["confirmatory"]
    if (
        canonical_out_dir != expected_confirmatory_paths["out_dir"]
        or launch_receipt_path != expected_confirmatory_paths["receipt"]
        or paid_preflight_report_path
        != expected_confirmatory_paths["preflight"]
        or paid_preflight_receipt_path
        != expected_confirmatory_paths["preflight_receipt"]
    ):
        raise ValueError("V6 confirmatory canonical path contract drifted")

    scenario_payload = [
        scenario.as_dict() for scenario in V6_SCENARIO_SETS[scenario_set]
    ]
    schedule_hashes: Dict[str, str] = {}
    allocation_hashes: Dict[str, str] = {}
    episode_counts: Dict[str, int] = {}
    for episode_seed_count in episode_seed_grid:
        cfg = ControlledExperimentConfig(
            experiment_id="controlled_v6_checkpoint",
            n_rounds=n_rounds,
            swap_round=swap_round,
            heldout_start_round=heldout_start_round,
            n_episode_seeds=episode_seed_count,
            seed=master_seed,
            randomization_seed=randomization_seed,
            conditions=conditions,
            target_params=ControlledTargetParams(
                p_match=float(target["p_match"]),
                p_mismatch=float(target["p_mismatch"]),
                p_random=float(target["p_random"]),
            ),
            model=ModelConfig(),
        )
        specs = build_controlled_episode_specs(cfg)
        if len(specs) != V6_CONFIRMATORY_EPISODES_PER_SEED * episode_seed_count:
            raise ValueError("V6 confirmatory condition grid no longer has 24 episodes per seed")
        rows: List[Dict[str, Any]] = []
        for spec in specs:
            scenarios = v6_scenario_sequence(
                scenario_set, spec.episode_index, n_rounds, master_seed
            )
            for round_index, scenario in enumerate(scenarios, start=1):
                candidates = bank.candidate_set(
                    scenario,
                    spec.episode_index,
                    round_index,
                    heldout_start_round,
                    master_seed,
                )
                rows.append(
                    {
                        "episode_id": spec.episode_id,
                        "condition": spec.condition.name,
                        "episode_index": spec.episode_index,
                        "initial_target_type": spec.initial_target_type,
                        "final_target_type": spec.final_target_type,
                        "pair_family": spec.pair_family,
                        "pair_id": spec.pair_id,
                        "pair_slot": spec.pair_slot,
                        "allocation_bit": spec.allocation_bit,
                        "assigned_regime": spec.assigned_regime,
                        "stable_counterfactual": spec.stable_counterfactual,
                        "nominal_transition": spec.nominal_transition,
                        "round": round_index,
                        "scenario_id": scenario.id,
                        "candidate_ids_by_slot": [
                            candidate.candidate_id
                            for candidate in sorted(
                                candidates, key=lambda item: item.slot
                            )
                        ],
                    }
                )
        schedule_hashes[str(episode_seed_count)] = canonical_sha256(rows)
        allocation_hashes[str(episode_seed_count)] = v6_allocation_schedule(
            episode_seed_count, seed=randomization_seed
        )["schedule_sha256"]
        episode_counts[str(episode_seed_count)] = len(specs)

    metadata: Dict[str, Any] = {
        "scenario_set": scenario_set,
        "official_run_id": official_run_ids["confirmatory"],
        "scenario_set_canonical_sha256": canonical_sha256(scenario_payload),
        "n_scenarios": len(scenario_payload),
        "master_seed": master_seed,
        "randomization_seed": randomization_seed,
        "n_rounds": n_rounds,
        "swap_round": swap_round,
        "heldout_start_round": heldout_start_round,
        "conditions": conditions,
        "canonical_out_dir": canonical_out_dir,
        "launch_receipt_path": launch_receipt_path,
        "paid_preflight_report_path": paid_preflight_report_path,
        "paid_preflight_receipt_path": paid_preflight_receipt_path,
        "episodes_per_seed": V6_CONFIRMATORY_EPISODES_PER_SEED,
        "episode_seed_grid": episode_seed_grid,
        "n_episodes_by_episode_seed_count": episode_counts,
        # The pending -> validated transition changes status/provenance fields
        # but not candidate content.  Schedule identity must therefore bind the
        # immutable candidate content, while the two checkpoints separately
        # prove the exact pending and validated full-bank hashes.
        "bank_candidate_content_sha256": bank_content_sha256(bank.payload),
        "schedule_schema": [
            "episode_index",
            "episode_id",
            "condition",
            "initial_target_type",
            "final_target_type",
            "pair_family",
            "pair_id",
            "pair_slot",
            "allocation_bit",
            "assigned_regime",
            "stable_counterfactual",
            "nominal_transition",
            "round",
            "scenario_id",
            "candidate_ids_by_slot",
        ],
        "schedule_sha256_by_episode_seed_count": schedule_hashes,
        "randomization_schedule_sha256_by_episode_seed_count": allocation_hashes,
    }
    if selected_episode_seeds is not None:
        selected_key = str(int(selected_episode_seeds))
        if selected_key not in schedule_hashes:
            raise ValueError("V6 power selected a count outside the frozen grid")
        metadata["selected_episode_seeds"] = int(selected_episode_seeds)
        metadata["selected_schedule_sha256"] = schedule_hashes[selected_key]
        metadata["selected_randomization_schedule_sha256"] = allocation_hashes[
            selected_key
        ]
    metadata["contract_sha256"] = canonical_sha256(metadata)
    return metadata


def build_v6_analysis_contract(
    protocol: Mapping[str, Any],
    validated_bank: V6TriadBank,
    confirmatory_schedule: Mapping[str, Any],
    focal_runtime: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    """Derive the self-contained, pre-outcome confirmatory analysis contract."""
    selected_episode_seeds = int(
        confirmatory_schedule["selected_episode_seeds"]
    )
    n_episodes = V6_CONFIRMATORY_EPISODES_PER_SEED * selected_episode_seeds
    n_rounds = int(confirmatory_schedule["n_rounds"])
    behavioral_thresholds = protocol.get("behavioral_gate_thresholds")
    if behavioral_thresholds != CONTROLLED_V6_GATE_THRESHOLDS:
        raise ValueError(
            "V6 protocol behavioral thresholds differ from the executable gate"
        )
    model = protocol.get("primary_model", {})
    generation = protocol.get("generation", {})
    design = protocol.get("confirmatory_design", {})
    analysis = protocol.get("analysis")
    if not _strict_json_equal(analysis, CONTROLLED_V6_ANALYSIS_CONFIG):
        raise ValueError(
            "V6 protocol analysis settings differ from the executable contract"
        )
    contract: Dict[str, Any] = {
        "version": CONTROLLED_V6_VERSION,
        "status": V6_FINAL_CHECKPOINT_STATUS,
        "pre_confirmatory_outcome": True,
        "outcome_blind_freeze": True,
        "official_run_id": confirmatory_schedule["official_run_id"],
        "experiment": {
            "conditions": list(confirmatory_schedule["conditions"]),
            "n_episode_seeds": selected_episode_seeds,
            "n_rounds": n_rounds,
            "swap_round": int(confirmatory_schedule["swap_round"]),
            "heldout_start_round": int(
                confirmatory_schedule["heldout_start_round"]
            ),
            "master_seed": int(confirmatory_schedule["master_seed"]),
            "randomization_seed": int(
                confirmatory_schedule["randomization_seed"]
            ),
            "randomization_schedule_sha256": confirmatory_schedule[
                "selected_randomization_schedule_sha256"
            ],
            "record_counts": {"total": n_episodes * n_rounds},
            "episode_counts": {"total": n_episodes},
            "scenario_set": confirmatory_schedule["scenario_set"],
            "scenario_ids": [
                scenario.as_dict()["id"]
                for scenario in V6_SCENARIO_SETS["confirmatory"]
            ],
            "scenario_set_canonical_sha256": confirmatory_schedule[
                "scenario_set_canonical_sha256"
            ],
            "full_schedule_sha256": confirmatory_schedule[
                "selected_schedule_sha256"
            ],
            "canonical_out_dir": confirmatory_schedule["canonical_out_dir"],
            "launch_receipt_path": confirmatory_schedule[
                "launch_receipt_path"
            ],
            "paid_preflight_report_path": confirmatory_schedule[
                "paid_preflight_report_path"
            ],
            "paid_preflight_receipt_path": confirmatory_schedule[
                "paid_preflight_receipt_path"
            ],
            "single_official_run": design.get("single_official_run"),
        },
        "primary_model": {
            "id": model.get("id"),
            "revision": model.get("revision"),
        },
        "generation": json.loads(json.dumps(generation)),
        "target": json.loads(json.dumps(design.get("target", {}))),
        "message_bank": {
            "sha256": validated_bank.sha256(),
            "content_sha256": bank_content_sha256(validated_bank.payload),
        },
        "thresholds": json.loads(json.dumps(behavioral_thresholds)),
        "analysis": json.loads(json.dumps(analysis)),
    }
    if focal_runtime is not None:
        runtime_audit = audit_v6_focal_runtime_checkpoint(
            focal_runtime, protocol
        )
        if runtime_audit.get("pass") is not True:
            raise ValueError("V6 analysis contract received an invalid focal runtime")
        contract["focal_runtime"] = json.loads(
            json.dumps(focal_runtime, allow_nan=False)
        )
    contract["contract_sha256"] = canonical_sha256(contract)
    return contract


def _load_reference(
    reference: Mapping[str, Any], repository_root: str
) -> tuple[Dict[str, Any], bool, bool, bool]:
    path = _resolve(repository_root, str(reference.get("path", "")))
    if not os.path.isfile(path):
        return {}, False, False, False
    with open(path, "r", encoding="utf-8") as handle:
        payload = strict_json_load(handle)
    return (
        payload,
        True,
        file_sha256(path) == reference.get("file_sha256"),
        canonical_sha256(payload) == reference.get("canonical_sha256"),
    )


def audit_v6_calibration_plan(
    spec: Mapping[str, Any],
    bank: V6TriadBank,
    provider: Mapping[str, Any],
    mode: str,
    seed: int,
    n_episode_blocks: Optional[int],
    repository_root: str,
    prevalidation_checkpoint: Optional[Mapping[str, Any]] = None,
    run_id: Optional[str] = None,
    require_runtime_evidence: bool = True,
) -> Dict[str, Any]:
    if mode not in {V6_POOL_MODE, V6_VALIDATION_MODE}:
        raise ValueError("unknown V6 calibration mode")
    pool_ref = spec.get("candidate_pool", {})
    semantic_ref = spec.get("semantic_validation", {})
    quality_ref = spec.get("quality_validation", {})
    model = spec.get("primary_model", {})
    generation = spec.get("generation", {})
    confirmatory_design = spec.get("confirmatory_design", {})
    schedule_key = (
        "pool_screening_schedule"
        if mode == V6_POOL_MODE
        else "selected_bank_validation_schedule"
    )
    schedule = spec.get(schedule_key, {})
    official_run_ids = _safe_v6_official_run_ids(spec)
    pool_path = _resolve(repository_root, str(pool_ref.get("path", "")))
    semantic, semantic_exists, semantic_file_ok, semantic_canonical_ok = _load_reference(
        semantic_ref, repository_root
    )
    quality, quality_exists, quality_file_ok, quality_canonical_ok = _load_reference(
        quality_ref, repository_root
    )
    pool_exists = os.path.isfile(pool_path)
    source_pool: Optional[V6TriadBank] = None
    if pool_exists:
        try:
            source_pool = V6TriadBank.load(pool_path)
        except (OSError, TypeError, ValueError):
            pass
    semantic_raw_replay: Dict[str, Any] = {}
    quality_raw_replay: Dict[str, Any] = {}
    if source_pool is not None and semantic and quality:
        try:
            semantic_raw_replay = audit_v6_semantic_validation_summary(
                semantic, source_pool, repository_root
            )
        except (KeyError, OSError, TypeError, ValueError, RuntimeError):
            pass
        try:
            quality_raw_replay = audit_v6_quality_validation_summary(
                quality, source_pool, repository_root
            )
        except (KeyError, OSError, TypeError, ValueError, RuntimeError):
            pass
    source_pool_hash = pool_ref.get("sha256")
    expected_records = int(schedule.get("n_records", -1))
    calculated_records = int(schedule.get("n_triads", -1)) * int(
        schedule.get("n_scenarios", -1)
    ) * int(schedule.get("n_slot_permutations", -1))
    expected_scenario_set = "calibration" if mode == V6_POOL_MODE else "validation"
    scenario_refs = spec.get("scenario_sets", {})
    scenario_hashes = {
        name: canonical_sha256([scenario.as_dict() for scenario in scenarios])
        for name, scenarios in V6_SCENARIO_SETS.items()
    }
    expected_triads = 20 if mode == V6_POOL_MODE else 10
    expected_records_for_mode = 1680 if mode == V6_POOL_MODE else 840
    planned_semantic_judges = list(semantic_ref.get("judges", []))
    planned_quality_judges = list(quality_ref.get("judges", []))
    observed_semantic_judges = [
        semantic.get("primary_judge", {}).get("model"),
        semantic.get("sensitivity_judge", {}).get("model"),
    ]
    observed_quality_judges = [
        quality.get("primary_judge", {}).get("model"),
        quality.get("sensitivity_judge", {}).get("model"),
    ]
    planned_semantic_contract = semantic_ref.get("judge_contract", {})
    planned_quality_contract = quality_ref.get("judge_contract", {})
    observed_semantic_contract = semantic.get("judge_contract", {})
    observed_quality_contract = quality.get("judge_contract", {})

    def judge_contract_matches(planned: Any, observed: Any, kind: str) -> bool:
        if not isinstance(planned, Mapping) or not isinstance(observed, Mapping):
            return False
        fields = (
            "models",
            "seeds",
            "batch_size",
            "prompt_version",
            "prompt_sha256",
            "rubric_sha256",
            "contract_sha256",
        )
        return (
            all(observed.get(field) == planned.get(field) for field in fields)
            and observed.get("enforced") is True
            and observed.get("kind") == kind
        )
    prevalidation = (
        prevalidation_checkpoint
        if isinstance(prevalidation_checkpoint, Mapping)
        else {}
    )
    prevalidation_audit: Dict[str, Any] = {}
    if mode == V6_VALIDATION_MODE and prevalidation:
        prevalidation_audit = audit_v6_prevalidation_checkpoint(
            prevalidation, repository_root
        )
    provider_runtime = _runtime_mapping(
        provider.get("focal_runtime_evidence")
    )
    prevalidation_runtime = _runtime_mapping(prevalidation.get("focal_runtime"))
    expected_runtime = _runtime_mapping(prevalidation_runtime.get("evidence"))
    runtime_audit = audit_v6_focal_runtime(
        spec.get("focal_runtime"),
        provider_runtime,
        expected_evidence=(
            expected_runtime
            if mode == V6_VALIDATION_MODE and expected_runtime
            else None
        ),
        device_argument=provider.get("device"),
    )
    checks = {
        "protocol_version": spec.get("protocol_version")
        == V6_CALIBRATION_PROTOCOL_VERSION,
        "task_version": spec.get("task_version") == CONTROLLED_V6_VERSION,
        "pre_target_outcomes": spec.get("pre_target_outcomes") is True,
        "final_version_no_v7_rescue": spec.get("final_version_no_v7_rescue") is True,
        "machine_only_validation_declared": spec.get("machine_only_validation")
        is True
        and spec.get("human_validation") is False,
        "protocol_status": spec.get("status")
        == "SEMANTIC_AND_QUALITY_GATES_PASSED_READY_FOR_PAID_POOL_SCREENING",
        "pool_file_exists": pool_exists,
        "pool_file_hash": pool_exists
        and file_sha256(pool_path) == pool_ref.get("file_sha256"),
        "pool_canonical_hash": source_pool is not None
        and source_pool.sha256() == source_pool_hash,
        "semantic_file_exists": semantic_exists,
        "semantic_canonical_paths": semantic_ref.get("path")
        == V6_CANONICAL_MEASUREMENT_PATHS["semantic"]["summary"]
        and semantic_ref.get("canonical_out_dir")
        == V6_CANONICAL_MEASUREMENT_PATHS["semantic"]["out_dir"]
        and semantic_ref.get("canonical_cache_dir")
        == V6_CANONICAL_MEASUREMENT_PATHS["semantic"]["cache_dir"],
        "semantic_file_hash": semantic_file_ok,
        "semantic_canonical_hash": semantic_canonical_ok,
        "semantic_gate_pass": semantic.get("pass") is True
        and semantic.get("pool_sha256") == source_pool_hash
        and semantic_raw_replay.get("ok") is True
        and semantic_raw_replay.get("pass") is True,
        "semantic_raw_artifacts_replayed": semantic_raw_replay.get("ok")
        is True,
        "semantic_judges_match_plan": planned_semantic_judges
        == observed_semantic_judges
        == ["gpt-5.6-sol", "gpt-5.6-luna"],
        "semantic_judge_contract": judge_contract_matches(
            planned_semantic_contract, observed_semantic_contract, "semantic"
        ),
        "quality_file_exists": quality_exists,
        "quality_canonical_paths": quality_ref.get("path")
        == V6_CANONICAL_MEASUREMENT_PATHS["quality"]["summary"]
        and quality_ref.get("canonical_out_dir")
        == V6_CANONICAL_MEASUREMENT_PATHS["quality"]["out_dir"]
        and quality_ref.get("canonical_cache_dir")
        == V6_CANONICAL_MEASUREMENT_PATHS["quality"]["cache_dir"],
        "quality_file_hash": quality_file_ok,
        "quality_canonical_hash": quality_canonical_ok,
        "quality_gate_pass": quality.get("pass") is True
        and quality.get("pool_sha256") == source_pool_hash
        and quality_raw_replay.get("ok") is True
        and quality_raw_replay.get("pass") is True,
        "quality_raw_artifacts_replayed": quality_raw_replay.get("ok") is True,
        "quality_judges_match_plan": planned_quality_judges
        == observed_quality_judges
        == ["gpt-5.6-sol", "gpt-5.6-luna"],
        "quality_judge_contract": judge_contract_matches(
            planned_quality_contract, observed_quality_contract, "quality"
        ),
        "semantic_thresholds": spec.get("semantic_thresholds")
        == CONTROLLED_V6_SEMANTIC_THRESHOLDS,
        "quality_thresholds": spec.get("quality_thresholds")
        == CONTROLLED_V6_QUALITY_THRESHOLDS,
        "calibration_thresholds": spec.get("calibration_thresholds")
        == CONTROLLED_V6_CALIBRATION_THRESHOLDS,
        "power_canonical_path": spec.get("power_design", {}).get(
            "canonical_out_dir"
        )
        == V6_CANONICAL_MEASUREMENT_PATHS["power"]["out_dir"],
        "behavioral_thresholds": spec.get("behavioral_gate_thresholds")
        == CONTROLLED_V6_GATE_THRESHOLDS,
        "analysis_contract": _strict_json_equal(
            spec.get("analysis"), CONTROLLED_V6_ANALYSIS_CONFIG
        ),
        "confirmatory_paid_preflight_paths": isinstance(
            confirmatory_design, Mapping
        )
        and confirmatory_design.get("paid_preflight_report_path")
        == V6_CANONICAL_RUN_PATHS["confirmatory"]["preflight"]
        and confirmatory_design.get("paid_preflight_receipt_path")
        == V6_CANONICAL_RUN_PATHS["confirmatory"]["preflight_receipt"],
        "scenario_set_name": schedule.get("scenario_set") == expected_scenario_set,
        "scenario_count": schedule.get("n_scenarios")
        == len(V6_SCENARIO_SETS[expected_scenario_set])
        == 14,
        "scenario_hashes": all(
            scenario_refs.get(name, {}).get("canonical_sha256") == digest
            and scenario_refs.get(name, {}).get("n_scenarios")
            == len(V6_SCENARIO_SETS[name])
            for name, digest in scenario_hashes.items()
        ),
        "scenario_sets_disjoint": len(
            {
                scenario.id
                for scenarios in V6_SCENARIO_SETS.values()
                for scenario in scenarios
            }
        )
        == sum(len(scenarios) for scenarios in V6_SCENARIO_SETS.values()),
        "cross_validation_folds": spec.get("cross_validation_folds")
        == [list(pair) for pair in V6_CALIBRATION_FOLDS],
        "focal_runtime_contract": _strict_json_equal(
            spec.get("focal_runtime"), V6_FROZEN_FOCAL_RUNTIME_CONTRACT
        ),
        "focal_runtime_evidence": not require_runtime_evidence
        or runtime_audit.get("pass") is True,
        "focal_runtime_device_auto": not require_runtime_evidence
        or provider.get("device") == "auto",
        "selected_mode_runtime_anchor": not require_runtime_evidence
        or mode != V6_VALIDATION_MODE
        or bool(expected_runtime),
        "model_id": provider.get("model") == model.get("id"),
        "model_revision": provider.get("revision") == model.get("revision"),
        "provider_kind": provider.get("provider") == "huggingface",
        "temperature": provider.get("temperature") == generation.get("temperature"),
        "top_p": provider.get("top_p") == generation.get("top_p"),
        "top_k": provider.get("top_k") == generation.get("top_k"),
        "max_tokens": provider.get("max_tokens") == generation.get("max_tokens"),
        "dtype": provider.get("dtype") == generation.get("dtype"),
        "thinking_disabled": provider.get("enable_thinking")
        is generation.get("enable_thinking")
        is False,
        "capture_disabled": provider.get("capture")
        is generation.get("activation_capture")
        is False,
        "constrained_choices": provider.get("constrained_choices")
        == generation.get("constrained_choices")
        == ["1", "2", "3"],
        "invalid_output_aborts": generation.get("invalid_output_policy")
        == "abort; no fallback",
        "provider_seed": provider.get("torch_seed_base") == seed,
        "schedule_seed": seed == schedule.get("seed"),
        "official_run_ids_frozen": bool(official_run_ids),
        "official_run_id": bool(official_run_ids)
        and run_id == schedule.get("official_run_id")
        == official_run_ids.get(mode),
        "canonical_out_dir": schedule.get("canonical_out_dir")
        == V6_CANONICAL_RUN_PATHS[mode]["out_dir"],
        "canonical_launch_receipt": schedule.get("launch_receipt_path")
        == V6_CANONICAL_RUN_PATHS[mode]["receipt"],
        "record_count": calculated_records
        == expected_records
        == expected_records_for_mode,
        "triad_count": schedule.get("n_triads") == expected_triads,
        "all_six_slot_permutations": schedule.get("n_slot_permutations") == 6,
        "round_contract": schedule.get("n_rounds") == 24
        and schedule.get("heldout_start_round") == 19,
        "history_absent": schedule.get("history_present") is False,
        "target_absent": schedule.get("target_simulator_present") is False,
        "pool_mode_exact_source_bank": mode != V6_POOL_MODE
        or bank.sha256() == source_pool_hash,
        "selected_mode_pending_bank": mode != V6_VALIDATION_MODE
        or bank.payload.get("status")
        == "selected_bank_pending_no_history_validation",
        "selected_mode_source_pool": mode != V6_VALIDATION_MODE
        or bank.payload.get("source_pool_sha256") == source_pool_hash,
        "selected_mode_semantic_hash": mode != V6_VALIDATION_MODE
        or bank.payload.get("semantic_validation_sha256")
        == semantic_ref.get("canonical_sha256"),
        "selected_mode_quality_hash": mode != V6_VALIDATION_MODE
        or bank.payload.get("quality_validation_sha256")
        == quality_ref.get("canonical_sha256"),
        "selected_mode_prevalidation_checkpoint": mode != V6_VALIDATION_MODE
        or prevalidation_audit.get("pass") is True,
        "selected_mode_checkpoint_pending_hash": mode != V6_VALIDATION_MODE
        or prevalidation_audit.get("pending_bank_sha256") == bank.sha256(),
        "selected_mode_checkpoint_pending_content": mode != V6_VALIDATION_MODE
        or prevalidation_audit.get("pending_bank_content_sha256")
        == bank_content_sha256(bank.payload),
        "selected_mode_checkpoint_protocol": mode != V6_VALIDATION_MODE
        or prevalidation.get("calibration_protocol", {}).get(
            "canonical_sha256"
        )
        == canonical_sha256(spec),
        "episode_blocks_not_used_for_complete_permutation_schedules": schedule.get(
            "n_episode_blocks"
        )
        is None,
        "episode_blocks_argument_absent": n_episode_blocks is None,
        "fresh_validation_seed": spec.get("pool_screening_schedule", {}).get("seed")
        != spec.get("selected_bank_validation_schedule", {}).get("seed"),
    }
    return {
        "pass": all(checks.values()),
        "mode": mode,
        "checks": checks,
        "protocol_version": V6_CALIBRATION_PROTOCOL_VERSION,
        "bank_sha256": bank.sha256(),
        "semantic_validation_path": _resolve(
            repository_root, str(semantic_ref.get("path", ""))
        ),
        "semantic_raw_replay_sha256": semantic_raw_replay.get(
            "recomputed_evaluation_sha256"
        ),
        "quality_validation_path": _resolve(
            repository_root, str(quality_ref.get("path", ""))
        ),
        "quality_raw_replay_sha256": quality_raw_replay.get(
            "recomputed_evaluation_sha256"
        ),
        "prevalidation_checkpoint_sha256": (
            canonical_sha256(prevalidation)
            if prevalidation
            else None
        ),
        "focal_runtime_audit": runtime_audit,
    }


def build_v6_prevalidation_checkpoint(
    *,
    calibration_protocol_path: str,
    source_pool_path: str,
    semantic_validation_path: str,
    quality_validation_path: str,
    prevalidation_power_path: str,
    pool_calibration_log_path: str,
    pool_calibration_manifest_path: str,
    selection_report_path: str,
    pending_bank_path: str,
    repository_root: str,
) -> Dict[str, Any]:
    """Build and self-audit the checkpoint required before validation."""
    pool = V6TriadBank.load(source_pool_path)
    pending = V6TriadBank.load(pending_bank_path)
    with open(calibration_protocol_path, "r", encoding="utf-8") as handle:
        protocol = strict_json_load(handle)
    with open(prevalidation_power_path, "r", encoding="utf-8") as handle:
        power = strict_json_load(handle)
    with open(semantic_validation_path, "r", encoding="utf-8") as handle:
        semantic_summary = strict_json_load(handle)
    with open(quality_validation_path, "r", encoding="utf-8") as handle:
        quality_summary = strict_json_load(handle)
    with open(pool_calibration_manifest_path, "r", encoding="utf-8") as handle:
        pool_manifest = strict_json_load(handle)
    pool_receipt_reference = pool_manifest.get("frozen_protocol", {}).get(
        "single_launch_receipt", {}
    )
    pool_receipt_path, pool_receipt_inside = _checkpoint_reference_path(
        pool_receipt_reference, repository_root
    )
    if not pool_receipt_inside or not os.path.isfile(pool_receipt_path):
        raise ValueError("V6 pool manifest has no repository-local launch receipt")
    with open(pool_receipt_path, "r", encoding="utf-8") as handle:
        pool_receipt = strict_json_load(handle)
    if not isinstance(pool_receipt, Mapping):
        raise ValueError("V6 pool launch receipt must be a JSON object")
    pool_runtime_evidence = _runtime_mapping(
        pool_manifest.get("provider", {}).get("focal_runtime_evidence")
    )
    pool_receipt_runtime = _runtime_mapping(pool_receipt.get("focal_runtime"))
    if not pool_runtime_evidence or not _strict_json_equal(
        pool_receipt_runtime.get("evidence"), pool_runtime_evidence
    ):
        raise ValueError(
            "V6 pool provider and launch receipt lack identical runtime evidence"
        )
    power_replay = audit_v6_power_payload(power, require_official=True)
    if power_replay.get("scientific_power_pass") is not True:
        raise ValueError("V6 prevalidation power did not authorize validation")
    selected_episode_seeds = power_replay.get("selected_episode_seeds")
    checkpoint: Dict[str, Any] = {
        "checkpoint_version": V6_PREVALIDATION_CHECKPOINT_VERSION,
        "status": V6_PREVALIDATION_CHECKPOINT_STATUS,
        "independent_validation_outputs_included": False,
        "official_run_ids": v6_official_run_ids(protocol),
        "calibration_protocol": v6_artifact_reference(
            calibration_protocol_path, repository_root
        ),
        "source_pool": {
            **v6_artifact_reference(source_pool_path, repository_root),
            "bank_sha256": pool.sha256(),
            "bank_content_sha256": bank_content_sha256(pool.payload),
        },
        "semantic_validation": v6_artifact_reference(
            semantic_validation_path, repository_root
        ),
        "semantic_raw_judge_runs": json.loads(
            json.dumps(semantic_summary.get("raw_judge_run_manifests", {}))
        ),
        "quality_validation": v6_artifact_reference(
            quality_validation_path, repository_root
        ),
        "quality_raw_judge_runs": json.loads(
            json.dumps(quality_summary.get("raw_judge_run_manifests", {}))
        ),
        "prevalidation_power": v6_artifact_reference(
            prevalidation_power_path, repository_root
        ),
        "pool_calibration_log": v6_artifact_reference(
            pool_calibration_log_path, repository_root, canonical_json=False
        ),
        "pool_calibration_manifest": v6_artifact_reference(
            pool_calibration_manifest_path, repository_root
        ),
        "pool_launch_receipt": v6_artifact_reference(
            pool_receipt_path, repository_root
        ),
        "focal_runtime": build_v6_focal_runtime_checkpoint(
            protocol, pool_runtime_evidence
        ),
        "selection_report": v6_artifact_reference(
            selection_report_path, repository_root
        ),
        "pending_bank": {
            **v6_artifact_reference(pending_bank_path, repository_root),
            "bank_sha256": pending.sha256(),
            "bank_content_sha256": bank_content_sha256(pending.payload),
        },
        "source_code": _source_code_references(
            repository_root, V6_PREVALIDATION_SOURCE_PATHS
        ),
        "confirmatory_schedule": build_v6_confirmatory_schedule_metadata(
            protocol, pending, selected_episode_seeds=selected_episode_seeds
        ),
    }
    audit = audit_v6_prevalidation_checkpoint(checkpoint, repository_root)
    if not audit["pass"]:
        failed = sorted(name for name, passed in audit["checks"].items() if not passed)
        raise ValueError(
            "refusing to freeze V6 pre-validation checkpoint: %s"
            % ", ".join(failed)
        )
    return checkpoint


def audit_v6_prevalidation_checkpoint(
    checkpoint: Mapping[str, Any], repository_root: str
) -> Dict[str, Any]:
    """Replay source selection and reject any edited or reselected bank."""
    checks: Dict[str, bool] = {
        "checkpoint_version": checkpoint.get("checkpoint_version")
        == V6_PREVALIDATION_CHECKPOINT_VERSION,
        "checkpoint_status": checkpoint.get("status")
        == V6_PREVALIDATION_CHECKPOINT_STATUS,
        "validation_outputs_absent": checkpoint.get(
            "independent_validation_outputs_included"
        )
        is False,
    }
    _prefix_checks(
        checks,
        "source_code",
        _audit_source_code_references(
            checkpoint.get("source_code"),
            repository_root,
            V6_PREVALIDATION_SOURCE_PATHS,
        ),
    )
    protocol, protocol_checks, _protocol_path = _load_checkpoint_json_reference(
        checkpoint.get("calibration_protocol", {}), repository_root
    )
    pool_payload, pool_checks, pool_path = _load_checkpoint_json_reference(
        checkpoint.get("source_pool", {}), repository_root
    )
    semantic, semantic_checks, _semantic_path = _load_checkpoint_json_reference(
        checkpoint.get("semantic_validation", {}), repository_root
    )
    quality, quality_checks, _quality_path = _load_checkpoint_json_reference(
        checkpoint.get("quality_validation", {}), repository_root
    )
    power, power_checks, _power_path = _load_checkpoint_json_reference(
        checkpoint.get("prevalidation_power", {}), repository_root
    )
    records, log_checks, log_path = _load_checkpoint_log_reference(
        checkpoint.get("pool_calibration_log", {}), repository_root
    )
    manifest, manifest_checks, manifest_path = _load_checkpoint_json_reference(
        checkpoint.get("pool_calibration_manifest", {}), repository_root
    )
    pool_receipt, pool_receipt_checks, _pool_receipt_path = (
        _load_checkpoint_json_reference(
            checkpoint.get("pool_launch_receipt", {}), repository_root
        )
    )
    selection, selection_checks, _selection_path = _load_checkpoint_json_reference(
        checkpoint.get("selection_report", {}), repository_root
    )
    pending_payload, pending_checks, pending_path = _load_checkpoint_json_reference(
        checkpoint.get("pending_bank", {}), repository_root
    )
    for prefix, values in (
        ("protocol", protocol_checks),
        ("source_pool", pool_checks),
        ("semantic", semantic_checks),
        ("quality", quality_checks),
        ("prevalidation_power", power_checks),
        ("pool_log", log_checks),
        ("pool_manifest", manifest_checks),
        ("pool_launch_receipt", pool_receipt_checks),
        ("selection_report", selection_checks),
        ("pending_bank", pending_checks),
    ):
        _prefix_checks(checks, prefix, values)

    runtime_checkpoint_audit = audit_v6_focal_runtime_checkpoint(
        checkpoint.get("focal_runtime"), protocol
    )
    _prefix_checks(checks, "focal_runtime", runtime_checkpoint_audit["checks"])
    checkpoint_runtime = _runtime_mapping(checkpoint.get("focal_runtime"))
    checkpoint_runtime_evidence = _runtime_mapping(
        checkpoint_runtime.get("evidence")
    )
    manifest_provider = _runtime_mapping(manifest.get("provider"))
    manifest_runtime_audit = _runtime_mapping(
        manifest.get("frozen_protocol", {}).get("focal_runtime")
    )
    receipt_runtime = _runtime_mapping(pool_receipt.get("focal_runtime"))

    pool: Optional[V6TriadBank] = None
    pending: Optional[V6TriadBank] = None
    try:
        if pool_payload:
            pool = V6TriadBank.load(pool_path)
    except (OSError, ValueError, TypeError):
        pass
    try:
        if pending_payload:
            pending = V6TriadBank.load(pending_path)
    except (OSError, ValueError, TypeError):
        pass

    semantic_raw_replay: Dict[str, Any] = {}
    quality_raw_replay: Dict[str, Any] = {}
    power_replay: Dict[str, Any] = {}
    if pool is not None:
        try:
            semantic_raw_replay = audit_v6_semantic_validation_summary(
                semantic, pool, repository_root
            )
        except (KeyError, OSError, TypeError, ValueError, RuntimeError):
            pass
        try:
            quality_raw_replay = audit_v6_quality_validation_summary(
                quality, pool, repository_root
            )
        except (KeyError, OSError, TypeError, ValueError, RuntimeError):
            pass
    try:
        power_replay = audit_v6_power_payload(power, require_official=True)
    except (KeyError, OSError, TypeError, ValueError, RuntimeError):
        pass

    source_ref = checkpoint.get("source_pool", {})
    pending_ref = checkpoint.get("pending_bank", {})
    checks.update(
        {
            "source_pool_structural_audit": pool is not None,
            "source_pool_provisional": pool is not None
            and pool.payload.get("status") == V6_PROVISIONAL_POOL_STATUS,
            "source_pool_bank_hash": pool is not None
            and source_ref.get("bank_sha256") == pool.sha256(),
            "source_pool_content_hash": pool is not None
            and source_ref.get("bank_content_sha256")
            == bank_content_sha256(pool.payload),
            "pending_bank_structural_audit": pending is not None,
            "pending_bank_status": pending is not None
            and pending.payload.get("status")
            == "selected_bank_pending_no_history_validation",
            "pending_bank_hash": pending is not None
            and pending_ref.get("bank_sha256") == pending.sha256(),
            "pending_bank_content_hash": pending is not None
            and pending_ref.get("bank_content_sha256")
            == bank_content_sha256(pending.payload),
        }
    )

    run_audit: Dict[str, Any] = {}
    recomputed_plan: Dict[str, Any] = {}
    if pool is not None and records and manifest and protocol:
        try:
            recomputed_plan = audit_v6_calibration_plan(
                protocol,
                pool,
                manifest.get("provider", {}),
                V6_POOL_MODE,
                int(manifest.get("schedule", {}).get("seed", -1)),
                manifest.get("schedule", {}).get("n_episode_blocks"),
                repository_root,
                run_id=str(manifest.get("run_id", "")),
                require_runtime_evidence=True,
            )
            run_audit = audit_v6_calibration_run(
                records, manifest, pool, V6_POOL_MODE
            )
        except (KeyError, TypeError, ValueError, RuntimeError):
            pass
    checks.update(
        {
            "protocol_version": protocol.get("protocol_version")
            == V6_CALIBRATION_PROTOCOL_VERSION,
            "behavioral_thresholds_frozen": protocol.get(
                "behavioral_gate_thresholds"
            )
            == CONTROLLED_V6_GATE_THRESHOLDS,
            "official_run_ids": bool(protocol)
            and bool(_safe_v6_official_run_ids(protocol))
            and checkpoint.get("official_run_ids")
            == _safe_v6_official_run_ids(protocol),
            "protocol_source_pool": pool is not None
            and protocol.get("candidate_pool", {}).get("sha256") == pool.sha256()
            and protocol.get("candidate_pool", {}).get("file_sha256")
            == source_ref.get("file_sha256"),
            "protocol_semantic_summary": bool(semantic)
            and protocol.get("semantic_validation", {}).get("canonical_sha256")
            == canonical_sha256(semantic)
            and protocol.get("semantic_validation", {}).get("file_sha256")
            == checkpoint.get("semantic_validation", {}).get("file_sha256"),
            "protocol_quality_summary": bool(quality)
            and protocol.get("quality_validation", {}).get("canonical_sha256")
            == canonical_sha256(quality)
            and protocol.get("quality_validation", {}).get("file_sha256")
            == checkpoint.get("quality_validation", {}).get("file_sha256"),
            "semantic_pass_and_pool": pool is not None
            and semantic.get("pass") is True
            and semantic.get("pool_sha256") == pool.sha256()
            and semantic_raw_replay.get("ok") is True
            and semantic_raw_replay.get("pass") is True,
            "semantic_raw_manifest_checkpoint_binding": checkpoint.get(
                "semantic_raw_judge_runs"
            )
            == semantic.get("raw_judge_run_manifests"),
            "quality_pass_and_pool": pool is not None
            and quality.get("pass") is True
            and quality.get("pool_sha256") == pool.sha256()
            and quality_raw_replay.get("ok") is True
            and quality_raw_replay.get("pass") is True,
            "quality_raw_manifest_checkpoint_binding": checkpoint.get(
                "quality_raw_judge_runs"
            )
            == quality.get("raw_judge_run_manifests"),
            "pool_manifest_completed": manifest.get("run_status") == "completed"
            and manifest.get("mode") == V6_POOL_MODE,
            "pool_manifest_log_hash": log_checks.get("file_sha256") is True
            and manifest.get("log_file_sha256")
            == checkpoint.get("pool_calibration_log", {}).get("file_sha256"),
            "pool_launch_receipt_manifest_binding": bool(pool_receipt)
            and manifest.get("frozen_protocol", {}).get(
                "single_launch_receipt"
            )
            == checkpoint.get("pool_launch_receipt"),
            "pool_manifest_runtime_binding": bool(checkpoint_runtime_evidence)
            and _strict_json_equal(
                manifest_provider.get("focal_runtime_evidence"),
                checkpoint_runtime_evidence,
            ),
            "pool_manifest_runtime_audit_binding": manifest_runtime_audit.get(
                "pass"
            )
            is True
            and _strict_json_equal(
                manifest_runtime_audit.get("evidence"),
                checkpoint_runtime_evidence,
            )
            and manifest_runtime_audit.get("evidence_sha256")
            == checkpoint_runtime.get("evidence_sha256"),
            "pool_receipt_runtime_binding": bool(checkpoint_runtime_evidence)
            and _strict_json_equal(receipt_runtime, checkpoint_runtime),
            "pool_plan_recomputed": recomputed_plan.get("pass") is True,
            "pool_plan_matches_manifest": bool(recomputed_plan)
            and manifest.get("frozen_protocol", {}).get("plan_audit")
            == recomputed_plan,
            "pool_run_recomputed": run_audit.get("pass") is True,
            "selection_support_pass": selection.get("support_pass") is True,
            "selection_embedded_run_audit": selection.get(
                "calibration_run_audit"
            )
            == run_audit,
            "selection_manifest_hash": manifest_checks.get("file_sha256") is True
            and selection.get("calibration_manifest_file_sha256")
            == checkpoint.get("pool_calibration_manifest", {}).get("file_sha256"),
            "selection_log_hash": log_checks.get("file_sha256") is True
            and selection.get("calibration_log_file_sha256")
            == checkpoint.get("pool_calibration_log", {}).get("file_sha256"),
        }
    )

    expected_pool_receipt: Dict[str, Any] = {}
    if protocol and pool is not None:
        try:
            expected_pool_receipt = build_v6_calibration_launch_receipt(
                protocol=protocol,
                protocol_path=_protocol_path,
                bank=pool,
                mode=V6_POOL_MODE,
                repository_root=repository_root,
                runtime_evidence=checkpoint_runtime_evidence,
            )
        except (KeyError, OSError, TypeError, ValueError, RuntimeError):
            pass
    checks["pool_launch_receipt_exact"] = (
        bool(expected_pool_receipt) and pool_receipt == expected_pool_receipt
    )

    power_design = protocol.get("power_design", {})
    selected_episode_seeds = power_replay.get("selected_episode_seeds")
    frozen_power_contract = power_design.get("contract", {})
    frozen_power_section = (
        frozen_power_contract.get("power", {})
        if isinstance(frozen_power_contract, Mapping)
        else {}
    )
    frozen_simulation = (
        frozen_power_contract.get("simulation", {})
        if isinstance(frozen_power_contract, Mapping)
        else {}
    )
    checks.update(
        {
            "power_contract_exact": canonical_sha256(frozen_power_contract)
            == V6_POWER_CONTRACT_SHA256
            and power_design.get("contract_sha256")
            == V6_POWER_CONTRACT_SHA256,
            "power_payload_replayed": power_replay.get("audit_pass") is True,
            "power_pass": power_replay.get("scientific_power_pass") is True
            and power_replay.get("power_selection_pass") is True
            and power_replay.get("null_type_i_pass") is True
            and power_replay.get("status")
            == "PASS_V6_PROSPECTIVE_BUNDLE_POWER",
            "power_outcome_independence": power.get("focal_model_outcomes_used")
            is False
            and power.get("confirmatory_outcomes_used") is False
            and power.get("selected_bank_validation_outputs_used") is False,
            "power_episode_grid": power.get("episode_seed_grid")
            == frozen_power_section.get("n_grid"),
            "power_ceiling": bool(frozen_power_section.get("n_grid"))
            and max(frozen_power_section.get("n_grid", [])) == 30,
            "power_simulations": type(power.get("n_sim_per_cell")) is int
            and power.get("n_sim_per_cell", 0)
            >= int(
                frozen_power_section.get(
                    "official_simulations_per_cell_minimum", -1
                )
            ),
            "power_seed": power.get("simulation_seed")
            == frozen_simulation.get("power_rng_root"),
            "power_target": frozen_power_section.get(
                "target_wilson_lower_bound"
            )
            == 0.80,
            "power_payload_contract_binding": canonical_sha256(
                power.get("contract")
            )
            == canonical_sha256(frozen_power_contract),
            "power_selected_count": type(selected_episode_seeds) is int
            and selected_episode_seeds
            in frozen_power_section.get("n_grid", [])
            and selected_episode_seeds
            <= max(frozen_power_section.get("n_grid", [-1])),
        }
    )

    regenerated_pending: Optional[Dict[str, Any]] = None
    regenerated_report: Dict[str, Any] = {}
    if pool is not None and run_audit.get("pass") is True:
        try:
            regenerated_pending, regenerated_report = select_v6_bank(
                pool, records, semantic, quality
            )
            regenerated_report["calibration_run_audit"] = run_audit
            regenerated_report["calibration_manifest_file_sha256"] = file_sha256(
                manifest_path
            )
            regenerated_report["calibration_log_file_sha256"] = file_sha256(log_path)
        except (KeyError, TypeError, ValueError, RuntimeError):
            regenerated_pending = None
            regenerated_report = {}
    checks.update(
        {
            "selection_report_exactly_regenerated": bool(regenerated_report)
            and regenerated_report == selection,
            "pending_bank_exactly_regenerated": regenerated_pending is not None
            and regenerated_pending == pending_payload,
            "pending_bank_matches_selection_hash": pending is not None
            and selection.get("selected_bank_sha256") == pending.sha256(),
            "pending_content_matches_selection_hash": pending is not None
            and selection.get("selected_bank_content_sha256")
            == bank_content_sha256(pending.payload),
            "pending_source_pool_hash": pool is not None
            and pending is not None
            and pending.payload.get("source_pool_sha256") == pool.sha256(),
            "pending_semantic_hash": pending is not None
            and pending.payload.get("semantic_validation_sha256")
            == canonical_sha256(semantic),
            "pending_quality_hash": pending is not None
            and pending.payload.get("quality_validation_sha256")
            == canonical_sha256(quality),
        }
    )

    expected_schedule: Dict[str, Any] = {}
    if protocol and pending is not None:
        try:
            expected_schedule = build_v6_confirmatory_schedule_metadata(
                protocol,
                pending,
                selected_episode_seeds=selected_episode_seeds,
            )
        except (KeyError, TypeError, ValueError, RuntimeError):
            pass
    checks["confirmatory_schedule_exact"] = bool(expected_schedule) and checkpoint.get(
        "confirmatory_schedule"
    ) == expected_schedule
    return {
        "pass": all(checks.values()),
        "checks": checks,
        "checkpoint_canonical_sha256": canonical_sha256(checkpoint),
        "pending_bank_sha256": pending.sha256() if pending is not None else None,
        "pending_bank_content_sha256": (
            bank_content_sha256(pending.payload) if pending is not None else None
        ),
        "confirmatory_schedule": expected_schedule,
        "pool_run_audit": run_audit,
        "semantic_raw_replay": {
            "ok": semantic_raw_replay.get("ok"),
            "pass": semantic_raw_replay.get("pass"),
            "recomputed_evaluation_sha256": semantic_raw_replay.get(
                "recomputed_evaluation_sha256"
            ),
        },
        "quality_raw_replay": {
            "ok": quality_raw_replay.get("ok"),
            "pass": quality_raw_replay.get("pass"),
            "recomputed_evaluation_sha256": quality_raw_replay.get(
                "recomputed_evaluation_sha256"
            ),
        },
        "power_replay": {
            key: power_replay.get(key)
            for key in (
                "audit_pass",
                "schema_version",
                "official",
                "status",
                "scientific_power_pass",
                "power_selection_pass",
                "null_type_i_pass",
                "selected_episode_seeds",
                "forbidden_outcome_flags",
            )
        },
        "calibration_protocol": protocol,
        "focal_runtime_evidence": dict(checkpoint_runtime_evidence),
    }


def build_v6_final_checkpoint(
    *,
    prevalidation_checkpoint_path: str,
    validation_summary_path: str,
    validation_log_path: str,
    validation_manifest_path: str,
    validated_bank_path: str,
    repository_root: str,
) -> Dict[str, Any]:
    """Build the confirmatory checkpoint after independent validation passes."""
    with open(prevalidation_checkpoint_path, "r", encoding="utf-8") as handle:
        prevalidation = strict_json_load(handle)
    prevalidation_audit = audit_v6_prevalidation_checkpoint(
        prevalidation, repository_root
    )
    if not prevalidation_audit["pass"]:
        raise ValueError("V6 pre-validation checkpoint no longer passes its audit")
    final_bank = V6TriadBank.load(validated_bank_path)
    protocol = prevalidation_audit.get("calibration_protocol", {})
    with open(validation_manifest_path, "r", encoding="utf-8") as handle:
        validation_manifest = strict_json_load(handle)
    validation_receipt_reference = validation_manifest.get(
        "frozen_protocol", {}
    ).get("single_launch_receipt", {})
    validation_receipt_path, validation_receipt_inside = (
        _checkpoint_reference_path(
            validation_receipt_reference, repository_root
        )
    )
    if not validation_receipt_inside or not os.path.isfile(
        validation_receipt_path
    ):
        raise ValueError(
            "V6 validation manifest has no repository-local launch receipt"
        )
    with open(validation_receipt_path, "r", encoding="utf-8") as handle:
        validation_receipt = strict_json_load(handle)
    if not isinstance(validation_receipt, Mapping):
        raise ValueError("V6 validation launch receipt must be a JSON object")
    frozen_runtime = _runtime_mapping(prevalidation.get("focal_runtime"))
    frozen_runtime_evidence = _runtime_mapping(frozen_runtime.get("evidence"))
    validation_runtime_evidence = _runtime_mapping(
        validation_manifest.get("provider", {}).get("focal_runtime_evidence")
    )
    if not frozen_runtime_evidence or not _strict_json_equal(
        validation_runtime_evidence, frozen_runtime_evidence
    ):
        raise ValueError("V6 validation runtime differs from pool screening")
    if not _strict_json_equal(
        validation_receipt.get("focal_runtime"), frozen_runtime
    ):
        raise ValueError("V6 validation receipt runtime differs from pool screening")
    confirmatory_schedule = json.loads(
        json.dumps(prevalidation["confirmatory_schedule"])
    )
    checkpoint: Dict[str, Any] = {
        "checkpoint_version": V6_FINAL_CHECKPOINT_VERSION,
        "status": V6_FINAL_CHECKPOINT_STATUS,
        "pre_confirmatory_outcomes": True,
        "prevalidation_checkpoint": v6_artifact_reference(
            prevalidation_checkpoint_path, repository_root
        ),
        "official_run_ids": json.loads(
            json.dumps(prevalidation["official_run_ids"])
        ),
        "independent_validation": v6_artifact_reference(
            validation_summary_path, repository_root
        ),
        "independent_validation_log": v6_artifact_reference(
            validation_log_path, repository_root, canonical_json=False
        ),
        "independent_validation_manifest": v6_artifact_reference(
            validation_manifest_path, repository_root
        ),
        "independent_validation_launch_receipt": v6_artifact_reference(
            validation_receipt_path, repository_root
        ),
        "validated_bank": {
            **v6_artifact_reference(validated_bank_path, repository_root),
            "bank_sha256": final_bank.sha256(),
            "bank_content_sha256": bank_content_sha256(final_bank.payload),
        },
        "source_code": _source_code_references(
            repository_root, V6_CONFIRMATORY_SOURCE_PATHS
        ),
        "focal_runtime": json.loads(
            json.dumps(frozen_runtime, allow_nan=False)
        ),
        "confirmatory_schedule": confirmatory_schedule,
        "analysis_contract": build_v6_analysis_contract(
            protocol, final_bank, confirmatory_schedule, frozen_runtime
        ),
    }
    audit = audit_v6_final_checkpoint(checkpoint, repository_root)
    if not audit["pass"]:
        failed = sorted(name for name, passed in audit["checks"].items() if not passed)
        raise ValueError(
            "refusing to freeze V6 final checkpoint: %s" % ", ".join(failed)
        )
    return checkpoint


def audit_v6_final_checkpoint(
    checkpoint: Mapping[str, Any], repository_root: str
) -> Dict[str, Any]:
    """Prove validation and replay pending-to-validated finalization."""
    checks: Dict[str, bool] = {
        "checkpoint_version": checkpoint.get("checkpoint_version")
        == V6_FINAL_CHECKPOINT_VERSION,
        "checkpoint_status": checkpoint.get("status") == V6_FINAL_CHECKPOINT_STATUS,
        "pre_confirmatory_outcomes": checkpoint.get("pre_confirmatory_outcomes")
        is True,
    }
    _prefix_checks(
        checks,
        "source_code",
        _audit_source_code_references(
            checkpoint.get("source_code"),
            repository_root,
            V6_CONFIRMATORY_SOURCE_PATHS,
        ),
    )
    prevalidation, pre_checks, _prevalidation_path = _load_checkpoint_json_reference(
        checkpoint.get("prevalidation_checkpoint", {}), repository_root
    )
    validation, validation_checks, _validation_path = _load_checkpoint_json_reference(
        checkpoint.get("independent_validation", {}), repository_root
    )
    records, log_checks, log_path = _load_checkpoint_log_reference(
        checkpoint.get("independent_validation_log", {}), repository_root
    )
    manifest, manifest_checks, manifest_path = _load_checkpoint_json_reference(
        checkpoint.get("independent_validation_manifest", {}), repository_root
    )
    validation_receipt, validation_receipt_checks, _validation_receipt_path = (
        _load_checkpoint_json_reference(
            checkpoint.get("independent_validation_launch_receipt", {}),
            repository_root,
        )
    )
    final_payload, final_checks, final_path = _load_checkpoint_json_reference(
        checkpoint.get("validated_bank", {}), repository_root
    )
    for prefix, values in (
        ("prevalidation_checkpoint", pre_checks),
        ("validation_summary", validation_checks),
        ("validation_log", log_checks),
        ("validation_manifest", manifest_checks),
        ("validation_launch_receipt", validation_receipt_checks),
        ("validated_bank", final_checks),
    ):
        _prefix_checks(checks, prefix, values)

    prevalidation_audit: Dict[str, Any] = {}
    if prevalidation:
        try:
            prevalidation_audit = audit_v6_prevalidation_checkpoint(
                prevalidation, repository_root
            )
        except (KeyError, TypeError, ValueError, RuntimeError):
            pass
    checks["prevalidation_checkpoint_recomputed"] = (
        prevalidation_audit.get("pass") is True
    )

    pending: Optional[V6TriadBank] = None
    protocol: Dict[str, Any] = {}
    if prevalidation_audit.get("pass") is True:
        pending_ref = prevalidation.get("pending_bank", {})
        pending_path, pending_inside = _checkpoint_reference_path(
            pending_ref, repository_root
        )
        protocol_ref = prevalidation.get("calibration_protocol", {})
        protocol, protocol_checks, _ = _load_checkpoint_json_reference(
            protocol_ref, repository_root
        )
        _prefix_checks(checks, "reloaded_protocol", protocol_checks)
        try:
            if pending_inside:
                pending = V6TriadBank.load(pending_path)
        except (OSError, ValueError, TypeError):
            pass
    else:
        checks.update(
            {
                "reloaded_protocol_path_inside_root": False,
                "reloaded_protocol_exists": False,
                "reloaded_protocol_json_object": False,
                "reloaded_protocol_file_sha256": False,
                "reloaded_protocol_canonical_sha256": False,
            }
        )

    prevalidation_runtime = _runtime_mapping(prevalidation.get("focal_runtime"))
    prevalidation_runtime_evidence = _runtime_mapping(
        prevalidation_runtime.get("evidence")
    )
    checkpoint_runtime = _runtime_mapping(checkpoint.get("focal_runtime"))
    checkpoint_runtime_evidence = _runtime_mapping(
        checkpoint_runtime.get("evidence")
    )
    runtime_checkpoint_audit = audit_v6_focal_runtime_checkpoint(
        checkpoint_runtime,
        protocol,
        expected_evidence=prevalidation_runtime_evidence,
    )
    _prefix_checks(checks, "focal_runtime", runtime_checkpoint_audit["checks"])
    validation_provider = _runtime_mapping(manifest.get("provider"))
    validation_manifest_runtime_audit = _runtime_mapping(
        manifest.get("frozen_protocol", {}).get("focal_runtime")
    )
    validation_receipt_runtime = _runtime_mapping(
        validation_receipt.get("focal_runtime")
    )

    manifest_proof = manifest.get("frozen_protocol", {}).get(
        "prevalidation_checkpoint", {}
    )
    checks.update(
        {
            "pending_bank_reloaded": pending is not None,
            "validation_manifest_checkpoint_binding": bool(manifest_proof)
            and manifest_proof
            == checkpoint.get("prevalidation_checkpoint", {}),
            "validation_launch_receipt_manifest_binding": bool(
                validation_receipt
            )
            and manifest.get("frozen_protocol", {}).get(
                "single_launch_receipt"
            )
            == checkpoint.get("independent_validation_launch_receipt"),
            "validation_manifest_log_hash": log_checks.get("file_sha256") is True
            and manifest.get("log_file_sha256")
            == checkpoint.get("independent_validation_log", {}).get("file_sha256"),
            "validation_summary_log_hash": log_checks.get("file_sha256") is True
            and validation.get("validation_log_file_sha256")
            == checkpoint.get("independent_validation_log", {}).get("file_sha256"),
            "validation_summary_manifest_hash": manifest_checks.get("file_sha256")
            is True
            and validation.get("validation_manifest_file_sha256")
            == checkpoint.get("independent_validation_manifest", {}).get(
                "file_sha256"
            ),
            "runtime_matches_prevalidation": bool(checkpoint_runtime_evidence)
            and _strict_json_equal(checkpoint_runtime, prevalidation_runtime),
            "validation_manifest_runtime_binding": bool(
                checkpoint_runtime_evidence
            )
            and _strict_json_equal(
                validation_provider.get("focal_runtime_evidence"),
                checkpoint_runtime_evidence,
            ),
            "validation_manifest_runtime_audit_binding": (
                validation_manifest_runtime_audit.get("pass") is True
                and _strict_json_equal(
                    validation_manifest_runtime_audit.get("evidence"),
                    checkpoint_runtime_evidence,
                )
                and validation_manifest_runtime_audit.get("evidence_sha256")
                == checkpoint_runtime.get("evidence_sha256")
            ),
            "validation_receipt_runtime_binding": bool(
                checkpoint_runtime_evidence
            )
            and _strict_json_equal(
                validation_receipt_runtime, checkpoint_runtime
            ),
        }
    )

    expected_validation_receipt: Dict[str, Any] = {}
    if pending is not None and protocol:
        try:
            protocol_path, protocol_inside = _checkpoint_reference_path(
                prevalidation.get("calibration_protocol", {}), repository_root
            )
            if protocol_inside:
                expected_validation_receipt = (
                    build_v6_calibration_launch_receipt(
                        protocol=protocol,
                        protocol_path=protocol_path,
                        bank=pending,
                        mode=V6_VALIDATION_MODE,
                        repository_root=repository_root,
                        prevalidation_reference=checkpoint.get(
                            "prevalidation_checkpoint", {}
                        ),
                        runtime_evidence=checkpoint_runtime_evidence,
                    )
                )
        except (KeyError, OSError, TypeError, ValueError, RuntimeError):
            pass
    checks["validation_launch_receipt_exact"] = (
        bool(expected_validation_receipt)
        and validation_receipt == expected_validation_receipt
    )

    recomputed_plan: Dict[str, Any] = {}
    run_audit: Dict[str, Any] = {}
    if pending is not None and protocol and manifest and records:
        try:
            recomputed_plan = audit_v6_calibration_plan(
                protocol,
                pending,
                manifest.get("provider", {}),
                V6_VALIDATION_MODE,
                int(manifest.get("schedule", {}).get("seed", -1)),
                manifest.get("schedule", {}).get("n_episode_blocks"),
                repository_root,
                prevalidation_checkpoint=prevalidation,
                run_id=str(manifest.get("run_id", "")),
                require_runtime_evidence=True,
            )
            run_audit = audit_v6_calibration_run(
                records, manifest, pending, V6_VALIDATION_MODE
            )
        except (KeyError, TypeError, ValueError, RuntimeError):
            pass
    checks.update(
        {
            "validation_plan_recomputed": recomputed_plan.get("pass") is True,
            "validation_plan_matches_manifest": bool(recomputed_plan)
            and manifest.get("frozen_protocol", {}).get("plan_audit")
            == recomputed_plan,
            "validation_run_recomputed": run_audit.get("pass") is True,
        }
    )

    expected_validation: Dict[str, Any] = {}
    expected_final: Dict[str, Any] = {}
    if pending is not None and run_audit.get("pass") is True:
        try:
            expected_validation = evaluate_v6_bank_validation(records, pending)
            expected_validation["calibration_run_audit"] = run_audit
            expected_validation["validation_manifest_file_sha256"] = file_sha256(
                manifest_path
            )
            expected_validation["validation_log_file_sha256"] = file_sha256(log_path)
            if expected_validation.get("pass") is True:
                expected_final = finalize_validated_v6_bank(
                    pending.payload, expected_validation
                )
        except (KeyError, TypeError, ValueError, RuntimeError):
            expected_validation = {}
            expected_final = {}
    checks.update(
        {
            "validation_pass_recomputed": expected_validation.get("pass") is True,
            "validation_summary_exactly_recomputed": bool(expected_validation)
            and validation == expected_validation,
            "validated_bank_transition_recomputed": bool(expected_final)
            and final_payload == expected_final,
        }
    )

    final_bank: Optional[V6TriadBank] = None
    try:
        if final_payload:
            final_bank = V6TriadBank.load(final_path)
    except (OSError, ValueError, TypeError):
        pass
    final_ref = checkpoint.get("validated_bank", {})
    checks.update(
        {
            "validated_bank_structural_audit": final_bank is not None,
            "validated_bank_status": final_bank is not None
            and final_bank.payload.get("status") == V6_SELECTED_BANK_STATUS,
            "validated_bank_hash": final_bank is not None
            and final_ref.get("bank_sha256") == final_bank.sha256(),
            "validated_bank_content_hash": final_bank is not None
            and final_ref.get("bank_content_sha256")
            == bank_content_sha256(final_bank.payload),
        }
    )

    expected_schedule: Dict[str, Any] = {}
    if protocol and pending is not None:
        try:
            expected_schedule = build_v6_confirmatory_schedule_metadata(
                protocol,
                pending,
                selected_episode_seeds=prevalidation.get(
                    "confirmatory_schedule", {}
                ).get("selected_episode_seeds"),
            )
        except (KeyError, TypeError, ValueError, RuntimeError):
            pass
    checks["confirmatory_schedule_matches_prevalidation"] = checkpoint.get(
        "confirmatory_schedule"
    ) == prevalidation.get("confirmatory_schedule")
    checks["official_run_ids_match_prevalidation"] = checkpoint.get(
        "official_run_ids"
    ) == prevalidation.get("official_run_ids")
    checks["confirmatory_schedule_recomputed"] = bool(expected_schedule) and checkpoint.get(
        "confirmatory_schedule"
    ) == expected_schedule
    expected_analysis_contract: Dict[str, Any] = {}
    if protocol and final_bank is not None and expected_schedule:
        try:
            expected_analysis_contract = build_v6_analysis_contract(
                protocol, final_bank, expected_schedule, checkpoint_runtime
            )
        except (KeyError, TypeError, ValueError, RuntimeError):
            pass
    checks["analysis_contract_recomputed"] = bool(
        expected_analysis_contract
    ) and checkpoint.get("analysis_contract") == expected_analysis_contract
    checkpoint_analysis = checkpoint.get("analysis_contract", {})
    checkpoint_experiment = (
        checkpoint_analysis.get("experiment", {})
        if isinstance(checkpoint_analysis, Mapping)
        else {}
    )
    checks["analysis_settings_frozen"] = isinstance(
        checkpoint_analysis, Mapping
    ) and _strict_json_equal(
        checkpoint_analysis.get("analysis"), CONTROLLED_V6_ANALYSIS_CONFIG
    )
    checks["confirmatory_paid_preflight_receipt_path_frozen"] = isinstance(
        checkpoint_experiment, Mapping
    ) and checkpoint_experiment.get("paid_preflight_receipt_path") == (
        V6_CANONICAL_RUN_PATHS["confirmatory"]["preflight_receipt"]
    )
    return {
        "pass": all(checks.values()),
        "checks": checks,
        "checkpoint_canonical_sha256": canonical_sha256(checkpoint),
        "validated_bank_sha256": (
            final_bank.sha256() if final_bank is not None else None
        ),
        "validated_bank_content_sha256": (
            bank_content_sha256(final_bank.payload)
            if final_bank is not None
            else None
        ),
        "confirmatory_schedule": expected_schedule,
        "analysis_contract": expected_analysis_contract,
        "calibration_protocol": protocol,
        "focal_runtime": dict(checkpoint_runtime),
        "focal_runtime_evidence": dict(checkpoint_runtime_evidence),
        "prevalidation_checkpoint_sha256": prevalidation_audit.get(
            "checkpoint_canonical_sha256"
        ),
    }
