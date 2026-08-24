"""Direct elicitation baseline for latent-target decoding.

The question is asked in a separate, deterministic forward pass after the
experiment.  Its answer is never inserted into any episode, so this baseline
cannot change the focal model's subsequent behaviour.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, Iterable, Mapping, Optional

from .hf_provider import black_box_guess


GuessMap = Dict[str, Dict[str, str]]


def collect_black_box_guesses(
    records: Iterable[Mapping[str, Any]],
    provider,
    existing: Optional[GuessMap] = None,
    checkpoint: Optional[Callable[[GuessMap], None]] = None,
) -> GuessMap:
    """Measure one belief report per logged prompt, with safe resume support."""
    guesses: GuessMap = {
        str(episode): {str(round_number): str(value) for round_number, value in rounds.items()}
        for episode, rounds in (existing or {}).items()
    }
    ordered = sorted(
        records,
        key=lambda row: (str(row["episode_id"]), int(row["round"])),
    )
    for row in ordered:
        episode = str(row["episode_id"])
        round_number = str(int(row["round"]))
        episode_guesses = guesses.setdefault(episode, {})
        if round_number in episode_guesses:
            continue
        episode_guesses[round_number] = black_box_guess(
            provider, str(row["focal_user_prompt"])
        )
        if checkpoint is not None:
            checkpoint(guesses)
    return guesses


def score_black_box_guesses(
    records: Iterable[Mapping[str, Any]], guesses: GuessMap
) -> Dict[str, Any]:
    """Accuracy and coverage; ``unknown``/``unparsed`` count as incorrect."""
    n = 0
    hits = 0
    by_condition: Dict[str, Dict[str, int]] = {}
    for row in records:
        episode = str(row["episode_id"])
        round_number = str(int(row["round"]))
        guess = guesses.get(episode, {}).get(round_number)
        if guess is None:
            continue
        n += 1
        hit = int(guess == str(row["hidden_target_type"]))
        hits += hit
        bucket = by_condition.setdefault(str(row["condition"]), {"n": 0, "hits": 0})
        bucket["n"] += 1
        bucket["hits"] += hit
    return {
        "n_scored": n,
        "accuracy": hits / n if n else None,
        "by_condition": {
            name: {
                "n": values["n"],
                "accuracy": values["hits"] / values["n"] if values["n"] else None,
            }
            for name, values in sorted(by_condition.items())
        },
    }
