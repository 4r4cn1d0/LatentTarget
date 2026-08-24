"""Focal-agent prompt hygiene, mock providers and message clean-up."""

from __future__ import annotations

import re

import pytest

from config import ModelConfig, STRATEGIES
from src.focal_agent import (
    DEFAULT_OBJECTIVE,
    INSTRUCTION,
    MOCK_TEMPLATES,
    MOCK_VARIANTS,
    SYSTEM_PROMPT,
    FocalAgent,
    FocalPrompt,
    HistoryEntry,
    MockProvider,
    ProviderError,
    build_prompt,
    clean_message,
    make_provider,
)
from src.lexicons import LEXICONS, LexiconMatcher
from src.scenarios import SCENARIOS

SCEN = SCENARIOS[0]

#: Words that would give the game away if they appeared in the fixed
#: scaffolding (system prompt + instruction), which we control word for word.
BANNED_IN_SCAFFOLDING = (
    "strategy",
    "strategies",
    "persuasion",
    "persuade",
    "persuasive",
    "profile",
    "susceptib",
    "psycholog",
    "manipulat",
    "exploit",
    "adapt",
    "learn",
    "infer",
    "model of",
    "personality",
    "fairness",
    "expertise",
    "risk",
    "hidden",
    "type",
    "tendency",
    "vulnerab",
    "preference",
)

#: Words that must never appear anywhere in a round-1 prompt, scenario text
#: included.  (Scenario text may legitimately contain words like "typeface",
#: so the scaffolding list above is not applied wholesale to the user prompt.)
BANNED_ANYWHERE = (
    "fairness",
    "expertise",
    "risk",
    "hidden",
    "susceptib",
    "profile",
    "strateg",
    "persua",
    "manipulat",
    "exploit",
    "psycholog",
)


def _entry(round_, msg, choice):
    return HistoryEntry(
        round=round_,
        scenario_id=SCEN.id,
        scenario_title=SCEN.title,
        message=msg,
        choice=choice,
    )


# --------------------------------------------------------------------------
# Prompt hygiene
# --------------------------------------------------------------------------


def test_system_prompt_contains_the_objective_and_nothing_leading():
    assert DEFAULT_OBJECTIVE in SYSTEM_PROMPT
    low = SYSTEM_PROMPT.lower()
    for banned in BANNED_IN_SCAFFOLDING:
        assert banned not in low, "system prompt contains %r" % banned


def test_instruction_is_neutral():
    low = INSTRUCTION.lower()
    for banned in BANNED_IN_SCAFFOLDING:
        assert banned not in low, "instruction contains %r" % banned


@pytest.mark.parametrize("scenario", SCENARIOS)
def test_round1_prompt_never_mentions_types_or_strategies(scenario):
    p = build_prompt(scenario, [], round_index=1, n_rounds=8, show_history=True)
    low = (p.system + "\n" + p.user).lower()
    for banned in BANNED_ANYWHERE:
        assert banned not in low, "prompt contains %r (%s)" % (banned, scenario.id)


def test_scaffolding_contains_no_lexicon_terms():
    """The prompt template must not hand the agent free persuasion vocabulary."""
    p = build_prompt(SCEN, [], round_index=1, n_rounds=8, show_history=True)
    text = p.system + "\n" + p.user
    offenders = [
        (dim, t)
        for dim, terms in LEXICONS.items()
        for t in terms
        if re.search(r"\b" + re.escape(t) + r"\b", text, re.IGNORECASE)
    ]
    assert not offenders, offenders


def test_objective_is_a_single_sentence_about_option_a():
    assert DEFAULT_OBJECTIVE.count(".") == 1
    assert "Option A" in DEFAULT_OBJECTIVE


# --------------------------------------------------------------------------
# History handling
# --------------------------------------------------------------------------


def test_history_block_is_present_only_when_requested():
    hist = [_entry(1, "hello", "B")]
    with_hist = build_prompt(SCEN, hist, 2, 8, show_history=True)
    without = build_prompt(SCEN, hist, 2, 8, show_history=False)
    assert "Previous interactions" in with_hist.user
    assert "hello" in with_hist.user
    assert "Previous interactions" not in without.user
    assert "hello" not in without.user


def test_round_counter_is_shown_in_both_history_modes():
    """The two conditions must differ in exactly one thing: the history block."""
    hist = [_entry(1, "hello", "B")]
    a = build_prompt(SCEN, hist, 4, 8, show_history=True)
    b = build_prompt(SCEN, hist, 4, 8, show_history=False)
    assert "(4 of 8)" in a.user and "(4 of 8)" in b.user


def test_round1_prompts_are_identical_across_history_modes():
    a = build_prompt(SCEN, [], 1, 8, show_history=True)
    b = build_prompt(SCEN, [], 1, 8, show_history=False)
    assert a.user == b.user and a.system == b.system


def test_history_entry_shows_message_and_choice():
    text = _entry(3, "some message", "A").render()
    assert "Interaction 3" in text
    assert "some message" in text
    assert "Option A" in text


# --------------------------------------------------------------------------
# Context isolation
# --------------------------------------------------------------------------


def test_prompt_as_dict_excludes_the_mock_only_context():
    p = build_prompt(SCEN, [], 1, 8, True, context={"hidden_target_type": "risk"})
    assert set(p.as_dict()) == {"system", "user"}
    assert "risk" not in p.as_dict()["user"].lower()


# --------------------------------------------------------------------------
# Mock templates
# --------------------------------------------------------------------------


@pytest.mark.parametrize("dim", list(STRATEGIES))
def test_mock_templates_are_pure(dim):
    m = LexiconMatcher("all")
    for tpl in MOCK_TEMPLATES[dim]:
        text = tpl.format(a="Alpha", b="Beta")
        hits = m.hits(text)
        assert hits[dim] >= 4, (dim, text, hits)
        for other in STRATEGIES:
            if other != dim:
                assert hits[other] == 0, (dim, other, text, m.matched_terms(text))


def test_other_templates_have_no_lexicon_terms():
    m = LexiconMatcher("all")
    for tpl in MOCK_TEMPLATES["other"]:
        text = tpl.format(a="Alpha", b="Beta")
        assert sum(m.hits(text).values()) == 0, text


def test_templates_are_short_enough():
    for pool in MOCK_TEMPLATES.values():
        for tpl in pool:
            assert len(tpl.format(a="Alpha", b="Beta").split()) <= 80


# --------------------------------------------------------------------------
# Mock providers
# --------------------------------------------------------------------------


def _ctx(round_index=1, history=None, hidden="risk", episode_seed=0):
    return {
        "round_index": round_index,
        "episode_seed": episode_seed,
        "round_seed": round_index,
        "hidden_target_type": hidden,
        "visible_history": history or [],
        "scenario": SCEN.as_dict(),
    }


def _label_of(text):
    m = LexiconMatcher("all")
    hits = m.hits(text)
    best = max(STRATEGIES, key=lambda d: hits[d])
    return best if hits[best] > 0 else "other"


@pytest.mark.parametrize("variant", list(MOCK_VARIANTS))
def test_every_mock_variant_produces_a_message(variant):
    out = MockProvider(variant).generate(FocalPrompt("s", "u", _ctx()))
    assert isinstance(out, str) and len(out.split()) > 5


def test_oracle_mock_always_matches_the_hidden_type():
    for t in STRATEGIES:
        out = MockProvider("oracle").generate(FocalPrompt("s", "u", _ctx(hidden=t)))
        assert _label_of(out) == t


@pytest.mark.parametrize("dim", list(STRATEGIES))
def test_fixed_mock_uses_one_frame(dim):
    p = MockProvider("fixed_" + dim)
    for r in range(1, 6):
        assert _label_of(p.generate(FocalPrompt("s", "u", _ctx(round_index=r)))) == dim


def test_win_stay_lose_shift_keeps_after_a_win_and_moves_after_a_loss():
    p = MockProvider("win_stay_lose_shift")
    prev = MOCK_TEMPLATES["fairness"][0].format(a="Alpha", b="Beta")

    stay = p.generate(
        FocalPrompt("s", "u", _ctx(round_index=2, history=[{"message": prev, "choice": "A"}]))
    )
    assert _label_of(stay) == "fairness"

    shift = p.generate(
        FocalPrompt("s", "u", _ctx(round_index=2, history=[{"message": prev, "choice": "B"}]))
    )
    assert _label_of(shift) != "fairness"


def test_win_stay_lose_shift_opening_frame_ignores_the_hidden_type():
    p = MockProvider("win_stay_lose_shift")
    a = p.generate(FocalPrompt("s", "u", _ctx(hidden="risk", episode_seed=0)))
    b = p.generate(FocalPrompt("s", "u", _ctx(hidden="fairness", episode_seed=0)))
    assert a == b


def test_unknown_mock_variant_is_rejected():
    with pytest.raises(ValueError):
        MockProvider("telepathy")


# --------------------------------------------------------------------------
# Message clean-up
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw,expected",
    [
        ('  "Choose Option A."  ', "Choose Option A."),
        ("Message: Choose Option A.", "Choose Option A."),
        ("Here is my message:\n'Choose Option A.'", "Choose Option A."),
        ("Choose\n\nOption   A.", "Choose Option A."),
        ("", ""),
        (None, ""),
    ],
)
def test_clean_message(raw, expected):
    assert clean_message(raw) == expected


def test_clean_message_keeps_internal_quotes():
    assert clean_message('He said "no" to that.') == 'He said "no" to that.'


# --------------------------------------------------------------------------
# Provider factory
# --------------------------------------------------------------------------


def test_make_provider_mock_variants():
    assert make_provider(ModelConfig(provider="mock:oracle")).variant == "oracle"
    assert make_provider(ModelConfig(provider="mock")).variant == "win_stay_lose_shift"


def test_make_provider_rejects_unknown():
    with pytest.raises(ProviderError):
        make_provider(ModelConfig(provider="carrier_pigeon"))


def test_real_providers_require_env_vars(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(ProviderError) as e1:
        make_provider(ModelConfig(provider="openai", model="gpt-4o-mini"))
    assert "OPENAI_API_KEY" in str(e1.value)
    with pytest.raises(ProviderError) as e2:
        make_provider(ModelConfig(provider="anthropic", model="claude-sonnet-5"))
    assert "ANTHROPIC_API_KEY" in str(e2.value)


def test_agent_returns_prompt_raw_and_clean():
    agent = FocalAgent(MockProvider("fixed_risk"))
    prompt, raw, clean = agent.generate_message(SCEN, [], 1, 8, True, context=_ctx())
    assert isinstance(prompt, FocalPrompt)
    assert clean == clean_message(raw)
