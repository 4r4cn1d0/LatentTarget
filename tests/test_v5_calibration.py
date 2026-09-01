from __future__ import annotations

import json
from pathlib import Path

import pytest

from config import STRATEGIES
from src.controlled_v5_messages import V5MessageBank
from src.focal_agent import BaseProvider
from src.v5_calibration import (
    audit_v5_calibration_schedule,
    build_blind_semantic_samples,
    build_v5_calibration_schedule,
    evaluate_v5_bank_validation,
    finalize_validated_v5_bank,
    run_v5_no_history_calibration,
    select_v5_bank,
)


POOL = Path(__file__).parents[1] / "data" / "v5" / "v5_candidate_pool_v1.json"


class _CyclingChoiceProvider(BaseProvider):
    name = "test-cycling-choice"
    model = "test"

    def __init__(self):
        self.index = 0
        self.contexts = []

    def generate(self, prompt):
        self.contexts.append(prompt.context)
        choice = self.index % 3 + 1
        self.index += 1
        return str(choice)

    def describe(self):
        return {
            "provider": self.name,
            "model": self.model,
            "scientific_status": "implementation control only",
        }


def _all_eligible_semantic_validation(bank):
    candidate_ids = [
        entry["candidate_id"]
        for split in bank.payload["splits"].values()
        for entries in split.values()
        for entry in entries
    ]
    return {
        "pass": True,
        "pool_sha256": bank.sha256(),
        "eligible_candidate_ids": candidate_ids,
        "scientific_status": "synthetic test fixture, not a real semantic judgment",
    }


def test_v5_calibration_schedule_balances_every_candidate_and_slot():
    bank = V5MessageBank.load(str(POOL))
    rows = build_v5_calibration_schedule(bank)
    audit = audit_v5_calibration_schedule(rows, bank)
    assert audit["pass"] is True
    assert len(rows) == 24 * 24
    assert audit["minimum_candidate_exposure"] == 24
    assert all(
        set(counts) == {1, 2, 3} and len(set(counts.values())) == 1
        for counts in audit["candidate_slot_counts"].values()
    )


def test_blind_semantic_export_contains_no_intended_labels_or_candidate_ids():
    bank = V5MessageBank.load(str(POOL))
    visible, key = build_blind_semantic_samples(bank)
    assert len(visible) == len(key) == 42
    assert all(set(row) == {"sample_id", "message"} for row in visible)
    assert all("candidate_id" not in row and "intended_frame" not in row for row in visible)
    assert {entry["intended_frame"] for entry in key.values()} == set(STRATEGIES)


def test_target_free_calibration_selects_then_validates_bank(tmp_path):
    pool = V5MessageBank.load(str(POOL))
    provider = _CyclingChoiceProvider()
    calibration = run_v5_no_history_calibration(
        pool, provider, "calibration", str(tmp_path / "calibration")
    )
    assert calibration["manifest"]["target_simulator_present"] is False
    assert calibration["manifest"]["history_present"] is False
    assert len(calibration["records"]) == 576
    assert all(context == {} for context in provider.contexts)

    pending_payload, selection_report = select_v5_bank(
        pool,
        calibration["records"],
        _all_eligible_semantic_validation(pool),
    )
    assert pending_payload["status"] == "selected_bank_pending_no_history_validation"
    assert all(
        len(pending_payload["splits"]["development"][frame]) == 6
        and len(pending_payload["splits"]["heldout"][frame]) == 4
        for frame in STRATEGIES
    )
    assert selection_report["selected_bank_content_sha256"]

    pending_path = tmp_path / "pending_bank.json"
    pending_path.write_text(json.dumps(pending_payload), encoding="utf-8")
    pending = V5MessageBank.load(str(pending_path))
    validation = run_v5_no_history_calibration(
        pending,
        _CyclingChoiceProvider(),
        "validation",
        str(tmp_path / "validation"),
        mode="selected_bank_validation",
    )
    gate = evaluate_v5_bank_validation(validation["records"], pending)
    assert gate["pass"] is True
    final_payload = finalize_validated_v5_bank(pending_payload, gate)
    final_path = tmp_path / "final_bank.json"
    final_path.write_text(json.dumps(final_payload), encoding="utf-8")
    final_bank = V5MessageBank.load(str(final_path), require_validated=True)
    assert final_bank.payload["status"] == "selected_bank_validated"


def test_semantic_hash_mismatch_and_unbalanced_validation_fail(tmp_path):
    pool = V5MessageBank.load(str(POOL))
    calibration = run_v5_no_history_calibration(
        pool,
        _CyclingChoiceProvider(),
        "calibration",
        str(tmp_path / "calibration"),
    )
    semantic = _all_eligible_semantic_validation(pool)
    semantic["pool_sha256"] = "wrong"
    with pytest.raises(ValueError, match="hash mismatch"):
        select_v5_bank(pool, calibration["records"], semantic)

    changed = [dict(row, selected_frame="expertise") for row in calibration["records"]]
    gate = evaluate_v5_bank_validation(changed, pool)
    assert gate["pass"] is False
    assert gate["sections"]["overall"]["shares"]["expertise"] == 1.0
