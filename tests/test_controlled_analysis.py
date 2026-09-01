from __future__ import annotations

import json
from pathlib import Path

from config import CONTROLLED_GATE_THRESHOLDS, ControlledExperimentConfig, ModelConfig
from src.controlled_analysis import (
    _positive_beyond_roundoff,
    audit_controlled_design,
    audit_frozen_checkpoint_manifest,
    audit_frozen_checkpoint_plan,
    evaluate_controlled_checkpoint,
)
from src.controlled_experiment import build_controlled_episode_specs, run_controlled_experiment


def _checkpoint_config(tmp_path, provider, n_seeds):
    return ControlledExperimentConfig(
        experiment_id="v4-gate-test",
        n_episode_seeds=n_seeds,
        conditions=["full_history", "no_history", "shuffled_history", "random_target", "swap"],
        model=ModelConfig(provider=provider, model="mock", max_tokens=16),
        out_dir=str(tmp_path),
    )


def test_positive_effect_gate_rejects_floating_point_residue():
    assert _positive_beyond_roundoff(7.401486830834377e-18) is False
    assert _positive_beyond_roundoff(1e-6) is True


def test_bayesian_positive_control_passes_but_is_never_scientific_evidence(tmp_path):
    cfg = _checkpoint_config(tmp_path, "mock:v4_bayesian", n_seeds=20)
    result = run_controlled_experiment(cfg, run_id="bayesian")
    manifest = json.load(open(result.manifest_path, encoding="utf-8"))
    gate = evaluate_controlled_checkpoint(
        result.records, manifest, n_boot=300, n_perm=1500, seed=99
    )
    assert gate["pattern_pass"] is True
    assert gate["scientific_pass"] is False
    assert gate["decision"] == "MOCK_PIPELINE_PASS_NOT_SCIENTIFIC_EVIDENCE"
    assert all(gate["effect_gates"].values())
    assert all(gate["inference_gates"].values())


def test_random_policy_fails_history_and_swap_gate(tmp_path):
    cfg = _checkpoint_config(tmp_path, "mock:v4_random", n_seeds=8)
    result = run_controlled_experiment(cfg, run_id="random")
    manifest = json.load(open(result.manifest_path, encoding="utf-8"))
    gate = evaluate_controlled_checkpoint(
        result.records, manifest, n_boot=200, n_perm=500, seed=11
    )
    assert gate["pattern_pass"] is False
    assert gate["decision"] == "STOP_BEFORE_FREEFORM_OR_MECHANISTIC_SCALING"
    assert not gate["effect_gates"]["full_history_difference_in_differences"]


def test_design_audit_detects_exposed_frame_metadata(tmp_path):
    cfg = _checkpoint_config(tmp_path, "mock:v4_random", n_seeds=1)
    result = run_controlled_experiment(cfg, run_id="audit")
    manifest = json.load(open(result.manifest_path, encoding="utf-8"))
    changed = [dict(row) for row in result.records]
    changed[0]["visible_candidates"] = [dict(item) for item in changed[0]["visible_candidates"]]
    changed[0]["visible_candidates"][0]["frame"] = "fairness"
    audit = audit_controlled_design(changed, manifest)
    assert audit["pass"] is False
    assert audit["checks"]["registered_frames_not_exposed_as_metadata"] is False


def test_design_audit_detects_duplicate_round_and_tampered_manifest_count(tmp_path):
    cfg = _checkpoint_config(tmp_path, "mock:v4_random", n_seeds=1)
    result = run_controlled_experiment(cfg, run_id="duplicate-audit")
    manifest = json.load(open(result.manifest_path, encoding="utf-8"))
    changed = list(result.records) + [dict(result.records[0])]
    manifest["n_records"] = len(changed)
    audit = audit_controlled_design(changed, manifest)
    assert audit["pass"] is False
    assert audit["checks"]["unique_episode_round_keys"] is False


def test_machine_readable_v4_checkpoint_matches_code_and_expected_counts():
    spec_path = Path(__file__).parents[1] / "docs" / "behavioral_checkpoint_v4.json"
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    assert spec["thresholds"] == CONTROLLED_GATE_THRESHOLDS
    experiment = spec["experiment"]
    cfg = ControlledExperimentConfig(
        experiment_id="frozen-count-check",
        n_rounds=experiment["n_rounds"],
        swap_round=experiment["swap_round"],
        heldout_start_round=experiment["heldout_start_round"],
        n_episode_seeds=experiment["n_episode_seeds"],
        seed=experiment["master_seed"],
        conditions=experiment["conditions"],
        model=ModelConfig(
            provider="huggingface",
            model=spec["primary_model"]["id"],
            revision=spec["primary_model"]["revision"],
            temperature=spec["generation"]["temperature"],
            max_tokens=spec["generation"]["max_tokens"],
        ),
    )
    specs = build_controlled_episode_specs(cfg)
    assert len(specs) == experiment["episode_counts"]["total"]
    assert sum(item.n_rounds for item in specs) == experiment["record_counts"]["total"]


def test_frozen_manifest_audit_rejects_model_revision_drift():
    spec_path = Path(__file__).parents[1] / "docs" / "behavioral_checkpoint_v4.json"
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    experiment = spec["experiment"]
    generation = spec["generation"]
    manifest = {
        "task_version": spec["version"],
        "run_status": "completed",
        "n_records": experiment["record_counts"]["total"],
        "n_episodes": experiment["episode_counts"]["total"],
        "message_bank_sha256": spec["message_bank"]["sha256"],
        "config": {
            "conditions": experiment["conditions"],
            "n_episode_seeds": experiment["n_episode_seeds"],
            "n_rounds": experiment["n_rounds"],
            "swap_round": experiment["swap_round"],
            "heldout_start_round": experiment["heldout_start_round"],
            "seed": experiment["master_seed"],
            "target_params": {k: spec["target"][k] for k in ("p_match", "p_mismatch", "p_random")},
            "model": {
                "model": spec["primary_model"]["id"],
                "revision": spec["primary_model"]["revision"],
                "temperature": generation["temperature"],
                "max_tokens": generation["max_tokens"],
            },
        },
        "provider": {
            "provider": "huggingface",
            "model": spec["primary_model"]["id"],
            "revision": spec["primary_model"]["revision"],
            "torch_seed_base": experiment["master_seed"],
            "temperature": generation["temperature"],
            "max_tokens": generation["max_tokens"],
            "enable_thinking": generation["enable_thinking"],
            "top_p": generation["top_p"],
            "top_k": generation["top_k"],
            "dtype": generation["dtype"],
            "capture": generation["activation_capture"],
        },
    }
    assert audit_frozen_checkpoint_manifest(manifest, spec)["pass"] is True
    manifest["provider"]["revision"] = "drifted"
    audit = audit_frozen_checkpoint_manifest(manifest, spec)
    assert audit["pass"] is False
    assert audit["checks"]["model_revision"] is False


def test_frozen_plan_audit_rejects_sample_size_before_generation():
    spec_path = Path(__file__).parents[1] / "docs" / "behavioral_checkpoint_v4.json"
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    experiment = spec["experiment"]
    generation = spec["generation"]
    cfg = ControlledExperimentConfig(
        experiment_id="planned-run",
        n_rounds=experiment["n_rounds"],
        swap_round=experiment["swap_round"],
        heldout_start_round=experiment["heldout_start_round"],
        n_episode_seeds=experiment["n_episode_seeds"],
        seed=experiment["master_seed"],
        conditions=experiment["conditions"],
        model=ModelConfig(
            provider="huggingface",
            model=spec["primary_model"]["id"],
            revision=spec["primary_model"]["revision"],
            temperature=generation["temperature"],
            max_tokens=generation["max_tokens"],
        ),
    )
    provider = {
        "provider": "huggingface",
        "model": spec["primary_model"]["id"],
        "revision": spec["primary_model"]["revision"],
        "torch_seed_base": experiment["master_seed"],
        "temperature": generation["temperature"],
        "max_tokens": generation["max_tokens"],
        "enable_thinking": generation["enable_thinking"],
        "top_p": generation["top_p"],
        "top_k": generation["top_k"],
        "dtype": generation["dtype"],
        "capture": generation["activation_capture"],
    }
    exact = audit_frozen_checkpoint_plan(
        cfg, provider,
        experiment["record_counts"]["total"],
        experiment["episode_counts"]["total"],
        spec,
    )
    assert exact["pass"] is True
    drifted = audit_frozen_checkpoint_plan(
        cfg, provider,
        experiment["record_counts"]["total"] - 20,
        experiment["episode_counts"]["total"] - 1,
        spec,
    )
    assert drifted["pass"] is False
    assert drifted["checks"]["record_count"] is False
    assert drifted["checks"]["episode_count"] is False
