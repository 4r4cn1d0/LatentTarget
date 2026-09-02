from __future__ import annotations

import copy
import hashlib
from itertools import product
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

from config import CONTROLLED_V6_GATE_THRESHOLDS, STRATEGIES
import src.controlled_v6_power as power
from src.controlled_v6_randomization import v6_allocation_schedule
from src.controlled_v6_power import (
    V6_ALLOCATION_RNG_ROOT,
    V6_EPISODE_SEED_GRID,
    V6_LEARNER_PROFILES,
    V6_MINIMUM_SIMULATIONS_PER_CELL,
    V6_NULL_LATENT_PROFILES,
    V6_POWER_CONTRACT_SHA256,
    V6_POWER_PAYLOAD_SCHEMA_VERSION,
    V6_POWER_SEED,
    V6_PROSPECTIVE_POWER_CONTRACT,
    V6_SWAP_COMPONENT_ALTERNATIVES,
    V6PowerAuditError,
    _passes_v6_realized_no_history_balance_gate,
    analyze_v6_bundle_study,
    audit_v6_path_balance_dominance_screen,
    audit_v6_power_payload,
    enumerate_v6_frame_share_nuisance_configurations,
    exact_one_sided_bundle_randomization_test,
    reconstruct_v6_bundle_assignments,
    run_v6_worst_case_power,
    run_v6_path_balance_dominance_screen,
    simulate_controlled_v6_power,
    simulate_v6_bundle_study,
    simulate_v6_feedback_path,
    simulate_v6_no_history_balance_study,
    simulate_v6_null_size,
    summarize_v6_null_type_i,
)


ROOT = Path(__file__).parents[1]


def _manual_assignment_bit(study_index, bundle_index, family_code):
    allocation_index = study_index * 31 + bundle_index
    sequence = np.random.SeedSequence(
        [V6_ALLOCATION_RNG_ROOT, family_code, allocation_index]
    )
    rng = np.random.Generator(np.random.PCG64DXSM(sequence))
    return int(rng.integers(0, 2))


def _overwrite_with_false_adaptation(study):
    no_frames = list(STRATEGIES) * 8
    transitions = V6_PROSPECTIVE_POWER_CONTRACT["design"][
        "ordered_transitions"
    ]
    for bundle in study["bundles"]:
        full = next(
            slot
            for slot in bundle["stable_slots"]
            if slot["condition"] == "full_history"
        )
        no = next(
            slot
            for slot in bundle["stable_slots"]
            if slot["condition"] == "no_history"
        )
        for target in STRATEGIES:
            no["target_trajectories"][target]["frames"] = no_frames.copy()
            filler = next(
                frame
                for frame in STRATEGIES
                if frame not in {target, no_frames[0]}
            )
            full_frames = [no_frames[0]] + [filler] * 5
            full_frames += [filler] * 12 + [target] * 6
            full["target_trajectories"][target]["frames"] = full_frames
            bundle["random_target_controls"][target][
                "frames"
            ] = no_frames.copy()

        swap = next(
            slot
            for slot in bundle["transition_slots"]
            if slot["condition"] == "silent_swap"
        )
        stable = next(
            slot
            for slot in bundle["transition_slots"]
            if slot["condition"] == "stable_old"
        )
        for transition in transitions:
            old, new = transition.split("->")
            other = next(
                frame for frame in STRATEGIES if frame not in {old, new}
            )
            stable_frames = [other] * 6 + [old] * 6
            stable_frames += [other] * 6 + [old] * 6
            swap_frames = [other] * 6 + [old] * 6
            swap_frames += [other] * 12
            stable["transitions"][transition]["frames"] = stable_frames
            swap["transitions"][transition]["frames"] = swap_frames
    return study


def _fake_interval(successes, trials):
    return power._power_result(successes, trials)


def _fake_effect_result(
    n,
    n_sim,
    scenario,
    shares,
    seed,
    offset,
):
    return {
        "schema_version": V6_POWER_PAYLOAD_SCHEMA_VERSION,
        "n_episode_seeds": n,
        "n_sim": n_sim,
        "simulation_seed": seed,
        "simulation_study_offset": offset,
        "planning_scenario": dict(scenario),
        "baseline_frame_shares": dict(shares),
        "stable_co_primary": {
            **_fake_interval(n_sim, n_sim),
            "mean_estimated_effect": 0.2,
        },
        "revision_co_primary": {
            **_fake_interval(n_sim, n_sim),
            "mean_estimated_effect": 0.25,
        },
        "joint_co_primary": _fake_interval(n_sim, n_sim),
        "complete_behavioral_pattern": _fake_interval(0, n_sim),
        "no_history_balance_gate": _fake_interval(0, n_sim),
        "mean_adjusted_new_gain": 0.125,
        "mean_adjusted_old_drop": 0.125,
        "mean_late_swap_new_minus_old": 0.1,
        "aggregate_sufficient_statistics": {},
        "assumptions": {},
    }


def _fake_null_result(n, n_sim, shares, seed, offset):
    metrics = {
        name: {
            metric: _fake_interval(0, n_sim)
            for metric in (
                "stable",
                "revision",
                "joint_both",
                "familywise_any",
            )
        }
        for name in (
            "symmetric",
            "asymmetric_slots",
            "adversarial_serial",
        )
    }
    return {
        "schema_version": V6_POWER_PAYLOAD_SCHEMA_VERSION,
        "n_episode_seeds": n,
        "n_sim_per_profile": n_sim,
        "simulation_seed": seed,
        "simulation_study_offset": offset,
        "baseline_frame_shares": dict(shares),
        "profiles": metrics,
    }


def test_contract_serializes_every_prospective_nuisance_assumption():
    contract = json.loads(json.dumps(V6_PROSPECTIVE_POWER_CONTRACT))
    assert power._canonical_sha256(contract) == V6_POWER_CONTRACT_SHA256
    assert contract["schema_version"].endswith(
        "prospective-randomized-bundles"
    )
    assert contract["allocation"]["rng_root"] == 20262006
    assert contract["allocation"]["bit_generator"] == "PCG64DXSM"
    assert contract["simulation"]["power_rng_root"] == 20262003
    assert contract["simulation"]["target_rates"] == {
        "match": 0.72,
        "mismatch": 0.38,
        "random": 0.5,
    }
    assert V6_LEARNER_PROFILES == (
        (2, 0.0, 0.0),
        (6, 0.035, 0.035),
        (12, 0.07, 0.07),
    )
    assert V6_SWAP_COMPONENT_ALTERNATIVES == (
        (0.10, 0.15),
        (0.125, 0.125),
        (0.15, 0.10),
    )
    assert contract["power"] == {
        **contract["power"],
        "n_grid": [12, 18, 24, 30],
        "official_simulations_per_cell_minimum": 10_000,
        "target_wilson_lower_bound": 0.80,
        "official_effect_cell_count": 156,
        "official_null_cell_count": 13,
        "official_total_cell_count": 169,
    }
    assert contract["null_size"]["decision_rule"].startswith(
        "upper limits only"
    )
    screen = contract["power"]["path_balance_dominance_screen"]
    assert screen["configuration_id"] == "minimum_share_boundary_01"
    assert screen["simulations_per_cell"] == 10_000
    assert screen["planning_scenario_ids"] == [
        "learner_1",
        "learner_2",
        "learner_3",
    ]


def test_exact_assignment_reconstruction_uses_two_shared_independent_bits():
    runtime_rows = v6_allocation_schedule(30)["rows"]
    actual_rows = reconstruct_v6_bundle_assignments(30, study_index=0)
    assert [row["stable_full_slot"] for row in actual_rows] == [
        row["history_treated_slot"] for row in runtime_rows
    ]
    assert [row["swap_slot"] for row in actual_rows] == [
        row["swap_treated_slot"] for row in runtime_rows
    ]
    study_index = 7
    assignments = reconstruct_v6_bundle_assignments(
        30, study_index=study_index
    )
    assert assignments == reconstruct_v6_bundle_assignments(
        30, study_index=study_index
    )
    for row in assignments:
        bundle = row["bundle_index"]
        assert row["stable_full_slot"] == _manual_assignment_bit(
            study_index, bundle, 0
        )
        assert row["swap_slot"] == _manual_assignment_bit(
            study_index, bundle, 1
        )
    assert {row["stable_full_slot"] for row in assignments} == {0, 1}
    assert {row["swap_slot"] for row in assignments} == {0, 1}
    assert any(
        row["stable_full_slot"] != row["swap_slot"]
        for row in assignments
    )


def test_exact_test_enumerates_all_bundle_sign_assignments():
    values = (-2, -1, 0, 1, 2)
    observed = sum(values)
    brute = sum(
        sum(sign * abs(value) for sign, value in zip(signs, values))
        >= observed
        for signs in product((-1, 1), repeat=len(values))
    ) / float(2 ** len(values))
    result = exact_one_sided_bundle_randomization_test(
        [value / 18.0 for value in values], integer_scale=18
    )
    assert result["p_value_one_sided"] == brute
    assert result["n_assignments_enumerated"] == 2 ** len(values)
    assert result["integer_bundle_contrasts"] == list(values)


def test_complete_round_paths_freeze_no_history_and_couple_full_slot_round_one():
    study = simulate_v6_bundle_study(3, study_index=11, seed=91)
    for bundle in study["bundles"]:
        full = next(
            slot
            for slot in bundle["stable_slots"]
            if slot["condition"] == "full_history"
        )
        no = next(
            slot
            for slot in bundle["stable_slots"]
            if slot["condition"] == "no_history"
        )
        no_paths = [
            no["target_trajectories"][target]["frames"]
            for target in STRATEGIES
        ]
        assert no_paths[0] == no_paths[1] == no_paths[2]
        assert all(len(path) == 24 for path in no_paths)
        full_first = []
        for target in STRATEGIES:
            full_path = full["target_trajectories"][target]["frames"]
            assert len(full_path) == 24
            full_first.append(full_path[0])
        assert len(set(full_first)) == 1
        for slot in bundle["transition_slots"]:
            assert all(
                len(path["frames"]) == 24
                for path in slot["transitions"].values()
            )
    summary = analyze_v6_bundle_study(study)
    assert summary["no_history_unique_prompt_count"] == 3 * 24


def test_visible_history_feedback_is_sequential_and_no_history_is_frozen():
    choice_uniforms = [0.30] * 24
    favorable = simulate_v6_feedback_path(
        target=STRATEGIES[0],
        choice_uniforms=choice_uniforms,
        outcome_uniforms=[0.0] * 24,
        visible_history=True,
    )
    unfavorable = simulate_v6_feedback_path(
        target=STRATEGIES[0],
        choice_uniforms=choice_uniforms,
        outcome_uniforms=[0.99] * 24,
        visible_history=True,
    )
    assert favorable["frames"] != unfavorable["frames"]
    assert favorable["posterior_means_before_round"][0] == [0.5, 0.5, 0.5]
    assert favorable["posterior_means_before_round"][1] != [0.5, 0.5, 0.5]
    frozen_a = simulate_v6_feedback_path(
        target=STRATEGIES[0],
        choice_uniforms=choice_uniforms,
        outcome_uniforms=[0.0] * 24,
        visible_history=False,
    )
    frozen_b = simulate_v6_feedback_path(
        target=STRATEGIES[0],
        choice_uniforms=choice_uniforms,
        outcome_uniforms=[0.99] * 24,
        visible_history=False,
    )
    assert frozen_a["frames"] == frozen_b["frames"]
    assert all(
        posterior == [0.5, 0.5, 0.5]
        for posterior in frozen_a["posterior_means_before_round"]
    )


def test_component_gate_rejects_false_adaptation_from_old_drop_only():
    study = _overwrite_with_false_adaptation(
        simulate_v6_bundle_study(12, study_index=23, seed=4)
    )
    result = analyze_v6_bundle_study(study)
    assert result["adjusted_new_gain"] == pytest.approx(0.0)
    assert result["adjusted_old_drop"] == pytest.approx(1.0)
    assert result["revision"] == pytest.approx(1.0)
    assert result["late_swap_new_minus_old"] == pytest.approx(0.0)
    assert result["revision_test"]["p_value_one_sided"] <= 0.025
    assert result["effect_gates"]["adjusted_new_gain"] is False
    assert result["complete_gate"] is False


def test_every_power_replicate_calls_shared_analysis_helper(monkeypatch):
    original = power.analyze_v6_bundle_study
    calls = []

    def recording(study):
        calls.append(study["study_index"])
        return original(study)

    monkeypatch.setattr(power, "analyze_v6_bundle_study", recording)
    result = simulate_controlled_v6_power(6, n_sim=3, seed=99)
    assert calls == [1, 2, 3]
    assert result["assumptions"]["analysis_helper"] == (
        "analyze_v6_bundle_study"
    )


def test_null_profiles_are_asymmetric_and_upper_bound_only():
    assert {profile["profile_id"] for profile in V6_NULL_LATENT_PROFILES} == {
        "symmetric",
        "asymmetric_slots",
        "adversarial_serial",
    }
    row = simulate_v6_null_size(
        12,
        8,
        {frame: 1.0 / 3.0 for frame in STRATEGIES},
        seed=303,
    )
    row["frame_share_configuration_id"] = "balanced"
    assert set(row["profiles"]) == {
        "symmetric",
        "asymmetric_slots",
        "adversarial_serial",
    }
    summary = summarize_v6_null_type_i([row])
    assert summary["decision_rule"] == (
        "upper Wilson bound only; no lower Type-I bound"
    )
    for metric in summary["metrics"].values():
        assert "upper_limit" in metric
        assert "pass" in metric


def test_asymmetric_sharp_null_sign_flip_size_is_not_inflated():
    rng = np.random.Generator(np.random.PCG64DXSM(777))
    magnitudes = np.array([18, 17, 11, 9, 7, 5, 3, 2, 1, 1, 1, 1])
    rejects = 0
    n_sim = 2000
    for _ in range(n_sim):
        signs = 2 * rng.integers(0, 2, size=len(magnitudes)) - 1
        p_value = power._exact_one_sided_sign_flip_p(
            tuple(int(value) for value in signs * magnitudes)
        )
        rejects += int(p_value <= 0.025)
    assert rejects / n_sim <= 0.035


def test_balance_grid_and_realized_boundary_are_not_held_by_construction():
    configurations = enumerate_v6_frame_share_nuisance_configurations()
    assert len(configurations) == 13
    assert _passes_v6_realized_no_history_balance_gate(
        (25, 35, 40), sample_size=100
    )
    assert not _passes_v6_realized_no_history_balance_gate(
        (24, 35, 41), sample_size=100
    )
    assert "near one half" in power.FINITE_NUISANCE_GRID_COVERAGE_NOTE


def test_iid_boundary_probability_is_labeled_sensitivity_only():
    boundary = dict(zip(STRATEGIES, (0.25, 0.35, 0.40)))
    observed = {
        str(n): round(
            power.iid_v6_balance_gate_sensitivity_probability(n, boundary), 6
        )
        for n in (12, 18, 24, 30)
    }
    assert observed == {
        "12": 0.411239,
        "18": 0.409141,
        "24": 0.414593,
        "30": 0.418843,
    }
    assert "known_design_limit" not in V6_PROSPECTIVE_POWER_CONTRACT["power"]


def test_path_balance_study_is_exact_projection_of_complete_simulator():
    shares = dict(zip(STRATEGIES, (0.25, 0.35, 0.40)))
    projected = simulate_v6_no_history_balance_study(
        3,
        baseline_frame_shares=shares,
        planning_scenario=2,
        study_index=9123,
    )
    complete = simulate_v6_bundle_study(
        3,
        baseline_frame_shares=shares,
        planning_scenario=2,
        study_index=9123,
    )
    frames = []
    for bundle in complete["bundles"]:
        no_history = next(
            slot
            for slot in bundle["stable_slots"]
            if slot["condition"] == "no_history"
        )
        frames.extend(
            no_history["target_trajectories"]["fairness"]["frames"]
        )
    assert projected["counts"] == {
        frame: frames.count(frame) for frame in STRATEGIES
    }
    assert projected["pass"] == _passes_v6_realized_no_history_balance_gate(
        tuple(projected["counts"][frame] for frame in STRATEGIES),
        sample_size=len(frames),
    )


def test_path_balance_dominance_screen_replays_and_rejects_mutation():
    certificate = run_v6_path_balance_dominance_screen(n_sim=4)
    assert certificate["terminal"] is True
    assert certificate["status"] == "STOP_V6_UNDERPOWERED_BEFORE_VALIDATION"
    assert len(certificate["screen_results"]) == 12
    audit = audit_v6_path_balance_dominance_screen(certificate)
    assert audit["audit_pass"] is True
    forged = copy.deepcopy(certificate)
    forged["screen_results"][0]["no_history_balance_gate"]["successes"] += 1
    with pytest.raises(V6PowerAuditError, match="digest failed"):
        audit_v6_path_balance_dominance_screen(forged)


def test_repository_protocol_binds_terminal_corrected_power_result():
    protocol = json.loads(
        (ROOT / "docs" / "v6_calibration_protocol.json").read_text(
            encoding="utf-8"
        )
    )
    reference = protocol["power_design"]["result"]
    artifact_path = ROOT / reference["path"]
    artifact_bytes = artifact_path.read_bytes()
    artifact = json.loads(artifact_bytes)
    assert protocol["status"] == "STOP_V6_UNDERPOWERED_FINAL"
    assert reference["status"] == "STOP_V6_UNDERPOWERED_BEFORE_VALIDATION"
    assert reference["terminal"] is True
    assert reference["official"] is True
    assert reference["pass"] is False
    assert reference["selected_episode_seeds"] is None
    assert hashlib.sha256(artifact_bytes).hexdigest() == reference["file_sha256"]
    assert artifact["certificate_sha256"] == reference["certificate_sha256"]
    assert audit_v6_path_balance_dominance_screen(
        artifact, replay=False
    )["audit_pass"] is True
    assert protocol["power_design"]["contract_sha256"] == (
        V6_POWER_CONTRACT_SHA256
    )
    assert protocol["next_gate"] is None


def test_contract_and_live_gate_drift_fail_closed(monkeypatch):
    monkeypatch.setitem(
        CONTROLLED_V6_GATE_THRESHOLDS,
        "minimum_adjusted_new_target_gain",
        0.051,
    )
    with pytest.raises(RuntimeError, match="GATE_THRESHOLDS drifted"):
        power._assert_v6_power_contract()


def test_run_has_169_cells_and_audit_replays_them(monkeypatch):
    effect_calls = []
    null_calls = []

    def fake_effect(
        n,
        n_sim,
        baseline_frame_shares,
        *,
        planning_scenario,
        seed,
        simulation_study_offset,
        **_kwargs,
    ):
        effect_calls.append((n, planning_scenario["scenario_id"]))
        return _fake_effect_result(
            n,
            n_sim,
            planning_scenario,
            baseline_frame_shares,
            seed,
            simulation_study_offset,
        )

    def fake_null(
        n,
        n_sim,
        baseline_frame_shares,
        *,
        seed,
        simulation_study_offset,
    ):
        null_calls.append(n)
        return _fake_null_result(
            n,
            n_sim,
            baseline_frame_shares,
            seed,
            simulation_study_offset,
        )

    monkeypatch.setattr(power, "simulate_controlled_v6_power", fake_effect)
    monkeypatch.setattr(power, "simulate_v6_null_size", fake_null)
    payload = run_v6_worst_case_power(n_sim=1, official=False)
    assert len(effect_calls) == 156
    assert len(null_calls) == 13
    effect_calls.clear()
    null_calls.clear()
    audit = audit_v6_power_payload(
        payload, require_official=False, replay=True
    )
    assert audit["audit_pass"] is True
    assert audit["deterministic_replay_performed"] is True
    assert len(effect_calls) == 156
    assert len(null_calls) == 13

    forged = copy.deepcopy(payload)
    forged["effect_results"][0]["joint_co_primary"]["successes"] = 0
    with pytest.raises(V6PowerAuditError, match="power_summary"):
        audit_v6_power_payload(
            forged, require_official=False, replay=False
        )


def test_study_and_power_replay_are_deterministic():
    first = simulate_v6_bundle_study(2, study_index=4, seed=41)
    second = simulate_v6_bundle_study(2, study_index=4, seed=41)
    assert first == second
    first_power = simulate_controlled_v6_power(6, n_sim=2, seed=42)
    second_power = simulate_controlled_v6_power(6, n_sim=2, seed=42)
    assert first_power == second_power


def test_official_guards_reject_short_runs_before_any_cell(monkeypatch):
    monkeypatch.setattr(
        power,
        "_map_cells",
        lambda *_args, **_kwargs: pytest.fail("cells must not run"),
    )
    with pytest.raises(ValueError, match="10,000 simulations"):
        run_v6_worst_case_power(
            n_sim=V6_MINIMUM_SIMULATIONS_PER_CELL - 1,
            official=True,
        )
    with pytest.raises(ValueError, match="seed must be 20262003"):
        run_v6_worst_case_power(
            n_sim=V6_MINIMUM_SIMULATIONS_PER_CELL,
            official=True,
            seed=V6_POWER_SEED + 1,
        )
    with pytest.raises(ValueError, match=r"\[12,18,24,30\]"):
        run_v6_worst_case_power(
            n_sim=V6_MINIMUM_SIMULATIONS_PER_CELL,
            official=True,
            episode_seed_grid=V6_EPISODE_SEED_GRID[:-1],
        )


def test_cli_rejects_exploratory_counts_without_writing(tmp_path):
    process = subprocess.run(
        [
            sys.executable,
            "scripts/power_controlled_v6.py",
            "--n-sim",
            "9999",
            "--out-dir",
            str(tmp_path / "power"),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert process.returncode == 2
    assert "at least 10,000 simulations per cell" in process.stderr
    assert not (tmp_path / "power").exists()
