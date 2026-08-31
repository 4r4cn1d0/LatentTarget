from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from config import STRATEGIES, TargetParams
from src.bayesian_observer import (
    BayesianEvidenceObserver,
    BayesianObserverConfig,
    LoggedPersuasionScorer,
    augment_with_bayesian_observer,
    baseline_corrected_trajectory_gap,
)


FAIR = "The fair and equal choice treats everyone impartially and reciprocally."
RISK = "The safe and reliable choice avoids risk and protects against downside."


def test_empty_history_is_uniform():
    obs = BayesianEvidenceObserver()
    assert np.allclose(obs.prior_from_history([]), [1 / 3] * 3)


def test_repeated_successful_fairness_messages_raise_fairness_posterior():
    obs = BayesianEvidenceObserver(config=BayesianObserverConfig(change_hazard=0.0))
    history = [{"message": FAIR, "choice": "A"}] * 4
    p = obs.prior_from_history(history)
    assert p[STRATEGIES.index("fairness")] > 0.75


def test_rejection_of_fairness_message_lowers_fairness_posterior():
    obs = BayesianEvidenceObserver(config=BayesianObserverConfig(change_hazard=0.0))
    p_a = obs.prior_from_history([{"message": FAIR, "choice": "A"}])
    p_b = obs.prior_from_history([{"message": FAIR, "choice": "B"}])
    i = STRATEGIES.index("fairness")
    assert p_a[i] > 1 / 3
    assert p_b[i] < 1 / 3


def test_transition_preserves_probability_and_pulls_toward_uniform():
    obs = BayesianEvidenceObserver(config=BayesianObserverConfig(change_hazard=0.2))
    p = obs.transition([0.9, 0.05, 0.05])
    assert p.sum() == pytest.approx(1.0)
    assert 1 / 3 < p[0] < 0.9
    assert p[1] > 0.05 and p[2] > 0.05


def test_quadrature_matches_monte_carlo():
    params = TargetParams(logit_noise_sd=0.8)
    obs = BayesianEvidenceObserver(params=params)
    exact = obs.p_a(RISK, "risk")
    # Independent numerical check of the logistic-normal integral.
    rng = np.random.default_rng(4)
    scores = obs.scorer.score(RISK)
    base = params.base_bias + params.w_match * scores["risk"] + params.w_off * (
        scores["fairness"] + scores["expertise"]
    )
    x = base + rng.normal(0.0, params.logit_noise_sd, size=300_000)
    approx = float(np.mean(1.0 / (1.0 + np.exp(-x))))
    assert exact == pytest.approx(approx, abs=0.002)


def _row(round_no, visible, active="fairness", initial="fairness", final="fairness",
         condition="full_history", swap=False, since=None, strategy="fairness"):
    return {
        "episode_id": "e0", "round": round_no, "visible_history": visible,
        "hidden_target_type": active, "initial_target_type": initial,
        "final_target_type": final, "condition": condition,
        "swap_condition": swap, "rounds_since_swap": since,
        "primary_strategy": strategy,
    }


def test_augmentation_is_start_of_round_not_after_current_outcome():
    history = [{"message": FAIR, "choice": "A"}]
    df = pd.DataFrame([_row(1, []), _row(2, history)])
    out = augment_with_bayesian_observer(df, hazard=0.0)
    assert out.loc[0, "bayes_p_fairness"] == pytest.approx(1 / 3)
    assert out.loc[1, "bayes_p_fairness"] > 1 / 3


def test_no_history_stays_uniform_on_every_round():
    df = pd.DataFrame([
        _row(r, [], condition="no_history", active="risk", initial="risk", final="risk")
        for r in range(1, 6)
    ])
    out = augment_with_bayesian_observer(df)
    assert np.allclose(out[["bayes_p_fairness", "bayes_p_risk", "bayes_p_expertise"]], 1 / 3)


def test_shuffled_history_tracks_visible_donor_evidence_not_true_type():
    history = [{"message": FAIR, "choice": "A"}] * 5
    df = pd.DataFrame([
        _row(6, history, active="risk", initial="risk", final="risk",
             condition="shuffled_history")
    ])
    out = augment_with_bayesian_observer(df, hazard=0.0)
    assert out.loc[0, "bayes_pred"] == "fairness"
    assert out.loc[0, "bayes_matches_active"] == 0


def test_baseline_corrected_gap_detects_evidence_leading_behaviour():
    rows = []
    for e in range(20):
        for since in (-2, -1, 0, 1, 2, 3, 4):
            rows.append({
                "episode_id": "e%02d" % e,
                "swap_condition": True,
                "rounds_since_swap": since,
                "bayes_p_final": 0.05 if since <= 0 else 0.85,
                "behaviour_matches_final": int(since >= 3),
            })
    out = baseline_corrected_trajectory_gap(pd.DataFrame(rows), n_boot=300, seed=0)
    assert out["statistic"] > 0
    assert out["ci95"][0] > 0
    assert "bayes_p_final rises" in out["interpretation"]


def test_invalid_choice_and_hazard_fail_loudly():
    with pytest.raises(ValueError, match="hazard"):
        BayesianObserverConfig(change_hazard=1.1)
    with pytest.raises(ValueError, match="choice"):
        BayesianEvidenceObserver().likelihoods("x", "C")


def test_logged_scorer_reconstructs_exact_message_only_scores():
    df = pd.DataFrame(
        [
            {
                "focal_message": "implicit appeal",
                "target_scores": {
                    "fairness": 0.8,
                    "risk": 0.1,
                    "expertise": 0.05,
                    "raw_scores": {
                        "fairness": 0.8, "risk": 0.1,
                        "expertise": 0.05, "other": 0.05,
                    },
                    "intensity": 0.95,
                },
            }
        ]
    )
    scorer = LoggedPersuasionScorer.from_dataframe(df)
    scores = scorer.score("implicit appeal")
    assert scores.fairness == pytest.approx(0.8)
    assert scores.raw_scores["other"] == pytest.approx(0.05)
    with pytest.raises(KeyError, match="no logged"):
        scorer.score("unseen")


def test_logged_scorer_rejects_nondeterministic_duplicate_scores():
    df = pd.DataFrame(
        [
            {"focal_message": "same", "target_scores": {
                "fairness": 0.8, "risk": 0.1, "expertise": 0.1,
            }},
            {"focal_message": "same", "target_scores": {
                "fairness": 0.7, "risk": 0.2, "expertise": 0.1,
            }},
        ]
    )
    with pytest.raises(ValueError, match="inconsistent"):
        LoggedPersuasionScorer.from_dataframe(df)


def test_augmentation_can_use_exact_logged_semantic_scores():
    scorer_df = pd.DataFrame(
        [{"focal_message": "implicit", "target_scores": {
            "fairness": 0.9, "risk": 0.05, "expertise": 0.01,
        }}]
    )
    scorer = LoggedPersuasionScorer.from_dataframe(scorer_df)
    df = pd.DataFrame([
        _row(1, []),
        _row(2, [{"message": "implicit", "choice": "A"}]),
    ])
    out = augment_with_bayesian_observer(df, hazard=0.0, scorer=scorer)
    assert out.loc[1, "bayes_p_fairness"] > out.loc[1, "bayes_p_risk"]
