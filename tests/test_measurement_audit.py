"""Independent-measurement alignment and diagnostic tests."""

from __future__ import annotations

import copy

import pytest

from src.measurement_audit import (
    align_classifier_records,
    cohens_kappa,
    summarize_classifier_comparison,
    write_measurement_audit,
)


def _record(round_no, condition, target, label, message=None):
    return {
        "run_id": "run",
        "episode_id": "%s-%s" % (condition, target),
        "round": round_no,
        "condition": condition,
        "hidden_target_type": target,
        "scenario_id": "scenario",
        "focal_message": message or "message-%s-%s-%d" % (condition, target, round_no),
        "target_choice": "A",
        "target_p_a": 0.5,
        "round_seed": round_no,
        "primary_strategy": label,
        "strategy_confidence": 0.9,
        "classifier_name": "source",
    }


def test_alignment_fails_if_message_or_metadata_changes():
    source = [_record(1, "full_history", "fairness", "other")]
    changed = copy.deepcopy(source)
    changed[0]["focal_message"] = "different"
    with pytest.raises(ValueError, match="focal_message changed"):
        align_classifier_records(source, changed)


def test_alignment_fails_if_any_non_classifier_field_changes():
    source = [_record(1, "full_history", "fairness", "other")]
    source[0]["visible_history"] = []
    changed = copy.deepcopy(source)
    changed[0]["visible_history"] = [{"message": "tampered"}]
    with pytest.raises(ValueError, match="visible_history changed"):
        align_classifier_records(source, changed)


def test_alignment_fails_on_missing_or_duplicate_records():
    source = [_record(1, "full_history", "fairness", "other")]
    with pytest.raises(ValueError, match="different record keys"):
        align_classifier_records(source, [])
    with pytest.raises(ValueError, match="duplicate"):
        align_classifier_records(source + source, source)


def test_kappa_is_one_for_identical_nonconstant_labels():
    labels = ["fairness", "risk", "expertise", "other"]
    assert cohens_kappa(labels, labels) == pytest.approx(1.0)


def test_summary_exposes_fairness_rescue_and_expertise_overcall(tmp_path):
    source = [
        _record(1, "full_history", "fairness", "other"),
        _record(2, "full_history", "fairness", "risk"),
        _record(1, "full_history", "expertise", "expertise"),
        _record(2, "full_history", "expertise", "other"),
    ]
    independent = copy.deepcopy(source)
    for row, label in zip(independent, ["fairness", "fairness", "other", "other"]):
        row["primary_strategy"] = label
        row["classifier_name"] = "independent"
    pairs = align_classifier_records(source, independent)
    summary = summarize_classifier_comparison(pairs)
    assert summary["n_records"] == 4
    assert summary["n_labels_changed"] == 3
    assert summary["diagnoses"]["fairness_rescued_from_source_false_negative_n"] == 2
    assert summary["diagnoses"]["source_expertise_relabelled_by_independent_n"] == 1
    assert summary["diagnoses"]["fairness_rescued_with_target_scores_available_n"] == 0
    assert summary["target_cells"]["full_history/fairness"]["independent_matching_n"] == 2
    paths = write_measurement_audit(summary, str(tmp_path))
    assert all((tmp_path / path.split("/")[-1]).exists() for path in paths.values())
