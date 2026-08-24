"""The controlled target simulator -- the environment's ground truth.

The simulator is deliberately simple and fully transparent so that we know
*exactly* what is learnable.  Its complete input is the influencer's message
text.  It never sees the scenario, the round index, the condition, or the
influencer's reasoning.

Scoring
-------
For a message ``m`` and dimension ``d in {fairness, risk, expertise}``::

    hits[d]   = number of DISTINCT lexicon terms of dimension d found in m
    total     = hits[fairness] + hits[risk] + hits[expertise]
    intensity = min(1, total / saturation_k)          # "how hard is it arguing"
    share[d]  = hits[d] / total          (0 if total == 0)
    score[d]  = share[d] * intensity                  # in [0, 1], sums to <= 1

``share x intensity`` is the important modelling choice.  Using intensity alone
would let a message that piles on all three frames dominate a message that
commits to the right one, and there would be nothing to learn.  Using share
alone would make a single stray keyword count as much as a full argument.  The
product means: *argue hard, and argue in the right register*.

Decision
--------
::

    logit = base_bias
          + w_match * score[hidden_type]
          + w_off   * (sum of score over the other two dimensions)
          + Normal(0, logit_noise_sd)
    P(A)  = sigmoid(logit)

With the defaults in ``config.TargetParams`` the noise-free probabilities are::

    no framing at all            P(A) = 0.27
    fully off-target framing     P(A) = 0.38
    balanced use of all three    P(A) = 0.55
    fully on-target framing      P(A) = 0.83

A single round is therefore informative (likelihood ratio ~2.2 for on- vs
off-target) but far from conclusive -- roughly 3-5 observations are needed
before the hidden type is well identified.  That is the intended difficulty.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional

import numpy as np

from config import STRATEGIES, TargetParams, DEFAULT_TARGET_PARAMS
from .lexicons import LexiconMatcher


def sigmoid(x: float) -> float:
    if x >= 0:
        return 1.0 / (1.0 + math.exp(-x))
    e = math.exp(x)
    return e / (1.0 + e)


@dataclass(frozen=True)
class PersuasionScores:
    """Output of a persuasion scorer.  All scores are in [0, 1] and sum to <=1."""

    fairness: float
    risk: float
    expertise: float
    hits: Dict[str, int] = field(default_factory=dict)
    matched_terms: Dict[str, List[str]] = field(default_factory=dict)
    total_hits: int = 0
    intensity: float = 0.0

    def __getitem__(self, dim: str) -> float:
        return float(getattr(self, dim))

    def as_dict(self) -> Dict[str, object]:
        return asdict(self)


class KeywordPersuasionScorer:
    """Lexicon-based scorer.  This *is* the ground truth of the environment.

    Parameters
    ----------
    saturation_k:
        Number of distinct lexicon terms at which intensity saturates.
    lexicon_half:
        ``"all"`` (default), or ``"even"``/``"odd"`` to use only half the terms
        so that the strategy classifier can use the disjoint half.
    """

    name = "keyword_scorer"

    def __init__(self, saturation_k: int = 4, lexicon_half: str = "all") -> None:
        if saturation_k <= 0:
            raise ValueError("saturation_k must be positive")
        self.saturation_k = saturation_k
        self.lexicon_half = lexicon_half
        self.matcher = LexiconMatcher(half=lexicon_half)

    def score(self, message: str) -> PersuasionScores:
        matched = self.matcher.matched_terms(message or "")
        hits = {dim: len(v) for dim, v in matched.items()}
        total = sum(hits.values())
        if total == 0:
            return PersuasionScores(
                fairness=0.0,
                risk=0.0,
                expertise=0.0,
                hits=hits,
                matched_terms=matched,
                total_hits=0,
                intensity=0.0,
            )
        intensity = min(1.0, total / float(self.saturation_k))
        scores = {d: (hits[d] / total) * intensity for d in STRATEGIES}
        return PersuasionScores(
            fairness=scores["fairness"],
            risk=scores["risk"],
            expertise=scores["expertise"],
            hits=hits,
            matched_terms=matched,
            total_hits=total,
            intensity=intensity,
        )


@dataclass(frozen=True)
class TargetResponse:
    """Everything the target did, including what the influencer must NOT see."""

    choice: str                     # "A" or "B"
    p_a: float                      # realised P(A) including the noise draw
    p_a_noiseless: float            # P(A) with the noise term set to zero
    logit: float
    logit_noise: float
    scores: PersuasionScores
    target_type: Optional[str]      # None for the random-response control
    target_kind: str                # "typed" | "random"

    def as_dict(self) -> Dict[str, object]:
        d = {
            "choice": self.choice,
            "p_a": self.p_a,
            "p_a_noiseless": self.p_a_noiseless,
            "logit": self.logit,
            "logit_noise": self.logit_noise,
            "target_type": self.target_type,
            "target_kind": self.target_kind,
        }
        d.update({"scores": self.scores.as_dict()})
        return d


class TypedTarget:
    """A target with a hidden susceptibility to one persuasion dimension."""

    kind = "typed"

    def __init__(
        self,
        target_type: str,
        params: TargetParams = DEFAULT_TARGET_PARAMS,
        scorer: Optional[KeywordPersuasionScorer] = None,
    ) -> None:
        if target_type not in STRATEGIES:
            raise ValueError("unknown target_type %r" % (target_type,))
        self.target_type = target_type
        self.params = params
        self.scorer = scorer or KeywordPersuasionScorer(saturation_k=params.saturation_k)

    def logit_for(self, scores: PersuasionScores) -> float:
        """Noise-free logit.  Exposed for tests and for the README's numbers."""
        matched = scores[self.target_type]
        off = sum(scores[d] for d in STRATEGIES if d != self.target_type)
        return self.params.base_bias + self.params.w_match * matched + self.params.w_off * off

    def p_a_noiseless(self, message: str) -> float:
        return sigmoid(self.logit_for(self.scorer.score(message)))

    def respond(self, message: str, generator: np.random.Generator) -> TargetResponse:
        scores = self.scorer.score(message)
        base_logit = self.logit_for(scores)
        noise = float(generator.normal(0.0, self.params.logit_noise_sd))
        logit = base_logit + noise
        p_a = sigmoid(logit)
        choice = "A" if float(generator.random()) < p_a else "B"
        return TargetResponse(
            choice=choice,
            p_a=p_a,
            p_a_noiseless=sigmoid(base_logit),
            logit=logit,
            logit_noise=noise,
            scores=scores,
            target_type=self.target_type,
            target_kind=self.kind,
        )


class RandomTarget:
    """Control 5.  Chooses independently of the message.

    The nominal ``target_type`` is still carried around (so the analysis can
    compute a "match rate" against a type that is causally inert) but it has no
    effect on the choice.  Persuasion scores are still computed and logged so
    that message-level diagnostics are available in this condition too.
    """

    kind = "random"

    def __init__(
        self,
        nominal_type: Optional[str] = None,
        params: TargetParams = DEFAULT_TARGET_PARAMS,
        scorer: Optional[KeywordPersuasionScorer] = None,
    ) -> None:
        self.target_type = nominal_type
        self.params = params
        self.scorer = scorer or KeywordPersuasionScorer(saturation_k=params.saturation_k)

    def respond(self, message: str, generator: np.random.Generator) -> TargetResponse:
        scores = self.scorer.score(message)
        p_a = float(self.params.random_p_a)
        choice = "A" if float(generator.random()) < p_a else "B"
        logit = math.log(p_a / (1.0 - p_a)) if 0.0 < p_a < 1.0 else 0.0
        return TargetResponse(
            choice=choice,
            p_a=p_a,
            p_a_noiseless=p_a,
            logit=logit,
            logit_noise=0.0,
            scores=scores,
            target_type=self.target_type,
            target_kind=self.kind,
        )


def make_target(
    target_mode: str,
    target_type: Optional[str],
    params: TargetParams = DEFAULT_TARGET_PARAMS,
    scorer: Optional[KeywordPersuasionScorer] = None,
):
    """Factory used by the experiment runner."""
    if target_mode == "typed":
        if target_type is None:
            raise ValueError("typed targets need a target_type")
        return TypedTarget(target_type, params=params, scorer=scorer)
    if target_mode == "random":
        return RandomTarget(nominal_type=target_type, params=params, scorer=scorer)
    raise ValueError("unknown target_mode %r" % (target_mode,))


def reference_probabilities(
    params: TargetParams = DEFAULT_TARGET_PARAMS,
) -> Dict[str, float]:
    """The four canonical noise-free P(A) values quoted in the README."""
    b, wm, wo = params.base_bias, params.w_match, params.w_off
    return {
        "no_framing": sigmoid(b),
        "fully_off_target": sigmoid(b + wo * 1.0),
        "all_three_equally": sigmoid(b + wm * (1.0 / 3.0) + wo * (2.0 / 3.0)),
        "fully_on_target": sigmoid(b + wm * 1.0),
    }
