import hashlib

from src import controlled_focal_agent as fa

V4_TEMPLATE_SHA256 = "f0fbae7ac412e652c496d336a330381d40463124e3812e08906d26b2cdfc17f5"
PROHIBITED = ("hidden type", "susceptib", "psychological profile", "persuasion strateg", "manipulat", "exploit", "learn the participant", "adapt to the participant")


def test_v4_template_is_unchanged_and_default():
    assert hashlib.sha256(fa.SPONTANEOUS_SYSTEM_TEMPLATE.encode()).hexdigest() == V4_TEMPLATE_SHA256
    fa.set_spontaneous_prompt_variant("v4")
    assert fa._system_prompt("spontaneous", 20) == fa.SPONTANEOUS_SYSTEM_TEMPLATE.format(n_rounds=20)


def test_paraphrase_variant_switches_only_the_spontaneous_prompt():
    try:
        fa.set_spontaneous_prompt_variant("paraphrase_1")
        rendered = fa._system_prompt("spontaneous", 20)
        assert rendered == fa.SPONTANEOUS_SYSTEM_TEMPLATE_PARAPHRASE_1.format(n_rounds=20)
        assert rendered != fa.SPONTANEOUS_SYSTEM_TEMPLATE.format(n_rounds=20)
        assert "20 rounds" in rendered and "1, 2, or 3" in rendered and "Option A" in rendered
        assert not any(p in rendered.lower() for p in PROHIBITED)
        assert fa._system_prompt("elicited", 20) == fa.ELICITED_SYSTEM_TEMPLATE.format(n_rounds=20)
    finally:
        fa.set_spontaneous_prompt_variant("v4")


def test_unknown_variant_rejected():
    import pytest
    with pytest.raises(ValueError):
        fa.set_spontaneous_prompt_variant("nope")
