"""Contract tests for the open-weight provider.

These run without torch/transformers: they check the *isolation guarantee* and
the bookkeeping, which are the parts that could silently invalidate a result.
The model loading itself is exercised on the pod, not here.
"""

from __future__ import annotations

import inspect

import numpy as np
import pytest

from src.focal_agent import FocalPrompt, ProviderError
from src.hf_provider import (
    BLACK_BOX_QUESTION,
    HuggingFaceProvider,
    _choice_prefix_allowed_tokens,
    _choice_token_sequences,
    black_box_answer,
    black_box_guess,
)
from src.probing import ActivationStore


def test_generate_never_reads_prompt_context():
    """Structural guarantee: the hidden target type lives in FocalPrompt.context
    (for the mock oracle). If generate() touched it, the real model could see
    the answer. Metadata is attached afterwards via tag_last instead."""
    src = inspect.getsource(HuggingFaceProvider.generate)
    assert ".context" not in src
    assert "hidden_target_type" not in src
    assert "prompt.system" in src and "prompt.user" in src


def test_tag_last_attaches_metadata_after_the_fact():
    p = HuggingFaceProvider(model="fake/model")
    p.kept_layers = [0, 1]
    p._last_acts = np.zeros((2, 8), dtype=np.float16)
    p.tag_last({"episode_id": "e0", "round": 1})
    assert len(p.captured) == 1
    assert p.captured[0][0] == {"episode_id": "e0", "round": 1}
    # A second tag with nothing captured must not duplicate the previous row.
    p.tag_last({"episode_id": "e0", "round": 2})
    assert len(p.captured) == 1


def test_to_store_bundles_captures():
    p = HuggingFaceProvider(model="fake/model")
    p.kept_layers = [0, 2, 4]
    for r in range(1, 4):
        p._last_acts = np.full((3, 8), r, dtype=np.float16)
        p.tag_last({"episode_id": "e0", "round": r})
    store = p.to_store()
    assert isinstance(store, ActivationStore)
    assert store.n_rows == 3 and store.n_layers == 3 and store.d_model == 8
    assert store.layers == [0, 2, 4]
    assert store.key(2) == ("e0", 3)


def test_to_store_refuses_when_nothing_captured():
    with pytest.raises(ValueError, match="nothing captured"):
        HuggingFaceProvider(model="fake/model").to_store()


def test_capture_disabled_records_nothing():
    p = HuggingFaceProvider(model="fake/model", capture=False)
    p._last_acts = np.zeros((2, 8))
    p.tag_last({"episode_id": "e0", "round": 1})
    assert p.captured == []


def test_describe_reports_the_settings_that_matter():
    d = HuggingFaceProvider(model="Qwen/Qwen3.8-27B", layer_stride=2).describe()
    assert d["model"] == "Qwen/Qwen3.8-27B"
    assert d["layer_stride"] == 2
    assert d["enable_thinking"] is False
    assert d["top_p"] == pytest.approx(0.8)
    assert d["top_k"] == 20
    assert set(d) >= {"provider", "model", "temperature", "dtype", "capture"}
    assert "constrained_choices" not in d


class _FakeChoiceTokenizer:
    eos_token_id = 99
    _encodings = {
        "1": [11], " 1": [21, 11],
        "2": [12], " 2": [21, 12],
        "3": [13], " 3": [21, 13],
    }

    def encode(self, text, add_special_tokens=False):
        assert add_special_tokens is False
        return list(self._encodings[text])

    def decode(self, token_ids, skip_special_tokens=True):
        assert skip_special_tokens is True
        token_ids = list(token_ids)
        if token_ids == [21, 11]:
            return " 1"
        if token_ids == [21, 12]:
            return " 2"
        if token_ids == [21, 13]:
            return " 3"
        return {11: "1", 12: "2", 13: "3", 99: ""}.get(token_ids[0], "?")


def test_choice_constraint_builds_exact_token_trie():
    sequences = _choice_token_sequences(_FakeChoiceTokenizer(), ("1", "2", "3"))
    assert set(sequences) == {(11,), (12,), (13,), (21, 11), (21, 12), (21, 13)}
    allowed = _choice_prefix_allowed_tokens(2, sequences, eos_token_id=99)
    assert allowed(0, [7, 8]) == [11, 12, 13, 21]
    assert allowed(0, [7, 8, 21]) == [11, 12, 13]
    assert allowed(0, [7, 8, 12]) == [99]
    with pytest.raises(ProviderError, match="left the constrained-choice"):
        allowed(0, [7, 8, 55])


def test_constrained_provider_reports_and_validates_exact_choices():
    provider = HuggingFaceProvider(
        model="fake/model", max_tokens=2, constrained_choices=("1", "2", "3")
    )
    provider._tok = _FakeChoiceTokenizer()
    kwargs = provider._choice_generation_kwargs(
        {"input_ids": np.asarray([[7, 8]], dtype=np.int64)}
    )
    assert kwargs["prefix_allowed_tokens_fn"](0, [7, 8]) == [11, 12, 13, 21]
    description = provider.describe()
    assert description["constrained_choices"] == ["1", "2", "3"]
    assert provider._validate_constrained_text(" 2 \n") == "2"
    with pytest.raises(ProviderError, match="invalid choice"):
        provider._validate_constrained_text("I choose 2")

    provider.max_tokens = 1
    with pytest.raises(ProviderError, match="cannot emit every constrained choice"):
        provider._choice_generation_kwargs(
            {"input_ids": np.asarray([[7, 8]], dtype=np.int64)}
        )


def test_missing_torch_gives_an_actionable_error(monkeypatch):
    import builtins

    real_import = builtins.__import__

    def fake_import(name, *a, **k):
        if name in ("torch", "transformers"):
            raise ImportError("no module named %s" % name)
        return real_import(name, *a, **k)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    from src.focal_agent import ProviderError

    with pytest.raises(ProviderError, match="requirements-pod.txt"):
        HuggingFaceProvider(model="fake/model")._ensure_loaded()


class _FakeAsker:
    def __init__(self, answer):
        self.answer = answer
        self.seen = None

    def ask(self, system, user, max_tokens=64):
        self.seen = user
        return self.answer


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("fairness", "fairness"),
        ("  Risk.", "risk"),
        ("I think expertise", "expertise"),
        ("unknown", "unknown"),
        ("purple monkey dishwasher", "unparsed"),
    ],
)
def test_black_box_guess_parses_the_answer(raw, expected):
    assert black_box_guess(_FakeAsker(raw), "some prompt") == expected


def test_black_box_answer_preserves_exact_raw_text():
    raw = "  I think Expertise.  "
    answer = black_box_answer(_FakeAsker(raw), "some prompt")
    assert answer == {"label": "expertise", "raw": "I think Expertise."}


def test_black_box_question_is_asked_in_a_separate_pass():
    """The baseline must not contaminate the episode: it appends its question to
    a COPY of the prompt and its answer is never returned to the focal agent."""
    fake = _FakeAsker("risk")
    original = "--- Current interaction (3 of 8) ---"
    black_box_guess(fake, original)
    assert fake.seen == original + BLACK_BOX_QUESTION
    assert original == "--- Current interaction (3 of 8) ---"  # unmodified
