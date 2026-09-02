"""Adversarial coverage for the V6 pre-validation and final checkpoints."""

from __future__ import annotations

import importlib.util
import json
import shutil
from copy import deepcopy
from pathlib import Path

import pytest
import src.v6_protocol_gate as v6_protocol_gate_module

from config import CONTROLLED_V6_VERSION, STRATEGIES
from src.controlled_focal_agent import build_controlled_prompt
from src.controlled_v6_messages import V6TriadBank, make_v6_protocol
from src.v6_calibration import (
    V6_CALIBRATION_VERSION,
    V6_POOL_MODE,
    V6_VALIDATION_MODE,
    _message_candidates,
    _scenario_proxy,
    audit_v6_calibration_run,
    bank_content_sha256,
    build_v6_pool_schedule,
    build_v6_validation_schedule,
    evaluate_v6_bank_validation,
    file_sha256,
    finalize_validated_v6_bank,
    select_v6_bank,
)
from src.v6_protocol_gate import (
    V6_CONFIRMATORY_SOURCE_PATHS,
    V6_PREVALIDATION_SOURCE_PATHS,
    audit_v6_calibration_plan,
    audit_v6_final_checkpoint,
    audit_v6_prevalidation_checkpoint,
    build_v6_calibration_launch_receipt,
    build_v6_confirmatory_schedule_metadata,
    build_v6_final_checkpoint,
    v6_artifact_reference,
)


ROOT = Path(__file__).parents[1]
SOURCE_POOL = ROOT / "data" / "v6" / "v6_triad_pool_v1.json"
SOURCE_PROTOCOL = ROOT / "docs" / "v6_calibration_protocol.json"
POOL_RUN_ID = "v6_pool_screening_qwen38_27b_20260902"
VALIDATION_RUN_ID = "v6_bank_validation_qwen38_27b_20260902"
CONFIRMATORY_RUN_ID = "qwen38_27b_v6_confirmatory_20260902"
SYNTHETIC_FOCAL_RUNTIME = {
    "evidence_version": "v6-focal-runtime-evidence-1.0",
    "requested_device": "auto",
    "resolved_device_type": "cuda",
    "python": {
        "implementation": "CPython",
        "version": "3.12.11",
        "version_info": [3, 12, 11],
    },
    "packages": {
        "numpy": "2.3.4",
        "torch": "2.9.1+cu128",
        "torchvision": "0.24.1+cu128",
        "torchaudio": "2.9.1+cu128",
        "transformers": "5.16.1",
        "accelerate": "1.14.0",
        "sentencepiece": "0.2.1",
    },
    "module_versions": {
        "numpy": "2.3.4",
        "torch": "2.9.1+cu128",
        "transformers": "5.16.1",
        "accelerate": "1.14.0",
    },
    "cuda": {
        "available": True,
        "torch_build_version": "12.8",
        "runtime_version": 12080,
        "device_count": 1,
        "bfloat16_supported": True,
    },
    "devices": [
        {
            "index": 0,
            "name": "NVIDIA A100-SXM4-80GB",
            "compute_capability": [8, 0],
            "total_memory_bytes": 85_056_798_720,
        }
    ],
}


def _write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, allow_nan=False),
        encoding="utf-8",
    )


def _write_jsonl(path: Path, rows) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(
            json.dumps(row, sort_keys=True, ensure_ascii=False, allow_nan=False)
            + "\n"
            for row in rows
        ),
        encoding="utf-8",
    )


def _provider(protocol, seed):
    return {
        "provider": "huggingface",
        "model": protocol["primary_model"]["id"],
        "revision": protocol["primary_model"]["revision"],
        "temperature": protocol["generation"]["temperature"],
        "top_p": protocol["generation"]["top_p"],
        "top_k": protocol["generation"]["top_k"],
        "max_tokens": protocol["generation"]["max_tokens"],
        "dtype": protocol["generation"]["dtype"],
        "enable_thinking": False,
        "capture": False,
        "constrained_choices": ["1", "2", "3"],
        "torch_seed_base": seed,
        "device": "auto",
        "focal_runtime_evidence": deepcopy(SYNTHETIC_FOCAL_RUNTIME),
    }


def _balanced_records(schedule, mode, run_id):
    records = []
    for row in schedule:
        dominant = (int(row["triad_index"]) + int(row["scenario_index"])) % 3
        permutation_index = int(row["permutation_index"])
        if permutation_index < 3:
            frame_index = dominant
        elif permutation_index < 5:
            frame_index = (dominant + 1) % 3
        else:
            frame_index = (dominant + 2) % 3
        selected_frame = STRATEGIES[frame_index]
        selected = next(
            candidate
            for candidate in row["candidates"]
            if candidate["frame"] == selected_frame
        )
        prompt = build_controlled_prompt(
            scenario=_scenario_proxy(row["scenario"]),
            candidates=_message_candidates(row),
            history=[],
            round_index=int(row["round"]),
            n_rounds=24,
            show_history=False,
            focal_mode="spontaneous",
            context={},
        )
        records.append(
            {
                **row,
                "run_id": run_id,
                "mode": mode,
                "selection_valid": True,
                "fallback_used": False,
                "focal_output_raw": str(selected["slot"]),
                "selected_slot": selected["slot"],
                "selected_frame": selected_frame,
                "selected_candidate_id": selected["candidate_id"],
                "selected_pool_candidate_id": selected["pool_candidate_id"],
                "focal_system_prompt": prompt.system,
                "focal_user_prompt": prompt.user,
            }
        )
    return records


def _manifest(bank, protocol, provider, records, mode, run_id, seed, log_path):
    schedule_audit = (
        "pool_screening_schedule"
        if mode == V6_POOL_MODE
        else "selected_bank_validation_schedule"
    )
    return {
        "calibration_version": V6_CALIBRATION_VERSION,
        "task_version": CONTROLLED_V6_VERSION,
        "mode": mode,
        "run_id": run_id,
        "run_status": "completed",
        "target_simulator_present": False,
        "history_present": False,
        "pool_sha256": bank.sha256(),
        "bank_content_sha256": bank_content_sha256(bank.payload),
        "bank_source": bank.source_path,
        "provider": provider,
        "schedule": {
            "seed": seed,
            "n_records": len(records),
            "n_episode_blocks": None,
            "n_rounds": 24,
            "heldout_start_round": 19,
            "protocol_section": schedule_audit,
        },
        "n_records": len(records),
        "valid_selection_rate": 1.0,
        "log_file_sha256": file_sha256(str(log_path)),
    }


def _load_script(monkeypatch, filename, module_name):
    script = ROOT / "scripts" / filename
    monkeypatch.syspath_prepend(str(script.parent))
    spec = importlib.util.spec_from_file_location(module_name, script)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_v6_checkpoint_chain_replays_selection_validation_and_run_identity(
    tmp_path, monkeypatch
):
    def fake_judge_replay(summary, _pool, _root):
        return {
            "ok": True,
            "pass": summary.get("pass") is True,
            "recomputed_evaluation_sha256": summary.get(
                "recomputed_evaluation_sha256"
            ),
        }

    def fake_power_replay(payload, require_official=True):
        assert require_official is True
        selected = payload.get("selected_episode_seeds")
        return {
            "audit_pass": True,
            "schema_version": "synthetic-power-replay",
            "official": True,
                "status": "PASS_V6_PROSPECTIVE_BUNDLE_POWER",
            "scientific_power_pass": True,
            "power_selection_pass": True,
            "null_type_i_pass": True,
            "selected_episode_seeds": selected,
            "forbidden_outcome_flags": {
                "focal_model_outcomes_used": False,
                "confirmatory_outcomes_used": False,
                "selected_bank_validation_outputs_used": False,
            },
        }

    monkeypatch.setattr(
        v6_protocol_gate_module,
        "audit_v6_semantic_validation_summary",
        fake_judge_replay,
    )
    monkeypatch.setattr(
        v6_protocol_gate_module,
        "audit_v6_quality_validation_summary",
        fake_judge_replay,
    )
    monkeypatch.setattr(
        v6_protocol_gate_module,
        "audit_v6_power_payload",
        fake_power_replay,
    )
    for relative_path in sorted(
        set(V6_PREVALIDATION_SOURCE_PATHS) | set(V6_CONFIRMATORY_SOURCE_PATHS)
    ):
        source = ROOT / relative_path
        destination = tmp_path / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
    pool_path = tmp_path / "artifacts" / "pool.json"
    pool_path.parent.mkdir(parents=True)
    shutil.copyfile(SOURCE_POOL, pool_path)
    pool = V6TriadBank.load(str(pool_path))
    protocol = json.loads(SOURCE_PROTOCOL.read_text(encoding="utf-8"))
    triad_ids = [
        triad["triad_id"]
        for split in ("development", "heldout")
        for triad in pool.payload["splits"][split]
    ]
    semantic = {
        "pass": True,
        "pool_sha256": pool.sha256(),
        "eligible_triad_ids": triad_ids,
        "primary_judge": {"model": "gpt-5.6-sol"},
        "sensitivity_judge": {"model": "gpt-5.6-luna"},
        "judge_contract": {
            **protocol["semantic_validation"]["judge_contract"],
            "kind": "semantic",
            "enforced": True,
        },
        "raw_judge_run_manifests": {
            "primary": {"manifest_sha256": "synthetic-semantic-primary"},
            "sensitivity": {
                "manifest_sha256": "synthetic-semantic-sensitivity"
            },
        },
        "recomputed_evaluation_sha256": "synthetic-semantic-evaluation",
    }
    quality = deepcopy(semantic)
    quality["judge_contract"] = {
        **protocol["quality_validation"]["judge_contract"],
        "kind": "quality",
        "enforced": True,
    }
    quality["raw_judge_run_manifests"] = {
        "primary": {"manifest_sha256": "synthetic-quality-primary"},
        "sensitivity": {
            "manifest_sha256": "synthetic-quality-sensitivity"
        },
    }
    quality["recomputed_evaluation_sha256"] = "synthetic-quality-evaluation"
    semantic_path = tmp_path / "artifacts" / "semantic.json"
    quality_path = tmp_path / "artifacts" / "quality.json"
    _write_json(semantic_path, semantic)
    _write_json(quality_path, quality)
    synthetic_measurement_paths = deepcopy(
        v6_protocol_gate_module.V6_CANONICAL_MEASUREMENT_PATHS
    )
    synthetic_measurement_paths["semantic"]["summary"] = str(
        semantic_path.relative_to(tmp_path)
    )
    synthetic_measurement_paths["quality"]["summary"] = str(
        quality_path.relative_to(tmp_path)
    )
    monkeypatch.setattr(
        v6_protocol_gate_module,
        "V6_CANONICAL_MEASUREMENT_PATHS",
        synthetic_measurement_paths,
    )

    protocol["status"] = (
        "SEMANTIC_AND_QUALITY_GATES_PASSED_READY_FOR_PAID_POOL_SCREENING"
    )
    protocol["pool_screening_schedule"]["official_run_id"] = POOL_RUN_ID
    protocol["selected_bank_validation_schedule"][
        "official_run_id"
    ] = VALIDATION_RUN_ID
    protocol["confirmatory_design"]["official_run_id"] = CONFIRMATORY_RUN_ID
    protocol["candidate_pool"].update(
        {
            "path": str(pool_path.relative_to(tmp_path)),
            "sha256": pool.sha256(),
            "file_sha256": file_sha256(str(pool_path)),
        }
    )
    for key, path, payload in (
        ("semantic_validation", semantic_path, semantic),
        ("quality_validation", quality_path, quality),
    ):
        protocol[key].update(
            {
                "path": str(path.relative_to(tmp_path)),
                "file_sha256": file_sha256(str(path)),
                "canonical_sha256": v6_artifact_reference(
                    str(path), str(tmp_path)
                )["canonical_sha256"],
            }
        )
    protocol_path = tmp_path / "artifacts" / "protocol.json"
    _write_json(protocol_path, protocol)
    power_design = protocol["power_design"]
    power_contract = power_design["contract"]
    selected_episode_seeds = 24
    power = {
        "status": "PASS_V6_PROSPECTIVE_BUNDLE_POWER",
        "pass": True,
        "power_selection_pass": True,
        "null_type_i_pass": True,
        "focal_model_outcomes_used": False,
        "confirmatory_outcomes_used": False,
        "selected_bank_validation_outputs_used": False,
        "contract": power_contract,
        "episode_seed_grid": power_contract["power"]["n_grid"],
        "n_sim_per_cell": power_contract["power"][
            "official_simulations_per_cell_minimum"
        ],
        "simulation_seed": power_contract["simulation"]["power_rng_root"],
        "selected_episode_seeds": selected_episode_seeds,
    }
    power_path = tmp_path / "artifacts" / "power.json"
    _write_json(power_path, power)

    pool_seed = int(protocol["pool_screening_schedule"]["seed"])
    pool_records = _balanced_records(
        build_v6_pool_schedule(pool, seed=pool_seed), V6_POOL_MODE, POOL_RUN_ID
    )
    pool_log_path = tmp_path / "artifacts" / "pool.jsonl"
    _write_jsonl(pool_log_path, pool_records)
    pool_provider = _provider(protocol, pool_seed)
    pool_plan = audit_v6_calibration_plan(
        protocol,
        pool,
        pool_provider,
        V6_POOL_MODE,
        pool_seed,
        None,
        str(tmp_path),
        run_id=POOL_RUN_ID,
    )
    assert pool_plan["pass"] is True
    pool_manifest = _manifest(
        pool,
        protocol,
        pool_provider,
        pool_records,
        V6_POOL_MODE,
        POOL_RUN_ID,
        pool_seed,
        pool_log_path,
    )
    pool_receipt_path = tmp_path / "artifacts" / "pool-launch-receipt.json"
    _write_json(
        pool_receipt_path,
        build_v6_calibration_launch_receipt(
            protocol=protocol,
            protocol_path=str(protocol_path),
            bank=pool,
            mode=V6_POOL_MODE,
            repository_root=str(tmp_path),
            runtime_evidence=pool_provider["focal_runtime_evidence"],
        ),
    )
    pool_manifest["frozen_protocol"] = {
        "plan_audit": pool_plan,
        "focal_runtime": v6_protocol_gate_module.require_v6_focal_runtime(
            protocol, pool_provider["focal_runtime_evidence"]
        ),
        "single_launch_receipt": v6_artifact_reference(
            str(pool_receipt_path), str(tmp_path)
        ),
    }
    pool_manifest_path = tmp_path / "artifacts" / "pool.manifest.json"
    _write_json(pool_manifest_path, pool_manifest)
    pool_run_audit = audit_v6_calibration_run(
        pool_records, pool_manifest, pool, V6_POOL_MODE
    )
    assert pool_run_audit["pass"] is True

    pending_payload, selection = select_v6_bank(
        pool, pool_records, semantic, quality
    )
    assert pending_payload is not None
    selection["calibration_run_audit"] = pool_run_audit
    selection["calibration_manifest_file_sha256"] = file_sha256(
        str(pool_manifest_path)
    )
    selection["calibration_log_file_sha256"] = file_sha256(str(pool_log_path))
    pending_path = tmp_path / "artifacts" / "pending.json"
    selection_path = tmp_path / "artifacts" / "selection.json"
    _write_json(pending_path, pending_payload)
    _write_json(selection_path, selection)

    freeze_cli = _load_script(
        monkeypatch,
        "freeze_v6_validation_checkpoint.py",
        "freeze_v6_validation_checkpoint_test",
    )
    freeze_cli._bootstrap.ROOT = str(tmp_path)
    prevalidation_path = tmp_path / "artifacts" / "prevalidation.json"
    assert (
        freeze_cli.main(
            [
                "--calibration-protocol",
                str(protocol_path),
                "--source-pool",
                str(pool_path),
                "--semantic-validation",
                str(semantic_path),
                "--quality-validation",
                str(quality_path),
                "--prevalidation-power",
                str(power_path),
                "--pool-calibration-log",
                str(pool_log_path),
                "--pool-calibration-manifest",
                str(pool_manifest_path),
                "--selection-report",
                str(selection_path),
                "--pending-bank",
                str(pending_path),
                "--out",
                str(prevalidation_path),
            ]
        )
        == 0
    )
    prevalidation = json.loads(prevalidation_path.read_text(encoding="utf-8"))
    prevalidation_audit = audit_v6_prevalidation_checkpoint(
        prevalidation, str(tmp_path)
    )
    assert prevalidation_audit["pass"] is True

    # The source closure is deliberately exhaustive. A dependency that the
    # earlier hand-written list omitted must now invalidate the checkpoint.
    transitive_dependency = tmp_path / "src" / "controlled_messages.py"
    original_dependency = transitive_dependency.read_text(encoding="utf-8")
    transitive_dependency.write_text(
        original_dependency + "\n# synthetic post-freeze drift\n",
        encoding="utf-8",
    )
    dependency_drift_audit = audit_v6_prevalidation_checkpoint(
        prevalidation, str(tmp_path)
    )
    assert dependency_drift_audit["pass"] is False
    assert dependency_drift_audit["checks"][
        "source_code_src/controlled_messages.py_hash"
    ] is False
    transitive_dependency.write_text(original_dependency, encoding="utf-8")
    assert audit_v6_prevalidation_checkpoint(
        prevalidation, str(tmp_path)
    )["pass"] is True

    # Make an edited pending bank and selection report internally self-consistent.
    # Replaying selection must still recover the original objects and reject it.
    edited_payload = deepcopy(pending_payload)
    edited_candidate = edited_payload["splits"]["development"][0]["candidates"][
        "fairness"
    ]
    edited_candidate["template"] = edited_candidate["template"].replace(".", "!", 1)
    edited_path = tmp_path / "artifacts" / "edited-pending.json"
    _write_json(edited_path, edited_payload)
    edited_bank = V6TriadBank.load(str(edited_path))
    edited_selection = deepcopy(selection)
    edited_selection["selected_bank_sha256"] = edited_bank.sha256()
    edited_selection["selected_bank_content_sha256"] = bank_content_sha256(
        edited_payload
    )
    edited_selection_path = tmp_path / "artifacts" / "edited-selection.json"
    _write_json(edited_selection_path, edited_selection)
    edited_checkpoint = deepcopy(prevalidation)
    edited_checkpoint["pending_bank"] = {
        **v6_artifact_reference(str(edited_path), str(tmp_path)),
        "bank_sha256": edited_bank.sha256(),
        "bank_content_sha256": bank_content_sha256(edited_payload),
    }
    edited_checkpoint["selection_report"] = v6_artifact_reference(
        str(edited_selection_path), str(tmp_path)
    )
    edited_checkpoint["confirmatory_schedule"] = (
        build_v6_confirmatory_schedule_metadata(
            protocol,
            edited_bank,
            selected_episode_seeds=selected_episode_seeds,
        )
    )
    edited_audit = audit_v6_prevalidation_checkpoint(
        edited_checkpoint, str(tmp_path)
    )
    assert edited_audit["pass"] is False
    assert edited_audit["checks"]["pending_bank_exactly_regenerated"] is False
    assert edited_audit["checks"]["selection_report_exactly_regenerated"] is False

    pending = V6TriadBank.load(str(pending_path))
    validation_seed = int(protocol["selected_bank_validation_schedule"]["seed"])
    validation_records = _balanced_records(
        build_v6_validation_schedule(pending, seed=validation_seed),
        V6_VALIDATION_MODE,
        VALIDATION_RUN_ID,
    )
    validation_log_path = tmp_path / "artifacts" / "validation.jsonl"
    _write_jsonl(validation_log_path, validation_records)
    validation_provider = _provider(protocol, validation_seed)
    validation_plan = audit_v6_calibration_plan(
        protocol,
        pending,
        validation_provider,
        V6_VALIDATION_MODE,
        validation_seed,
        None,
        str(tmp_path),
        prevalidation_checkpoint=prevalidation,
        run_id=VALIDATION_RUN_ID,
    )
    assert validation_plan["pass"] is True
    validation_manifest = _manifest(
        pending,
        protocol,
        validation_provider,
        validation_records,
        V6_VALIDATION_MODE,
        VALIDATION_RUN_ID,
        validation_seed,
        validation_log_path,
    )
    validation_receipt_path = (
        tmp_path / "artifacts" / "validation-launch-receipt.json"
    )
    prevalidation_reference = v6_artifact_reference(
        str(prevalidation_path), str(tmp_path)
    )
    _write_json(
        validation_receipt_path,
        build_v6_calibration_launch_receipt(
            protocol=protocol,
            protocol_path=str(protocol_path),
            bank=pending,
            mode=V6_VALIDATION_MODE,
            repository_root=str(tmp_path),
            prevalidation_reference=prevalidation_reference,
            runtime_evidence=validation_provider["focal_runtime_evidence"],
        ),
    )
    validation_manifest["frozen_protocol"] = {
        "plan_audit": validation_plan,
        "focal_runtime": v6_protocol_gate_module.require_v6_focal_runtime(
            protocol,
            validation_provider["focal_runtime_evidence"],
            expected_evidence=prevalidation["focal_runtime"]["evidence"],
        ),
        "prevalidation_checkpoint": prevalidation_reference,
        "single_launch_receipt": v6_artifact_reference(
            str(validation_receipt_path), str(tmp_path)
        ),
    }
    validation_manifest_path = tmp_path / "artifacts" / "validation.manifest.json"
    _write_json(validation_manifest_path, validation_manifest)
    validation_run_audit = audit_v6_calibration_run(
        validation_records, validation_manifest, pending, V6_VALIDATION_MODE
    )
    assert validation_run_audit["pass"] is True
    validation = evaluate_v6_bank_validation(validation_records, pending)
    assert validation["pass"] is True
    validation["calibration_run_audit"] = validation_run_audit
    validation["validation_manifest_file_sha256"] = file_sha256(
        str(validation_manifest_path)
    )
    validation["validation_log_file_sha256"] = file_sha256(
        str(validation_log_path)
    )
    validation_path = tmp_path / "artifacts" / "validation.json"
    _write_json(validation_path, validation)
    final_payload = finalize_validated_v6_bank(pending.payload, validation)
    final_bank_path = tmp_path / "artifacts" / "validated.json"
    _write_json(final_bank_path, final_payload)

    final_checkpoint = build_v6_final_checkpoint(
        prevalidation_checkpoint_path=str(prevalidation_path),
        validation_summary_path=str(validation_path),
        validation_log_path=str(validation_log_path),
        validation_manifest_path=str(validation_manifest_path),
        validated_bank_path=str(final_bank_path),
        repository_root=str(tmp_path),
    )
    final_checkpoint_path = tmp_path / "artifacts" / "final-checkpoint.json"
    _write_json(final_checkpoint_path, final_checkpoint)
    final_audit = audit_v6_final_checkpoint(final_checkpoint, str(tmp_path))
    assert final_audit["pass"] is True

    proved_bank = V6TriadBank.load(
        str(final_bank_path),
        require_validated=True,
        final_checkpoint_path=str(final_checkpoint_path),
        checkpoint_root=str(tmp_path),
    )
    assert proved_bank.sha256() == final_audit["validated_bank_sha256"]
    protocol_object = make_v6_protocol(
        str(final_bank_path),
        require_validated=True,
        final_checkpoint_path=str(final_checkpoint_path),
        checkpoint_root=str(tmp_path),
        confirmatory_run_id=CONFIRMATORY_RUN_ID,
        confirmatory_episode_seeds=selected_episode_seeds,
    )
    assert protocol_object.protocol_provenance_manifest()[
        "v6_final_checkpoint"
    ]["artifact_audit"]["pass"] is True
    with pytest.raises(ValueError, match="single frozen official run ID"):
        make_v6_protocol(
            str(final_bank_path),
            require_validated=True,
            final_checkpoint_path=str(final_checkpoint_path),
            checkpoint_root=str(tmp_path),
            confirmatory_run_id="replacement-confirmatory-run",
            confirmatory_episode_seeds=selected_episode_seeds,
        )
    with pytest.raises(ValueError, match="episode count"):
        make_v6_protocol(
            str(final_bank_path),
            require_validated=True,
            final_checkpoint_path=str(final_checkpoint_path),
            checkpoint_root=str(tmp_path),
            confirmatory_run_id=CONFIRMATORY_RUN_ID,
            confirmatory_episode_seeds=18,
        )
    with pytest.raises(ValueError, match="scenario coordinates"):
        protocol_object.scenario_sequence(0, 24, validation_seed)
    frozen_scenario = protocol_object.scenario_sequence(0, 24, 20262004)[0]
    with pytest.raises(ValueError, match="candidate coordinates"):
        protocol_object.candidate_set(frozen_scenario, 0, 1, 18, 20262004)

    # A hand-written validated status remains insufficient even when all file
    # hashes in the forged checkpoint are refreshed.
    forged_payload = deepcopy(pending_payload)
    forged_payload["status"] = "selected_bank_validated"
    forged_path = tmp_path / "artifacts" / "forged-validated.json"
    _write_json(forged_path, forged_payload)
    forged_bank = V6TriadBank.load(str(forged_path))
    forged_checkpoint = deepcopy(final_checkpoint)
    forged_checkpoint["validated_bank"] = {
        **v6_artifact_reference(str(forged_path), str(tmp_path)),
        "bank_sha256": forged_bank.sha256(),
        "bank_content_sha256": bank_content_sha256(forged_payload),
    }
    forged_audit = audit_v6_final_checkpoint(forged_checkpoint, str(tmp_path))
    assert forged_audit["checks"]["validated_bank_status"] is True
    assert forged_audit["checks"]["validated_bank_transition_recomputed"] is False
    assert forged_audit["pass"] is False

    schedule_tamper = deepcopy(final_checkpoint)
    schedule_tamper["confirmatory_schedule"]["official_run_id"] = "replacement"
    assert audit_v6_final_checkpoint(schedule_tamper, str(tmp_path))["pass"] is False

    run_cli = _load_script(
        monkeypatch, "run_v6_calibration.py", "run_v6_calibration_checkpoint_test"
    )
    run_cli._bootstrap.ROOT = str(tmp_path)
    with pytest.raises(ValueError, match="single official run-id"):
        run_cli.main(
            [
                "--bank",
                str(pending_path),
                "--protocol-spec",
                str(protocol_path),
                "--mode",
                V6_VALIDATION_MODE,
                "--run-id",
                "replacement-validation-run",
                "--pre-validation-checkpoint",
                str(prevalidation_path),
                "--dry-run",
            ]
        )
    with pytest.raises(ValueError, match="single frozen canonical directory"):
        run_cli.main(
            [
                "--bank",
                str(pending_path),
                "--protocol-spec",
                str(protocol_path),
                "--mode",
                V6_VALIDATION_MODE,
                "--run-id",
                VALIDATION_RUN_ID,
                "--pre-validation-checkpoint",
                str(prevalidation_path),
                "--out-dir",
                str(tmp_path / "alternative-validation-output"),
                "--dry-run",
            ]
        )
