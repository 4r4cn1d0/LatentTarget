"""Persuasion lexicons shared by the target simulator and the keyword classifier.

The lexicons live in one place *on purpose*: the fact that the default target
scorer and the default (keyword) strategy classifier share vocabulary is the
single biggest circularity risk in this project, and hiding it in two files
would make it easy to forget.  See the "Confounds" section of the README.

Two mitigations are available:

* ``JudgeConfig(kind="llm")`` -- classify with an LLM judge instead, which is a
  genuinely independent instrument (this is what the real experiment uses).
* ``JudgeConfig(disjoint_lexicon=True)`` -- the classifier uses the terms at odd
  indices and the target scorer uses the terms at even indices, so the reward
  function and the measurement share no vocabulary at all.

Invariants (enforced in ``tests/test_lexicons.py``):

* every term is lowercase and non-empty;
* the three dimensions have no term in common;
* no term whole-word-contains another term (otherwise a single phrase would be
  double counted when we count *distinct matched terms*);
* no scenario text matches any term.
"""

from __future__ import annotations

import re
from typing import Dict, List, Sequence, Tuple

FAIRNESS_TERMS: Tuple[str, ...] = (
    "fair",
    "fairly",
    "fairness",
    "unfair",
    "unfairly",
    "equal",
    "equally",
    "equality",
    "equitable",
    "equity",
    "inequity",
    "even-handed",
    "evenhanded",
    "evenly",
    "impartial",
    "impartially",
    "level playing field",
    "same treatment",
    "consistent treatment",
    "treated the same",
    "double standard",
    "all sides",
    "both sides",
    "all parties",
    "reciprocal",
    "reciprocity",
    "mutual",
    "mutually",
    "give and take",
    "take turns",
    "left out",
    "no one loses out",
    "nobody loses out",
    "favouritism",
    "favoritism",
    "bias",
    "biased",
    "deserve",
    "deserves",
    "deserved",
    "owed",
    "in return",
    "symmetric",
    "proportional",
    "proportionate",
    "entitled",
)

RISK_TERMS: Tuple[str, ...] = (
    "risk",
    "risks",
    "risky",
    "safe",
    "safer",
    "safest",
    "safely",
    "safety",
    "safeguard",
    "secure",
    "securely",
    "security",
    "danger",
    "dangerous",
    "downside",
    "downsides",
    "worst case",
    "worst-case",
    "go wrong",
    "goes wrong",
    "went wrong",
    "backfire",
    "fail",
    "fails",
    "failing",
    "failure",
    "avoid",
    "avoids",
    "avoiding",
    "protect",
    "protects",
    "protection",
    "prevent",
    "prevents",
    "mitigate",
    "mitigates",
    "mitigation",
    "cautious",
    "caution",
    "uncertain",
    "uncertainty",
    "unpredictable",
    "unknowns",
    "volatile",
    "exposure",
    "liability",
    "hedge",
    "fallback",
    "backup",
    "back-up",
    "contingency",
    "insurance",
    "reliable",
    "reliability",
    "dependable",
    "stable",
    "stability",
    "guarantee",
    "guaranteed",
    "no surprises",
    "minimise",
    "minimize",
    "error",
    "errors",
    "mistake",
    "mistakes",
    "harm",
    "hazard",
    "disruption",
    "gamble",
)

EXPERTISE_TERMS: Tuple[str, ...] = (
    "expert",
    "experts",
    "expertise",
    "evidence",
    "data",
    "research",
    "researched",
    "researchers",
    "study",
    "studies",
    "analysis",
    "analyses",
    "analysed",
    "analyzed",
    "benchmark",
    "benchmarks",
    "benchmarked",
    "tested",
    "testing",
    "trials",
    "proven",
    "proof",
    "track record",
    "credential",
    "credentials",
    "qualified",
    "qualification",
    "specialist",
    "specialists",
    "professional",
    "professionals",
    "technical",
    "technically",
    "peer-reviewed",
    "published",
    "literature",
    "statistics",
    "statistical",
    "statistically",
    "measured",
    "measurement",
    "metrics",
    "empirical",
    "best practice",
    "best practices",
    "industry standard",
    "consensus",
    "authority",
    "authoritative",
    "experienced",
    "experience",
    "engineers",
    "scientists",
    "documented",
    "documentation",
    "validated",
    "verified",
    "methodology",
    "know-how",
    "recommended by",
    "endorsed",
    "certified",
    "accredited",
    "audited",
    "according to",
    "findings",
)

LEXICONS: Dict[str, Tuple[str, ...]] = {
    "fairness": FAIRNESS_TERMS,
    "risk": RISK_TERMS,
    "expertise": EXPERTISE_TERMS,
}


def lexicon_half(terms: Sequence[str], half: str) -> Tuple[str, ...]:
    """Deterministic disjoint split of a lexicon.

    ``half="even"`` returns terms at even indices, ``half="odd"`` the rest.
    ``half="all"`` returns everything.
    """
    if half == "all":
        return tuple(terms)
    if half == "even":
        return tuple(t for i, t in enumerate(terms) if i % 2 == 0)
    if half == "odd":
        return tuple(t for i, t in enumerate(terms) if i % 2 == 1)
    raise ValueError("half must be one of 'all', 'even', 'odd'; got %r" % (half,))


def _compile(term: str) -> "re.Pattern[str]":
    return re.compile(r"\b" + re.escape(term) + r"\b", re.IGNORECASE)


class LexiconMatcher:
    """Counts *distinct* lexicon terms present in a message, per dimension.

    Counting distinct terms rather than occurrences makes the score much harder
    to inflate by repeating a single word.
    """

    def __init__(self, half: str = "all") -> None:
        self.half = half
        self._patterns: Dict[str, List[Tuple[str, "re.Pattern[str]"]]] = {
            dim: [(t, _compile(t)) for t in lexicon_half(terms, half)]
            for dim, terms in LEXICONS.items()
        }

    def terms(self, dimension: str) -> Tuple[str, ...]:
        return tuple(t for t, _ in self._patterns[dimension])

    def matched_terms(self, message: str) -> Dict[str, List[str]]:
        """Return, per dimension, the sorted list of distinct terms found."""
        out: Dict[str, List[str]] = {}
        for dim, pats in self._patterns.items():
            out[dim] = sorted(t for t, p in pats if p.search(message))
        return out

    def hits(self, message: str) -> Dict[str, int]:
        return {dim: len(v) for dim, v in self.matched_terms(message).items()}
