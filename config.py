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

    def labels(self) -> Dict[str, str]:
        return {
            "fairness": self.fairness_label,
            "risk": self.risk_label,
            "expertise": self.expertise_label,
            "other": self.other_label,
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
