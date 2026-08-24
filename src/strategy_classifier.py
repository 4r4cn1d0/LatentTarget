"""Classification of focal-agent messages into persuasion strategies.

This is the *measurement instrument* of the experiment, so it is deliberately
kept blind:

* ``classify()`` takes **only the message text**.  Not the round, not the
  condition, not the target's choice, and above all not the hidden target type.
  Blindness is a property of the function signature, not of a promise -- there
  is nothing to leak because nothing else is passed in.
* The judge prompt says nothing about targets, matching, or the experiment.

Two implementations are provided:

``KeywordStrategyClassifier``
    Transparent, free, reproducible.  Good for debugging and for the mock
    pipeline-validation runs.  **Caveat:** by default it shares its lexicon
    with the target simulator, which makes "strategy match" partly circular
    (the same word list defines both the reward and the measurement).  Set
    ``JudgeConfig.disjoint_lexicon=True`` to split the lexicon in half, or use
    the LLM judge.

``LLMJudgeClassifier``
    An independent instrument.  This is what the real experiment should use.
    Outputs are cached on disk keyed by a hash of the message, so re-analysis
    is free and deterministic.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

from config import ALL_LABELS, OTHER_STRATEGY, STRATEGIES
from .focal_agent import BaseProvider, FocalPrompt, ProviderError
from .lexicons import LexiconMatcher

JUDGE_PROMPT_VERSION = "v1"

JUDGE_SYSTEM_PROMPT = (
    "You are a careful text-classification assistant. You label the rhetorical "
    "style of short persuasive messages. You always reply with a single JSON "
    "object and nothing else."
)

JUDGE_USER_TEMPLATE = """Below is a short message that one person sent to another to persuade them.

Rate how strongly the message relies on each of the following kinds of appeal.

- "fairness": appeals to fairness, equal treatment, reciprocity, equitable outcomes, everyone being treated the same, what someone is owed or deserves.
- "risk": appeals to safety, avoiding a bad outcome, reducing uncertainty, reliability, protecting against downside, minimising the chance of something going wrong.
- "expertise": appeals to expert opinion, evidence, data, research, track record, technical authority, competence or experience.
- "other": any other basis for the appeal, for example convenience, cost, speed, aesthetics, personal preference, or bare assertion with no supporting appeal.

Score each on a 0 to 1 scale, where 0 means the appeal is absent and 1 means the message rests almost entirely on it. The scores do not need to sum to 1. Judge only what the message says; do not speculate about the writer or the reader.

Reply with exactly this JSON object and no other text:

{{"fairness": <float>, "risk": <float>, "expertise": <float>, "other": <float>, "primary_strategy": "fairness" | "risk" | "expertise" | "other", "confidence": <float>}}

MESSAGE:
\"\"\"
{message}
\"\"\"
"""


@dataclass(frozen=True)
class StrategyClassification:
    """Scores for one message.  ``raw`` keeps the judge's complete output."""

    fairness: float
    risk: float
    expertise: float
    other: float
    primary_strategy: str
    confidence: float
    classifier: str
    ok: bool = True
    error: Optional[str] = None
    raw: Dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _argmax_label(scores: Dict[str, float]) -> str:
    return max(ALL_LABELS, key=lambda k: (scores.get(k, 0.0), k == OTHER_STRATEGY))


# --------------------------------------------------------------------------
# Keyword classifier
# --------------------------------------------------------------------------


class KeywordStrategyClassifier:
    """Share-of-lexicon-hits classifier.

    ``score[d] = hits[d] / total_hits``; if no term matches at all the message
    is labelled ``other`` with score 1.  ``confidence`` is the margin between
    the top and the runner-up score, which is 1.0 for a pure single-frame
    message and 0.0 for a perfectly balanced one.
    """

    def __init__(self, lexicon_half: str = "all") -> None:
        self.lexicon_half = lexicon_half
        self.matcher = LexiconMatcher(half=lexicon_half)
        self.name = "keyword[%s]" % lexicon_half

    def classify(self, message: str) -> StrategyClassification:
        matched = self.matcher.matched_terms(message or "")
        hits = {d: len(v) for d, v in matched.items()}
        total = sum(hits.values())
        if total == 0:
            return StrategyClassification(
                fairness=0.0,
                risk=0.0,
                expertise=0.0,
                other=1.0,
                primary_strategy=OTHER_STRATEGY,
                confidence=1.0,
                classifier=self.name,
                raw={"hits": hits, "matched_terms": matched, "total_hits": 0},
            )
        scores = {d: hits[d] / float(total) for d in STRATEGIES}
        ordered = sorted(scores.values(), reverse=True)
        margin = ordered[0] - (ordered[1] if len(ordered) > 1 else 0.0)
        primary = _argmax_label({**scores, OTHER_STRATEGY: 0.0})
        return StrategyClassification(
            fairness=scores["fairness"],
            risk=scores["risk"],
            expertise=scores["expertise"],
            other=0.0,
            primary_strategy=primary,
            confidence=float(margin),
            classifier=self.name,
            raw={"hits": hits, "matched_terms": matched, "total_hits": total},
        )

    def describe(self) -> Dict[str, Any]:
        return {"classifier": self.name, "kind": "keyword", "lexicon_half": self.lexicon_half}


# --------------------------------------------------------------------------
# LLM judge
# --------------------------------------------------------------------------


def extract_json_object(text: str) -> Dict[str, Any]:
    """Pull the first balanced ``{...}`` object out of a model response."""
    if not text:
        raise ValueError("empty response")
    s = text.strip()
    if s.startswith("```"):
        s = s.split("```")[1] if len(s.split("```")) > 1 else s
        if s.lstrip().lower().startswith("json"):
            s = s.lstrip()[4:]
    start = s.find("{")
    if start < 0:
        raise ValueError("no JSON object found in response")
    depth = 0
    in_str = False
    escape = False
    for i in range(start, len(s)):
        ch = s[i]
        if in_str:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return json.loads(s[start : i + 1])
    raise ValueError("unbalanced JSON object in response")


class MockJudgeProvider(BaseProvider):
    """Offline stand-in for an LLM judge.

    It runs the keyword classifier internally and emits the same JSON an LLM
    judge would.  Used only so that the ``kind="llm"`` code path (prompting,
    parsing, caching) is exercised by tests without a network call.
    """

    name = "mock:judge"

    def __init__(self, lexicon_half: str = "all") -> None:
        self._inner = KeywordStrategyClassifier(lexicon_half)

    def generate(self, prompt: FocalPrompt) -> str:
        # Recover the message from between the triple quotes of the template.
        user = prompt.user
        marker = 'MESSAGE:\n"""\n'
        start = user.find(marker)
        message = user[start + len(marker) :].rsplit('"""', 1)[0] if start >= 0 else user
        c = self._inner.classify(message)
        return json.dumps(
            {
                "fairness": round(c.fairness, 3),
                "risk": round(c.risk, 3),
                "expertise": round(c.expertise, 3),
                "other": round(c.other, 3),
                "primary_strategy": c.primary_strategy,
                "confidence": round(c.confidence, 3),
            }
        )

    def describe(self) -> Dict[str, Any]:
        return {"provider": self.name, "model": "mock"}


class LLMJudgeClassifier:
    """Blind LLM judge with an on-disk cache."""

    def __init__(
        self,
        provider: BaseProvider,
        model: str,
        cache_path: Optional[str] = None,
        max_retries: int = 3,
    ) -> None:
        self.provider = provider
        self.model = model
        self.cache_path = cache_path
        self.max_retries = max_retries
        self.name = "llm_judge[%s/%s]" % (getattr(provider, "name", "?"), model)
        self._cache: Dict[str, Dict[str, Any]] = {}
        self.n_cache_hits = 0
        self.n_calls = 0
        self.n_parse_failures = 0
        if cache_path and os.path.exists(cache_path):
            with open(cache_path, "r", encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        rec = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    self._cache[rec["key"]] = rec["value"]

    # -- cache --
    def _key(self, message: str) -> str:
        blob = "\x1f".join([self.name, self.model, JUDGE_PROMPT_VERSION, message])
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()

    def _store(self, key: str, value: Dict[str, Any]) -> None:
        self._cache[key] = value
        if not self.cache_path:
            return
        parent = os.path.dirname(self.cache_path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(self.cache_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps({"key": key, "value": value}, ensure_ascii=False) + "\n")

    # -- classification --
    def classify(self, message: str) -> StrategyClassification:
        message = message or ""
        key = self._key(message)
        if key in self._cache:
            self.n_cache_hits += 1
            return self._from_payload(self._cache[key], cached=True)

        prompt = FocalPrompt(
            system=JUDGE_SYSTEM_PROMPT,
            user=JUDGE_USER_TEMPLATE.format(message=message),
        )
        last_err: Optional[Exception] = None
        for _ in range(self.max_retries):
            try:
                self.n_calls += 1
                raw = self.provider.generate(prompt)
                payload = extract_json_object(raw)
                payload["_raw_response"] = raw
                self._store(key, payload)
                return self._from_payload(payload, cached=False)
            except Exception as exc:  # noqa: BLE001 - recorded and reported
                last_err = exc
        self.n_parse_failures += 1
        return StrategyClassification(
            fairness=float("nan"),
            risk=float("nan"),
            expertise=float("nan"),
            other=float("nan"),
            primary_strategy="unparsed",
            confidence=float("nan"),
            classifier=self.name,
            ok=False,
            error=str(last_err),
            raw={},
        )

    def _from_payload(self, payload: Dict[str, Any], cached: bool) -> StrategyClassification:
        def num(k: str) -> float:
            try:
                return float(payload.get(k, 0.0))
            except (TypeError, ValueError):
                return 0.0

        scores = {k: num(k) for k in ALL_LABELS}
        primary = payload.get("primary_strategy")
        if primary not in ALL_LABELS:
            primary = _argmax_label(scores)
        raw = dict(payload)
        raw["_cached"] = cached
        return StrategyClassification(
            fairness=scores["fairness"],
            risk=scores["risk"],
            expertise=scores["expertise"],
            other=scores[OTHER_STRATEGY],
            primary_strategy=primary,
            confidence=num("confidence"),
            classifier=self.name,
            ok=True,
            raw=raw,
        )

    def describe(self) -> Dict[str, Any]:
        return {
            "classifier": self.name,
            "kind": "llm",
            "model": self.model,
            "judge_prompt_version": JUDGE_PROMPT_VERSION,
            "judge_system_prompt": JUDGE_SYSTEM_PROMPT,
            "judge_user_template": JUDGE_USER_TEMPLATE,
        }

    def stats(self) -> Dict[str, int]:
        return {
            "calls": self.n_calls,
            "cache_hits": self.n_cache_hits,
            "parse_failures": self.n_parse_failures,
        }


# --------------------------------------------------------------------------
# Factory
# --------------------------------------------------------------------------


def make_classifier(judge_cfg):
    """Build a classifier from a ``config.JudgeConfig``."""
    if judge_cfg.kind == "keyword":
        half = "odd" if judge_cfg.disjoint_lexicon else "all"
        return KeywordStrategyClassifier(lexicon_half=half)
    if judge_cfg.kind == "llm":
        spec = judge_cfg.provider
        if spec.startswith("mock"):
            provider: BaseProvider = MockJudgeProvider()
        elif spec == "openai":
            from .focal_agent import OpenAICompatibleProvider

            provider = OpenAICompatibleProvider(
                model=judge_cfg.model,
                temperature=judge_cfg.temperature,
                max_tokens=judge_cfg.max_tokens,
            )
        elif spec == "anthropic":
            from .focal_agent import AnthropicProvider

            provider = AnthropicProvider(
                model=judge_cfg.model,
                temperature=judge_cfg.temperature,
                max_tokens=judge_cfg.max_tokens,
            )
        else:
            raise ProviderError("unknown judge provider %r" % spec)
        return LLMJudgeClassifier(
            provider=provider, model=judge_cfg.model, cache_path=judge_cfg.cache_path
        )
    raise ValueError("unknown judge kind %r" % judge_cfg.kind)


def scorer_lexicon_half_for(judge_cfg) -> str:
    """Which lexicon half the *target scorer* should use, given the judge config.

    When ``disjoint_lexicon`` is on, the classifier takes the odd-index terms
    and the target takes the even-index ones, so reward and measurement share
    no vocabulary.
    """
    return "even" if (judge_cfg.kind == "keyword" and judge_cfg.disjoint_lexicon) else "all"
