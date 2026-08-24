"""Strategy classification: correctness, blindness, robustness and caching."""

from __future__ import annotations

import inspect
import json

import pytest

from config import ALL_LABELS, JudgeConfig
from src.focal_agent import MOCK_TEMPLATES
from src.strategy_classifier import (
    JUDGE_SYSTEM_PROMPT,
    JUDGE_USER_TEMPLATE,
    KeywordStrategyClassifier,
    LLMJudgeClassifier,
    MockJudgeProvider,
    extract_json_object,
    make_classifier,
    scorer_lexicon_half_for,
)


def _msg(kind, i=0):
    return MOCK_TEMPLATES[kind][i].format(a="Alpha", b="Beta")


# --------------------------------------------------------------------------
# Blindness
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "cls", [KeywordStrategyClassifier(), LLMJudgeClassifier(MockJudgeProvider(), "mock")]
)
def test_classify_takes_only_the_message(cls):
    """Blindness is structural: there is no other argument to leak through."""
    params = list(inspect.signature(cls.classify).parameters)
    assert params == ["message"]


def test_judge_prompt_says_nothing_about_targets_or_matching():
    text = (JUDGE_SYSTEM_PROMPT + " " + JUDGE_USER_TEMPLATE).lower()
    for banned in (
        "target",
        "hidden",
        "match",
        "correct",
        "susceptib",
        "experiment",
        "round",
        "should",
    ):
        assert banned not in text, "judge prompt mentions %r" % banned


# --------------------------------------------------------------------------
# Keyword classifier
# --------------------------------------------------------------------------


@pytest.mark.parametrize("kind", ["fairness", "risk", "expertise"])
@pytest.mark.parametrize("i", [0, 1, 2, 3])
def test_keyword_classifier_labels_pure_templates(kind, i):
    c = KeywordStrategyClassifier().classify(_msg(kind, i))
    assert c.primary_strategy == kind
    assert c.confidence == pytest.approx(1.0)
    assert getattr(c, kind) == pytest.approx(1.0)


@pytest.mark.parametrize("i", [0, 1, 2, 3])
def test_keyword_classifier_labels_unframed_messages_other(i):
    c = KeywordStrategyClassifier().classify(_msg("other", i))
    assert c.primary_strategy == "other"
    assert c.other == 1.0


def test_keyword_classifier_on_mixed_message():
    c = KeywordStrategyClassifier().classify(_msg("fairness") + " " + _msg("risk"))
    assert c.primary_strategy == "fairness"  # 6 fairness terms vs 5 risk terms
    assert 0 < c.risk < c.fairness
    assert c.confidence < 0.5


def test_keyword_classifier_scores_are_a_distribution():
    c = KeywordStrategyClassifier().classify(_msg("risk"))
    assert sum(getattr(c, k) for k in ALL_LABELS) == pytest.approx(1.0)


def test_empty_message_is_other():
    c = KeywordStrategyClassifier().classify("")
    assert c.primary_strategy == "other"


# --------------------------------------------------------------------------
# JSON extraction
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        '{"fairness": 0.1, "risk": 0.8, "expertise": 0.1, "other": 0.0, '
        '"primary_strategy": "risk", "confidence": 0.9}',
        'Sure! Here is the JSON:\n```json\n{"fairness": 0.1, "risk": 0.8, "expertise": 0.1, '
        '"other": 0.0, "primary_strategy": "risk", "confidence": 0.9}\n```\nHope that helps.',
        'prefix {"fairness": 0.1, "risk": 0.8, "expertise": 0.1, "other": 0.0, '
        '"primary_strategy": "risk", "confidence": 0.9, "note": {"nested": "yes {not json}"}} suffix',
    ],
)
def test_extract_json_object_is_robust(text):
    obj = extract_json_object(text)
    assert obj["primary_strategy"] == "risk"
    assert obj["risk"] == 0.8


@pytest.mark.parametrize("text", ["", "no json here", "{unbalanced"])
def test_extract_json_object_raises_on_garbage(text):
    with pytest.raises(ValueError):
        extract_json_object(text)


# --------------------------------------------------------------------------
# LLM judge plumbing
# --------------------------------------------------------------------------


def test_llm_judge_parses_mock_provider_output():
    j = LLMJudgeClassifier(MockJudgeProvider(), "mock")
    c = j.classify(_msg("expertise"))
    assert c.ok
    assert c.primary_strategy == "expertise"
    assert c.classifier.startswith("llm_judge")


def test_llm_judge_caches_to_disk(tmp_path):
    cache = tmp_path / "cache.jsonl"
    j = LLMJudgeClassifier(MockJudgeProvider(), "mock", cache_path=str(cache))
    m = _msg("risk")
    j.classify(m)
    j.classify(m)
    assert j.stats() == {"calls": 1, "cache_hits": 1, "parse_failures": 0}

    j2 = LLMJudgeClassifier(MockJudgeProvider(), "mock", cache_path=str(cache))
    c = j2.classify(m)
    assert j2.stats()["calls"] == 0
    assert c.raw["_cached"] is True
    assert len(cache.read_text().strip().splitlines()) == 1


class _BrokenProvider:
    name = "broken"

    def generate(self, prompt):
        return "I am afraid I cannot do that."

    def describe(self):
        return {"provider": "broken"}


def test_llm_judge_reports_parse_failure_without_crashing():
    j = LLMJudgeClassifier(_BrokenProvider(), "mock", max_retries=2)
    c = j.classify("anything")
    assert c.ok is False
    assert c.primary_strategy == "unparsed"
    assert j.stats()["parse_failures"] == 1


class _BadLabelProvider:
    name = "badlabel"

    def generate(self, prompt):
        return json.dumps(
            {"fairness": 0.2, "risk": 0.7, "expertise": 0.1, "other": 0.0,
             "primary_strategy": "vibes", "confidence": 0.5}
        )

    def describe(self):
        return {"provider": "badlabel"}


def test_llm_judge_falls_back_to_argmax_for_unknown_labels():
    j = LLMJudgeClassifier(_BadLabelProvider(), "mock")
    c = j.classify("anything")
    assert c.primary_strategy == "risk"


# --------------------------------------------------------------------------
# Factory / disjoint lexicon
# --------------------------------------------------------------------------


def test_make_classifier_keyword_and_llm():
    assert isinstance(make_classifier(JudgeConfig(kind="keyword")), KeywordStrategyClassifier)
    assert isinstance(
        make_classifier(JudgeConfig(kind="llm", provider="mock:judge")), LLMJudgeClassifier
    )
    with pytest.raises(ValueError):
        make_classifier(JudgeConfig(kind="tarot"))


def test_disjoint_lexicon_pairs_classifier_and_scorer_halves():
    cfg = JudgeConfig(kind="keyword", disjoint_lexicon=True)
    cls = make_classifier(cfg)
    assert cls.lexicon_half == "odd"
    assert scorer_lexicon_half_for(cfg) == "even"
    assert scorer_lexicon_half_for(JudgeConfig(kind="keyword")) == "all"
    assert scorer_lexicon_half_for(JudgeConfig(kind="llm")) == "all"
