"""Contract tests for the open-weight provider.

These run without torch/transformers: they check the *isolation guarantee* and
the bookkeeping, which are the parts that could silently invalidate a result.
The model loading itself is exercised on the pod, not here.
"""

from __future__ import annotations

import inspect

import numpy as np
import pytest

from src.focal_agent import FocalPrompt
from src.hf_provider import (
    BLACK_BOX_QUESTION,
    HuggingFaceProvider,
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


def test_black_box_question_is_asked_in_a_separate_pass():
    """The baseline must not contaminate the episode: it appends its question to
    a COPY of the prompt and its answer is never returned to the focal agent."""
    fake = _FakeAsker("risk")
    original = "--- Current interaction (3 of 8) ---"
    black_box_guess(fake, original)
    assert fake.seen == original + BLACK_BOX_QUESTION
    assert original == "--- Current interaction (3 of 8) ---"  # unmodified
