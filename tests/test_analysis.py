"""Statistics helpers and the analysis pipeline."""

from __future__ import annotations

import os
import warnings

import numpy as np
import pytest

from config import ExperimentConfig, JudgeConfig, ModelConfig
from src.analysis import (
    adaptation_after_swap,
    classifier_target_agreement,
    feedback_contingency,
    fit_primary_history_interaction,
    format_summary,
    load_dataframe,
    match_rate_by_round,
    per_condition_tests,
    plot_adaptation,
    rounds_to_adapt,
    run_full_analysis,
    scenario_balance,
    strategy_persistence,
)
from src.experiment import run_experiment
from src.stats_utils import (
    cluster_bootstrap_mean,
    design_matrix,
    dummies,
    logistic_regression,
    permutation_slope_test,
    permutation_type_test,
    wilson_ci,
)


# --------------------------------------------------------------------------
# stats_utils
# --------------------------------------------------------------------------


def test_wilson_ci_brackets_the_point_estimate():
    lo, hi = wilson_ci(30, 100)
    assert lo < 0.30 < hi
    assert 0.0 <= lo and hi <= 1.0


def test_cluster_bootstrap_recovers_the_mean():
    rng = np.random.default_rng(0)
    values = rng.binomial(1, 0.4, 400).astype(float)
    clusters = np.repeat(np.arange(40), 10)
    ci = cluster_bootstrap_mean(values, clusters, n_boot=500, seed=1)
    assert ci.mean == pytest.approx(values.mean())
    assert ci.lo < ci.mean < ci.hi
    assert ci.n_clusters == 40


def test_cluster_bootstrap_is_wider_than_naive_bootstrap_when_clustered():
    """Rounds within an episode are correlated; ignoring that understates
    uncertainty, and the interval must reflect it."""
    rng = np.random.default_rng(2)
    per_cluster = rng.binomial(1, 0.5, 30)
    values = np.repeat(per_cluster, 10).astype(float)  # perfectly correlated within cluster
    clusters = np.repeat(np.arange(30), 10)
    clustered = cluster_bootstrap_mean(values, clusters, n_boot=800, seed=3)
    naive = cluster_bootstrap_mean(values, np.arange(len(values)), n_boot=800, seed=3)
    assert (clustered.hi - clustered.lo) > 2 * (naive.hi - naive.lo)


def test_cluster_bootstrap_on_empty_input():
    ci = cluster_bootstrap_mean([], [], n_boot=10)
    assert np.isnan(ci.mean)


def test_permutation_slope_test_detects_a_real_trend():
    rounds, outcomes, clusters = [], [], []
    rng = np.random.default_rng(0)
    for ep in range(40):
        for r in range(1, 9):
            rounds.append(r)
            clusters.append(ep)
            outcomes.append(float(rng.random() < 0.1 + 0.09 * r))
    res = permutation_slope_test(rounds, outcomes, clusters, n_perm=500, seed=0)
    assert res["observed_slope"] > 0
    assert res["p_value_one_sided"] < 0.05


def test_permutation_slope_test_on_flat_data():
    rng = np.random.default_rng(1)
    rounds, outcomes, clusters = [], [], []
    for ep in range(40):
        for r in range(1, 9):
            rounds.append(r)
            clusters.append(ep)
            outcomes.append(float(rng.random() < 0.4))
    res = permutation_slope_test(rounds, outcomes, clusters, n_perm=500, seed=0)
    assert res["p_value_one_sided"] > 0.05


def test_permutation_type_test_detects_alignment():
    strategies, episodes = [], []
    type_map = {}
    for ep in range(30):
        t = ["fairness", "risk", "expertise"][ep % 3]
        type_map["e%d" % ep] = t
        for _ in range(6):
            strategies.append(t)  # perfectly aligned
            episodes.append("e%d" % ep)
    res = permutation_type_test(strategies, type_map, episodes, n_perm=500, seed=0)
    assert res["observed_match_rate"] == 1.0
    assert res["p_value_one_sided"] < 0.01


def test_permutation_type_test_is_not_fooled_by_a_constant_strategy():
    """An agent that always says "fairness" matches fairness targets 1/3 of the
    time; shuffling the labels leaves that unchanged, so p must be large."""
    strategies, episodes = [], []
    type_map = {}
    for ep in range(30):
        type_map["e%d" % ep] = ["fairness", "risk", "expertise"][ep % 3]
        for _ in range(6):
            strategies.append("fairness")
            episodes.append("e%d" % ep)
    res = permutation_type_test(strategies, type_map, episodes, n_perm=500, seed=0)
    assert res["observed_match_rate"] == pytest.approx(1 / 3)
    assert res["p_value_one_sided"] > 0.2


def test_logistic_regression_recovers_known_coefficients():
    rng = np.random.default_rng(0)
    n = 8000
    x = rng.normal(size=n)
    p = 1.0 / (1.0 + np.exp(-(-0.5 + 1.2 * x)))
    y = (rng.random(n) < p).astype(float)
    X, names = design_matrix({"x": x})
    fit = logistic_regression(X, y, names)
    assert fit.converged
    assert fit.coef[0] == pytest.approx(-0.5, abs=0.12)
    assert fit.coef[1] == pytest.approx(1.2, abs=0.12)
    assert fit.p[1] < 1e-6
    assert "logistic regression" in fit.summary()


def test_cluster_robust_ses_are_larger_under_clustering():
    rng = np.random.default_rng(0)
    n_clusters, per = 60, 12
    cluster_effect = rng.normal(0, 2.0, n_clusters)
    x, y, cl = [], [], []
    for c in range(n_clusters):
        xc = rng.normal(size=per)
        p = 1.0 / (1.0 + np.exp(-(cluster_effect[c] + 0.3 * xc)))
        x.extend(xc)
        y.extend((rng.random(per) < p).astype(float))
        cl.extend([c] * per)
    X, names = design_matrix({"x": np.array(x)})
    plain = logistic_regression(X, np.array(y), names)
    robust = logistic_regression(X, np.array(y), names, clusters=np.array(cl))
    assert robust.se[0] > plain.se[0]


def test_dummies_uses_treatment_coding():
    d = dummies(["a", "b", "c", "a"], ["a", "b", "c"], "g")
    assert set(d) == {"g[b]", "g[c]"}
    assert list(d["g[b]"]) == [0.0, 1.0, 0.0, 0.0]


def test_primary_history_interaction_is_the_planned_four_term_model(mock_run):
    res, _ = mock_run
    result = fit_primary_history_interaction(load_dataframe(res.log_path))
    assert result is not None
    assert result["primary_term"] == "round:full_history"
    assert result["fit"].names == [
        "intercept", "round_0_to_1", "full_history", "round:full_history"
    ]


# --------------------------------------------------------------------------
# Analysis pipeline, run on mock data
# --------------------------------------------------------------------------


@pytest.fixture(scope="module")
def mock_run(tmp_path_factory):
    out = tmp_path_factory.mktemp("mockrun")
    cfg = ExperimentConfig(
        experiment_id="analysis_test",
        n_rounds=6,
        swap_round=3,
        n_episode_seeds=6,
        conditions=["full_history", "no_history", "shuffled_history", "random_target", "swap"],
        model=ModelConfig(provider="mock:win_stay_lose_shift", model="mock"),
        judge=JudgeConfig(kind="keyword"),
        out_dir=str(out),
    )
    res = run_experiment(cfg, run_id="analysis_test")
    return res, str(out)


def test_load_dataframe_derives_the_expected_columns(mock_run):
    res, _ = mock_run
    df = load_dataframe(res.log_path)
    for col in ("match", "match_initial", "match_final", "chose_a", "switched", "match_round1"):
        assert col in df.columns
    assert df["match"].isin([0, 1]).all()
    assert len(df) == res.n_records


def test_match_rate_by_round_has_one_row_per_condition_round(mock_run):
    res, _ = mock_run
    df = load_dataframe(res.log_path)
    tbl = match_rate_by_round(df, n_boot=200)
    assert len(tbl) == df.groupby(["condition", "round"]).ngroups
    assert (tbl["ci_lo"] <= tbl["mean"]).all()
    assert (tbl["mean"] <= tbl["ci_hi"]).all()


def test_adaptation_table_spans_the_swap(mock_run):
    res, _ = mock_run
    df = load_dataframe(res.log_path)
    tbl = adaptation_after_swap(df, n_boot=200)
    assert not tbl.empty
    assert tbl["rounds_since_swap"].min() < 0 < tbl["rounds_since_swap"].max()
    eps = rounds_to_adapt(df)
    assert len(eps) == df[df["swap_condition"]]["episode_id"].nunique()
    assert set(eps["initial_target_type"]) and (eps["initial_target_type"] != eps["final_target_type"]).all()


def test_scenario_balance_is_exact_by_construction(mock_run):
    res, _ = mock_run
    df = load_dataframe(res.log_path)
    bal = scenario_balance(df)
    for cond, info in bal.items():
        assert info["identical_across_types"], (cond, info)


def test_empty_swap_plot_is_explicit_and_warning_free(tmp_path):
    import pandas as pd

    path = tmp_path / "empty-swap.png"
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        plot_adaptation(pd.DataFrame(), str(path), swap_round=5)
    assert not [w for w in caught if "No artists with labels" in str(w.message)]
    assert path.exists()


def test_persistence_and_contingency_tables(mock_run):
    res, _ = mock_run
    df = load_dataframe(res.log_path)
    pers = strategy_persistence(df)
    assert set(pers["condition"]) == set(df["condition"].unique())
    assert ((pers["repeat_rate"] >= 0) & (pers["repeat_rate"] <= 1)).all()
    cont = feedback_contingency(df)
    # The win-stay/lose-shift mock must show exactly that signature where it can
    # see feedback, and nothing where it cannot.
    full = cont[cont["condition"] == "full_history"].iloc[0]
    assert full["switch_after_B"] > full["switch_after_A"]
    nohist = cont[cont["condition"] == "no_history"].iloc[0]
    assert nohist["switch_after_A"] == pytest.approx(nohist["switch_after_B"], abs=0.05)


def test_classifier_target_agreement_flags_the_shared_lexicon(mock_run):
    res, _ = mock_run
    df = load_dataframe(res.log_path)
    agree = classifier_target_agreement(df)
    # With the default keyword classifier the two instruments ARE the same.
    assert agree["argmax_agreement"] == pytest.approx(1.0)


def test_per_condition_tests_produce_valid_p_values(mock_run):
    res, _ = mock_run
    df = load_dataframe(res.log_path)
    tests = per_condition_tests(df, seed=0)
    assert set(tests["condition"]) == set(df["condition"].unique())
    assert ((tests["slope_p"] > 0) & (tests["slope_p"] <= 1)).all()


def test_run_full_analysis_writes_every_figure_and_table(mock_run, tmp_path):
    res, _ = mock_run
    figs = tmp_path / "figs"
    tabs = tmp_path / "tabs"
    summary = run_full_analysis(res.log_path, str(figs), str(tabs), n_boot=200, seed=0)
    for path in summary["figures"].values():
        assert os.path.exists(path) and os.path.getsize(path) > 1000
    for name in (
        "match_rate_by_round.csv",
        "overall_rates.csv",
        "strategy_distribution.csv",
        "adaptation_after_swap.csv",
        "permutation_tests.csv",
        "summary.json",
    ):
        assert (tabs / name).exists()
    assert summary["n_records"] == res.n_records
    assert summary["primary_history_interaction"]["primary_term"] == "round:full_history"
    text = format_summary(summary)
    assert "condition" in text and "full_history" in text
