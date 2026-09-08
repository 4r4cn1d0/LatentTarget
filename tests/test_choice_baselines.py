from __future__ import annotations

import copy
import json
from pathlib import Path

import numpy as np
import pytest

from config import ControlledExperimentConfig, ModelConfig
from src.controlled_experiment import run_controlled_experiment
from src.choice_baselines import (
    FRAMES, ChoiceData, HistoryFeatures, balanced_weights, bundle_scores,
    descriptive, group_folds, nested_predictions, parameter_grid, predict,
    prepare_data, score_predictions, select_on_training, summarize, training_prior,
)

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def plan():
    return json.loads((ROOT / "docs/baseline_comparison_20260907.json").read_text())


@pytest.fixture
def small_plan(plan):
    return dict(plan, outer_folds=2, inner_folds=2, n_boot=20,
                beta=[3.0], stickiness=[1.0], prior_power=[1.0],
                alpha=[.3], hazard=[.2], repeat_strength=[0, .75])


@pytest.fixture(scope="module")
def mock_records(tmp_path_factory):
    directory = tmp_path_factory.mktemp("baseline-mock")
    config = ControlledExperimentConfig(
        n_episode_seeds=4,
        conditions=["full_history", "no_history", "shuffled_history", "random_target", "swap"],
        model=ModelConfig(provider="mock:v4_random", model="mock"),
        out_dir=str(directory),
    )
    return run_controlled_experiment(config, run_id="baseline-mock").records


def test_reward_update_only_changes_chosen_frame():
    f = HistoryFeatures([[(0, 1), (0, 0), (1, 1)], []])
    np.testing.assert_allclose(f.reward_values(.5), [[.375, .75, .5], [.5, .5, .5]])


def test_bayes_update_matches_hand_calculation():
    f = HistoryFeatures([[(0, 1)], [(0, 0)], []])
    np.testing.assert_allclose(f.posterior(0)[0], np.array([.72, .38, .38]) / 1.48)
    np.testing.assert_allclose(f.posterior(0)[1], np.array([.28, .62, .62]) / 1.52)
    np.testing.assert_allclose(f.posterior(0)[2], [1/3] * 3)
    np.testing.assert_allclose(f.posterior(.2), .8 * f.posterior(0) + .2 / 3)
    np.testing.assert_allclose(f.posterior(1), np.full((3, 3), 1/3))


def test_static_belief_order_invariant_dynamic_not():
    f = HistoryFeatures([[(0, 1), (1, 0)], [(1, 0), (0, 1)]])
    np.testing.assert_allclose(f.posterior(0)[0], f.posterior(0)[1])
    assert not np.allclose(f.posterior(.5)[0], f.posterior(.5)[1])


def test_frequency_ignores_rewards():
    a = HistoryFeatures([[(0, 1), (2, 0)]])
    b = HistoryFeatures([[(0, 0), (2, 1)]])
    np.testing.assert_array_equal(a.frequency, b.frequency)


def test_repeat_and_win_stay_rules():
    f = HistoryFeatures([[(0, 1)], [(1, 0)], []])
    prior = np.array([.2, .3, .5])
    repeat = predict(f, "repeat_last", {"strength": 1}, prior)
    win = predict(f, "win_stay_expertise", {"strength": 1}, prior)
    assert repeat[:2].argmax(1).tolist() == [0, 1]
    assert win.argmax(1).tolist() == [0, 2, 2]
    np.testing.assert_allclose(repeat[2], .98 * prior + .02 / 3)


def test_all_declared_models_are_finite_normalized(plan):
    features = HistoryFeatures([[], [(0, 1)] * 19, [(2, 0)] * 19])
    for family in plan["simple_families"] + plan["belief_families"]:
        for params in parameter_grid(family, plan):
            p = predict(features, family, params, np.array([.01, .08, .91]), plan["lapse"])
            assert p.min() >= plan["lapse"] / 3
            np.testing.assert_allclose(p.sum(1), 1)
            score_predictions(p, np.array([0, 1, 2]))


def test_uniform_loss_brier_and_fractional_tie_accuracy():
    s = score_predictions(np.full((3, 3), 1/3), np.arange(3))
    np.testing.assert_allclose(s["log_loss"], np.log(3))
    np.testing.assert_allclose(s["brier"], 2/3)
    np.testing.assert_allclose(s["accuracy"], 1/3)
    p = np.array([[.49, .49, .02]])
    assert score_predictions(p, np.array([1]))["accuracy"][0] == .5


@pytest.mark.parametrize("p", [np.array([[0., .5, .5]]), np.array([[np.nan, .5, .5]]), np.ones((1, 3))])
def test_reject_bad_probabilities(p):
    with pytest.raises(ValueError):
        score_predictions(p, np.array([0]))


def test_prepare_data_reconstructs_actual_shuffled_history(mock_records):
    data = prepare_data(mock_records)
    by_key = {(r["episode_id"], r["round"]): r for r in mock_records}
    for meta, history in zip(data.metadata, data.histories):
        row = by_key[meta["episode_id"], meta["round"]]
        if row["condition"] == "no_history":
            assert history == ()
        elif row["condition"] == "shuffled_history" and row["round"] > 1:
            donor = by_key[row["history_source_episode_id"], row["round"] - 1]
            assert history[-1] == (FRAMES.index(donor["selected_frame"]), int(donor["target_choice"] == "A"))


@pytest.mark.parametrize("damage", ["duplicate", "missing", "future_feedback", "donor", "cross_seed", "mapping", "fallback"])
def test_reject_corrupt_data(mock_records, damage):
    rows = copy.deepcopy(mock_records)
    r = next(r for r in rows if r["condition"] == "shuffled_history" and r["round"] == 2)
    if damage == "duplicate":
        rows.append(rows[0])
    elif damage == "missing":
        rows.pop()
    elif damage == "future_feedback":
        r["visible_history"][0]["round"] = 2
    elif damage == "donor":
        r["history_source_episode_id"] = "missing"
    elif damage == "cross_seed":
        r["history_source_episode_id"] = next(x["episode_id"] for x in rows if x["episode_index"] != r["episode_index"])
    elif damage == "mapping":
        rows[0]["selected_frame"] = "not-a-frame"
    else:
        rows[0]["fallback_used"] = rows[0]["selection_valid"]
    with pytest.raises(ValueError):
        prepare_data(rows)


def test_group_split_is_complete_reproducible_and_disjoint(plan):
    folds = group_folds(np.repeat(np.arange(20), 15), 5, plan["split_seed"])
    assert all(len(f) == 4 for f in folds)
    assert sorted(np.concatenate(folds)) == list(range(20))
    assert [x.tolist() for x in folds] == [x.tolist() for x in group_folds(np.arange(20), 5, plan["split_seed"])]
    with pytest.raises(ValueError):
        group_folds([1, 2], 3, 1)


def test_hidden_metadata_cannot_change_predictions(mock_records, small_plan):
    data = prepare_data(mock_records)
    tampered = copy.deepcopy(mock_records)
    for row in tampered:
        row["hidden_target_type"] = "unavailable"
        row["initial_target_type"] = "unavailable"
        row["final_target_type"] = "unavailable"
        row["target_p_a"] = -1000
        row["swap_round"] = -1
    changed = prepare_data(tampered)
    p, _, _ = nested_predictions(data, small_plan)
    q, _, _ = nested_predictions(changed, small_plan)
    for family in p:
        np.testing.assert_array_equal(p[family], q[family])


def test_outer_test_responses_do_not_influence_inner_selection(mock_records, small_plan):
    data = prepare_data(mock_records)
    features = HistoryFeatures(data.histories)
    before = select_on_training(data, features, [0, 1], small_plan, 25)
    y = data.y.copy()
    y[np.isin(data.groups, [2, 3])] = (y[np.isin(data.groups, [2, 3])] + 1) % 3
    changed = ChoiceData(data.histories, y, data.groups, data.rounds, data.conditions, data.valid, data.metadata)
    after = select_on_training(changed, features, [0, 1], small_plan, 25)
    assert before == after


def test_prior_uses_only_training_rows_and_equal_condition_weight(mock_records):
    data = prepare_data(mock_records)
    mask = data.fitting_mask & (data.groups == 0)
    w = balanced_weights(data, mask)
    assert np.isclose(w[data.conditions[mask] == "full_history"].sum(), .5)
    assert np.isclose(w[data.conditions[mask] == "swap"].sum(), .5)
    prior = training_prior(data, mask)
    assert np.isclose(prior.sum(), 1) and (prior > 0).all()


def test_nested_repeatability_and_fold_isolation(mock_records, small_plan):
    data = prepare_data(mock_records)
    p, audit, folds = nested_predictions(data, small_plan)
    q, audit2, folds2 = nested_predictions(data, small_plan)
    assert audit == audit2
    np.testing.assert_array_equal(folds, folds2)
    for name in p:
        np.testing.assert_array_equal(p[name], q[name])
    for fold in audit:
        assert set(fold["test_groups"]).isdisjoint(fold["train_groups"])
        for inner in fold["inner_folds"]:
            assert set(inner["validation_groups"]).isdisjoint(inner["train_groups"])
            assert set(fold["test_groups"]).isdisjoint(inner["validation_groups"] + inner["train_groups"])
    report = summarize(data, p, small_plan)
    assert len(report["diagnostics"]) == 5
    assert {x["subset"] for x in report["contrasts"]} >= {"swap_post:fairness_to_risk", "condition:shuffled_history"}


def test_fallback_rows_remain_primary_not_in_valid_subset(mock_records, small_plan):
    rows = copy.deepcopy(mock_records)
    for row in rows:
        if row["round"] == 2:
            row["selection_valid"] = False
            row["fallback_used"] = True
    data = prepare_data(rows)
    pred = {f: np.full((len(data.y), 3), 1/3) for f in ["simple_selected", "belief_selected"]}
    summary = summarize(data, pred, small_plan)
    primary = next(r for r in summary["metrics"] if r["subset"] == "own_history")
    sensitivity = next(r for r in summary["metrics"] if r["subset"] == "own_history_valid_only")
    assert primary["n_rows"] > sensitivity["n_rows"]
    assert primary["n_invalid"] > 0
    assert sensitivity["n_invalid"] == 0


def test_bootstrap_resamples_bundles_and_keeps_outliers(mock_records):
    data = prepare_data(mock_records)
    values = data.groups.astype(float)
    groups, means = bundle_scores(data, values, data.fitting_mask)
    np.testing.assert_allclose(groups, means)
    result = descriptive([0, 0, 0, 0, 10], 100, 1)
    assert result["n_groups"] == 5 and result["mean"] == 2 and result["iqr_outliers"] == 1


def synthetic_choices(family: str, n_groups=8) -> ChoiceData:
    """Known generative policy, not evidence about a real language model."""
    rng = np.random.default_rng(606)
    histories, y, groups, rounds, conditions, metadata = [], [], [], [], [], []
    params = {"alpha": .7, "hazard": .2, "beta": 20., "stickiness": 0., "prior_power": 0.}
    for group in range(n_groups):
        for episode in range(12):
            history = []
            condition = "swap" if episode % 2 else "full_history"
            for round_number in range(1, 21):
                p = predict(HistoryFeatures([history]), family, params, np.full(3, 1/3))[0]
                action = int(rng.choice(3, p=p))
                target = (episode % 3 + int(condition == "swap" and round_number > 10)) % 3
                reward = int(rng.random() < (.72 if action == target else .38))
                histories.append(tuple(history))
                y.append(action); groups.append(group); rounds.append(round_number); conditions.append(condition)
                metadata.append({"episode_id": f"{group}-{episode}", "episode_index": group,
                                 "condition": condition, "round": round_number})
                history.append((action, reward))
    return ChoiceData(tuple(histories), np.array(y), np.array(groups), np.array(rounds),
                      np.array(conditions), np.ones(len(y), dtype=bool), tuple(metadata))


@pytest.mark.parametrize("generating_family", ["reward_learning", "belief_dynamic"])
def test_synthetic_recovery_discriminates_known_generating_policy(plan, generating_family):
    reduced = dict(plan, outer_folds=2, inner_folds=2, beta=[8., 20.], stickiness=[0.],
                   prior_power=[0.], alpha=[.3, .7], hazard=[.2], repeat_strength=[0, .75])
    data = synthetic_choices(generating_family)
    predictions, _, _ = nested_predictions(data, reduced)
    alternative = "belief_dynamic" if generating_family == "reward_learning" else "reward_learning"
    own = score_predictions(predictions[generating_family], data.y)["log_loss"][data.fitting_mask].mean()
    other = score_predictions(predictions[alternative], data.y)["log_loss"][data.fitting_mask].mean()
    assert own < other


def test_prediction_file_is_deterministic_and_has_every_fallback(mock_records, tmp_path):
    import gzip
    from scripts.compare_choice_baselines import save_predictions

    data = prepare_data(mock_records)
    predictions = {"uniform": np.full((len(data.y), 3), 1/3)}
    first, second = tmp_path / "a.csv.gz", tmp_path / "b.csv.gz"
    save_predictions(first, data, predictions, np.zeros(len(data.y), dtype=int))
    save_predictions(second, data, predictions, np.zeros(len(data.y), dtype=int))
    assert first.read_bytes() == second.read_bytes()
    with gzip.open(first, "rt") as handle:
        assert sum(1 for _ in handle) == len(data.y) + 1


def test_cli_refuses_overwrite_and_missing_data(tmp_path, plan):
    from scripts.compare_choice_baselines import main

    data_path = tmp_path / "fixture.jsonl"
    data_path.write_text("{}\n")
    data_path.with_suffix(".manifest.json").write_text("{}")
    plan_path = tmp_path / "plan.json"
    plan_path.write_text(json.dumps(dict(plan, runs={"V4": str(data_path)})))
    with pytest.raises(FileExistsError):
        main(["--plan", str(plan_path), "--out-dir", str(tmp_path)])
    missing_plan = dict(plan, runs={"V4": str(tmp_path / "not-available.jsonl")})
    plan_path.write_text(json.dumps(missing_plan))
    out_dir = tmp_path / "output"
    with pytest.raises(FileNotFoundError):
        main(["--plan", str(plan_path), "--out-dir", str(out_dir)])
    assert not out_dir.exists()
