from __future__ import annotations

import json
from pathlib import Path

import pytest

from config import STRATEGIES
from src.controlled_v6_messages import V6TriadBank
from src.v6_calibration import (
    V6_CALIBRATION_FOLDS,
    audit_v6_pool_schedule,
    audit_v6_validation_schedule,
    build_v6_pool_schedule,
    build_v6_validation_schedule,
    evaluate_v6_bank_validation,
    finalize_validated_v6_bank,
    run_v6_target_free_calibration,
    select_v6_bank,
)


ROOT = Path(__file__).parents[1]
POOL = ROOT / "data" / "v6" / "v6_triad_pool_v1.json"


def _all_eligible(bank):
    ids = [
        triad["triad_id"]
        for split in ("development", "heldout")
        for triad in bank.payload["splits"][split]
    ]
    base = {"pass": True, "pool_sha256": bank.sha256(), "eligible_triad_ids": ids}
    return dict(base), dict(base)


def _balanced_records(rows):
    out = []
    for row in rows:
        dominant = (int(row["triad_index"]) + int(row["scenario_index"])) % 3
        permutation_index = int(row["permutation_index"])
        if permutation_index < 3:
            frame_index = dominant
        elif permutation_index < 5:
            frame_index = (dominant + 1) % 3
        else:
            frame_index = (dominant + 2) % 3
        selected_frame = STRATEGIES[frame_index]
        selected = next(
            candidate
            for candidate in row["candidates"]
            if candidate["frame"] == selected_frame
        )
        out.append(
            {
                **row,
                "selection_valid": True,
                "fallback_used": False,
                "focal_output_raw": str(selected["slot"]),
                "selected_slot": selected["slot"],
                "selected_frame": selected_frame,
                "selected_candidate_id": selected["candidate_id"],
                "selected_pool_candidate_id": selected["pool_candidate_id"],
            }
        )
    return out


def _pending_bank(tmp_path):
    pool = V6TriadBank.load(str(POOL))
    semantic, quality = _all_eligible(pool)
    selected, report = select_v6_bank(
        pool, _balanced_records(build_v6_pool_schedule(pool)), semantic, quality
    )
    assert selected is not None and report["support_pass"] is True
    path = tmp_path / "pending.json"
    path.write_text(json.dumps(selected), encoding="utf-8")
    return selected, V6TriadBank.load(str(path))


def test_pool_schedule_is_complete_all_six_and_scenario_blocked():
    bank = V6TriadBank.load(str(POOL))
    rows = build_v6_pool_schedule(bank)
    audit = audit_v6_pool_schedule(rows, bank)
    assert audit["pass"] is True
    assert len(rows) == 20 * 14 * 6
    assert set(audit["triad_exposures"].values()) == {84}
    assert len(V6_CALIBRATION_FOLDS) == 7
    assert len({item for pair in V6_CALIBRATION_FOLDS for item in pair}) == 14


def test_true_foldwise_selection_never_reads_heldout_pair():
    pool = V6TriadBank.load(str(POOL))
    semantic, quality = _all_eligible(pool)
    selected, report = select_v6_bank(
        pool, _balanced_records(build_v6_pool_schedule(pool)), semantic, quality
    )
    assert selected is not None
    assert report["support_pass"] is True
    for split in ("development", "heldout"):
        metric = report["selection_metrics"][split]
        assert metric["cross_validation_pass"] is True
        for fold in metric["cross_validation"].values():
            assert fold["no_heldout_rows_in_selection"] is True
            assert not (
                set(fold["heldout_scenario_ids"])
                & set(fold["training_scenario_ids"])
            )
            assert fold["heldout_evaluation"]["pass"] is True


def test_independent_validation_uses_new_scenarios_and_passes_robust_gates(
    tmp_path,
):
    pending_payload, pending = _pending_bank(tmp_path)
    schedule = build_v6_validation_schedule(pending)
    audit = audit_v6_validation_schedule(schedule, pending)
    assert audit["pass"] is True
    assert len(schedule) == 10 * 14 * 6
    assert all(str(row["scenario"]["id"]).startswith("v6v_") for row in schedule)
    gate = evaluate_v6_bank_validation(_balanced_records(schedule), pending)
    assert gate["pass"] is True
    assert gate["anti_triviality"]["pass"] is True
    assert all(value["pass"] for value in gate["scenario_cluster_bootstrap"].values())
    final = finalize_validated_v6_bank(pending_payload, gate)
    assert final["status"] == "selected_bank_validated"


def test_position_only_policy_fails_anti_triviality_despite_balanced_shares(
    tmp_path,
):
    _payload, pending = _pending_bank(tmp_path)
    rows = build_v6_validation_schedule(pending)
    position_only = []
    for row in rows:
        selected = next(item for item in row["candidates"] if item["slot"] == 1)
        position_only.append(
            {
                **row,
                "selection_valid": True,
                "fallback_used": False,
                "selected_frame": selected["frame"],
            }
        )
    gate = evaluate_v6_bank_validation(position_only, pending)
    assert all(section["pass"] for section in gate["sections"].values())
    assert gate["anti_triviality"]["fraction"] == 0.0
    assert gate["anti_triviality"]["pass"] is False
    assert gate["pass"] is False


def test_calibration_support_failure_writes_no_pending_payload():
    pool = V6TriadBank.load(str(POOL))
    semantic, quality = _all_eligible(pool)
    rows = [
        {**row, "selection_valid": True, "fallback_used": False, "selected_frame": "expertise"}
        for row in build_v6_pool_schedule(pool)
    ]
    selected, report = select_v6_bank(pool, rows, semantic, quality)
    assert selected is None
    assert report["support_pass"] is False
    assert report["status"].startswith("STOP")


def test_v6_run_rejects_legacy_episode_block_override(tmp_path):
    bank = V6TriadBank.load(str(POOL))
    with pytest.raises(ValueError, match="episode-block overrides"):
        run_v6_target_free_calibration(
            bank=bank,
            provider=object(),
            run_id="must-not-run",
            out_dir=str(tmp_path),
            seed=20262001,
            mode="pool_screening",
            n_episode_blocks=24,
        )
