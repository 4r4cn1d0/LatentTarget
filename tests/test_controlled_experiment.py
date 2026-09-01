from __future__ import annotations

import dataclasses
import json

import pytest

from config import ControlledExperimentConfig, ModelConfig, STRATEGIES
from src.controlled_experiment import (
    CONTROLLED_REQUIRED_FIELDS,
    build_controlled_episode_specs,
    run_controlled_experiment,
    validate_controlled_record,
)
from src.focal_agent import BaseProvider


def _config(tmp_path, conditions, provider="mock:v4_bayesian", n_seeds=1):
    return ControlledExperimentConfig(
        experiment_id="v4-test",
        n_rounds=8,
        swap_round=4,
        heldout_start_round=7,
        n_episode_seeds=n_seeds,
        seed=2026,
        conditions=list(conditions),
        model=ModelConfig(provider=provider, model="mock", max_tokens=16),
        out_dir=str(tmp_path),
    )


def test_v4_episode_specs_balance_types_and_all_ordered_swaps(tmp_path):
    stable = build_controlled_episode_specs(_config(tmp_path, ["full_history"], n_seeds=2))
    assert len(stable) == 2 * 3
    swaps = build_controlled_episode_specs(_config(tmp_path, ["swap"], n_seeds=2))
    assert len(swaps) == 2 * 6
    pairs = {(spec.initial_target_type, spec.final_target_type) for spec in swaps}
    assert pairs == {(a, b) for a in STRATEGIES for b in STRATEGIES if a != b}


def test_v4_shuffled_history_requires_prior_full_history(tmp_path):
    with pytest.raises(ValueError, match="requires full_history"):
        build_controlled_episode_specs(_config(tmp_path, ["shuffled_history"]))
    with pytest.raises(ValueError, match="precede"):
        build_controlled_episode_specs(
            _config(tmp_path, ["shuffled_history", "full_history"])
        )


def test_complete_v4_mock_run_has_schema_and_condition_semantics(tmp_path):
    cfg = _config(
        tmp_path,
        ["full_history", "no_history", "shuffled_history", "random_target", "swap",
         "elicited_full_history", "elicited_swap"],
    )
    result = run_controlled_experiment(cfg, run_id="complete")
    assert result.n_episodes == 27
    assert result.n_records == 27 * 8
    assert set(CONTROLLED_REQUIRED_FIELDS) <= set(result.records[0])
    for record in result.records:
        validate_controlled_record(record)

    no_history = [row for row in result.records if row["condition"] == "no_history"]
    assert all(row["visible_history"] == [] for row in no_history)
    assert all("Previous interactions" not in row["focal_user_prompt"] for row in no_history)

    random_rows = [row for row in result.records if row["condition"] == "random_target"]
    assert {row["target_p_a"] for row in random_rows} == {0.5}

    swap_rows = [row for row in result.records if row["condition"] == "swap"]
    assert all(
        row["hidden_target_type"]
        == (row["initial_target_type"] if row["round"] <= 4 else row["final_target_type"])
        for row in swap_rows
    )


def test_candidate_and_scenario_schedule_is_identical_across_conditions_and_types(tmp_path):
    cfg = _config(
        tmp_path,
        ["full_history", "no_history", "shuffled_history", "random_target", "swap"],
    )
    rows = run_controlled_experiment(cfg, run_id="schedule").records
    signatures = {}
    for row in rows:
        key = (row["episode_index"], row["round"])
        signature = (
            row["scenario_id"],
            tuple((candidate["slot"], candidate["candidate_id"], candidate["message"])
                  for candidate in row["candidates"]),
        )
        signatures.setdefault(key, signature)
        assert signatures[key] == signature


def test_shuffled_history_uses_different_target_donor(tmp_path):
    cfg = _config(tmp_path, ["full_history", "shuffled_history"])
    rows = run_controlled_experiment(cfg, run_id="donors").records
    shuffled = [row for row in rows if row["condition"] == "shuffled_history"]
    for row in shuffled:
        if row["round"] == 1:
            assert row["visible_history"] == []
        else:
            assert len(row["visible_history"]) == row["round"] - 1
        donor_type = row["history_source_episode_id"].rsplit("-", 1)[-1]
        assert donor_type != row["hidden_target_type"]


class ContextBoundaryProvider(BaseProvider):
    name = "context-boundary-spy"
    model = "spy"

    def __init__(self):
        self.contexts = []

    def generate(self, prompt):
        self.contexts.append(prompt.context)
        return "1"


class FailAfterProvider(ContextBoundaryProvider):
    name = "fail-after"

    def __init__(self, fail_after):
        super().__init__()
        self.fail_after = fail_after

    def generate(self, prompt):
        if len(self.contexts) >= self.fail_after:
            raise RuntimeError("simulated provider interruption")
        return super().generate(prompt)


def test_real_provider_boundary_receives_no_mock_metadata(tmp_path):
    cfg = _config(tmp_path, ["full_history"])
    provider = ContextBoundaryProvider()
    run_controlled_experiment(cfg, run_id="boundary", provider=provider)
    assert provider.contexts
    assert all(context == {} for context in provider.contexts)


def test_logged_visible_history_omits_registered_frame_ground_truth(tmp_path):
    cfg = _config(tmp_path, ["full_history", "elicited_full_history"])
    rows = run_controlled_experiment(cfg, run_id="visible-boundary").records
    histories = [entry for row in rows for entry in row["visible_history"]]
    assert histories
    assert all("selected_frame" not in entry for entry in histories)
    spontaneous = [
        entry for row in rows if row["focal_mode"] == "spontaneous"
        for entry in row["visible_history"]
    ]
    assert all(set(entry) == {
        "round", "scenario_title", "selected_message", "choice"
    } for entry in spontaneous)
    elicited = [
        entry for row in rows if row["focal_mode"] == "elicited"
        for entry in row["visible_history"]
    ]
    assert all(set(entry) == {
        "round", "scenario_title", "selected_message", "choice",
        "predicted_p_a", "candidate_messages",
    } for entry in elicited)


def test_invalid_outputs_are_preserved_and_use_seeded_fallback(tmp_path):
    cfg = _config(tmp_path, ["full_history"], provider="mock:v4_invalid")
    rows = run_controlled_experiment(cfg, run_id="invalid").records
    assert all(row["focal_output_raw"] == "I recommend the second message." for row in rows)
    assert all(not row["selection_valid"] and row["fallback_used"] for row in rows)


def test_v4_run_is_reproducible_and_refuses_overwrite(tmp_path):
    cfg = _config(tmp_path, ["full_history", "no_history"])
    first = run_controlled_experiment(cfg, run_id="first")
    second = run_controlled_experiment(cfg, run_id="second")
    volatile = {"run_id", "timestamp"}
    for left, right in zip(first.records, second.records):
        assert {k: v for k, v in left.items() if k not in volatile} == {
            k: v for k, v in right.items() if k not in volatile
        }
    with pytest.raises(FileExistsError, match="overwrite"):
        run_controlled_experiment(cfg, run_id="first")


def test_v4_run_resumes_at_episode_boundary_without_duplicates(tmp_path):
    cfg = _config(tmp_path, ["full_history"])
    with pytest.raises(RuntimeError, match="interruption"):
        run_controlled_experiment(
            cfg, run_id="resumable", provider=FailAfterProvider(9)
        )
    from src.logging_utils import read_jsonl

    partial = list(read_jsonl(str(tmp_path / "resumable.jsonl")))
    assert len(partial) == 8  # one complete episode; the interrupted one was not appended
    resumed = run_controlled_experiment(
        cfg,
        run_id="resumable",
        provider=FailAfterProvider(1000),
        resume=True,
    )
    assert resumed.n_records == 3 * 8
    assert len({(row["episode_id"], row["round"]) for row in resumed.records}) == 3 * 8
    manifest = json.load(open(resumed.manifest_path, encoding="utf-8"))
    assert manifest["run_status"] == "completed"


def test_v4_resume_rejects_provider_setting_drift(tmp_path):
    cfg = _config(tmp_path, ["full_history"])
    with pytest.raises(RuntimeError, match="interruption"):
        run_controlled_experiment(
            cfg, run_id="provider-drift", provider=FailAfterProvider(9)
        )
    with pytest.raises(ValueError, match="provider settings"):
        run_controlled_experiment(
            cfg,
            run_id="provider-drift",
            provider=ContextBoundaryProvider(),
            resume=True,
        )


def test_v4_resume_rejects_message_bank_manifest_drift(tmp_path):
    cfg = _config(tmp_path, ["full_history"])
    with pytest.raises(RuntimeError, match="interruption"):
        run_controlled_experiment(
            cfg, run_id="bank-drift", provider=FailAfterProvider(9)
        )
    manifest_path = tmp_path / "bank-drift.manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["message_bank_sha256"] = "tampered"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    with pytest.raises(ValueError, match="message bank"):
        run_controlled_experiment(
            cfg,
            run_id="bank-drift",
            provider=FailAfterProvider(1000),
            resume=True,
        )


def test_controlled_record_validation_detects_selected_candidate_tampering(tmp_path):
    cfg = _config(tmp_path, ["full_history"])
    record = run_controlled_experiment(cfg, run_id="tamper").records[0]
    changed = dict(record, selected_message="not the registered message")
    with pytest.raises(ValueError, match="selected candidate"):
        validate_controlled_record(changed)


def test_v4_manifest_contains_exact_prompts_banks_and_revision(tmp_path):
    cfg = dataclasses.replace(
        _config(tmp_path, ["full_history"]),
        model=ModelConfig(
            provider="mock:v4_random", model="mock", revision="immutable-revision"
        ),
    )
    result = run_controlled_experiment(cfg, run_id="manifest")
    manifest = json.load(open(result.manifest_path, encoding="utf-8"))
    assert manifest["task_version"] == "controlled-choice-v4.0"
    assert manifest["config"]["model"]["revision"] == "immutable-revision"
    assert len(manifest["message_banks"]["development"]["fairness"]) == 10
    assert "spontaneous_system_rendered" in manifest["focal_prompt_templates"]
    assert manifest["message_bank_sha256"]
