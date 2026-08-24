"""Linear probe machinery: does it find real signal, and refuse fake signal?"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from config import STRATEGIES
from src.probing import (
    ActivationStore,
    select_l2,
    align_to_log,
    behavioural_readout_features,
    behavioural_readout_baseline,
    context_leakage_check,
    cross_val_probe,
    fit_probe,
    grouped_folds,
    layer_sweep,
    majority_baseline,
    nearest_centroid_accuracy,
    probe_belief_trajectory,
    shuffled_label_baseline,
    stratified_episode_split,
    switch_lag,
)

D = 64
N_EP = 30
N_ROUNDS = 6


def synth(signal_strength=3.0, seed=0, d=D, n_ep=N_EP, n_rounds=N_ROUNDS,
          episode_nuisance=5.0, n_layers=3):
    """Activations = class direction + a large EPISODE-specific nuisance + noise.

    The episode nuisance is deliberately larger than the signal: it is what makes
    row-wise splitting leak, and it is realistic (rounds inside an episode share
    a prompt prefix).
    """
    rng = np.random.default_rng(seed)
    dirs = rng.normal(0, 1, size=(len(STRATEGIES), d))
    dirs /= np.linalg.norm(dirs, axis=1, keepdims=True)
    X, y, groups, meta = [], [], [], []
    for e in range(n_ep):
        cls = e % len(STRATEGIES)
        nuisance = rng.normal(0, episode_nuisance, size=d)
        for r in range(1, n_rounds + 1):
            v = signal_strength * dirs[cls] + nuisance + rng.normal(0, 1.0, size=d)
            X.append(np.stack([v + rng.normal(0, 0.1, size=d) for _ in range(n_layers)]))
            y.append(STRATEGIES[cls])
            groups.append("ep%02d" % e)
            meta.append({"episode_id": "ep%02d" % e, "round": r})
    return np.asarray(X), np.asarray(y, dtype=object), np.asarray(groups, dtype=object), meta


# --------------------------------------------------------------------------
# fitting
# --------------------------------------------------------------------------


def test_probe_recovers_a_linearly_separable_signal():
    X, y, _, _ = synth(signal_strength=6.0, episode_nuisance=0.0)
    probe = fit_probe(X[:, 0, :], y, l2=1.0)
    assert float(np.mean(probe.predict(X[:, 0, :]) == y)) > 0.95


def test_probe_standardiser_uses_training_statistics_only():
    X, y, _, _ = synth()
    probe = fit_probe(X[:60, 0, :], y[:60])
    assert probe.mu.shape == (D,) and probe.sigma.shape == (D,)
    assert np.all(probe.sigma > 0)
    # Predicting on unseen rows must not require refitting the scaler.
    assert probe.predict(X[60:, 0, :]).shape == (len(y) - 60,)


def test_probe_probabilities_are_a_distribution():
    X, y, _, _ = synth()
    p = fit_probe(X[:, 0, :], y).predict_proba(X[:, 0, :])
    assert np.allclose(p.sum(axis=1), 1.0)
    assert (p >= 0).all() and (p <= 1).all()


def test_probe_roundtrips_through_disk(tmp_path):
    X, y, _, _ = synth(signal_strength=5.0, episode_nuisance=0.5)
    original = fit_probe(X[:, 0, :], y, l2=10.0)
    path = str(tmp_path / "probe.npz")
    original.save(path)
    loaded = type(original).load(path)
    assert loaded.classes == original.classes
    assert loaded.l2 == pytest.approx(10.0)
    assert np.allclose(loaded.predict_proba(X[:8, 0, :]), original.predict_proba(X[:8, 0, :]))


# --------------------------------------------------------------------------
# grouped splitting
# --------------------------------------------------------------------------


def test_folds_never_split_an_episode_across_train_and_test():
    _, _, groups, _ = synth()
    folds = grouped_folds(groups, n_folds=5, seed=0)
    assert sum(len(f) for f in folds) == len(groups)
    for f in folds:
        test_eps = set(groups[f])
        train_eps = set(groups[np.setdiff1d(np.arange(len(groups)), f)])
        assert not (test_eps & train_eps)


def test_stratified_episode_split_is_disjoint_and_balanced():
    _, y, groups, _ = synth(n_ep=24)
    split = stratified_episode_split(y, groups, seed=7)
    episode_sets = {name: set(groups[idx]) for name, idx in split.items()}
    assert not (episode_sets["train"] & episode_sets["dev"])
    assert not (episode_sets["train"] & episode_sets["test"])
    assert not (episode_sets["dev"] & episode_sets["test"])
    assert set.union(*episode_sets.values()) == set(groups)
    for idx in split.values():
        assert set(y[idx]) == set(STRATEGIES)


def test_stratified_episode_split_refuses_multilabel_episode():
    with pytest.raises(ValueError, match="multiple labels"):
        stratified_episode_split(["fairness", "risk"] * 4, ["same"] * 8)


def test_row_wise_splitting_would_inflate_accuracy():
    """The reason splits are by episode. If this ever stops being true, the
    episode-grouped guard has become unnecessary -- but it is true."""
    X, y, groups, _ = synth(signal_strength=0.0, episode_nuisance=8.0)
    honest = cross_val_probe(X[:, 0, :], y, groups, n_folds=5, seed=0).accuracy
    row_groups = np.array([str(i) for i in range(len(y))], dtype=object)
    leaky = cross_val_probe(X[:, 0, :], y, row_groups, n_folds=5, seed=0).accuracy
    assert leaky > honest + 0.2, (leaky, honest)
    assert honest < 0.55


# --------------------------------------------------------------------------
# does it find signal, and refuse noise?
# --------------------------------------------------------------------------


def test_cross_val_finds_real_signal_despite_episode_nuisance():
    """Nuisance comparable to signal, 45 episodes -- a fair regime.

    (Nuisance an order of magnitude above the signal with only 30 episodes is
    genuinely unlearnable and the probe correctly returns chance there; that is
    a property of the data, not a bug, and is why the real runs need enough
    episodes.)
    """
    X, y, groups, _ = synth(signal_strength=5.0, episode_nuisance=1.5, n_ep=45)
    res = cross_val_probe(X[:, 0, :], y, groups, n_folds=5, seed=0)
    assert res.accuracy > 0.7
    assert res.n_test == len(y)
    assert set(res.confusion) == set(STRATEGIES)


def test_cross_val_is_at_chance_on_pure_noise():
    X, y, groups, _ = synth(signal_strength=0.0, episode_nuisance=1.0)
    res = cross_val_probe(X[:, 0, :], y, groups, n_folds=5, seed=0)
    assert res.accuracy < 0.55


def test_shuffled_label_baseline_stays_at_chance_when_signal_is_real():
    X, y, groups, _ = synth(signal_strength=5.0, episode_nuisance=1.5, n_ep=45)
    real = cross_val_probe(X[:, 0, :], y, groups, n_folds=5, seed=0).accuracy
    null = shuffled_label_baseline(X[:, 0, :], y, groups, n_repeats=3, n_folds=5, seed=0)
    assert real > null["mean"] + 0.2, (real, null)
    assert null["mean"] < 0.55


def test_select_l2_picks_a_value_that_beats_the_extremes():
    X, y, groups, _ = synth(signal_strength=5.0, episode_nuisance=1.5, n_ep=45)
    best, table = select_l2(X[:, 0, :], y, groups, grid=(0.01, 1.0, 100.0), n_folds=4, seed=0)
    assert best in (0.01, 1.0, 100.0)
    assert len(table) == 3
    assert max(t["accuracy"] for t in table) == pytest.approx(
        [t["accuracy"] for t in table if t["l2"] == best][0]
    )


def test_majority_baseline():
    assert majority_baseline(["a", "a", "b"]) == pytest.approx(2 / 3)
    assert np.isnan(majority_baseline([]))


def test_layer_sweep_returns_one_result_per_layer():
    X, y, groups, meta = synth(n_layers=4)
    store = ActivationStore(acts=X, meta=meta)
    res = layer_sweep(store, y, groups, n_folds=3, seed=0)
    assert len(res) == 4
    assert all(0.0 <= r.accuracy <= 1.0 for r in res)


def test_nearest_centroid_layer_selector_finds_signal():
    X, y, groups, _ = synth(signal_strength=5.0, episode_nuisance=0.3, n_ep=24)
    split = stratified_episode_split(y, groups, seed=0)
    acc = nearest_centroid_accuracy(
        X[split["train"], 0, :], y[split["train"]],
        X[split["dev"], 0, :], y[split["dev"]],
    )
    assert acc > 0.8


# --------------------------------------------------------------------------
# storage and alignment
# --------------------------------------------------------------------------


def test_store_roundtrips_through_disk(tmp_path):
    X, y, _, meta = synth(n_layers=2)
    store = ActivationStore(acts=X.astype(np.float16), meta=meta)
    path = str(tmp_path / "acts.npz")
    store.save(path)
    back = ActivationStore.load(path)
    assert back.n_rows == store.n_rows
    assert back.n_layers == 2 and back.d_model == D
    assert back.meta[0] == store.meta[0]
    assert np.allclose(back.layer(0), store.layer(0))


def test_store_rejects_mismatched_meta():
    X, _, _, meta = synth()
    with pytest.raises(ValueError, match="meta"):
        ActivationStore(acts=X, meta=meta[:-1])


def test_align_to_log_raises_rather_than_silently_dropping():
    X, y, _, meta = synth()
    store = ActivationStore(acts=X, meta=meta)
    df = pd.DataFrame({"episode_id": [m["episode_id"] for m in meta],
                       "round": [m["round"] for m in meta]})
    assert (align_to_log(store, df) == np.arange(len(meta))).all()
    with pytest.raises(ValueError, match="no matching"):
        align_to_log(store, df.iloc[:-5])


# --------------------------------------------------------------------------
# baselines and the headline analysis
# --------------------------------------------------------------------------


def _mock_log(behaviour_lag=3, probe_perfect_from=1, n_ep=12, n_rounds=10, swap_round=5):
    """A log where behaviour switches to the new frame `behaviour_lag` rounds
    after the swap, so `switch_lag` has a known right answer."""
    rows = []
    for e in range(n_ep):
        t0 = STRATEGIES[e % 3]
        t1 = STRATEGIES[(e % 3 + 1) % 3]
        for r in range(1, n_rounds + 1):
            since = r - swap_round
            active = t0 if r <= swap_round else t1
            if r <= swap_round:
                strat = t0
            else:
                strat = t1 if since >= behaviour_lag else t0
            rows.append({
                "episode_id": "sw%02d" % e, "round": r, "condition": "swap",
                "hidden_target_type": active, "initial_target_type": t0,
                "final_target_type": t1, "swap_condition": True,
                "rounds_since_swap": since, "primary_strategy": strat,
                "displayed_choice": "A" if strat == active else "B",
                "history_source_episode_id": "sw%02d" % e,
            })
    return pd.DataFrame(rows)


def test_behavioural_readout_baseline_runs_and_is_informative():
    df = _mock_log(behaviour_lag=1)
    res = behavioural_readout_baseline(df, n_folds=4, seed=0)
    assert 0.0 <= res.accuracy <= 1.0
    assert res.n_test == len(df)


def test_switch_lag_recovers_a_known_lag():
    df = _mock_log(behaviour_lag=3)
    traj = df.copy()
    traj["probe_pred"] = traj["hidden_target_type"]          # oracle probe: flips at once
    traj["probe_matches_final"] = (traj["probe_pred"] == traj["final_target_type"]).astype(int)
    traj["behaviour_matches_final"] = (traj["primary_strategy"] == traj["final_target_type"]).astype(int)
    out = switch_lag(traj, seed=0, n_boot=500)
    assert out["mean_probe_lag"] == pytest.approx(1.0)
    assert out["mean_behaviour_lag"] == pytest.approx(3.0)
    assert out["mean_behaviour_minus_probe"] == pytest.approx(2.0)
    assert out["ci95"][0] <= 2.0 <= out["ci95"][1]


def test_switch_lag_reports_episodes_that_never_flip_separately():
    df = _mock_log(behaviour_lag=99)  # never flips within the horizon
    traj = df.copy()
    traj["probe_pred"] = traj["hidden_target_type"]
    traj["probe_matches_final"] = (traj["probe_pred"] == traj["final_target_type"]).astype(int)
    traj["behaviour_matches_final"] = (traj["primary_strategy"] == traj["final_target_type"]).astype(int)
    out = switch_lag(traj, seed=0, n_boot=100)
    assert out["n_behaviour_never_flipped"] == out["n_swap_episodes"]
    assert out["n_both_flipped"] == 0
    assert "mean_behaviour_minus_probe" not in out  # not silently imputed


def test_probe_trajectory_joins_cleanly():
    df = _mock_log()
    n = len(df)
    rng = np.random.default_rng(0)
    acts = rng.normal(size=(n, 1, 16))
    meta = [{"episode_id": r["episode_id"], "round": int(r["round"])} for _, r in df.iterrows()]
    store = ActivationStore(acts=acts, meta=meta)
    rows = align_to_log(store, df)
    probe = fit_probe(store.layer(0), df["hidden_target_type"].tolist(), classes=list(STRATEGIES))
    traj = probe_belief_trajectory(probe, store, 0, df, rows)
    assert len(traj) == n
    for col in ("probe_pred", "probe_matches_final", "behaviour_matches_final"):
        assert col in traj.columns
    assert set(traj["probe_pred"]) <= set(STRATEGIES)


def test_context_leakage_check_reports_nothing_when_no_shuffled_episodes():
    df = _mock_log()
    n = len(df)
    acts = np.random.default_rng(0).normal(size=(n, 1, 16))
    meta = [{"episode_id": r["episode_id"], "round": int(r["round"])} for _, r in df.iterrows()]
    store = ActivationStore(acts=acts, meta=meta)
    rows = align_to_log(store, df)
    probe = fit_probe(store.layer(0), df["hidden_target_type"].tolist(), classes=list(STRATEGIES))
    out = context_leakage_check(probe, store, 0, df, rows)
    assert out["n"] == 0


# --------------------------------------------------------------------------
# The lag metric must not manufacture a result out of probe noise
# --------------------------------------------------------------------------


def _traj_with_probe(df, probe_flags_fn, seed=0):
    rng = np.random.default_rng(seed)
    t = df.copy()
    t["probe_matches_final"] = [probe_flags_fn(rng) for _ in range(len(t))]
    t["behaviour_matches_final"] = (t["primary_strategy"] == t["final_target_type"]).astype(int)
    return t


def test_raw_lag_is_inflated_by_an_uninformative_probe():
    """A probe carrying NO information still appears to 'lead' the behaviour,
    because first-match is biased downwards by noise. This is the reason
    null_lag_difference exists."""
    from src.probing import null_lag_difference

    df = _mock_log(behaviour_lag=3, n_ep=30)
    traj = _traj_with_probe(df, lambda rng: int(rng.random() < 1 / 3), seed=0)
    out = null_lag_difference(traj, n_perm=400, seed=0)
    assert out["observed_difference"] > 0          # spurious "probe leads"
    assert out["calibrated_difference"] == pytest.approx(0.0, abs=0.5)
    assert out["p_value_one_sided"] > 0.05         # correctly NOT significant


def test_permutation_null_is_silent_when_the_probe_is_always_right():
    """An always-right probe has no permutable timing structure, so the
    first-crossing null correctly reports nothing. That is a limitation of
    first-crossing, not of the null -- and it is why trajectory_gap is the
    primary statistic."""
    from src.probing import null_lag_difference

    df = _mock_log(behaviour_lag=4, n_ep=30)
    t = df.copy()
    t["probe_matches_final"] = (t["rounds_since_swap"] >= 1).astype(int)
    t["behaviour_matches_final"] = (t["primary_strategy"] == t["final_target_type"]).astype(int)
    out = null_lag_difference(t, n_perm=400, seed=0)
    assert out["calibrated_difference"] == pytest.approx(0.0, abs=1e-9)


def test_trajectory_gap_detects_a_genuine_lead():
    from src.probing import trajectory_gap

    df = _mock_log(behaviour_lag=4, n_ep=30)
    t = df.copy()
    t["probe_matches_final"] = (t["rounds_since_swap"] >= 1).astype(int)
    t["behaviour_matches_final"] = (t["primary_strategy"] == t["final_target_type"]).astype(int)
    out = trajectory_gap(t, n_boot=400, seed=0)
    assert out["statistic"] > 0.3
    assert out["ci95"][0] > 0


def test_trajectory_gap_does_not_manufacture_a_lead_from_probe_noise():
    """The case that breaks first-crossing. An uninformative probe against a
    behaviour that genuinely flips at round 3: first-crossing reports a
    spurious +0.74-round "probe leads"; the baseline-corrected statistic
    correctly reports the opposite sign (the BEHAVIOUR leads)."""
    from src.probing import null_lag_difference, trajectory_gap

    df = _mock_log(behaviour_lag=3, n_ep=40)
    rng = np.random.default_rng(0)
    t = df.copy()
    t["probe_matches_final"] = [int(rng.random() < 1 / 3) for _ in range(len(t))]
    t["behaviour_matches_final"] = (t["primary_strategy"] == t["final_target_type"]).astype(int)

    naive = null_lag_difference(t, n_perm=300, seed=0)
    assert naive["observed_difference"] > 0        # the trap

    out = trajectory_gap(t, n_boot=400, seed=0)
    assert out["statistic"] < 0                    # the trap avoided
    assert out["ci95"][1] < 0


def test_trajectory_gap_is_baseline_corrected():
    """A probe that is uniformly better than the behaviour but does not CHANGE
    after the swap must not register as leading."""
    from src.probing import trajectory_gap

    df = _mock_log(behaviour_lag=3, n_ep=30)
    t = df.copy()
    t["probe_matches_final"] = 1                      # always right, never changes
    t["behaviour_matches_final"] = (t["primary_strategy"] == t["final_target_type"]).astype(int)
    out = trajectory_gap(t, n_boot=300, seed=0)
    assert out["statistic"] < 0     # only the behaviour rises, so the gap is negative
    assert out["probe_pre_swap_baseline"] == pytest.approx(1.0)


def test_switch_lag_now_reports_the_calibration():
    df = _mock_log(behaviour_lag=3)
    traj = df.copy()
    traj["probe_pred"] = traj["hidden_target_type"]
    traj["probe_matches_final"] = (traj["probe_pred"] == traj["final_target_type"]).astype(int)
    traj["behaviour_matches_final"] = (traj["primary_strategy"] == traj["final_target_type"]).astype(int)
    out = switch_lag(traj, seed=0, n_boot=200)
    assert "null_calibration" in out
    assert "calibrated_difference" in out["null_calibration"]
    assert "do NOT quote alone" in out["interpretation"]
