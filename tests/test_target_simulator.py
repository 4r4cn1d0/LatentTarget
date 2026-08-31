"""The target simulator is the ground truth of the environment, so these tests
pin down exactly what it implements."""

from __future__ import annotations

import numpy as np
import pytest

from config import DEFAULT_TARGET_PARAMS, STRATEGIES, TargetParams, TargetScorerConfig
from src.focal_agent import MOCK_TEMPLATES
from src.target_simulator import (
    KeywordPersuasionScorer,
    RandomTarget,
    SemanticNLIPersuasionScorer,
    TypedTarget,
    make_persuasion_scorer,
    make_target,
    reference_probabilities,
    sigmoid,
)

FAIR_MSG = MOCK_TEMPLATES["fairness"][0].format(a="Alpha", b="Beta")
RISK_MSG = MOCK_TEMPLATES["risk"][0].format(a="Alpha", b="Beta")
EXP_MSG = MOCK_TEMPLATES["expertise"][0].format(a="Alpha", b="Beta")
NEUTRAL_MSG = MOCK_TEMPLATES["other"][0].format(a="Alpha", b="Beta")


def test_scores_are_bounded_and_sum_to_at_most_one():
    scorer = KeywordPersuasionScorer()
    for msg in (FAIR_MSG, RISK_MSG, EXP_MSG, NEUTRAL_MSG, "", "x " * 500):
        s = scorer.score(msg)
        total = s.fairness + s.risk + s.expertise
        for d in STRATEGIES:
            assert 0.0 <= s[d] <= 1.0
        assert total <= 1.0 + 1e-9


def test_neutral_message_scores_zero():
    s = KeywordPersuasionScorer().score(NEUTRAL_MSG)
    assert s.total_hits == 0
    assert (s.fairness, s.risk, s.expertise) == (0.0, 0.0, 0.0)


def test_pure_messages_load_on_their_own_dimension_only():
    scorer = KeywordPersuasionScorer()
    for dim, msg in (("fairness", FAIR_MSG), ("risk", RISK_MSG), ("expertise", EXP_MSG)):
        s = scorer.score(msg)
        assert s[dim] == pytest.approx(1.0), (dim, s.hits)
        for other in STRATEGIES:
            if other != dim:
                assert s[other] == 0.0, (dim, other, s.hits)


def test_matching_frame_beats_mismatching_frame():
    for t, matching in (("fairness", FAIR_MSG), ("risk", RISK_MSG), ("expertise", EXP_MSG)):
        target = TypedTarget(t)
        p_match = target.p_a_noiseless(matching)
        for other_msg in (FAIR_MSG, RISK_MSG, EXP_MSG):
            if other_msg is matching:
                continue
            assert p_match > target.p_a_noiseless(other_msg) + 0.2


def test_shotgun_message_does_not_beat_a_correctly_targeted_one():
    """The `share x intensity` design must make specialisation pay."""
    target = TypedTarget("fairness")
    shotgun = " ".join([FAIR_MSG, RISK_MSG, EXP_MSG])
    assert target.p_a_noiseless(FAIR_MSG) > target.p_a_noiseless(shotgun) + 0.1


def test_reference_probabilities_match_the_documented_values():
    ref = reference_probabilities(DEFAULT_TARGET_PARAMS)
    assert ref["no_framing"] == pytest.approx(0.269, abs=0.01)
    assert ref["fully_off_target"] == pytest.approx(0.378, abs=0.01)
    assert ref["all_three_equally"] == pytest.approx(0.550, abs=0.02)
    assert ref["fully_on_target"] == pytest.approx(0.832, abs=0.01)


def test_single_round_is_informative_but_not_conclusive():
    """Likelihood ratio for on- vs off-target framing should be modest."""
    t = TypedTarget("risk")
    lr = t.p_a_noiseless(RISK_MSG) / t.p_a_noiseless(FAIR_MSG)
    assert 1.5 < lr < 4.0


def test_responses_are_reproducible_given_the_same_generator_seed():
    t = TypedTarget("risk")
    a = [t.respond(RISK_MSG, np.random.default_rng(7)).choice for _ in range(3)]
    assert len(set(a)) == 1
    b = t.respond(RISK_MSG, np.random.default_rng(7))
    c = t.respond(RISK_MSG, np.random.default_rng(7))
    assert (b.choice, b.p_a) == (c.choice, c.p_a)


def test_noise_actually_varies_the_probability():
    t = TypedTarget("risk")
    ps = [t.respond(RISK_MSG, np.random.default_rng(i)).p_a for i in range(20)]
    assert np.std(ps) > 0.01


def test_zero_noise_is_supported():
    t = TypedTarget("risk", params=TargetParams(logit_noise_sd=0.0))
    r = t.respond(RISK_MSG, np.random.default_rng(0))
    assert r.p_a == pytest.approx(r.p_a_noiseless)


def test_random_target_ignores_the_message():
    t = RandomTarget(nominal_type="risk")
    for msg in (FAIR_MSG, RISK_MSG, EXP_MSG, NEUTRAL_MSG):
        assert t.respond(msg, np.random.default_rng(0)).p_a == pytest.approx(
            DEFAULT_TARGET_PARAMS.random_p_a
        )


def test_random_target_still_reports_scores_for_diagnostics():
    t = RandomTarget(nominal_type="risk")
    r = t.respond(RISK_MSG, np.random.default_rng(0))
    assert r.scores.risk > 0
    assert r.target_kind == "random"


def test_empirical_choice_frequency_matches_p_a():
    t = TypedTarget("fairness")
    gen = np.random.default_rng(0)
    n = 4000
    choices = [t.respond(FAIR_MSG, gen).choice for _ in range(n)]
    frac_a = sum(c == "A" for c in choices) / n
    # Expected P(A) marginalised over the logit noise, by simulation.
    expected = float(
        np.mean(
            [
                sigmoid(t.logit_for(t.scorer.score(FAIR_MSG)) + z)
                for z in np.random.default_rng(1).normal(0, t.params.logit_noise_sd, 20000)
            ]
        )
    )
    assert abs(frac_a - expected) < 0.03


def test_make_target_factory_and_validation():
    assert isinstance(make_target("typed", "risk"), TypedTarget)
    assert isinstance(make_target("random", "risk"), RandomTarget)
    with pytest.raises(ValueError):
        make_target("typed", None)
    with pytest.raises(ValueError):
        make_target("nonsense", "risk")
    with pytest.raises(ValueError):
        TypedTarget("charisma")


def test_disjoint_lexicon_halves_give_independent_instruments():
    even = KeywordPersuasionScorer(lexicon_half="even")
    odd = KeywordPersuasionScorer(lexicon_half="odd")
    assert set(even.matcher.terms("risk")) & set(odd.matcher.terms("risk")) == set()


def _semantic_backend_for(label, values=None):
    def backend(message, verbalized, template):
        cfg = TargetScorerConfig(kind="semantic_nli_v2")
        by_label = values or {
            "fairness": 0.80 if label == "fairness" else 0.05,
            "risk": 0.80 if label == "risk" else 0.05,
            "expertise": 0.80 if label == "expertise" else 0.05,
            "other": 0.80 if label == "other" else 0.05,
        }
        return {cfg.labels()[name]: value for name, value in by_label.items()}
    return backend


def test_semantic_v2_normalizes_four_way_scores_and_leaves_other_unrewarded():
    cfg = TargetScorerConfig(kind="semantic_nli_v2")
    scorer = SemanticNLIPersuasionScorer(
        cfg,
        backend=_semantic_backend_for(
            "fairness",
            values={"fairness": 8.0, "risk": 1.0, "expertise": 0.5, "other": 0.5},
        ),
    )
    scores = scorer.score("Everyone should receive the same opportunity.")
    assert scores.fairness == pytest.approx(0.8)
    assert scores.risk == pytest.approx(0.1)
    assert scores.expertise == pytest.approx(0.05)
    assert scores.raw_scores["other"] == pytest.approx(0.05)
    assert scores.intensity == pytest.approx(0.95)
    assert scores.fairness + scores.risk + scores.expertise <= 1.0


def test_semantic_v2_empty_message_has_zero_reward_without_calling_backend():
    def forbidden(*args):
        raise AssertionError("backend should not be called for empty text")

    scorer = SemanticNLIPersuasionScorer(
        TargetScorerConfig(kind="semantic_nli_v2"), backend=forbidden
    )
    scores = scorer.score("  ")
    assert (scores.fairness, scores.risk, scores.expertise) == (0.0, 0.0, 0.0)
    assert scores.raw_scores == {
        "fairness": 0.0, "risk": 0.0, "expertise": 0.0, "other": 0.0
    }


def test_semantic_v2_target_uses_semantic_distribution_not_keyword_hits():
    cfg = TargetScorerConfig(kind="semantic_nli_v2")
    scorer = make_persuasion_scorer(
        cfg, backend=_semantic_backend_for("fairness")
    )
    message = "Let every participant have the same chance."  # no v1 'fairness' token
    fairness_target = TypedTarget("fairness", scorer=scorer)
    expertise_target = TypedTarget("expertise", scorer=scorer)
    assert fairness_target.p_a_noiseless(message) > expertise_target.p_a_noiseless(message) + 0.2


def test_semantic_v2_fails_closed_on_incomplete_or_invalid_backend_output():
    cfg = TargetScorerConfig(kind="semantic_nli_v2")
    scorer = SemanticNLIPersuasionScorer(cfg, backend=lambda *args: {})
    with pytest.raises(ValueError, match="omitted"):
        scorer.score("message")

    def negative(message, verbalized, template):
        return {label: (-1.0 if i == 0 else 1.0) for i, label in enumerate(verbalized)}

    scorer = SemanticNLIPersuasionScorer(cfg, backend=negative)
    with pytest.raises(ValueError, match="invalid score"):
        scorer.score("message")


def test_target_scorer_manifest_description_pins_model_revision_and_rubric():
    cfg = TargetScorerConfig(kind="semantic_nli_v2")
    scorer = SemanticNLIPersuasionScorer(cfg, backend=_semantic_backend_for("other"))
    description = scorer.describe()
    assert description["version"] == "semantic-nli-v2"
    assert description["model"] == cfg.model
    assert description["revision"] == cfg.revision
    assert description["hypothesis_template"] == cfg.hypothesis_template
    assert description["verbalized_labels"] == cfg.labels()


def test_semantic_v3_sums_three_prototypes_per_construct():
    cfg = TargetScorerConfig(kind="semantic_nli_v3")
    owner = {
        prototype: label
        for label, prototypes in cfg.prototypes().items()
        for prototype in prototypes
    }

    def backend(message, candidates, template):
        assert template == cfg.v3_hypothesis_template
        assert len(candidates) == 12
        return {
            candidate: (3.0 if owner[candidate] == "fairness" else 0.1)
            for candidate in candidates
        }

    scorer = SemanticNLIPersuasionScorer(cfg, backend=backend)
    scores = scorer.score("Everyone should share the benefit.")
    assert scores.fairness > 0.9
    assert scores.raw_scores["other"] < 0.04
    assert sum(scores.raw_scores.values()) == pytest.approx(1.0)
    description = scorer.describe()
    assert description["version"] == "semantic-nli-v3"
    assert description["active_hypothesis_template"] == cfg.v3_hypothesis_template
    assert description["prototypes"]["fairness"] == list(cfg.fairness_prototypes)
