"""Direct elicitation baseline for latent-target decoding.

The question is asked in a separate, deterministic forward pass after the
experiment.  Its answer is never inserted into any episode, so this baseline
cannot change the focal model's subsequent behaviour.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, Iterable, Mapping, Optional

from .hf_provider import black_box_answer, black_box_guess


GuessMap = Dict[str, Dict[str, str]]
RawAnswerMap = Dict[str, Dict[str, str]]


def collect_black_box_guesses(
    records: Iterable[Mapping[str, Any]],
    provider,
    existing: Optional[GuessMap] = None,
    checkpoint: Optional[Callable[[GuessMap], None]] = None,
    raw_answers: Optional[RawAnswerMap] = None,
    raw_checkpoint: Optional[Callable[[RawAnswerMap], None]] = None,
) -> GuessMap:
    """Measure one belief report per logged prompt, with safe resume support.

    ``raw_answers`` is optional for API compatibility, but production runs pass
    it so the exact generated text is retained alongside the normalized label.
    If a legacy label-only checkpoint is resumed, missing raw answers are
    regenerated and checked against the saved deterministic label.
    """
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
        raw_episode = (
            raw_answers.setdefault(episode, {}) if raw_answers is not None else None
        )
        needs_guess = round_number not in episode_guesses
        needs_raw = raw_episode is not None and round_number not in raw_episode
        if not needs_guess and not needs_raw:
            continue
        if raw_episode is None:
            episode_guesses[round_number] = black_box_guess(
                provider, str(row["focal_user_prompt"])
            )
        else:
            answer = black_box_answer(provider, str(row["focal_user_prompt"]))
            if not needs_guess and episode_guesses[round_number] != answer["label"]:
                raise RuntimeError(
                    "regenerated black-box label disagrees with checkpoint for "
                    "%s round %s" % (episode, round_number)
                )
            episode_guesses[round_number] = answer["label"]
            raw_episode[round_number] = answer["raw"]
        if checkpoint is not None:
            checkpoint(guesses)
        if raw_checkpoint is not None and raw_answers is not None:
            raw_checkpoint(raw_answers)
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
