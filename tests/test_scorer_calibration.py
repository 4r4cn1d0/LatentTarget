from __future__ import annotations

import json

import pytest

from config import ALL_LABELS
from src.scorer_calibration import (
    CALIBRATION_SEED,
    build_calibration_rows,
    cohen_kappa,
    confusion_metrics,
)


def _existing_rows():
    rows = []
    counts = {"fairness": 13, "risk": 24, "expertise": 5, "other": 25}
    for label, n in counts.items():
        for i in range(n):
            rows.append(
                {
                    "focal_message": "%s natural message %d" % (label, i),
                    "primary_strategy": label,
                    # Metadata that the builder must not propagate.
                    "hidden_target_type": "risk",
                    "target_choice": "A",
                    "condition": "full_history",
                }
            )
    return rows


def test_calibration_builder_is_balanced_reproducible_and_outcome_free():
    a = build_calibration_rows(_existing_rows(), seed=CALIBRATION_SEED)
    b = build_calibration_rows(_existing_rows(), seed=CALIBRATION_SEED)
    assert a == b
    assert len(a) == 80
    assert len({row["sample_id"] for row in a}) == 80
    for label in ALL_LABELS:
        labelled = [row for row in a if row["reference_label"] == label]
        assert len(labelled) == 20
        assert sum(row["split"] == "test" for row in labelled) == 5
        assert sum(row["split"] == "dev" for row in labelled) == 15
    forbidden = {
        "hidden_target_type", "target_choice", "condition", "round", "scenario"
    }
    assert all(not (forbidden & set(row)) for row in a)
    assert any("expertise_hard_negative" in row["design_tags"] for row in a)
    assert any("implicit_fairness" in row["design_tags"] for row in a)


def test_calibration_builder_fails_if_natural_class_is_too_small():
    rows = [row for row in _existing_rows() if row["primary_strategy"] != "expertise"]
    with pytest.raises(ValueError, match="existing expertise"):
        build_calibration_rows(rows)


def test_confusion_metrics_perfect_and_imperfect_cases():
    perfect = [
        {"reference_label": label, "prediction": label} for label in ALL_LABELS
    ]
    metrics = confusion_metrics(perfect)
    assert metrics["accuracy"] == 1.0
    assert metrics["macro_f1"] == 1.0
    assert all(metrics["per_class"][label]["f1"] == 1.0 for label in ALL_LABELS)

    imperfect = [dict(row) for row in perfect]
    imperfect[0]["prediction"] = "other"
    metrics = confusion_metrics(imperfect)
    assert metrics["accuracy"] == 0.75
    assert metrics["per_class"]["fairness"]["recall"] == 0.0


def test_kappa_handles_perfect_chance_and_bad_inputs():
    labels = list(ALL_LABELS) * 2
    assert cohen_kappa(labels, labels) == pytest.approx(1.0)
    assert cohen_kappa(labels, labels[1:] + labels[:1]) < 0.0
    with pytest.raises(ValueError):
        cohen_kappa([], [])
    with pytest.raises(ValueError):
        cohen_kappa(["fairness"], ["fairness", "risk"])

