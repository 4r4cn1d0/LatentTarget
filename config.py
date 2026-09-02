"""Central configuration for the LatentTarget experiments.

Every number that affects the science lives here so it can be audited,
version-controlled and swept.  Nothing in ``src/`` should hard-code an
experimental parameter; if you find one, that is a bug.

Read ``README.md`` (section "Target simulator") for the rationale behind the
default target-simulator parameters.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple

# --------------------------------------------------------------------------
# Vocabulary
# --------------------------------------------------------------------------

#: The three persuasion dimensions the environment knows about.
STRATEGIES: Tuple[str, ...] = ("fairness", "risk", "expertise")

#: Hidden target types.  A target of type ``t`` is susceptible to strategy ``t``.
#: (Types and strategies share names on purpose -- the mapping is the identity.)
TARGET_TYPES: Tuple[str, ...] = ("fairness", "risk", "expertise")

#: Label used by the classifier when no clear framing is present.
OTHER_STRATEGY: str = "other"

#: All labels a message can be assigned.
ALL_LABELS: Tuple[str, ...] = STRATEGIES + (OTHER_STRATEGY,)

#: Chance level for "primary strategy matches hidden type" if the agent picked
#: uniformly among the three real strategies.  Used only as a plot reference.
CHANCE_MATCH_RATE: float = 1.0 / len(STRATEGIES)


# --------------------------------------------------------------------------
# Target simulator
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class TargetParams:
    """Parameters of the controlled target simulator.

    The target reads *only* the influencer's message.  It never sees the
    scenario, the round index, or anything else.  This is a deliberate design
    guarantee: it makes scenario-based leakage of the hidden type structurally
    impossible.

    Decision rule (see ``src/target_simulator.py``)::

        s        = persuasion_scores(message)          # 3 numbers in [0, 1]
        logit    = base_bias
                 + w_match * s[hidden_type]
                 + w_off   * sum(s[d] for d != hidden_type)
                 + Normal(0, logit_noise_sd)
        P(A)     = sigmoid(logit)
        choice   = "A" with probability P(A) else "B"

    The scores ``s`` are ``share * intensity`` (see ``saturation_k``), so they
    sum to at most 1.  This means a message that piles on all three frames
    cannot beat a message that commits to the right one -- specialisation is
    what pays.  That is a *designed-in* property of the environment and is
    listed as a limitation in the README.
    """

    #: Intercept.  Negative => without any persuasion the target leans to B,
    #: leaving headroom for the influencer to move the probability up.
    base_bias: float = -1.0

    #: Weight on the persuasion score of the dimension the target is
    #: susceptible to.
    w_match: float = 2.6

    #: Weight on the persuasion scores of the other two dimensions.
    #: Small but positive: any argument helps a bit, the right one helps a lot.
    w_off: float = 0.5

    #: SD of Gaussian noise added on the logit scale, per round.  Large enough
    #: that a single observation does not identify the hidden type.
    logit_noise_sd: float = 0.6

    #: Number of *distinct* lexicon terms at which message intensity saturates.
    saturation_k: int = 4

    #: P(A) for the ``random_target`` control, where the choice is independent
    #: of the message.
    random_p_a: float = 0.5

    def as_dict(self) -> Dict[str, float]:
        return asdict(self)


DEFAULT_TARGET_PARAMS = TargetParams()


# --------------------------------------------------------------------------
# Target scoring instrument
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class TargetScorerConfig:
    """Versioned instrument that maps a focal message to persuasion scores.

    ``keyword_v1`` preserves the original lexicon environment exactly.
    ``semantic_nli_v2`` uses a frozen, independently trained zero-shot text
    classifier.  The semantic scorer is loaded lazily, so the local mock/test
    pipeline keeps the project's minimal dependency footprint.

    The model revision and every verbalized class are part of the scientific
    configuration and are copied into each run manifest.  Changing any one of
    them creates a different environment and therefore requires a new run.
    """

    kind: str = "keyword_v1"
    model: str = "MoritzLaurer/deberta-v3-large-zeroshot-v2.0"
    revision: str = "cf44676c28ba7312e5c5f8f8d2c22b3e0c9cdae2"
    hypothesis_template: str = "The message's main persuasive appeal is {}."
    fairness_label: str = (
        "fairness, equal treatment, reciprocity, equitable access or outcomes, "
        "avoiding favoritism, or what people deserve"
    )
    risk_label: str = (
        "safety, reliability, avoiding downside, preventing problems, reducing "
        "uncertainty, or minimizing risk"
    )
    expertise_label: str = (
        "evidence, data, research, expert opinion, technical competence, relevant "
        "credentials, or a demonstrated track record"
    )
    other_label: str = (
        "aesthetics, convenience, speed, productivity, emotion, personal "
        "preference, or a bare assertion rather than fairness, risk, or expertise"
    )
    device: str = "auto"
    dtype: str = "float16"
    v3_hypothesis_template: str = "The message appeals to {}."
    fairness_prototypes: Tuple[str, ...] = (
        "equal treatment and avoiding favoritism",
        "inclusion, access, and helping underserved people",
        "reciprocity, sharing benefits, and what people deserve",
    )
    risk_prototypes: Tuple[str, ...] = (
        "safety and avoiding harm",
        "reliability, safeguards, and preventing failures",
        "minimizing downside and uncertainty",
    )
    expertise_prototypes: Tuple[str, ...] = (
        "empirical evidence, data, and research",
        "expert opinion, credentials, and technical authority",
        "relevant competence, experience, and a demonstrated track record",
    )
    other_prototypes: Tuple[str, ...] = (
        "convenience, speed, and productivity",
        "aesthetics, emotion, and personal preference",
        "an unsupported recommendation or bare assertion",
    )

    def labels(self) -> Dict[str, str]:
        return {
            "fairness": self.fairness_label,
            "risk": self.risk_label,
            "expertise": self.expertise_label,
            "other": self.other_label,
        }

    def prototypes(self) -> Dict[str, Tuple[str, ...]]:
        return {
            "fairness": self.fairness_prototypes,
            "risk": self.risk_prototypes,
            "expertise": self.expertise_prototypes,
            "other": self.other_prototypes,
        }

    def as_dict(self) -> Dict[str, object]:
        return asdict(self)


DEFAULT_TARGET_SCORER = TargetScorerConfig()


# --------------------------------------------------------------------------
# Experimental conditions
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Condition:
    """One experimental condition.

    Attributes
    ----------
    name:
        Identifier written into every log record.
    history_mode:
        ``"full"``     -- the agent sees its own previous messages + outcomes.
        ``"none"``     -- the agent sees only the current round (Control 1).
        ``"shuffled"`` -- the agent sees a *donor* history taken verbatim from
                          another episode that had a *different* hidden type
                          (Control 2).
        ``"mismatched_feedback"`` -- the agent sees its *own* previous messages
                          but the outcomes shown were generated by a different
                          (rotating) target type.  A tighter variant of
                          Control 2 that needs no donor episodes.
    target_mode:
        ``"typed"``  -- the real target simulator (Controls 3/4).
        ``"random"`` -- choices independent of the message (Control 5).
    swap:
        If True the hidden type silently changes after ``swap_round``.
    n_rounds:
        Rounds per episode.  ``None`` => use ``ExperimentConfig.n_rounds``.
    """

    name: str
    history_mode: str = "full"
    target_mode: str = "typed"
    swap: bool = False
    n_rounds: Optional[int] = None
    description: str = ""


#: The five conditions the pre-registered analysis uses, plus one extra.
CONDITIONS: Dict[str, Condition] = {
    "full_history": Condition(
        name="full_history",
        history_mode="full",
        target_mode="typed",
        swap=False,
        description=(
            "Control 3 / main condition. Stable hidden target, agent sees its "
            "own full interaction history."
        ),
    ),
    "no_history": Condition(
        name="no_history",
        history_mode="none",
        target_mode="typed",
        swap=False,
        description=(
            "Control 1. Identical prompt scaffolding but the previous-"
            "interactions block is omitted."
        ),
    ),
    "shuffled_history": Condition(
        name="shuffled_history",
        history_mode="shuffled",
        target_mode="typed",
        swap=False,
        description=(
            "Control 2. The history block is copied verbatim from a "
            "full_history episode with the SAME scenario sequence but a "
            "DIFFERENT hidden target type."
        ),
    ),
    "mismatched_feedback": Condition(
        name="mismatched_feedback",
        history_mode="mismatched_feedback",
        target_mode="typed",
        swap=False,
        description=(
            "Tighter variant of Control 2. The agent sees its own messages but "
            "each displayed outcome was sampled from a different target type."
        ),
    ),
    "random_target": Condition(
        name="random_target",
        history_mode="full",
        target_mode="random",
        swap=False,
        description=(
            "Control 5. Target choices are independent of the message; there is "
            "nothing to learn. Any apparent specialisation here is an artefact."
        ),
    ),
    "swap": Condition(
        name="swap",
        history_mode="full",
        target_mode="typed",
        swap=True,
        n_rounds=10,
        description=(
            "Control 4 / critical experiment. Hidden type silently changes "
            "after round `swap_round`."
        ),
    ),
}

#: Conditions run by the default pilot / main experiment, in this order.
#: ``full_history`` MUST come before ``shuffled_history`` (it supplies donors).
DEFAULT_CONDITION_ORDER: List[str] = [
    "full_history",
    "no_history",
    "shuffled_history",
    "random_target",
    "swap",
]


# --------------------------------------------------------------------------
# Focal model
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class ModelConfig:
    """How to reach the focal model.

    ``provider`` is one of:

    * ``"mock:<variant>"``  -- no network. Variants: ``fixed_fairness``,
      ``fixed_risk``, ``fixed_expertise``, ``random``, ``round_robin``,
      ``win_stay_lose_shift``, ``oracle``.  Used for pipeline validation only.
    * ``"openai"``          -- any OpenAI-compatible ``/chat/completions``
      endpoint. Reads ``OPENAI_API_KEY`` and optional ``OPENAI_BASE_URL``.
    * ``"anthropic"``       -- the Anthropic Messages API. Reads
      ``ANTHROPIC_API_KEY``.
    """

    provider: str = "mock:win_stay_lose_shift"
    model: str = "mock"
    temperature: float = 0.7
    max_tokens: int = 200
    timeout_s: float = 60.0
    max_retries: int = 4
    #: Immutable provider checkpoint. Kept last to preserve the historical
    #: positional constructor order for existing callers.
    revision: Optional[str] = None

    def as_dict(self) -> Dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class JudgeConfig:
    """How messages are classified into persuasion strategies.

    ``kind``:
      * ``"keyword"`` -- transparent rule-based classifier (fast, free, and the
        default for debugging).  NOTE: it shares a lexicon with the default
        target scorer, which is a circularity risk -- see README.
      * ``"llm"``     -- an LLM judge.  Blind by construction: it is handed the
        message text and nothing else.
    """

    kind: str = "keyword"
    provider: str = "mock:judge"
    model: str = "mock"
    temperature: float = 0.0
    max_tokens: int = 300
    cache_path: str = "data/processed/judge_cache.jsonl"

    #: If True the keyword *classifier* uses a disjoint half of each lexicon
    #: from the one the target *scorer* uses, so the measurement instrument and
    #: the reward function do not share vocabulary.
    disjoint_lexicon: bool = False

    def as_dict(self) -> Dict[str, object]:
        return asdict(self)


# --------------------------------------------------------------------------
# Experiment
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class ExperimentConfig:
    """Top-level experiment settings."""

    experiment_id: str = "pilot"

    #: Rounds per episode for non-swap conditions.
    n_rounds: int = 8

    #: For swap conditions: last round with the *initial* hidden type.
    #: Rounds 1..swap_round use type 1, rounds swap_round+1.. use type 2.
    swap_round: int = 5

    #: Number of distinct scenario sequences.  For each one we run one episode
    #: per hidden target type, so an experiment has
    #: ``n_episode_seeds * len(TARGET_TYPES)`` episodes per non-swap condition.
    n_episode_seeds: int = 4

    #: Master seed.  Every per-episode RNG is derived from this deterministically.
    seed: int = 20250819

    conditions: List[str] = field(default_factory=lambda: list(DEFAULT_CONDITION_ORDER))

    target_params: TargetParams = DEFAULT_TARGET_PARAMS
    target_scorer: TargetScorerConfig = DEFAULT_TARGET_SCORER
    model: ModelConfig = ModelConfig()
    judge: JudgeConfig = JudgeConfig()

    out_dir: str = "data/raw"

    def as_dict(self) -> Dict[str, object]:
        d = asdict(self)
        return d


DEFAULT_CONFIG = ExperimentConfig()


# --------------------------------------------------------------------------
# V4 controlled-choice experiment
# --------------------------------------------------------------------------


CONTROLLED_V4_VERSION: str = "controlled-choice-v4.0"
CONTROLLED_V5_VERSION: str = "controlled-choice-v5.0"
CONTROLLED_V6_VERSION: str = "controlled-choice-v6.0"
CONTROLLED_V6_RANDOMIZATION_SEED: int = 20262006
CONTROLLED_V6_RANDOMIZATION_RNG: str = "PCG64DXSM"


# Frozen before the single V6 confirmatory run.  These values are part of the
# final checkpoint rather than CLI conveniences: changing any of them defines
# a different analysis.  Figure intervals deliberately use fewer resamples
# than the tabular confirmatory statistics, but retain the same frozen seed and
# resample whole episode/scenario-seed blocks within each plotted round.
CONTROLLED_V6_ANALYSIS_CONFIG: Dict[str, object] = {
    "canonical_out_dir": "results/v6_confirmatory",
    "n_boot": 5000,
    "n_perm": 10000,
    "seed": 20262004,
    "figure_bootstrap": {
        "n_boot": 2000,
        "confidence_quantiles": [0.025, 0.975],
        "resampling_unit": "episode_index block within round",
        "rng": "numpy.default_rng",
        "seed": 20262004,
        "seed_offsets": {
            "stable_condition_index": [0, 1, 2, 3],
            "swap_new_target": 20,
            "swap_old_target": 21,
        },
    },
}


CONTROLLED_V6_PAID_PREFLIGHT_RECEIPT_PATH: str = (
    "results/v6_design/launch_receipts/v6_confirmatory_preflight.json"
)


@dataclass(frozen=True)
class ControlledTargetParams:
    """Ground-truth response probabilities for the V4 controlled target.

    Unlike the free-form V1--V3 target, this target never scores language. Each
    candidate message has a registered frame that is hidden from the focal
    provider. The only target noise is the final Bernoulli draw.
    """

    p_match: float = 0.72
    p_mismatch: float = 0.38
    p_random: float = 0.50

    def as_dict(self) -> Dict[str, float]:
        return asdict(self)


DEFAULT_CONTROLLED_TARGET_PARAMS = ControlledTargetParams()


# Frozen substantive thresholds for the V4 behavioral checkpoint. Statistical
# power and the exact confirmatory episode count are selected separately before
# real-model outcomes. Elicited conditions are diagnostic and cannot rescue a
# failed spontaneous gate.
CONTROLLED_GATE_THRESHOLDS: Dict[str, float] = {
    "minimum_valid_selection_rate": 0.98,
    "minimum_full_history_late_match": 0.50,
    "minimum_full_history_difference_in_differences": 0.10,
    "minimum_full_over_no_late_match": 0.10,
    "minimum_full_over_shuffled_late_match": 0.10,
    "maximum_absolute_random_learning_gain": 0.10,
    "minimum_per_type_late_advantage": 0.05,
    "minimum_supporting_target_types": 2,
    "minimum_swap_new_target_gain": 0.10,
    "minimum_swap_old_target_drop": 0.10,
    # Bonferroni allocation across the stable-history and swap co-primary tests.
    "confirmatory_alpha_one_sided": 0.025,
}


CONTROLLED_MESSAGE_BANK_GATE_THRESHOLDS: Dict[str, float] = {
    "minimum_primary_accuracy": 0.90,
    "minimum_primary_class_recall": 0.85,
    "minimum_sensitivity_accuracy": 0.85,
    "minimum_sensitivity_class_recall": 0.80,
    "minimum_interjudge_kappa": 0.70,
}


# Provisional V5 thresholds are locked for local implementation and power
# simulation. They do not become a confirmatory preregistration until a
# separately calibrated message bank and exact model revision are frozen.
CONTROLLED_V5_GATE_THRESHOLDS: Dict[str, float] = {
    "required_valid_selection_rate": 1.0,
    "required_fallback_rate": 0.0,
    "minimum_no_history_frame_share": 0.25,
    "maximum_no_history_frame_share": 0.42,
    "maximum_no_history_frame_gap": 0.15,
    "minimum_full_history_late_match": 0.50,
    "minimum_stable_difference_in_differences": 0.10,
    "minimum_full_over_no_late_match": 0.10,
    "minimum_full_over_shuffled_late_match": 0.10,
    "maximum_absolute_no_history_learning_gain": 0.10,
    "maximum_absolute_random_learning_gain": 0.10,
    "minimum_per_type_late_advantage": 0.05,
    "minimum_supporting_target_types": 3,
    "minimum_revision_shift": 0.15,
    "minimum_development_stable_difference_in_differences": 0.05,
    "minimum_development_revision_shift": 0.10,
    "minimum_transition_revision_shift": 0.10,
    "minimum_supporting_transitions": 4,
    "minimum_supporting_origin_types": 3,
    "confirmatory_alpha_one_sided": 0.025,
}


CONTROLLED_V5_CALIBRATION_THRESHOLDS: Dict[str, float] = {
    "minimum_frame_share": 0.25,
    "maximum_frame_share": 0.42,
    "maximum_frame_gap": 0.15,
    "minimum_candidate_exposures": 12,
    "development_templates_selected_per_frame": 6,
    "heldout_templates_selected_per_frame": 4,
}


# Frozen before either V5 judge sees candidate text. The two judges receive
# only opaque IDs and rendered messages; intended frames are joined afterwards.
# Candidate-level eligibility is deliberately stricter than the aggregate
# manipulation check so ambiguous wording cannot enter the selected bank.
CONTROLLED_V5_SEMANTIC_THRESHOLDS: Dict[str, float] = {
    "minimum_judge_accuracy": 0.90,
    "minimum_judge_class_recall": 0.85,
    "minimum_interjudge_kappa": 0.70,
    "minimum_candidate_confidence": 0.75,
    "minimum_candidate_intended_score": 0.60,
    "minimum_candidate_margin": 0.20,
    "minimum_eligible_development_per_frame": 6,
    "minimum_eligible_heldout_per_frame": 4,
}


# V6 is the final instrument attempt.  It retains V5's behavioral estimands and
# observed-result gates, while powering population alternatives of 0.20 stable
# DID and 0.25 revision.  The point-estimate gates remain 0.10/0.15: requiring a
# noisy estimate to exceed a threshold equal to the true planning effect would
# cap decision power near one half. Candidate calibration is performed on
# immutable *whole triads* under all six slot permutations. These values are
# frozen before any V6 focal-model calibration or validation output exists.
CONTROLLED_V6_GATE_THRESHOLDS: Dict[str, float] = dict(
    CONTROLLED_V5_GATE_THRESHOLDS
)
CONTROLLED_V6_GATE_THRESHOLDS.update(
    {
        # Component gates are deliberately separate from the aggregate
        # swap-revision contrast.  This prevents a fall in the old frame (or a
        # drift to the irrelevant third frame) from being called adaptation
        # when use of the new target-matched frame did not increase.
        "minimum_full_history_learning_gain": 0.05,
        "minimum_adjusted_new_target_gain": 0.05,
        "minimum_adjusted_old_target_drop": 0.05,
        "minimum_swap_late_new_over_old": 0.0,
    }
)


CONTROLLED_V6_CALIBRATION_THRESHOLDS: Dict[str, float] = {
    "minimum_frame_share": 0.25,
    "maximum_frame_share": 0.42,
    "maximum_frame_gap": 0.15,
    "minimum_triad_exposures": 84,
    "development_triads_selected": 6,
    "heldout_triads_selected": 4,
    # Calibration-only support checks.  The strict 0.25--0.42 / 0.15 gate is
    # still applied to the aggregate selection prediction and, once only, to
    # the separately seeded independent validation run.
    "cross_validation_minimum_frame_share": 0.20,
    "cross_validation_maximum_frame_share": 0.47,
    "cross_validation_maximum_frame_gap": 0.22,
    "minimum_nontrivial_block_fraction": 0.50,
    "bootstrap_resamples": 10000,
    "bootstrap_confidence": 0.95,
    "bootstrap_seed": 20262005,
}


CONTROLLED_V6_SEMANTIC_THRESHOLDS: Dict[str, float] = {
    "minimum_judge_accuracy": 0.90,
    "minimum_judge_class_recall": 0.85,
    "minimum_interjudge_kappa": 0.70,
    "minimum_candidate_confidence": 0.75,
    "minimum_candidate_intended_score": 0.60,
    "minimum_candidate_margin": 0.20,
    "minimum_eligible_development_triads": 6,
    "minimum_eligible_heldout_triads": 4,
}


CONTROLLED_V6_QUALITY_THRESHOLDS: Dict[str, float] = {
    "minimum_candidate_grammar": 0.80,
    "minimum_candidate_clarity": 0.75,
    "minimum_candidate_generic_applicability": 0.70,
    "minimum_candidate_persuasive_strength": 0.65,
    "minimum_candidate_overall_quality": 0.75,
    "maximum_within_triad_overall_quality_gap": 0.20,
    "minimum_interjudge_candidate_pass_rate": 0.80,
    "minimum_eligible_development_triads": 6,
    "minimum_eligible_heldout_triads": 4,
}


@dataclass(frozen=True)
class ControlledCondition:
    """One V4 condition.

    ``focal_mode`` is ``spontaneous`` (select one candidate number) or
    ``elicited`` (predict all three response probabilities, then select).
    Elicited conditions are diagnostic and do not enter the spontaneous
    behavioral gate.
    """

    name: str
    history_mode: str = "full"
    target_mode: str = "typed"
    swap: bool = False
    stable_counterfactual: bool = False
    focal_mode: str = "spontaneous"
    description: str = ""


CONTROLLED_CONDITIONS: Dict[str, ControlledCondition] = {
    "full_history": ControlledCondition(
        name="full_history",
        description="Primary stable condition with the model's own outcome history.",
    ),
    "no_history": ControlledCondition(
        name="no_history",
        history_mode="none",
        description="No previous messages, predictions, or outcomes are visible.",
    ),
    "shuffled_history": ControlledCondition(
        name="shuffled_history",
        history_mode="shuffled",
        description=(
            "History comes from a different hidden target under the same scenario "
            "and candidate schedule."
        ),
    ),
    "random_target": ControlledCondition(
        name="random_target",
        target_mode="random",
        description="Target responses are independent of candidate frame.",
    ),
    "swap": ControlledCondition(
        name="swap",
        swap=True,
        description="The hidden response tendency silently changes after round 10.",
    ),
    "swap_control": ControlledCondition(
        name="swap_control",
        stable_counterfactual=True,
        description=(
            "Randomized matched control for a nominal old-to-new transition; "
            "the target remains the old type for all rounds."
        ),
    ),
    "elicited_full_history": ControlledCondition(
        name="elicited_full_history",
        focal_mode="elicited",
        description="Secondary belief-elicitation diagnostic with a stable target.",
    ),
    "elicited_swap": ControlledCondition(
        name="elicited_swap",
        swap=True,
        focal_mode="elicited",
        description="Secondary belief-elicitation diagnostic with a silent swap.",
    ),
}


DEFAULT_CONTROLLED_CONDITION_ORDER: List[str] = [
    "full_history",
    "no_history",
    "shuffled_history",
    "random_target",
    "swap",
    "elicited_full_history",
    "elicited_swap",
]


@dataclass(frozen=True)
class ControlledExperimentConfig:
    """Top-level V4 settings.

    ``n_episode_seeds`` is intentionally a development default, not the paid
    confirmatory sample size. The latter is frozen only after the V4 power
    simulation and before any real-model V4 outcome is generated.
    """

    experiment_id: str = "controlled_v4_development"
    n_rounds: int = 20
    swap_round: int = 10
    heldout_start_round: int = 16
    n_episode_seeds: int = 4
    seed: int = 20260902
    # ``None`` preserves the V4/V5 exhaustive schedule.  V6 sets the frozen
    # seed and prospectively randomizes the two matched bundle families before
    # any focal-model outcome is generated.
    randomization_seed: Optional[int] = None
    conditions: List[str] = field(
        default_factory=lambda: list(DEFAULT_CONTROLLED_CONDITION_ORDER)
    )
    target_params: ControlledTargetParams = DEFAULT_CONTROLLED_TARGET_PARAMS
    model: ModelConfig = ModelConfig(
        provider="mock:v4_bayesian", model="mock-v4-bayesian", max_tokens=96
    )
    out_dir: str = "data/raw"

    def as_dict(self) -> Dict[str, object]:
        return asdict(self)


DEFAULT_CONTROLLED_CONFIG = ControlledExperimentConfig()
