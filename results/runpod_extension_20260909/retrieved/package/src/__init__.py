"""LatentTarget: does an LLM build and revise a model of another agent's
susceptibility to different kinds of persuasion during repeated interaction?

Module map
----------
``scenarios``           neutral binary-choice decision problems
``lexicons``            the shared persuasion word lists (and their split)
``target_simulator``    the controlled target: ground truth of the environment
``focal_agent``         prompt construction + model providers (incl. mocks)
``strategy_classifier`` blind classification of messages into strategies
``experiment``          episode / experiment runners and the conditions
``logging_utils``       JSONL records and run manifests
``stats_utils``         bootstrap CIs, permutation tests, logistic regression
``analysis``            metrics, diagnostics, plots
``seeding``             stable seed derivation
"""

__all__ = [
    "analysis",
    "experiment",
    "focal_agent",
    "lexicons",
    "logging_utils",
    "scenarios",
    "seeding",
    "stats_utils",
    "strategy_classifier",
    "target_simulator",
]
