from __future__ import annotations

from collections import Counter

from config import CONTROLLED_MESSAGE_BANK_GATE_THRESHOLDS
from src.blind_judge import build_blind_batches
from src.controlled_messages import (
    DEVELOPMENT_TEMPLATES,
    HELDOUT_TEMPLATES,
    message_bank_sha256,
)
from src.scenarios import SCENARIOS


def _samples():
    rows = []
    for bank in (DEVELOPMENT_TEMPLATES, HELDOUT_TEMPLATES):
        for frame, templates in bank.items():
            for template in templates:
                for scenario in (SCENARIOS[0], SCENARIOS[7]):
                    rows.append({
                        "intended_frame": frame,
                        "message": template.format(a=scenario.option_a, b=scenario.option_b),
                    })
    return rows


def test_v4_manipulation_check_is_balanced_unique_and_blind_by_schema():
    samples = _samples()
    assert len(samples) == len({row["message"] for row in samples}) == 90
    assert Counter(row["intended_frame"] for row in samples) == {
        "fairness": 30, "risk": 30, "expertise": 30,
    }
    batches = build_blind_batches(
        (row["message"] for row in samples), "judge", batch_size=24, seed=1
    )
    assert all(
        set(sample.judge_dict()) == {"sample_id", "message"}
        for batch in batches for sample in batch
    )


def test_v4_message_bank_hash_and_gates_are_stable():
    assert message_bank_sha256() == "f352c0a17b8ff3c9fca7543399499e966f9a88a99c5620e051da0c9003d2c0f4"
    assert CONTROLLED_MESSAGE_BANK_GATE_THRESHOLDS["minimum_primary_accuracy"] == 0.90
    assert CONTROLLED_MESSAGE_BANK_GATE_THRESHOLDS["minimum_interjudge_kappa"] == 0.70
