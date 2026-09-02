#!/usr/bin/env python3
"""Run only the audited, single official V6 confirmatory GPU experiment."""

from __future__ import annotations

import _bootstrap  # noqa: F401
import argparse
import datetime as dt
import json
import math
import os
import secrets
import stat
import sys
import tempfile
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Sequence

from config import (
    CONTROLLED_V6_VERSION,
    CONTROLLED_V6_RANDOMIZATION_SEED,
    ControlledExperimentConfig,
    ControlledTargetParams,
    ModelConfig,
)
from src.controlled_experiment import (
    ControlledDonorRegistry,
    audit_or_recover_round_claim,
    build_controlled_episode_specs,
    controlled_resume_policy,
    run_controlled_episode,
    run_controlled_experiment,
)
from src.controlled_focal_agent import ControlledFocalAgent
from src.controlled_v6_analysis import (
    _canonical_sha256,
    audit_v6_launch_receipt_payload,
    reconcile_v6_records_against_runtime,
)
from src.controlled_protocol import ControlledProtocol
from src.controlled_v6_messages import (
    V6_SELECTED_BANK_STATUS,
    V6TriadBank,
    make_v6_protocol,
)
from src.hf_provider import HuggingFaceProvider, collect_focal_runtime_evidence
from src.file_lock import (
    ExclusiveFileLock,
    fsync_directory_best_effort,
    require_contained_path,
    require_directory_nonsymlink,
    require_regular_nonsymlink,
)
from src.focal_agent import BaseProvider
from src.logging_utils import read_jsonl, strict_json_load
from src.v6_calibration import file_sha256
from src.v6_protocol_gate import (
    V6_CANONICAL_RUN_PATHS,
    audit_v6_final_checkpoint,
    build_v6_confirmatory_schedule_metadata,
    require_v6_focal_runtime,
)


STRICT_CHOICES = ("1", "2", "3")
DEFAULT_FINAL_CHECKPOINT = os.path.join(
    _bootstrap.ROOT, "results", "v6_design", "final_checkpoint.json"
)
DEFAULT_EXPERIMENT_ID = "controlled_v6_checkpoint"
CONFIRMATORY_PATHS = dict(V6_CANONICAL_RUN_PATHS["confirmatory"])
ROUND_CLAIM_SUFFIX = ".inflight.json"
RUN_LOCK_SUFFIX = ".lock"


@dataclass(frozen=True)
class V6ConfirmatoryPlan:
    """Runtime objects derived exclusively from one passing final checkpoint."""

    repository_root: str
    checkpoint_path: str
    checkpoint: Dict[str, Any]
    checkpoint_audit: Dict[str, Any]
    prevalidation_path: str
    protocol_spec_path: str
    protocol_spec: Dict[str, Any]
    bank_path: str
    schedule: Dict[str, Any]
    generation: Dict[str, Any]
    target: Dict[str, Any]
    model_id: str
    revision: str
    run_id: str
    selected_episode_seeds: int
    config: ControlledExperimentConfig
    protocol: ControlledProtocol
    expected_n_episodes: int
    expected_n_records: int
    canonical_out_dir_relative: str
    launch_receipt_relative: str
    launch_receipt_path: str
    focal_runtime: Dict[str, Any]


def _official_run_paths(
    plan: V6ConfirmatoryPlan, *, create_parents: bool = False
) -> Dict[str, str]:
    root = plan.repository_root
    out_dir = _require_safe_path(
        plan.config.out_dir,
        root,
        "V6 canonical output directory",
        leaf_kind="directory",
        allow_missing=True,
    )
    receipt = _require_safe_path(
        plan.launch_receipt_path,
        root,
        "V6 official launch receipt",
        leaf_kind="file",
        allow_missing=True,
    )
    if create_parents:
        os.makedirs(out_dir, exist_ok=True)
        os.makedirs(os.path.dirname(receipt), exist_ok=True)
        _require_safe_path(
            out_dir,
            root,
            "V6 canonical output directory",
            leaf_kind="directory",
            allow_missing=False,
        )
    paths = {
        "out_dir": out_dir,
        "receipt": receipt,
        "log": os.path.join(out_dir, plan.run_id + ".jsonl"),
        "manifest": os.path.join(out_dir, plan.run_id + ".manifest.json"),
        "claim": os.path.join(out_dir, plan.run_id + ROUND_CLAIM_SUFFIX),
        "lock": os.path.join(out_dir, plan.run_id + RUN_LOCK_SUFFIX),
    }
    for name in ("receipt", "log", "manifest", "claim", "lock"):
        paths[name] = _require_safe_path(
            paths[name],
            root,
            "V6 %s" % name,
            leaf_kind="file",
            allow_missing=True,
        )
    return paths


def add_frozen_contract_arguments(
    parser: argparse.ArgumentParser, *, require_run_id: bool = True
) -> None:
    """Add only fail-closed overrides of fields frozen by the checkpoint."""
    parser.add_argument(
        "--final-checkpoint",
        default=DEFAULT_FINAL_CHECKPOINT,
        help="full V6 final checkpoint; all runtime settings are recovered from it",
    )
    parser.add_argument("--run-id", required=require_run_id)
    parser.add_argument("--bank", default=None)
    parser.add_argument("--model", default=None)
    parser.add_argument("--revision", default=None)
    parser.add_argument(
        "--episode-seeds", "--episodes", dest="episode_seeds", type=int, default=None
    )
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--conditions", nargs="+", default=None)
    parser.add_argument("--rounds", type=int, default=None)
    parser.add_argument("--swap-round", type=int, default=None)
    parser.add_argument("--heldout-start-round", type=int, default=None)
    parser.add_argument("--p-match", type=float, default=None)
    parser.add_argument("--p-mismatch", type=float, default=None)
    parser.add_argument("--p-random", type=float, default=None)
    parser.add_argument("--temperature", type=float, default=None)
    parser.add_argument("--top-p", type=float, default=None)
    parser.add_argument("--top-k", type=int, default=None)
    parser.add_argument("--max-tokens", type=int, default=None)
    parser.add_argument("--dtype", default=None)
    parser.add_argument(
        "--enable-thinking",
        action=argparse.BooleanOptionalAction,
        default=None,
    )
    parser.add_argument("--constrained-choices", nargs="+", default=None)
    parser.add_argument("--invalid-output-policy", default=None)


def _require_safe_path(
    path: str,
    root: str,
    label: str,
    *,
    leaf_kind: str,
    allow_missing: bool,
) -> str:
    """Reject lexical escapes, symlink components, and special-file leaves."""
    absolute_root = os.path.abspath(root)
    absolute = require_contained_path(path, absolute_root, label=label)
    require_directory_nonsymlink(absolute_root, label="V6 repository root")
    relative = os.path.relpath(absolute, absolute_root)
    current = absolute_root
    parts = [] if relative == "." else relative.split(os.sep)
    for index, part in enumerate(parts):
        current = os.path.join(current, part)
        is_leaf = index == len(parts) - 1
        try:
            metadata = os.lstat(current)
        except FileNotFoundError:
            if allow_missing:
                break
            raise FileNotFoundError("%s is missing: %s" % (label, current)) from None
        if stat.S_ISLNK(metadata.st_mode):
            raise ValueError("%s must not contain symlinks: %s" % (label, current))
        if not is_leaf and not stat.S_ISDIR(metadata.st_mode):
            raise ValueError("%s has a non-directory parent: %s" % (label, current))
        if is_leaf:
            expected = stat.S_ISDIR if leaf_kind == "directory" else stat.S_ISREG
            if not expected(metadata.st_mode):
                raise ValueError(
                    "%s must be a %s: %s" % (label, leaf_kind, current)
                )
    return absolute


def _input_path(path: str, root: str) -> str:
    candidate = path if os.path.isabs(path) else os.path.join(os.getcwd(), path)
    return _require_safe_path(
        candidate,
        root,
        "V6 runtime artifact",
        leaf_kind="file",
        allow_missing=False,
    )


def _frozen_repo_path(
    relative: Any,
    root: str,
    expected: str,
    label: str,
    *,
    leaf_kind: str = "file",
) -> str:
    """Resolve one exact code-and-checkpoint-frozen repository path."""
    if not isinstance(relative, str) or relative != expected:
        raise ValueError(
            "V6 %s must equal the code-frozen repository path %r"
            % (label, expected)
        )
    if os.path.isabs(relative) or os.path.normpath(relative) != relative:
        raise ValueError("V6 %s must be canonical and repository-relative" % label)
    return _require_safe_path(
        os.path.join(root, relative),
        root,
        "V6 %s" % label,
        leaf_kind=leaf_kind,
        allow_missing=True,
    )


def _reference_path(
    reference: Mapping[str, Any], root: str, label: str
) -> str:
    raw = reference.get("path")
    if not isinstance(raw, str) or not raw.strip():
        raise ValueError("V6 final checkpoint has no %s path" % label)
    candidate = raw if os.path.isabs(raw) else os.path.join(root, raw)
    return _require_safe_path(
        candidate,
        root,
        "V6 %s path" % label,
        leaf_kind="file",
        allow_missing=False,
    )


def _load_json_object(path: str, label: str) -> Dict[str, Any]:
    require_regular_nonsymlink(path, label=label)
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags)
    metadata = os.fstat(descriptor)
    if not stat.S_ISREG(metadata.st_mode):
        os.close(descriptor)
        raise ValueError("%s must be a regular file" % label)
    with os.fdopen(descriptor, "r", encoding="utf-8") as handle:
        payload = strict_json_load(handle)
    if not isinstance(payload, dict):
        raise ValueError("%s must be a JSON object" % label)
    return payload


def _require_mapping(value: Any, label: str) -> Dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError("V6 frozen %s must be an object" % label)
    return dict(value)


def _exact_override(args: argparse.Namespace, field: str, frozen: Any, label: str) -> Any:
    supplied = getattr(args, field, None)
    if supplied is not None and supplied != frozen:
        raise ValueError(
            "V6 confirmatory %s must equal the final checkpoint: expected %r, got %r"
            % (label, frozen, supplied)
        )
    return frozen


def _audit_frozen_generation(generation: Mapping[str, Any]) -> None:
    checks = {
        "activation_capture_disabled": generation.get("activation_capture") is False,
        "thinking_disabled": generation.get("enable_thinking") is False,
        "strict_choices": generation.get("constrained_choices")
        == list(STRICT_CHOICES),
        "invalid_output_aborts": generation.get("invalid_output_policy")
        == "abort; no fallback",
        "temperature_present": isinstance(generation.get("temperature"), (int, float)),
        "top_p_present": isinstance(generation.get("top_p"), (int, float)),
        "top_k_present": isinstance(generation.get("top_k"), int),
        "max_tokens_positive": isinstance(generation.get("max_tokens"), int)
        and int(generation["max_tokens"]) > 0,
        "dtype_present": isinstance(generation.get("dtype"), str)
        and bool(str(generation["dtype"]).strip()),
    }
    if not all(checks.values()):
        failed = sorted(name for name, passed in checks.items() if not passed)
        raise ValueError("invalid frozen V6 generation contract: %s" % ", ".join(failed))


def _audit_target(target: Mapping[str, Any]) -> None:
    failed = []
    for name in ("p_match", "p_mismatch", "p_random"):
        try:
            value = float(target[name])
        except (KeyError, TypeError, ValueError):
            failed.append(name)
            continue
        if not math.isfinite(value) or not 0.0 <= value <= 1.0:
            failed.append(name)
    if failed:
        raise ValueError("invalid frozen V6 target parameters: %s" % ", ".join(failed))


def _checkpoint_provenance(
    checkpoint_path: str,
    checkpoint: Mapping[str, Any],
    checkpoint_audit: Mapping[str, Any],
    prevalidation: Mapping[str, Any],
) -> Dict[str, Any]:
    provenance = {
        "checkpoint_path": checkpoint_path,
        "checkpoint_file_sha256": file_sha256(checkpoint_path),
        "checkpoint_canonical_sha256": checkpoint_audit[
            "checkpoint_canonical_sha256"
        ],
        "artifact_audit": dict(checkpoint_audit),
        "prevalidation_checkpoint": dict(checkpoint["prevalidation_checkpoint"]),
        "calibration_protocol": dict(prevalidation["calibration_protocol"]),
        "validated_bank": dict(checkpoint["validated_bank"]),
    }
    if isinstance(checkpoint.get("focal_runtime"), Mapping):
        provenance["focal_runtime"] = dict(checkpoint["focal_runtime"])
    return provenance


def prepare_v6_confirmatory_plan(
    args: argparse.Namespace,
    *,
    repository_root: str | None = None,
    out_dir: str | None = None,
) -> V6ConfirmatoryPlan:
    """Audit the artifact graph and construct the exact model-free run plan."""
    root = os.path.abspath(repository_root or _bootstrap.ROOT)
    require_directory_nonsymlink(root, label="V6 repository root")
    checkpoint_path = _input_path(str(args.final_checkpoint), root)
    if not os.path.isfile(checkpoint_path):
        raise FileNotFoundError(
            "V6 confirmatory final checkpoint is not frozen: %s" % checkpoint_path
        )
    checkpoint = _load_json_object(checkpoint_path, "V6 final checkpoint")

    # This must remain the first operation that interprets any checkpoint
    # references. It replays the complete pending-to-validated transition.
    checkpoint_audit = audit_v6_final_checkpoint(checkpoint, root)
    if checkpoint_audit.get("pass") is not True:
        failed = sorted(
            name
            for name, passed in checkpoint_audit.get("checks", {}).items()
            if not passed
        )
        raise ValueError(
            "V6 final checkpoint audit failed: %s"
            % (", ".join(failed) if failed else "unknown audit failure")
        )

    schedule = _require_mapping(
        checkpoint_audit.get("confirmatory_schedule"), "confirmatory schedule"
    )
    if schedule != checkpoint.get("confirmatory_schedule"):
        raise ValueError("audited V6 schedule differs from the final checkpoint")
    audited_runtime = checkpoint_audit.get("focal_runtime")
    focal_runtime = (
        dict(audited_runtime) if isinstance(audited_runtime, Mapping) else {}
    )
    if focal_runtime and focal_runtime != checkpoint.get("focal_runtime"):
        raise ValueError("audited V6 focal runtime differs from the final checkpoint")
    canonical_out_dir = _frozen_repo_path(
        schedule.get("canonical_out_dir"),
        root,
        CONFIRMATORY_PATHS["out_dir"],
        "confirmatory output directory",
        leaf_kind="directory",
    )
    launch_receipt_path = _frozen_repo_path(
        schedule.get("launch_receipt_path"),
        root,
        CONFIRMATORY_PATHS["receipt"],
        "confirmatory launch receipt",
    )
    _frozen_repo_path(
        schedule.get("paid_preflight_report_path"),
        root,
        CONFIRMATORY_PATHS["preflight"],
        "paid preflight report",
    )
    _frozen_repo_path(
        schedule.get("paid_preflight_receipt_path"),
        root,
        CONFIRMATORY_PATHS["preflight_receipt"],
        "paid preflight receipt",
    )
    supplied_out_dir = out_dir
    if supplied_out_dir is None:
        supplied_out_dir = getattr(args, "out_dir", None)
    if supplied_out_dir is not None and supplied_out_dir != CONFIRMATORY_PATHS["out_dir"]:
        raise ValueError(
            "V6 confirmatory output directory override is forbidden; use %r"
            % CONFIRMATORY_PATHS["out_dir"]
        )

    prevalidation_path = _reference_path(
        _require_mapping(
            checkpoint.get("prevalidation_checkpoint"),
            "prevalidation checkpoint reference",
        ),
        root,
        "prevalidation checkpoint",
    )
    prevalidation = _load_json_object(
        prevalidation_path, "V6 prevalidation checkpoint"
    )
    protocol_spec_path = _reference_path(
        _require_mapping(
            prevalidation.get("calibration_protocol"),
            "calibration protocol reference",
        ),
        root,
        "calibration protocol",
    )
    protocol_spec = _load_json_object(protocol_spec_path, "V6 calibration protocol")
    bank_path = _reference_path(
        _require_mapping(checkpoint.get("validated_bank"), "validated bank reference"),
        root,
        "validated bank",
    )

    supplied_bank = getattr(args, "bank", None)
    if supplied_bank is not None and _input_path(str(supplied_bank), root) != bank_path:
        raise ValueError("V6 confirmatory bank must be the checkpoint's validated bank")

    model = _require_mapping(protocol_spec.get("primary_model"), "primary model")
    generation = _require_mapping(protocol_spec.get("generation"), "generation")
    design = _require_mapping(
        protocol_spec.get("confirmatory_design"), "confirmatory design"
    )
    target = _require_mapping(design.get("target"), "target parameters")
    _audit_frozen_generation(generation)
    _audit_target(target)

    model_id = model.get("id")
    revision = model.get("revision")
    if not isinstance(model_id, str) or not model_id.strip():
        raise ValueError("V6 frozen primary model ID is missing")
    if not isinstance(revision, str) or not revision.strip():
        raise ValueError("V6 frozen immutable model revision is missing")

    official_run_id = schedule.get("official_run_id")
    selected_episode_seeds = schedule.get("selected_episode_seeds")
    if not isinstance(official_run_id, str) or not official_run_id.strip():
        raise ValueError("V6 frozen official confirmatory run ID is missing")
    if not isinstance(selected_episode_seeds, int) or selected_episode_seeds < 1:
        raise ValueError("V6 final checkpoint has no positive selected episode count")
    if getattr(args, "run_id", None) is None:
        args.run_id = official_run_id

    frozen_conditions = list(schedule.get("conditions", []))
    if not frozen_conditions:
        raise ValueError("V6 frozen confirmatory conditions are missing")
    selected_key = str(selected_episode_seeds)
    schedule_hashes = schedule.get("schedule_sha256_by_episode_seed_count", {})
    if not isinstance(schedule_hashes, Mapping) or schedule.get(
        "selected_schedule_sha256"
    ) != schedule_hashes.get(selected_key):
        raise ValueError("V6 selected confirmatory schedule hash is inconsistent")

    # Reconstruct every prospective episode/round/scenario/candidate coordinate
    # from the frozen bank rather than trusting internally consistent metadata.
    recomputed_schedule = build_v6_confirmatory_schedule_metadata(
        protocol_spec,
        V6TriadBank.load(bank_path),
        selected_episode_seeds=selected_episode_seeds,
    )
    if recomputed_schedule != schedule:
        raise ValueError(
            "V6 confirmatory schedule does not exactly regenerate from the "
            "frozen protocol and validated bank"
        )

    run_id = _exact_override(args, "run_id", official_run_id, "run ID")
    selected_model = _exact_override(args, "model", model_id, "model")
    selected_revision = _exact_override(args, "revision", revision, "revision")
    episode_seeds = _exact_override(
        args, "episode_seeds", selected_episode_seeds, "episode-seed count"
    )
    seed = _exact_override(args, "seed", int(schedule["master_seed"]), "master seed")
    conditions = _exact_override(args, "conditions", frozen_conditions, "conditions")
    rounds = _exact_override(args, "rounds", int(schedule["n_rounds"]), "round count")
    swap_round = _exact_override(
        args, "swap_round", int(schedule["swap_round"]), "swap round"
    )
    heldout_start = _exact_override(
        args,
        "heldout_start_round",
        int(schedule["heldout_start_round"]),
        "heldout start round",
    )
    p_match = _exact_override(args, "p_match", target["p_match"], "p_match")
    p_mismatch = _exact_override(
        args, "p_mismatch", target["p_mismatch"], "p_mismatch"
    )
    p_random = _exact_override(args, "p_random", target["p_random"], "p_random")
    temperature = _exact_override(
        args, "temperature", generation["temperature"], "temperature"
    )
    _exact_override(args, "top_p", generation["top_p"], "top_p")
    _exact_override(args, "top_k", generation["top_k"], "top_k")
    max_tokens = _exact_override(
        args, "max_tokens", generation["max_tokens"], "max_tokens"
    )
    _exact_override(args, "dtype", generation["dtype"], "dtype")
    _exact_override(
        args, "enable_thinking", generation["enable_thinking"], "thinking setting"
    )
    _exact_override(
        args,
        "constrained_choices",
        list(STRICT_CHOICES),
        "constrained choices",
    )
    _exact_override(
        args,
        "invalid_output_policy",
        generation["invalid_output_policy"],
        "invalid-output policy",
    )

    cfg = ControlledExperimentConfig(
        experiment_id=DEFAULT_EXPERIMENT_ID,
        n_rounds=rounds,
        swap_round=swap_round,
        heldout_start_round=heldout_start,
        n_episode_seeds=episode_seeds,
        seed=seed,
        randomization_seed=CONTROLLED_V6_RANDOMIZATION_SEED,
        conditions=list(conditions),
        target_params=ControlledTargetParams(
            p_match=float(p_match),
            p_mismatch=float(p_mismatch),
            p_random=float(p_random),
        ),
        model=ModelConfig(
            provider="huggingface",
            model=selected_model,
            revision=selected_revision,
            temperature=float(temperature),
            max_tokens=int(max_tokens),
        ),
        out_dir=canonical_out_dir,
    )
    specs = build_controlled_episode_specs(cfg)
    expected_by_count = schedule.get("n_episodes_by_episode_seed_count", {})
    expected_n_episodes = expected_by_count.get(selected_key)
    if not isinstance(expected_n_episodes, int) or len(specs) != expected_n_episodes:
        raise ValueError(
            "V6 confirmatory episode grid differs from the selected frozen schedule"
        )
    expected_n_records = sum(spec.n_rounds for spec in specs)

    provenance = _checkpoint_provenance(
        checkpoint_path, checkpoint, checkpoint_audit, prevalidation
    )
    protocol = make_v6_protocol(
        bank_path,
        require_validated=True,
        manifest_metadata=provenance,
        final_checkpoint_path=checkpoint_path,
        checkpoint_root=root,
        confirmatory_run_id=run_id,
        confirmatory_episode_seeds=episode_seeds,
    )
    protocol_checks = {
        "task_version": protocol.version == CONTROLLED_V6_VERSION,
        "strict_selection": protocol.strict_selection is True,
        "strict_choices": tuple(protocol.constrained_choices or ()) == STRICT_CHOICES,
        "validated_bank_hash": protocol.message_bank_sha256()
        == checkpoint_audit.get("validated_bank_sha256"),
        "validated_bank_status": protocol.message_bank_manifest().get("status")
        == V6_SELECTED_BANK_STATUS,
        "checkpoint_provenance": protocol.protocol_provenance_manifest()
        is not None,
    }
    if not all(protocol_checks.values()):
        failed = sorted(name for name, passed in protocol_checks.items() if not passed)
        raise ValueError("V6 confirmatory protocol audit failed: %s" % ", ".join(failed))

    return V6ConfirmatoryPlan(
        repository_root=root,
        checkpoint_path=checkpoint_path,
        checkpoint=checkpoint,
        checkpoint_audit=checkpoint_audit,
        prevalidation_path=prevalidation_path,
        protocol_spec_path=protocol_spec_path,
        protocol_spec=protocol_spec,
        bank_path=bank_path,
        schedule=schedule,
        generation=generation,
        target=target,
        model_id=selected_model,
        revision=selected_revision,
        run_id=run_id,
        selected_episode_seeds=episode_seeds,
        config=cfg,
        protocol=protocol,
        expected_n_episodes=expected_n_episodes,
        expected_n_records=expected_n_records,
        canonical_out_dir_relative=CONFIRMATORY_PATHS["out_dir"],
        launch_receipt_relative=CONFIRMATORY_PATHS["receipt"],
        launch_receipt_path=launch_receipt_path,
        focal_runtime=focal_runtime,
    )


def make_confirmatory_provider(
    plan: V6ConfirmatoryPlan,
    *,
    device: str = "auto",
    runtime_evidence: Mapping[str, Any] | None = None,
) -> HuggingFaceProvider:
    """Construct the exact no-capture provider after all artifact gates pass."""
    generation = plan.generation
    frozen_evidence = (
        plan.focal_runtime.get("evidence", {}) if plan.focal_runtime else {}
    )
    if frozen_evidence:
        if device != "auto":
            raise ValueError("V6 confirmatory device overrides are forbidden")
        if runtime_evidence is None:
            runtime_evidence = collect_focal_runtime_evidence(device=device)
        require_v6_focal_runtime(
            plan.protocol_spec,
            runtime_evidence,
            expected_evidence=frozen_evidence,
            device_argument=device,
        )
    provider = HuggingFaceProvider(
        model=plan.model_id,
        revision=plan.revision,
        temperature=generation["temperature"],
        max_tokens=generation["max_tokens"],
        device=device,
        dtype=generation["dtype"],
        capture=False,
        seed=plan.config.seed,
        enable_thinking=generation["enable_thinking"],
        top_p=generation["top_p"],
        top_k=generation["top_k"],
        constrained_choices=STRICT_CHOICES,
    )
    if frozen_evidence:
        bind_runtime = getattr(provider, "bind_runtime_evidence", None)
        if not callable(bind_runtime):
            raise ValueError("V6 provider cannot bind focal runtime evidence")
        bind_runtime(runtime_evidence or {})
    description = provider.describe()
    checks = {
        "provider": description.get("provider") == "huggingface",
        "model": description.get("model") == plan.model_id,
        "revision": description.get("revision") == plan.revision,
        "temperature": description.get("temperature") == generation["temperature"],
        "max_tokens": description.get("max_tokens") == generation["max_tokens"],
        "dtype": description.get("dtype") == generation["dtype"],
        "capture_disabled": description.get("capture") is False,
        "thinking": description.get("enable_thinking")
        is generation["enable_thinking"],
        "top_p": description.get("top_p") == generation["top_p"],
        "top_k": description.get("top_k") == generation["top_k"],
        "seed": description.get("torch_seed_base") == plan.config.seed,
        "strict_choices": description.get("constrained_choices")
        == list(STRICT_CHOICES),
        "strict_failure": description.get("invalid_output_policy")
        == "provider error; no fallback",
        "device_auto": not frozen_evidence
        or description.get("device") == "auto",
        "focal_runtime": not frozen_evidence
        or description.get("focal_runtime_evidence") == frozen_evidence,
    }
    if not all(checks.values()):
        failed = sorted(name for name, passed in checks.items() if not passed)
        raise ValueError("V6 provider differs from the frozen contract: %s" % ", ".join(failed))
    return provider


def _atomic_create_json(path: str, payload: Mapping[str, Any]) -> None:
    """Publish one immutable marker via a fully synced temporary hard link."""
    parent = os.path.dirname(path) or "."
    os.makedirs(parent, exist_ok=True)
    require_directory_nonsymlink(parent, label="V6 receipt parent")
    require_regular_nonsymlink(
        path, label="V6 official launch receipt", allow_missing=True
    )
    if os.path.lexists(path):
        raise FileExistsError(path)
    encoded = (
        json.dumps(payload, indent=2, ensure_ascii=False, allow_nan=False)
        + "\n"
    ).encode("utf-8")
    descriptor, temporary = tempfile.mkstemp(
        prefix=".v6-receipt-", suffix=".publish", dir=parent
    )
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, 0o444)
        os.link(temporary, path)
        fsync_directory_best_effort(parent)
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass


def _atomic_replace_json(path: str, payload: Mapping[str, Any]) -> None:
    parent = os.path.dirname(path) or "."
    os.makedirs(parent, exist_ok=True)
    require_directory_nonsymlink(parent, label="V6 manifest parent")
    require_regular_nonsymlink(path, label="V6 manifest", allow_missing=True)
    descriptor, temporary = tempfile.mkstemp(prefix=".v6-manifest-", dir=parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=False, allow_nan=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        try:
            directory_descriptor = os.open(parent, os.O_RDONLY)
        except OSError:
            directory_descriptor = None
        if directory_descriptor is not None:
            try:
                try:
                    os.fsync(directory_descriptor)
                except OSError:
                    pass
            finally:
                os.close(directory_descriptor)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _launch_receipt_payload(
    plan: V6ConfirmatoryPlan,
    *,
    runtime_evidence: Mapping[str, Any] | None = None,
) -> Dict[str, Any]:
    frozen_evidence = (
        plan.focal_runtime.get("evidence", {}) if plan.focal_runtime else {}
    )
    if frozen_evidence:
        if runtime_evidence is None:
            raise ValueError(
                "V6 launch receipt requires freshly probed runtime evidence"
            )
        require_v6_focal_runtime(
            plan.protocol_spec,
            runtime_evidence,
            expected_evidence=frozen_evidence,
        )
    payload: Dict[str, Any] = {
        "kind": "controlled_v6_official_launch_receipt",
        "schema_version": "2.0",
        "status": "OFFICIAL_RUN_RESERVED",
        "official_run_id": plan.run_id,
        "canonical_out_dir": plan.canonical_out_dir_relative,
        "final_checkpoint_file_sha256": file_sha256(plan.checkpoint_path),
        "final_checkpoint_canonical_sha256": plan.checkpoint_audit[
            "checkpoint_canonical_sha256"
        ],
        "selected_schedule_sha256": plan.schedule[
            "selected_schedule_sha256"
        ],
        "randomization_schedule_sha256": plan.schedule[
            "selected_randomization_schedule_sha256"
        ],
        "validated_bank_sha256": plan.protocol.message_bank_sha256(),
        "model": {"id": plan.model_id, "revision": plan.revision},
        "config_canonical_sha256": _canonical_sha256(plan.config.as_dict()),
        "created_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "launch_nonce": secrets.token_hex(32),
    }
    if frozen_evidence:
        payload["focal_runtime"] = plan.focal_runtime
    payload["receipt_id"] = _canonical_sha256(payload)
    return payload


def audit_official_launch_receipt(
    plan: V6ConfirmatoryPlan,
) -> tuple[Dict[str, Any], Dict[str, Any]]:
    receipt_path = _official_run_paths(plan)["receipt"]
    if not os.path.lexists(receipt_path):
        raise FileNotFoundError(
            "official V6 launch receipt is missing: %s"
            % plan.launch_receipt_relative
        )
    payload = _load_json_object(
        receipt_path, "V6 official launch receipt"
    )
    audit = audit_v6_launch_receipt_payload(
        payload,
        official_run_id=plan.run_id,
        canonical_out_dir=plan.canonical_out_dir_relative,
        checkpoint_file_sha256=file_sha256(plan.checkpoint_path),
        checkpoint_canonical_sha256=plan.checkpoint_audit[
            "checkpoint_canonical_sha256"
        ],
        selected_schedule_sha256=plan.schedule["selected_schedule_sha256"],
        randomization_schedule_sha256=plan.schedule[
            "selected_randomization_schedule_sha256"
        ],
        validated_bank_sha256=plan.protocol.message_bank_sha256(),
        model_id=plan.model_id,
        revision=plan.revision,
        config=plan.config.as_dict(),
        expected_focal_runtime=(plan.focal_runtime or None),
    )
    if audit.get("pass") is not True:
        failed = sorted(
            name for name, passed in audit.get("checks", {}).items() if not passed
        )
        raise ValueError(
            "official V6 launch receipt is not bound to this run: %s"
            % ", ".join(failed)
        )
    if plan.focal_runtime and payload.get("focal_runtime") != plan.focal_runtime:
        raise ValueError(
            "official V6 launch receipt runtime differs from the final checkpoint"
        )
    return payload, audit


def _running_manifest_checks(
    plan: V6ConfirmatoryPlan, existing: Mapping[str, Any]
) -> Dict[str, bool]:
    provider = existing.get("provider", {})
    if not isinstance(provider, Mapping):
        provider = {}
    generation = plan.generation
    return {
        "task_version": existing.get("task_version") == CONTROLLED_V6_VERSION,
        "config": existing.get("config") == plan.config.as_dict(),
        "round_atomic_resume": existing.get("resume_policy")
        == controlled_resume_policy(True),
        "validated_bank": existing.get("message_bank_sha256")
        == plan.protocol.message_bank_sha256(),
        "selection_policy": existing.get("selection_policy")
        == plan.protocol.selection_policy_manifest(),
        "final_checkpoint": existing.get("protocol_provenance")
        == plan.protocol.protocol_provenance_manifest(),
        "provider": provider.get("provider") == "huggingface",
        "model": provider.get("model") == plan.model_id,
        "revision": provider.get("revision") == plan.revision,
        "generation": all(
            provider.get(provider_key) == generation.get(generation_key)
            for provider_key, generation_key in (
                ("temperature", "temperature"),
                ("max_tokens", "max_tokens"),
                ("enable_thinking", "enable_thinking"),
                ("top_p", "top_p"),
                ("top_k", "top_k"),
                ("dtype", "dtype"),
                ("capture", "activation_capture"),
            )
        ),
        "strict_choices": provider.get("constrained_choices")
        == list(STRICT_CHOICES),
        "device_auto": not plan.focal_runtime
        or provider.get("device") == "auto",
        "focal_runtime": not plan.focal_runtime
        or provider.get("focal_runtime_evidence")
        == plan.focal_runtime.get("evidence"),
    }


def _manifest_seal_state(manifest: Mapping[str, Any]) -> str:
    """Classify a completed manifest without tolerating a partial seal."""
    has_receipt = "official_launch_receipt" in manifest
    has_log = "completed_log" in manifest
    if has_receipt != has_log:
        raise ValueError(
            "completed V6 manifest has a partial official seal; refusing recovery"
        )
    return "sealed" if has_receipt else "unsealed"


def _completed_manifest_checks(
    plan: V6ConfirmatoryPlan, manifest: Mapping[str, Any]
) -> Dict[str, bool]:
    return {
        "run_status": manifest.get("run_status") == "completed",
        "n_records": manifest.get("n_records") == plan.expected_n_records,
        "n_episodes": manifest.get("n_episodes") == plan.expected_n_episodes,
        "expected_n_records": manifest.get("expected_n_records")
        == plan.expected_n_records,
        "expected_n_episodes": manifest.get("expected_n_episodes")
        == plan.expected_n_episodes,
    }


def _replay_completed_manifest(
    plan: V6ConfirmatoryPlan,
    manifest: Mapping[str, Any],
    log_path: str,
) -> tuple[list[Dict[str, Any]], list[Dict[str, Any]]]:
    """Fully reconstruct a purportedly complete run from frozen inputs."""
    require_regular_nonsymlink(log_path, label="completed V6 canonical log")
    if not os.path.isfile(log_path):
        raise FileNotFoundError("completed V6 manifest has no canonical log")
    checks = {
        **_running_manifest_checks(plan, manifest),
        **_completed_manifest_checks(plan, manifest),
    }
    if not all(checks.values()):
        failed = sorted(name for name, passed in checks.items() if not passed)
        raise ValueError("completed V6 manifest drifted: %s" % ", ".join(failed))
    records = list(read_jsonl(log_path, root=plan.repository_root))
    replay, reconstructed = reconcile_v6_records_against_runtime(
        records, manifest, plan.config, plan.protocol, plan.run_id
    )
    if replay.get("pass") is not True:
        raise ValueError(
            "completed V6 log failed exact replay: %s"
            % json.dumps(
                {
                    "checks": replay.get("checks"),
                    "first_mismatches": replay.get("mismatches", [])[:3],
                },
                sort_keys=True,
            )
        )
    return records, reconstructed


class _RecordedChoiceProvider(BaseProvider):
    """No-model provider used only to replay a durable V6 JSONL prefix."""

    name = "huggingface"

    def __init__(self, plan: V6ConfirmatoryPlan, outputs: Sequence[str]) -> None:
        self.model = plan.model_id
        self.model_id = plan.model_id
        self._outputs = list(outputs)
        self._index = 0

    def set_next_seed(self, _seed: int) -> None:
        return None

    def generate(self, _prompt: Any) -> str:
        if self._index >= len(self._outputs):
            raise RuntimeError("V6 prefix replay exhausted its recorded choices")
        output = self._outputs[self._index]
        self._index += 1
        return output

    def describe(self) -> Dict[str, Any]:
        return {"provider": self.name, "model": self.model_id}


def _strict_json_equal(left: Any, right: Any) -> bool:
    try:
        return json.dumps(
            left, sort_keys=True, separators=(",", ":"), allow_nan=False
        ) == json.dumps(
            right, sort_keys=True, separators=(",", ":"), allow_nan=False
        )
    except (TypeError, ValueError):
        return False


def _replay_running_prefix(
    plan: V6ConfirmatoryPlan,
    records: Sequence[Mapping[str, Any]],
) -> list[Dict[str, Any]]:
    """Replay a whole-run prefix, including one trailing partial episode."""
    observed = [dict(row) for row in records]
    specs = build_controlled_episode_specs(plan.config)
    expected_coordinates = [
        (spec.episode_id, round_index)
        for spec in specs
        for round_index in range(1, spec.n_rounds + 1)
    ]
    coordinates = [(row.get("episode_id"), row.get("round")) for row in observed]
    if coordinates != expected_coordinates[: len(coordinates)]:
        raise ValueError("V6 resume log is not one exact official round prefix")

    donors = ControlledDonorRegistry()
    reconstructed: list[Dict[str, Any]] = []
    offset = 0
    for spec in specs:
        remaining = len(observed) - offset
        if remaining <= 0:
            break
        count = min(spec.n_rounds, remaining)
        episode_rows = observed[offset : offset + count]
        outputs = [row.get("focal_output_raw") for row in episode_rows]
        if any(type(output) is not str or output not in STRICT_CHOICES for output in outputs):
            raise ValueError("V6 resume log contains a non-strict raw choice")
        provider = _RecordedChoiceProvider(plan, outputs)
        result = run_controlled_episode(
            spec=spec,
            cfg=plan.config,
            agent=ControlledFocalAgent(provider),
            run_id=plan.run_id,
            donors=donors,
            progress=None,
            protocol=plan.protocol,
            end_round=count,
        )
        for row, regenerated in zip(episode_rows, result.records):
            regenerated["timestamp"] = row.get("timestamp")
            if not _strict_json_equal(row, regenerated):
                raise ValueError(
                    "V6 resume log failed exact replay at %s round %s"
                    % (row.get("episode_id"), row.get("round"))
                )
            reconstructed.append(regenerated)
        if spec.condition.name == "full_history" and count == spec.n_rounds:
            donors.add(
                spec.episode_index,
                spec.initial_target_type,
                spec.episode_id,
                result.own_history,
            )
        offset += count
        if count < spec.n_rounds:
            break
    if offset != len(observed):
        raise ValueError("V6 resume log contains records beyond its trailing prefix")
    return reconstructed


def assert_resume_checkpoint_binding(plan: V6ConfirmatoryPlan) -> str:
    """Replay all existing rows before a resumed run may load the model."""
    audit_official_launch_receipt(plan)
    paths = _official_run_paths(plan)
    log_path = paths["log"]
    manifest_path = paths["manifest"]
    if not (os.path.exists(log_path) or os.path.exists(manifest_path)):
        audit_or_recover_round_claim(paths["claim"], [], plan.run_id)
        return "empty"
    require_regular_nonsymlink(
        manifest_path, label="V6 resume manifest", allow_missing=True
    )
    if not os.path.isfile(manifest_path):
        raise FileNotFoundError("cannot resume without manifest %s" % manifest_path)
    existing = _load_json_object(manifest_path, "V6 resume manifest")
    checks = _running_manifest_checks(plan, existing)
    if not all(checks.values()):
        failed = sorted(name for name, passed in checks.items() if not passed)
        raise ValueError(
            "resume is not bound to this V6 final checkpoint: %s"
            % ", ".join(failed)
        )
    run_status = existing.get("run_status")
    if run_status not in {"running", "completed"}:
        raise ValueError("V6 resume manifest has an invalid run status")
    if run_status == "completed":
        _manifest_seal_state(existing)
        completed_records, _ = _replay_completed_manifest(
            plan, existing, log_path
        )
        audit_or_recover_round_claim(
            paths["claim"], completed_records, plan.run_id
        )
        return "completed"

    if "official_launch_receipt" in existing or "completed_log" in existing:
        raise ValueError("running V6 manifest must not contain a completion seal")
    require_regular_nonsymlink(log_path, label="V6 resume log", allow_missing=True)
    if os.path.isfile(log_path):
        records = list(read_jsonl(log_path, root=plan.repository_root))
        if records:
            try:
                _replay_running_prefix(plan, records)
            except (TypeError, ValueError) as exc:
                raise ValueError(
                    "resume log failed frozen schedule/raw-output replay: %s" % exc
                ) from exc
        audit_or_recover_round_claim(paths["claim"], records, plan.run_id)
    elif existing.get("n_records") not in {None, 0}:
        raise ValueError("running V6 manifest claims records but has no log")
    else:
        audit_or_recover_round_claim(paths["claim"], [], plan.run_id)
    return "running"


def claim_official_launch(
    plan: V6ConfirmatoryPlan,
    *,
    resume: bool,
    runtime_evidence: Mapping[str, Any] | None = None,
) -> Dict[str, Any]:
    """Atomically reserve the one canonical official run, or audit its resume."""
    paths = _official_run_paths(plan, create_parents=True)
    log_path = paths["log"]
    manifest_path = paths["manifest"]
    if resume:
        assert_resume_checkpoint_binding(plan)
        return audit_official_launch_receipt(plan)[0]
    if os.path.lexists(paths["receipt"]):
        require_regular_nonsymlink(
            paths["receipt"], label="V6 official launch receipt"
        )
        raise FileExistsError(
            "official V6 run was already claimed; only a bound --resume is allowed"
        )
    if os.path.lexists(log_path) or os.path.lexists(manifest_path):
        raise FileExistsError(
            "canonical V6 output already exists without a launch receipt"
        )
    if os.path.lexists(paths["claim"]):
        raise FileExistsError(
            "canonical V6 in-flight claim exists without a launch receipt"
        )
    receipt = _launch_receipt_payload(
        plan, runtime_evidence=runtime_evidence
    )
    _atomic_create_json(paths["receipt"], receipt)
    audit_official_launch_receipt(plan)
    return receipt


def finalize_official_manifest(
    plan: V6ConfirmatoryPlan,
    log_path: str,
    manifest_path: str,
    receipt: Mapping[str, Any],
) -> Dict[str, Any]:
    """Bind the completed raw JSONL and launch receipt into the final manifest."""
    paths = _official_run_paths(plan)
    expected_log = paths["log"]
    expected_manifest = paths["manifest"]
    if os.path.abspath(log_path) != expected_log or os.path.abspath(
        manifest_path
    ) != expected_manifest:
        raise ValueError("V6 runner returned a non-canonical output path")
    require_regular_nonsymlink(log_path, label="completed V6 canonical log")
    require_regular_nonsymlink(manifest_path, label="completed V6 manifest")
    manifest = _load_json_object(manifest_path, "completed V6 manifest")
    seal_state = _manifest_seal_state(manifest)
    records, reconstructed = _replay_completed_manifest(plan, manifest, log_path)
    receipt_payload, receipt_audit = audit_official_launch_receipt(plan)
    if receipt_payload != receipt:
        raise ValueError("V6 launch receipt changed during execution")
    expected_receipt_seal = {
        "path": plan.launch_receipt_relative,
        "file_sha256": file_sha256(plan.launch_receipt_path),
        "receipt_id": receipt_audit["receipt_id"],
    }
    expected_log_seal = {
        "path": os.path.join(
            plan.canonical_out_dir_relative, plan.run_id + ".jsonl"
        ),
        "file_sha256": file_sha256(log_path),
        "n_records": len(records),
        "reconstructed_records_canonical_sha256": _canonical_sha256(
            reconstructed
        ),
    }
    if seal_state == "sealed":
        checks = {
            "official_launch_receipt": manifest.get("official_launch_receipt")
            == expected_receipt_seal,
            "completed_log": manifest.get("completed_log") == expected_log_seal,
        }
        if not all(checks.values()):
            failed = sorted(name for name, passed in checks.items() if not passed)
            raise ValueError("sealed V6 manifest drifted: %s" % ", ".join(failed))
        return manifest

    manifest["official_launch_receipt"] = expected_receipt_seal
    manifest["completed_log"] = expected_log_seal
    _atomic_replace_json(manifest_path, manifest)
    return manifest


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    add_frozen_contract_arguments(parser)
    parser.add_argument("--device", choices=("auto",), default="auto")
    parser.add_argument(
        "--out-dir",
        default=None,
        help=(
            "optional assertion; if supplied it must be exactly %s"
            % CONFIRMATORY_PATHS["out_dir"]
        ),
    )
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--quiet", action="store_true")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="audit the complete plan without constructing or loading the model",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    plan = prepare_v6_confirmatory_plan(args, out_dir=args.out_dir)
    print("LatentTarget V6 open-weight confirmatory checkpoint")
    print("  official run ID: %s" % plan.run_id)
    print("  model: %s @ %s" % (plan.model_id, plan.revision))
    print("  validated bank: %s" % plan.protocol.message_bank_sha256())
    print("  episode seeds: %d" % plan.selected_episode_seeds)
    print(
        "  episodes: %d; generations: %d"
        % (plan.expected_n_episodes, plan.expected_n_records)
    )
    print("  final checkpoint and exact frozen-plan gates: PASS")
    print("  strict decoding: 1/2/3; activation capture: disabled")
    if args.dry_run:
        print("DRY RUN PASSED: no model constructed, loaded, or queried")
        return 0

    runtime_evidence: Mapping[str, Any] | None = None
    if plan.focal_runtime:
        runtime_evidence = collect_focal_runtime_evidence(device=args.device)
        require_v6_focal_runtime(
            plan.protocol_spec,
            runtime_evidence,
            expected_evidence=plan.focal_runtime.get("evidence", {}),
            device_argument=args.device,
        )

    paths = _official_run_paths(plan, create_parents=True)
    with ExclusiveFileLock(
        paths["lock"],
        label="official V6 confirmatory run",
        metadata={"run_id": plan.run_id},
    ):
        receipt = claim_official_launch(
            plan,
            resume=args.resume,
            runtime_evidence=runtime_evidence,
        )
        if args.resume and os.path.isfile(paths["manifest"]):
            existing = _load_json_object(paths["manifest"], "V6 resume manifest")
            if existing.get("run_status") == "completed":
                was_sealed = _manifest_seal_state(existing) == "sealed"
                sealed = finalize_official_manifest(
                    plan, paths["log"], paths["manifest"], receipt
                )
                action = "verified" if was_sealed else "recovered and sealed"
                print(
                    "%s completed official V6 run without loading or querying the model"
                    % action
                )
                print(
                    "wrote %d rows to %s"
                    % (plan.expected_n_records, paths["log"])
                )
                print("manifest: %s" % paths["manifest"])
                if sealed.get("completed_log", {}).get("n_records") != (
                    plan.expected_n_records
                ):
                    raise RuntimeError("finalized V6 manifest has an invalid row count")
                return 0
        provider = make_confirmatory_provider(
            plan,
            device=args.device,
            runtime_evidence=runtime_evidence,
        )
        progress = None if args.quiet else (lambda message: print(message, flush=True))
        result = run_controlled_experiment(
            plan.config,
            run_id=plan.run_id,
            provider=provider,
            progress=progress,
            resume=args.resume,
            protocol=plan.protocol,
            round_atomic=True,
            in_flight_path=paths["claim"],
            artifact_root=plan.repository_root,
        )
        finalize_official_manifest(
            plan, result.log_path, result.manifest_path, receipt
        )
        print("wrote %d rows to %s" % (result.n_records, result.log_path))
        print("manifest: %s" % result.manifest_path)
        return 0


if __name__ == "__main__":
    sys.exit(main())
