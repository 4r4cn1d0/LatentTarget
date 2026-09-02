#!/usr/bin/env python3
"""Run final V6 target-free pool screening or selected-bank validation."""

from __future__ import annotations

import _bootstrap  # noqa: F401
import argparse
import json
import os
import stat
import sys
import tempfile

from src.controlled_v6_messages import V6TriadBank
from src.hf_provider import HuggingFaceProvider, collect_focal_runtime_evidence
from src.file_lock import (
    ExclusiveFileLock,
    require_directory_nonsymlink,
    require_regular_nonsymlink,
)
from src.v6_calibration import (
    V6_POOL_MODE,
    V6_VALIDATION_MODE,
    audit_v6_pool_schedule,
    audit_v6_validation_schedule,
    build_v6_pool_schedule,
    build_v6_validation_schedule,
    file_sha256,
    preflight_v6_target_free_calibration,
    run_v6_target_free_calibration,
)
from src.v6_protocol_gate import (
    audit_v6_calibration_plan,
    audit_v6_prevalidation_checkpoint,
    build_v6_calibration_launch_receipt,
    require_v6_focal_runtime,
    v6_artifact_reference,
)
from src.logging_utils import strict_json_load


def _frozen_repo_path(relative_path: object, label: str) -> str:
    if not isinstance(relative_path, str) or not relative_path.strip():
        raise ValueError("V6 protocol has no %s" % label)
    if os.path.isabs(relative_path) or os.path.normpath(relative_path).startswith(
        os.pardir
    ):
        raise ValueError("V6 %s must be repository-relative" % label)
    root = os.path.realpath(_bootstrap.ROOT)
    normalized = os.path.normpath(relative_path)
    path = os.path.abspath(os.path.join(root, normalized))
    if os.path.commonpath([path, root]) != root:
        raise ValueError("V6 %s leaves the repository root" % label)
    cursor = root
    for component in os.path.relpath(path, root).split(os.sep):
        if component in ("", os.curdir):
            continue
        cursor = os.path.join(cursor, component)
        if os.path.lexists(cursor) and os.path.islink(cursor):
            raise ValueError("V6 %s must not traverse a symlink" % label)
    return path


def _json_exact(left, right) -> bool:
    try:
        return json.dumps(
            left,
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        ) == json.dumps(
            right,
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError):
        return False


def _fsync_parent(path: str) -> None:
    descriptor = None
    try:
        descriptor = os.open(os.path.dirname(os.path.abspath(path)), os.O_RDONLY)
        os.fsync(descriptor)
    except OSError:
        pass
    finally:
        if descriptor is not None:
            os.close(descriptor)


def _write_atomic_launch_receipt(path: str, payload: dict) -> bool:
    """Claim once, or accept the exact existing claim for a safe resume.

    Returns ``True`` only when this invocation created the receipt. A second
    invocation never rewrites it and rejects any foreign receipt content.
    """
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
        require_directory_nonsymlink(
            parent, label="V6 calibration launch-receipt directory"
        )

    def validate_existing() -> bool:
        require_regular_nonsymlink(
            path, label="V6 calibration launch receipt"
        )
        flags = os.O_RDONLY
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        try:
            descriptor = os.open(path, flags)
            if not stat.S_ISREG(os.fstat(descriptor).st_mode):
                os.close(descriptor)
                raise ValueError(
                    "V6 calibration launch receipt is not a regular file"
                )
            with os.fdopen(descriptor, "r", encoding="utf-8") as handle:
                existing = strict_json_load(handle)
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise ValueError("V6 calibration launch receipt is unreadable") from exc
        if not _json_exact(existing, payload):
            raise ValueError(
                "existing V6 calibration launch receipt belongs to a foreign run/config"
            )
        return False

    if os.path.lexists(path):
        return validate_existing()
    descriptor, temporary = tempfile.mkstemp(
        prefix=".%s.tmp." % os.path.basename(path), dir=parent or os.curdir
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=False, allow_nan=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        try:
            # Hard-link publication is atomic and fails rather than replacing
            # a receipt claimed by a concurrent launcher.
            os.link(temporary, path)
        except FileExistsError:
            return validate_existing()
        _fsync_parent(path)
        return True
    finally:
        if os.path.lexists(temporary):
            os.unlink(temporary)


def _expected_hf_provider_description(
    *,
    model: str,
    revision: str,
    generation: dict,
    dtype: str,
    seed: int,
    runtime_evidence: dict | None = None,
) -> dict:
    """Build the lazy provider's frozen description without constructing it."""
    description = {
        "provider": "huggingface",
        "model": model,
        "revision": revision,
        "temperature": generation["temperature"],
        "max_tokens": generation["max_tokens"],
        "dtype": dtype,
        "layer_stride": 1,
        "capture": False,
        "torch_seed_base": seed,
        "enable_thinking": generation["enable_thinking"],
        "top_p": generation["top_p"],
        "top_k": generation["top_k"],
        "architecture": None,
        "loaded_with": None,
        "processor": None,
        "per_generation_seed_supported": True,
        "constrained_choices": list(generation["constrained_choices"]),
        "invalid_output_policy": "provider error; no fallback",
    }
    if runtime_evidence is not None:
        description["device"] = "auto"
        description["focal_runtime_evidence"] = json.loads(
            json.dumps(runtime_evidence, allow_nan=False)
        )
    return description


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bank", required=True)
    parser.add_argument(
        "--protocol-spec",
        default=os.path.join(_bootstrap.ROOT, "docs", "v6_calibration_protocol.json"),
    )
    parser.add_argument(
        "--mode", choices=(V6_POOL_MODE, V6_VALIDATION_MODE), required=True
    )
    parser.add_argument("--model", default=None)
    parser.add_argument("--revision", default=None)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--out-dir", default=None)
    parser.add_argument("--episode-blocks", type=int, default=None)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--dtype", default=None)
    parser.add_argument("--device", choices=("auto",), default="auto")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--pre-validation-checkpoint",
        default=None,
        help="required immutable artifact graph for selected-bank validation",
    )
    args = parser.parse_args(argv)

    with open(args.protocol_spec, "r", encoding="utf-8") as handle:
        spec = strict_json_load(handle)
    schedule_key = (
        "pool_screening_schedule"
        if args.mode == V6_POOL_MODE
        else "selected_bank_validation_schedule"
    )
    schedule_spec = spec[schedule_key]
    canonical_out_dir = _frozen_repo_path(
        schedule_spec.get("canonical_out_dir"), "canonical calibration output directory"
    )
    if args.out_dir is not None:
        supplied_out_dir = os.path.abspath(
            args.out_dir
            if os.path.isabs(args.out_dir)
            else os.path.join(_bootstrap.ROOT, args.out_dir)
        )
        if supplied_out_dir != canonical_out_dir:
            raise ValueError(
                "V6 calibration output must equal the single frozen canonical directory"
            )
    out_dir = canonical_out_dir
    launch_receipt_path = _frozen_repo_path(
        schedule_spec.get("launch_receipt_path"), "calibration launch receipt path"
    )
    official_run_id = schedule_spec.get("official_run_id")
    if not isinstance(official_run_id, str) or args.run_id != official_run_id:
        raise ValueError(
            "V6 run-id must equal the single official run-id frozen in the protocol"
        )
    generation = spec["generation"]
    primary_model = spec["primary_model"]
    model = args.model or primary_model["id"]
    revision = args.revision or primary_model["revision"]
    seed = args.seed if args.seed is not None else int(schedule_spec["seed"])
    # V6 enumerates complete triad × scenario × permutation schedules, so an
    # episode-block count is deliberately absent (JSON null).  Retain the CLI
    # option only as a rejected compatibility surface; it must not alter the
    # frozen schedule.
    episode_blocks = args.episode_blocks
    dtype = args.dtype or generation["dtype"]
    bank = V6TriadBank.load(args.bank)
    prevalidation_checkpoint = None
    prevalidation_reference = None
    prevalidation_runtime_evidence = None
    if args.mode == V6_VALIDATION_MODE:
        if args.pre_validation_checkpoint is None:
            raise ValueError(
                "selected-bank validation requires a frozen pre-validation checkpoint"
            )
        with open(args.pre_validation_checkpoint, "r", encoding="utf-8") as handle:
            prevalidation_checkpoint = strict_json_load(handle)
        prevalidation_audit = audit_v6_prevalidation_checkpoint(
            prevalidation_checkpoint, _bootstrap.ROOT
        )
        if not prevalidation_audit["pass"]:
            failed = sorted(
                name
                for name, passed in prevalidation_audit["checks"].items()
                if not passed
            )
            raise ValueError(
                "V6 pre-validation checkpoint audit failed: %s"
                % ", ".join(failed)
            )
        if prevalidation_audit.get("pending_bank_sha256") != bank.sha256():
            raise ValueError("validation bank differs from the frozen pending bank")
        prevalidation_runtime_evidence = prevalidation_audit.get(
            "focal_runtime_evidence"
        )
        prevalidation_reference = v6_artifact_reference(
            args.pre_validation_checkpoint, _bootstrap.ROOT
        )
    elif args.pre_validation_checkpoint is not None:
        raise ValueError("pool screening must not consume a validation checkpoint")
    if args.mode == V6_POOL_MODE and not bank.payload.get(
        "candidate_text_authored_before_v6_focal_calibration"
    ):
        raise ValueError("pool screening requires a bank authored before outcomes")
    if args.mode == V6_VALIDATION_MODE and bank.payload.get("status") != (
        "selected_bank_pending_no_history_validation"
    ):
        raise ValueError("selected-bank validation requires a pending selected bank")
    expected_provider = _expected_hf_provider_description(
        model=model,
        revision=revision,
        generation=generation,
        dtype=dtype,
        seed=seed,
    )
    plan_audit = audit_v6_calibration_plan(
        spec=spec,
        bank=bank,
        provider=expected_provider,
        mode=args.mode,
        seed=seed,
        n_episode_blocks=episode_blocks,
        repository_root=_bootstrap.ROOT,
        prevalidation_checkpoint=prevalidation_checkpoint,
        run_id=args.run_id,
        require_runtime_evidence=False,
    )
    if not plan_audit["pass"]:
        failed = sorted(
            name for name, passed in plan_audit["checks"].items() if not passed
        )
        raise ValueError(
            "planned V6 calibration differs from frozen protocol: %s"
            % ", ".join(failed)
        )
    if args.mode == V6_POOL_MODE:
        schedule = build_v6_pool_schedule(bank, seed=seed)
        audit = audit_v6_pool_schedule(schedule, bank)
    else:
        schedule = build_v6_validation_schedule(bank, seed=seed)
        audit = audit_v6_validation_schedule(schedule, bank)
    print("LatentTarget V6 target-free calibration")
    print("  mode: %s" % args.mode)
    print("  model: %s @ %s" % (model, revision))
    print("  bank SHA-256: %s" % bank.sha256())
    print("  prompts: %d; target/history: absent" % len(schedule))
    print("  schedule audit: %s" % ("PASS" if audit["pass"] else "FAIL"))
    print("  frozen calibration protocol: PASS")
    if not audit["pass"]:
        raise ValueError("V6 calibration schedule audit failed")
    if args.dry_run:
        print("DRY RUN PASSED: no model loaded and no outcomes generated")
        return 0
    runtime_evidence = collect_focal_runtime_evidence(device=args.device)
    runtime_audit = require_v6_focal_runtime(
        spec,
        runtime_evidence,
        expected_evidence=prevalidation_runtime_evidence,
        device_argument=args.device,
    )
    expected_provider = _expected_hf_provider_description(
        model=model,
        revision=revision,
        generation=generation,
        dtype=dtype,
        seed=seed,
        runtime_evidence=runtime_evidence,
    )
    plan_audit = audit_v6_calibration_plan(
        spec=spec,
        bank=bank,
        provider=expected_provider,
        mode=args.mode,
        seed=seed,
        n_episode_blocks=episode_blocks,
        repository_root=_bootstrap.ROOT,
        prevalidation_checkpoint=prevalidation_checkpoint,
        run_id=args.run_id,
        require_runtime_evidence=True,
    )
    if not plan_audit["pass"]:
        failed = sorted(
            name for name, passed in plan_audit["checks"].items() if not passed
        )
        raise ValueError(
            "V6 runtime-bound calibration plan failed: %s" % ", ".join(failed)
        )
    launch_receipt = build_v6_calibration_launch_receipt(
        protocol=spec,
        protocol_path=args.protocol_spec,
        bank=bank,
        mode=args.mode,
        repository_root=_bootstrap.ROOT,
        prevalidation_reference=prevalidation_reference,
        runtime_evidence=runtime_evidence,
    )
    log_path = os.path.join(out_dir, args.run_id + ".jsonl")
    manifest_path = os.path.join(out_dir, args.run_id + ".manifest.json")
    sample_dir = os.path.join(out_dir, args.run_id + ".samples")
    claim_path = os.path.join(out_dir, args.run_id + ".inflight.json")
    lock_path = os.path.join(out_dir, args.run_id + ".lock")
    if not os.path.lexists(launch_receipt_path) and any(
        os.path.lexists(path)
        for path in (log_path, manifest_path, sample_dir, claim_path, lock_path)
    ):
        raise ValueError(
            "V6 calibration outputs exist without the canonical launch receipt"
        )
    receipt_created = _write_atomic_launch_receipt(
        launch_receipt_path, launch_receipt
    )
    provenance = {
        "protocol_path": os.path.abspath(args.protocol_spec),
        "protocol_file_sha256": file_sha256(args.protocol_spec),
        "plan_audit": plan_audit,
        "focal_runtime": runtime_audit,
        "single_launch_receipt": v6_artifact_reference(
            launch_receipt_path, _bootstrap.ROOT
        ),
        **(
            {"prevalidation_checkpoint": prevalidation_reference}
            if prevalidation_reference is not None
            else {}
        ),
    }
    # The lock covers prefix inspection, model construction, and every paid
    # generation. A concurrent exact launcher can audit the receipt but fails
    # before loading a second model or consuming a coordinate.
    with ExclusiveFileLock(
        lock_path,
        label="V6 calibration CLI run",
        metadata={"run_id": args.run_id, "mode": args.mode},
    ):
        # This is deliberately before provider construction: an interrupted
        # run's exact prefix, sample hashes, receipt, and frozen configuration
        # must all pass before a model can be loaded or queried again.
        preflight = preflight_v6_target_free_calibration(
            bank=bank,
            provider_description=expected_provider,
            run_id=args.run_id,
            out_dir=out_dir,
            seed=seed,
            mode=args.mode,
            n_episode_blocks=episode_blocks,
            provenance=provenance,
            _lock_held=True,
        )
        print(
            "  launch receipt: %s"
            % ("CLAIMED" if receipt_created else "EXACT RESUME")
        )
        print(
            "  durable prefix: %d/%d"
            % (len(preflight["records"]), len(preflight["schedule"]))
        )
        if preflight["state"] == "completed":
            print("OFFICIAL RUN ALREADY COMPLETED: full audit PASS; no model loaded")
            return 0
        provider = HuggingFaceProvider(
            model=model,
            revision=revision,
            temperature=generation["temperature"],
            max_tokens=generation["max_tokens"],
            device=args.device,
            dtype=dtype,
            capture=False,
            seed=seed,
            enable_thinking=generation["enable_thinking"],
            top_p=generation["top_p"],
            top_k=generation["top_k"],
            constrained_choices=tuple(generation["constrained_choices"]),
        )
        bind_runtime = getattr(provider, "bind_runtime_evidence", None)
        if not callable(bind_runtime):
            raise RuntimeError("V6 provider cannot bind focal runtime evidence")
        bind_runtime(runtime_evidence)
        if not _json_exact(provider.describe(), expected_provider):
            raise RuntimeError("constructed provider differs from frozen preflight metadata")
        result = run_v6_target_free_calibration(
            bank=bank,
            provider=provider,
            run_id=args.run_id,
            out_dir=out_dir,
            seed=seed,
            mode=args.mode,
            n_episode_blocks=episode_blocks,
            provenance=provenance,
            _lock_held=True,
        )
    print("wrote %d records to %s" % (len(result["records"]), result["log_path"]))
    print("manifest: %s" % result["manifest_path"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
