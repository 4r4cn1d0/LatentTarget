"""Evidence-only Bayesian baselines for latent-target inference.

This module answers a crucial alternative explanation for the probing arm:
could a probe merely decode the evidence already written in the prompt?

The observer knows the transparent target simulator, but it sees exactly what
the focal model sees: previous message/choice pairs.  It never sees target
type, target scores, sampled logit noise, or the current round's outcome.

The observer is intentionally called *model-based*, not universally
"Bayes-optimal".  In a swap episode an optimal posterior depends on a prior
over when targets change.  We predeclare a constant per-round change hazard and
report a sensitivity grid.  Giving the observer the true swap round would leak
experimental information that the focal model never receives.

Alignment is load-bearing.  Activations and messages are measured before the
current target choice, so the Bayesian columns for round ``r`` use only the
visible history through round ``r-1``.  Updating with the current choice would
give the baseline one observation the model did not have.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence

import numpy as np

from config import DEFAULT_TARGET_PARAMS, STRATEGIES, TargetParams
from .target_simulator import (
    KeywordPersuasionScorer,
    PersuasionScorer,
    PersuasionScores,
    sigmoid,
)


def _normalise(values: np.ndarray) -> np.ndarray:
    total = float(values.sum())
    if not math.isfinite(total) or total <= 0:
        raise ValueError("posterior has zero or non-finite mass")
    return values / total


@dataclass(frozen=True)
class BayesianObserverConfig:
    """Assumptions of the evidence-only observer.

    ``change_hazard`` is the probability that the target changes between two
    adjacent rounds. Conditional on a change, either other type is equally
    likely. A hazard of zero is the stable-target model.
    """

    change_hazard: float = 0.10
    quadrature_points: int = 40

    def __post_init__(self) -> None:
        if not 0.0 <= self.change_hazard <= 1.0:
            raise ValueError("change_hazard must be in [0, 1]")
        if self.quadrature_points < 8:
            raise ValueError("quadrature_points must be at least 8")


class BayesianEvidenceObserver:
    """Sequential posterior over the three hidden target types."""

    def __init__(
        self,
        params: TargetParams = DEFAULT_TARGET_PARAMS,
        config: BayesianObserverConfig = BayesianObserverConfig(),
        scorer: Optional[PersuasionScorer] = None,
        prior: Optional[Mapping[str, float]] = None,
    ) -> None:
        self.params = params
        self.config = config
        self.scorer = scorer or KeywordPersuasionScorer(params.saturation_k)
        if prior is None:
            self.initial = np.full(len(STRATEGIES), 1.0 / len(STRATEGIES))
        else:
            self.initial = _normalise(
                np.asarray([float(prior[s]) for s in STRATEGIES], dtype=float)
            )
        # Gauss-Hermite quadrature integrates the logistic-normal expectation
        # deterministically. It is fast enough to recompute from raw history.
        self._gh_x, self._gh_w = np.polynomial.hermite.hermgauss(
            self.config.quadrature_points
        )

    def transition(self, posterior: Sequence[float]) -> np.ndarray:
        """Apply the predeclared symmetric between-round change hazard."""
        p = _normalise(np.asarray(posterior, dtype=float))
        h = self.config.change_hazard
        k = len(p)
        if k < 2 or h == 0.0:
            return p
        # Stay with probability 1-h; on change, choose uniformly among the
        # other K-1 types. This transition has the uniform stationary prior.
        return (1.0 - h) * p + (h / (k - 1)) * (1.0 - p)

    def p_a(self, message: str, target_type: str) -> float:
        """Marginal P(A), integrating out unobserved Gaussian logit noise."""
        if target_type not in STRATEGIES:
            raise ValueError("unknown target_type %r" % target_type)
        scores = self.scorer.score(message)
        matched = scores[target_type]
        off = sum(scores[d] for d in STRATEGIES if d != target_type)
        base = self.params.base_bias + self.params.w_match * matched + self.params.w_off * off
        sd = self.params.logit_noise_sd
        if sd == 0.0:
            return sigmoid(base)
        logits = base + math.sqrt(2.0) * sd * self._gh_x
        probs = np.asarray([sigmoid(float(x)) for x in logits])
        return float(np.dot(self._gh_w, probs) / math.sqrt(math.pi))

    def likelihoods(self, message: str, choice: str) -> np.ndarray:
        if choice not in ("A", "B"):
            raise ValueError("choice must be 'A' or 'B'")
        p = np.asarray([self.p_a(message, t) for t in STRATEGIES])
        return p if choice == "A" else (1.0 - p)

    def update(self, prior: Sequence[float], message: str, choice: str) -> np.ndarray:
        """Posterior for the current round after observing its outcome."""
        p = _normalise(np.asarray(prior, dtype=float))
        return _normalise(p * self.likelihoods(message, choice))

    def prior_from_history(self, history: Iterable[Mapping[str, Any]]) -> np.ndarray:
        """Prior at the start of the next round from visible history only.

        A target transition is applied after every observed interaction, because
        the caller is asking about the *next* round's target.
        """
        p = self.initial.copy()
        for entry in history:
            p = self.update(p, str(entry["message"]), str(entry["choice"]))
            p = self.transition(p)
        return p

    @staticmethod
    def entropy(posterior: Sequence[float]) -> float:
        p = _normalise(np.asarray(posterior, dtype=float))
        return float(-np.sum(p * np.log(np.clip(p, 1e-15, 1.0))))


class LoggedPersuasionScorer:
    """Exact message-only scorer reconstructed from immutable run records.

    A model-based observer is assumed to know the target response function. For
    semantic environments, the log already contains that deterministic
    function's output for every message that can appear in visible history.
    Reusing those scores is equivalent to rerunning the frozen classifier, but
    avoids another model dependency and catches nondeterministic scoring if the
    same message ever has inconsistent logged values.
    """

    name = "logged_persuasion_scorer"

    def __init__(self, mapping: Mapping[str, PersuasionScores]) -> None:
        self.mapping = dict(mapping)

    @classmethod
    def from_dataframe(cls, df) -> "LoggedPersuasionScorer":
        mapping: Dict[str, PersuasionScores] = {}
        for _, row in df.iterrows():
            message = str(row["focal_message"])
            raw = row["target_scores"]
            if not isinstance(raw, Mapping):
                raise ValueError("target_scores must be a mapping for every logged row")
            scores = PersuasionScores(
                fairness=float(raw["fairness"]),
                risk=float(raw["risk"]),
                expertise=float(raw["expertise"]),
                hits=dict(raw.get("hits", {})),
                matched_terms=dict(raw.get("matched_terms", {})),
                total_hits=int(raw.get("total_hits", 0)),
                intensity=float(raw.get("intensity", 0.0)),
                raw_scores={k: float(v) for k, v in raw.get("raw_scores", {}).items()},
            )
            if message in mapping:
                old = mapping[message]
                if not np.allclose(
                    [old[s] for s in STRATEGIES],
                    [scores[s] for s in STRATEGIES],
                    atol=1e-12,
                    rtol=0.0,
                ):
                    raise ValueError(
                        "same message has inconsistent target scores; semantic "
                        "scoring may not be deterministic"
                    )
            else:
                mapping[message] = scores
        return cls(mapping)

    def score(self, message: str) -> PersuasionScores:
        try:
            return self.mapping[str(message)]
        except KeyError as exc:
            raise KeyError("visible-history message has no logged target score") from exc

    def describe(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "n_unique_messages": len(self.mapping),
            "source": "logged deterministic target_scores keyed only by focal_message",
        }


def augment_with_bayesian_observer(
    df,
    params: TargetParams = DEFAULT_TARGET_PARAMS,
    hazard: float = 0.10,
    quadrature_points: int = 40,
    lexicon_half: str = "all",
    scorer: Optional[PersuasionScorer] = None,
):
    """Return a copy of a run dataframe with start-of-round Bayesian beliefs.

    The function recomputes from each row's serialized ``visible_history``.
    That is slower than carrying state, but it handles full/no/shuffled history
    exactly and makes the information boundary auditable row by row.
    """
    out = df.copy()
    observer = BayesianEvidenceObserver(
        params=params,
        config=BayesianObserverConfig(hazard, quadrature_points),
        scorer=(
            scorer
            if scorer is not None
            else KeywordPersuasionScorer(params.saturation_k, lexicon_half=lexicon_half)
        ),
    )
    posteriors: List[np.ndarray] = []
    for history in out["visible_history"]:
        if history is None or (isinstance(history, float) and np.isnan(history)):
            history = []
        posteriors.append(observer.prior_from_history(history))
    matrix = np.vstack(posteriors)
    for j, strategy in enumerate(STRATEGIES):
        out["bayes_p_" + strategy] = matrix[:, j]
    pred_idx = matrix.argmax(axis=1)
    out["bayes_pred"] = [STRATEGIES[i] for i in pred_idx]
    out["bayes_entropy"] = [observer.entropy(p) for p in matrix]
    out["bayes_hazard"] = float(hazard)
    out["bayes_matches_active"] = (
        out["bayes_pred"] == out["hidden_target_type"]
    ).astype(int)
    out["bayes_matches_initial"] = (
        out["bayes_pred"] == out["initial_target_type"]
    ).astype(int)
    out["bayes_matches_final"] = (
        out["bayes_pred"] == out["final_target_type"]
    ).astype(int)
    out["bayes_p_final"] = [
        float(matrix[i, STRATEGIES.index(str(out.iloc[i]["final_target_type"]))])
        for i in range(len(out))
    ]
    out["behaviour_matches_final"] = (
        out["primary_strategy"] == out["final_target_type"]
    ).astype(int)
    return out


def baseline_corrected_trajectory_gap(
    traj,
    evidence_col: str = "bayes_p_final",
    behaviour_col: str = "behaviour_matches_final",
    n_boot: int = 5000,
    seed: int = 0,
) -> Dict[str, Any]:
    """Compare evidence and behaviour after swap, bootstrapping episodes.

    Positive means the evidence channel rises toward the new target faster than
    the message channel, after subtracting each channel's own pre-swap level.
    """
    import pandas as pd

    sw = traj[traj["swap_condition"] & traj["rounds_since_swap"].notna()].copy()
    if sw.empty:
        return {"n_swap_episodes": 0}
    sw["rounds_since_swap"] = sw["rounds_since_swap"].astype(int)

    def statistic(frame) -> float:
        pre = frame[frame["rounds_since_swap"] <= 0]
        post = frame[frame["rounds_since_swap"] > 0]
        if pre.empty or post.empty:
            return float("nan")
        base_e = float(pre[evidence_col].mean())
        base_b = float(pre[behaviour_col].mean())
        gaps = []
        for _, g in post.groupby("rounds_since_swap"):
            gaps.append(
                (float(g[evidence_col].mean()) - base_e)
                - (float(g[behaviour_col].mean()) - base_b)
            )
        return float(np.mean(gaps))

    observed = statistic(sw)
    episodes = sorted(sw["episode_id"].unique())
    by_episode = {eid: sw[sw["episode_id"] == eid] for eid in episodes}
    rng = np.random.default_rng(seed)
    boots = []
    for _ in range(n_boot):
        chosen = rng.integers(0, len(episodes), len(episodes))
        boots.append(statistic(pd.concat([by_episode[episodes[i]] for i in chosen])))
    boots = np.asarray([x for x in boots if np.isfinite(x)])
    lo, hi = np.quantile(boots, [0.025, 0.975]) if len(boots) else (np.nan, np.nan)
    return {
        "statistic": observed,
        "ci95": [float(lo), float(hi)],
        "n_swap_episodes": len(episodes),
        "n_boot": int(len(boots)),
        "evidence_col": evidence_col,
        "behaviour_col": behaviour_col,
        "interpretation": (
            "Positive means %s rises toward the new target faster than %s, "
            "after subtracting each channel's own pre-swap baseline. A causal "
            "or representational interpretation requires the separately stated "
            "controls."
            % (evidence_col, behaviour_col)
        ),
    }
