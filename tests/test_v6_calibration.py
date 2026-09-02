from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path

import pytest

import src.file_lock as file_lock_module
import src.v6_calibration as calibration_module
from config import CONTROLLED_V6_VERSION, STRATEGIES
from src.controlled_focal_agent import build_controlled_prompt
from src.controlled_v6_messages import V6TriadBank
from src.file_lock import ExclusiveFileLock
from src.v6_calibration import (
    V6_CALIBRATION_FOLDS,
    V6_CALIBRATION_VERSION,
    V6_POOL_MODE,
    _message_candidates,
    _scenario_proxy,
    audit_v6_calibration_run,
    audit_v6_pool_schedule,
    audit_v6_validation_schedule,
    bank_content_sha256,
    build_v6_pool_schedule,
    build_v6_validation_schedule,
    evaluate_v6_bank_validation,
    finalize_validated_v6_bank,
    preflight_v6_target_free_calibration,
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


def _assert_counterfactual_round_metadata(rows):
    by_block = {}
    rounds_by_split = {"development": set(), "heldout": set()}
    for row in rows:
        key = (row["triad_id"], row["scenario"]["id"])
        by_block.setdefault(key, set()).add(
            (row["round"], row["n_rounds"], row["heldout_start_round"])
        )
        rounds_by_split[row["split"]].add(row["round"])
    assert by_block
    assert all(len(metadata) == 1 for metadata in by_block.values())
    assert rounds_by_split["development"] == set(range(1, 19))
    assert rounds_by_split["heldout"] == set(range(19, 25))


def _auditable_pool_artifacts(bank, seed=20262001):
    run_id = "synthetic-audit-run"
    records = []
    for row in _balanced_records(build_v6_pool_schedule(bank, seed=seed)):
        prompt = build_controlled_prompt(
            scenario=_scenario_proxy(row["scenario"]),
            candidates=_message_candidates(row),
            history=[],
            round_index=row["round"],
            n_rounds=24,
            show_history=False,
            focal_mode="spontaneous",
            context={},
        )
        records.append(
            {
                **row,
                "run_id": run_id,
                "mode": V6_POOL_MODE,
                "focal_system_prompt": prompt.system,
                "focal_user_prompt": prompt.user,
            }
        )
    manifest = {
        "calibration_version": V6_CALIBRATION_VERSION,
        "task_version": CONTROLLED_V6_VERSION,
        "mode": V6_POOL_MODE,
        "run_id": run_id,
        "run_status": "completed",
        "target_simulator_present": False,
        "history_present": False,
        "pool_sha256": bank.sha256(),
        "bank_content_sha256": bank_content_sha256(bank.payload),
        "provider": {"constrained_choices": ["1", "2", "3"]},
        "schedule": {
            "seed": seed,
            "n_records": len(records),
            "n_episode_blocks": None,
            "n_rounds": 24,
            "heldout_start_round": 19,
        },
        "n_records": len(records),
        "frozen_protocol": {"plan_audit": {"pass": True}},
    }
    return records, manifest


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


class _ResumeProvider:
    name = "resume-test-provider"

    def __init__(self, fail_after=None):
        self.fail_after = fail_after
        self.calls = 0
        self.seeds = []

    def describe(self):
        return {
            "provider": self.name,
            "model": "resume-test-model",
            "revision": "frozen-test-revision",
            "constrained_choices": ["1", "2", "3"],
            "per_generation_seed_supported": True,
        }

    def set_next_seed(self, seed):
        self.seeds.append(seed)

    def generate(self, _prompt):
        if self.fail_after is not None and self.calls >= self.fail_after:
            raise RuntimeError("simulated provider interruption")
        self.calls += 1
        return "1"


def _install_tiny_calibration_schedule(monkeypatch, bank, n_rows=4):
    rows = copy.deepcopy(build_v6_pool_schedule(bank)[:n_rows])
    audit = {
        "pass": True,
        "checks": {"tiny_test_schedule": True},
        "n_rows": len(rows),
    }
    monkeypatch.setattr(
        calibration_module,
        "build_v6_pool_schedule",
        lambda _bank, seed=20262001: copy.deepcopy(rows),
    )
    monkeypatch.setattr(
        calibration_module,
        "audit_v6_pool_schedule",
        lambda _rows, _bank: copy.deepcopy(audit),
    )
    return rows


def _interrupted_run(tmp_path, monkeypatch, n_rows=4, completed=2):
    bank = V6TriadBank.load(str(POOL))
    schedule = _install_tiny_calibration_schedule(monkeypatch, bank, n_rows=n_rows)
    provider = _ResumeProvider()
    provenance = {"plan_audit": {"pass": True}, "receipt_id": "frozen-test"}
    original_write_manifest = calibration_module._atomic_write_manifest
    interrupted = False

    def interrupt_after_clean_prefix(path, payload):
        nonlocal interrupted
        if (
            not interrupted
            and payload.get("run_status") == "running"
            and payload.get("n_records_committed") == completed
        ):
            interrupted = True
            raise RuntimeError("simulated durable-prefix interruption")
        return original_write_manifest(path, payload)

    monkeypatch.setattr(
        calibration_module, "_atomic_write_manifest", interrupt_after_clean_prefix
    )
    try:
        with pytest.raises(RuntimeError, match="durable-prefix interruption"):
            run_v6_target_free_calibration(
                bank=bank,
                provider=provider,
                run_id="resume-test",
                out_dir=str(tmp_path),
                seed=20262001,
                mode=V6_POOL_MODE,
                provenance=provenance,
            )
    finally:
        monkeypatch.setattr(
            calibration_module, "_atomic_write_manifest", original_write_manifest
        )
    assert provider.calls == completed
    return bank, schedule, provenance


def test_pool_schedule_is_complete_all_six_and_scenario_blocked():
    bank = V6TriadBank.load(str(POOL))
    rows = build_v6_pool_schedule(bank)
    audit = audit_v6_pool_schedule(rows, bank)
    assert audit["pass"] is True
    assert len(rows) == 20 * 14 * 6
    assert set(audit["triad_exposures"].values()) == {84}
    assert audit["checks"]["counterfactual_round_metadata"] is True
    assert audit["checks"]["round_partitions"] is True
    _assert_counterfactual_round_metadata(rows)
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
    assert audit["checks"]["counterfactual_round_metadata"] is True
    assert audit["checks"]["round_partitions"] is True
    assert len(schedule) == 10 * 14 * 6
    assert all(str(row["scenario"]["id"]).startswith("v6v_") for row in schedule)
    _assert_counterfactual_round_metadata(schedule)
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


def test_round_parity_slot_policy_fails_text_blind_validation(tmp_path):
    _payload, pending = _pending_bank(tmp_path)
    text_blind = []
    for row in build_v6_validation_schedule(pending):
        selected_slot = 1 if int(row["round"]) % 2 else 2
        selected = next(
            candidate
            for candidate in row["candidates"]
            if candidate["slot"] == selected_slot
        )
        text_blind.append(
            {
                **row,
                "selection_valid": True,
                "fallback_used": False,
                "focal_output_raw": str(selected_slot),
                "selected_slot": selected_slot,
                "selected_frame": selected["frame"],
                "selected_candidate_id": selected["candidate_id"],
                "selected_pool_candidate_id": selected["pool_candidate_id"],
            }
        )
    gate = evaluate_v6_bank_validation(text_blind, pending)
    assert all(section["pass"] for section in gate["sections"].values())
    assert all(
        fold["pass"] for fold in gate["validation_scenario_pair_folds"].values()
    )
    assert all(
        section["pass"] for section in gate["scenario_cluster_bootstrap"].values()
    )
    assert gate["anti_triviality"]["fraction"] == 0.0
    assert gate["anti_triviality"]["pass"] is False
    assert gate["pass"] is False


def test_run_audit_rejects_schedule_order_and_field_tampering():
    bank = V6TriadBank.load(str(POOL))
    records, manifest = _auditable_pool_artifacts(bank)
    clean = audit_v6_calibration_run(records, manifest, bank, V6_POOL_MODE)
    assert clean["pass"] is True
    assert clean["checks"]["schedule_row_order"] is True
    assert clean["checks"]["immutable_schedule_fields"] is True
    assert set(clean["immutable_schedule_field_checks"]) == {
        "calibration_version",
        "pool_sha256",
        "split",
        "triad_id",
        "triad_index",
        "scenario_index",
        "permutation_index",
        "frame_order",
        "episode_index",
        "round",
        "n_rounds",
        "heldout_start_round",
        "scenario",
        "candidates",
        "generation_seed",
    }

    reordered = copy.deepcopy(records)
    reordered[0], reordered[1] = reordered[1], reordered[0]
    result = audit_v6_calibration_run(reordered, manifest, bank, V6_POOL_MODE)
    assert result["pass"] is False
    assert result["checks"]["schedule_row_order"] is False
    assert result["checks"]["exact_schedule"] is False

    for field in clean["immutable_schedule_field_checks"]:
        tampered = copy.deepcopy(records)
        tampered[0][field] = None
        result = audit_v6_calibration_run(tampered, manifest, bank, V6_POOL_MODE)
        assert result["pass"] is False, field
        assert result["checks"]["immutable_schedule_fields"] is False, field
        assert result["immutable_schedule_field_checks"][field] is False, field
        assert result["checks"]["exact_schedule"] is False, field

    changed_seed = copy.deepcopy(manifest)
    changed_seed["schedule"]["seed"] += 1
    result = audit_v6_calibration_run(records, changed_seed, bank, V6_POOL_MODE)
    assert result["pass"] is False
    assert result["checks"]["exact_schedule"] is False


def test_run_audit_reconciles_raw_slot_and_selected_candidate_metadata():
    bank = V6TriadBank.load(str(POOL))
    records, manifest = _auditable_pool_artifacts(bank)
    first = records[0]
    attacks = (
        (
            "focal_output_raw",
            next(value for value in ("1", "2", "3") if value != first["focal_output_raw"]),
        ),
        (
            "selected_slot",
            next(value for value in (1, 2, 3) if value != first["selected_slot"]),
        ),
        (
            "selected_frame",
            next(value for value in STRATEGIES if value != first["selected_frame"]),
        ),
        ("selected_candidate_id", "tampered-candidate"),
        ("selected_pool_candidate_id", "tampered-pool-candidate"),
    )
    for field, value in attacks:
        tampered = copy.deepcopy(records)
        tampered[0][field] = value
        result = audit_v6_calibration_run(tampered, manifest, bank, V6_POOL_MODE)
        assert result["pass"] is False, field
        assert result["checks"]["selection_reconciliation"] is False, field

    tampered_prompt = copy.deepcopy(records)
    tampered_prompt[0]["focal_user_prompt"] += "\nHidden extra instruction."
    result = audit_v6_calibration_run(
        tampered_prompt, manifest, bank, V6_POOL_MODE
    )
    assert result["pass"] is False
    assert result["checks"]["prompt_reconciliation"] is False


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


def test_interrupted_run_resumes_exact_prefix_without_repeating_paid_calls(
    tmp_path, monkeypatch
):
    bank, schedule, provenance = _interrupted_run(
        tmp_path, monkeypatch, n_rows=4, completed=2
    )
    log_path = tmp_path / "resume-test.jsonl"
    original_rows = [json.loads(line) for line in log_path.read_text().splitlines()]
    original_hashes = [row["sample_sha256"] for row in original_rows]

    # Simulate a process death after sample 2 was atomically sealed but before
    # its JSONL append completed. The immutable per-sample artifact must repair
    # the raw log and prevent sample 2 from being queried again.
    log_path.write_text(
        json.dumps(original_rows[0]) + "\n" + '{"schedule_index":',
        encoding="utf-8",
    )
    resumed_provider = _ResumeProvider()
    result = run_v6_target_free_calibration(
        bank=bank,
        provider=resumed_provider,
        run_id="resume-test",
        out_dir=str(tmp_path),
        seed=20262001,
        mode=V6_POOL_MODE,
        provenance=provenance,
    )

    assert result["run_state"] == "completed_resumed"
    assert resumed_provider.calls == len(schedule) - 2
    assert resumed_provider.seeds == [
        row["generation_seed"] for row in schedule[2:]
    ]
    assert [row["sample_sha256"] for row in result["records"][:2]] == original_hashes
    repaired_rows = [json.loads(line) for line in log_path.read_text().splitlines()]
    assert repaired_rows == result["records"]
    assert result["manifest"]["n_records_committed"] == len(schedule)


def test_provider_return_without_sample_is_ambiguous_and_never_repeated(
    tmp_path, monkeypatch
):
    bank = V6TriadBank.load(str(POOL))
    _install_tiny_calibration_schedule(monkeypatch, bank, n_rows=2)
    provenance = {"plan_audit": {"pass": True}, "receipt_id": "frozen-test"}
    original_create = calibration_module._atomic_create_json

    def crash_before_sample_seal(path, payload):
        if path.endswith(".samples/00000000.json"):
            raise RuntimeError("simulated crash before sample seal")
        return original_create(path, payload)

    monkeypatch.setattr(
        calibration_module, "_atomic_create_json", crash_before_sample_seal
    )
    first_provider = _ResumeProvider()
    with pytest.raises(RuntimeError, match="before sample seal"):
        run_v6_target_free_calibration(
            bank=bank,
            provider=first_provider,
            run_id="resume-test",
            out_dir=str(tmp_path),
            seed=20262001,
            mode=V6_POOL_MODE,
            provenance=provenance,
        )
    monkeypatch.setattr(calibration_module, "_atomic_create_json", original_create)

    assert first_provider.calls == 1
    assert (tmp_path / "resume-test.inflight.json").is_file()
    assert not (tmp_path / "resume-test.samples" / "00000000.json").exists()
    resumed_provider = _ResumeProvider()
    with pytest.raises(ValueError, match="ambiguous V6 in-flight claim"):
        run_v6_target_free_calibration(
            bank=bank,
            provider=resumed_provider,
            run_id="resume-test",
            out_dir=str(tmp_path),
            seed=20262001,
            mode=V6_POOL_MODE,
            provenance=provenance,
        )
    assert resumed_provider.calls == 0


def test_sealed_sample_clears_exact_claim_on_resume_without_repeating_call(
    tmp_path, monkeypatch
):
    bank = V6TriadBank.load(str(POOL))
    schedule = _install_tiny_calibration_schedule(monkeypatch, bank, n_rows=3)
    provenance = {"plan_audit": {"pass": True}, "receipt_id": "frozen-test"}
    original_clear = calibration_module._clear_inflight_claim_after_sample
    interrupted = False

    def crash_before_claim_clear(**kwargs):
        nonlocal interrupted
        if not interrupted:
            interrupted = True
            raise RuntimeError("simulated crash before claim clear")
        return original_clear(**kwargs)

    monkeypatch.setattr(
        calibration_module,
        "_clear_inflight_claim_after_sample",
        crash_before_claim_clear,
    )
    first_provider = _ResumeProvider()
    with pytest.raises(RuntimeError, match="before claim clear"):
        run_v6_target_free_calibration(
            bank=bank,
            provider=first_provider,
            run_id="resume-test",
            out_dir=str(tmp_path),
            seed=20262001,
            mode=V6_POOL_MODE,
            provenance=provenance,
        )
    monkeypatch.setattr(
        calibration_module,
        "_clear_inflight_claim_after_sample",
        original_clear,
    )

    assert first_provider.calls == 1
    assert (tmp_path / "resume-test.inflight.json").is_file()
    assert (tmp_path / "resume-test.samples" / "00000000.json").is_file()
    resumed_provider = _ResumeProvider()
    result = run_v6_target_free_calibration(
        bank=bank,
        provider=resumed_provider,
        run_id="resume-test",
        out_dir=str(tmp_path),
        seed=20262001,
        mode=V6_POOL_MODE,
        provenance=provenance,
    )
    assert resumed_provider.calls == len(schedule) - 1
    assert resumed_provider.seeds == [row["generation_seed"] for row in schedule[1:]]
    assert not (tmp_path / "resume-test.inflight.json").exists()
    assert len(result["records"]) == len(schedule)


def test_tampered_inflight_claim_fails_before_provider_reuse(tmp_path, monkeypatch):
    bank = V6TriadBank.load(str(POOL))
    _install_tiny_calibration_schedule(monkeypatch, bank, n_rows=2)
    provenance = {"plan_audit": {"pass": True}, "receipt_id": "frozen-test"}
    provider = _ResumeProvider(fail_after=0)
    with pytest.raises(RuntimeError, match="simulated provider interruption"):
        run_v6_target_free_calibration(
            bank=bank,
            provider=provider,
            run_id="resume-test",
            out_dir=str(tmp_path),
            seed=20262001,
            mode=V6_POOL_MODE,
            provenance=provenance,
        )
    claim_path = tmp_path / "resume-test.inflight.json"
    claim = json.loads(claim_path.read_text(encoding="utf-8"))
    claim["coordinate"]["generation_seed"] += 1
    claim_path.write_text(json.dumps(claim), encoding="utf-8")

    resumed_provider = _ResumeProvider()
    with pytest.raises(ValueError, match="differs from the frozen coordinate"):
        run_v6_target_free_calibration(
            bank=bank,
            provider=resumed_provider,
            run_id="resume-test",
            out_dir=str(tmp_path),
            seed=20262001,
            mode=V6_POOL_MODE,
            provenance=provenance,
        )
    assert resumed_provider.calls == 0


def test_completed_same_run_is_idempotent_and_never_loads_generation_path(
    tmp_path, monkeypatch
):
    bank = V6TriadBank.load(str(POOL))
    schedule = _install_tiny_calibration_schedule(monkeypatch, bank, n_rows=3)
    provenance = {"plan_audit": {"pass": True}, "receipt_id": "frozen-test"}
    first_provider = _ResumeProvider()
    first = run_v6_target_free_calibration(
        bank=bank,
        provider=first_provider,
        run_id="resume-test",
        out_dir=str(tmp_path),
        seed=20262001,
        mode=V6_POOL_MODE,
        provenance=provenance,
    )
    assert first_provider.calls == len(schedule)

    class NeverGenerateProvider(_ResumeProvider):
        def generate(self, _prompt):  # pragma: no cover - must remain unreachable
            raise AssertionError("completed run attempted another paid call")

    second_provider = NeverGenerateProvider()
    second = run_v6_target_free_calibration(
        bank=bank,
        provider=second_provider,
        run_id="resume-test",
        out_dir=str(tmp_path),
        seed=20262001,
        mode=V6_POOL_MODE,
        provenance=provenance,
    )
    assert second["run_state"] == "completed_existing"
    assert second_provider.calls == 0
    assert second["records"] == first["records"]


@pytest.mark.parametrize(
    "attack", ["gap", "substitution", "foreign_config", "malformed_tail"]
)
def test_resume_rejects_gaps_substitutions_and_foreign_configuration(
    tmp_path, monkeypatch, attack
):
    bank, _schedule, provenance = _interrupted_run(
        tmp_path, monkeypatch, n_rows=4, completed=2
    )
    sample_dir = tmp_path / "resume-test.samples"
    manifest_path = tmp_path / "resume-test.manifest.json"
    log_path = tmp_path / "resume-test.jsonl"
    if attack == "gap":
        (sample_dir / "00000001.json").rename(sample_dir / "00000002.json")
    elif attack == "substitution":
        rows = [json.loads(line) for line in log_path.read_text().splitlines()]
        rows[0]["triad_id"] = "substituted-triad"
        log_path.write_text(
            "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8"
        )
    elif attack == "foreign_config":
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["provider"]["revision"] = "foreign-revision"
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    else:
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write('{"foreign":')

    with pytest.raises(ValueError):
        preflight_v6_target_free_calibration(
            bank=bank,
            provider_description=_ResumeProvider().describe(),
            run_id="resume-test",
            out_dir=str(tmp_path),
            seed=20262001,
            mode=V6_POOL_MODE,
            provenance=provenance,
        )


@pytest.mark.parametrize(
    "artifact",
    ["log", "manifest", "samples", "claim", "lock", "sample_file"],
)
def test_preflight_rejects_symlinked_canonical_artifacts(
    tmp_path, monkeypatch, artifact
):
    bank = V6TriadBank.load(str(POOL))
    _install_tiny_calibration_schedule(monkeypatch, bank, n_rows=1)
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    external_file = tmp_path / "external.json"
    external_file.write_text("{}", encoding="utf-8")
    external_dir = tmp_path / "external-dir"
    external_dir.mkdir()
    paths = {
        "log": out_dir / "resume-test.jsonl",
        "manifest": out_dir / "resume-test.manifest.json",
        "samples": out_dir / "resume-test.samples",
        "claim": out_dir / "resume-test.inflight.json",
        "lock": out_dir / "resume-test.lock",
    }
    if artifact == "samples":
        paths["samples"].symlink_to(external_dir, target_is_directory=True)
    elif artifact == "sample_file":
        paths["samples"].mkdir()
        (paths["samples"] / "00000000.json").symlink_to(external_file)
    else:
        paths[artifact].symlink_to(external_file)

    with pytest.raises(ValueError, match="symlink"):
        preflight_v6_target_free_calibration(
            bank=bank,
            provider_description=_ResumeProvider().describe(),
            run_id="resume-test",
            out_dir=str(out_dir),
            seed=20262001,
            mode=V6_POOL_MODE,
            provenance={"plan_audit": {"pass": True}},
        )


@pytest.mark.parametrize(
    "artifact", ["log", "manifest", "samples", "claim", "lock", "sample_file"]
)
def test_preflight_rejects_nonregular_canonical_artifacts(
    tmp_path, monkeypatch, artifact
):
    bank = V6TriadBank.load(str(POOL))
    _install_tiny_calibration_schedule(monkeypatch, bank, n_rows=1)
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    paths = {
        "log": out_dir / "resume-test.jsonl",
        "manifest": out_dir / "resume-test.manifest.json",
        "samples": out_dir / "resume-test.samples",
        "claim": out_dir / "resume-test.inflight.json",
        "lock": out_dir / "resume-test.lock",
    }
    if artifact == "samples":
        paths["samples"].write_text("not a directory", encoding="utf-8")
    elif artifact == "sample_file":
        paths["samples"].mkdir()
        (paths["samples"] / "00000000.json").mkdir()
    else:
        paths[artifact].mkdir()

    with pytest.raises(ValueError, match="regular file|directory"):
        preflight_v6_target_free_calibration(
            bank=bank,
            provider_description=_ResumeProvider().describe(),
            run_id="resume-test",
            out_dir=str(out_dir),
            seed=20262001,
            mode=V6_POOL_MODE,
            provenance={"plan_audit": {"pass": True}},
        )


def test_run_rejects_symlinked_canonical_output_directory(tmp_path, monkeypatch):
    bank = V6TriadBank.load(str(POOL))
    _install_tiny_calibration_schedule(monkeypatch, bank, n_rows=1)
    actual = tmp_path / "actual"
    actual.mkdir()
    linked = tmp_path / "linked"
    linked.symlink_to(actual, target_is_directory=True)
    provider = _ResumeProvider()
    with pytest.raises(ValueError, match="symlink"):
        run_v6_target_free_calibration(
            bank=bank,
            provider=provider,
            run_id="resume-test",
            out_dir=str(linked),
            seed=20262001,
            mode=V6_POOL_MODE,
            provenance={"plan_audit": {"pass": True}},
        )
    assert provider.calls == 0


def test_run_rejects_output_directory_beneath_symlinked_parent(
    tmp_path, monkeypatch
):
    bank = V6TriadBank.load(str(POOL))
    _install_tiny_calibration_schedule(monkeypatch, bank, n_rows=1)
    actual_parent = tmp_path / "actual-parent"
    actual_parent.mkdir()
    (actual_parent / "out").mkdir()
    linked_parent = tmp_path / "linked-parent"
    linked_parent.symlink_to(actual_parent, target_is_directory=True)
    provider = _ResumeProvider()
    with pytest.raises(ValueError, match="traverse a symlink"):
        run_v6_target_free_calibration(
            bank=bank,
            provider=provider,
            run_id="resume-test",
            out_dir=str(linked_parent / "out"),
            seed=20262001,
            mode=V6_POOL_MODE,
            provenance={"plan_audit": {"pass": True}},
        )
    assert provider.calls == 0


def test_run_rejects_non_directory_canonical_output(tmp_path, monkeypatch):
    bank = V6TriadBank.load(str(POOL))
    _install_tiny_calibration_schedule(monkeypatch, bank, n_rows=1)
    out_path = tmp_path / "not-a-directory"
    out_path.write_text("invalid", encoding="utf-8")
    provider = _ResumeProvider()
    with pytest.raises(ValueError, match="directory"):
        run_v6_target_free_calibration(
            bank=bank,
            provider=provider,
            run_id="resume-test",
            out_dir=str(out_path),
            seed=20262001,
            mode=V6_POOL_MODE,
            provenance={"plan_audit": {"pass": True}},
        )
    assert provider.calls == 0


def test_mandatory_run_lock_rejects_concurrent_runner(tmp_path, monkeypatch):
    bank = V6TriadBank.load(str(POOL))
    _install_tiny_calibration_schedule(monkeypatch, bank, n_rows=1)
    lock_path = tmp_path / "resume-test.lock"
    provider = _ResumeProvider()
    with ExclusiveFileLock(str(lock_path), label="test-held calibration"):
        with pytest.raises(RuntimeError, match="another process holds"):
            run_v6_target_free_calibration(
                bank=bank,
                provider=provider,
                run_id="resume-test",
                out_dir=str(tmp_path),
                seed=20262001,
                mode=V6_POOL_MODE,
                provenance={"plan_audit": {"pass": True}},
            )
    assert provider.calls == 0


def test_mandatory_run_lock_fails_closed_without_backend(tmp_path, monkeypatch):
    bank = V6TriadBank.load(str(POOL))
    _install_tiny_calibration_schedule(monkeypatch, bank, n_rows=1)
    monkeypatch.setattr(file_lock_module, "_fcntl", None)
    monkeypatch.setattr(file_lock_module, "_msvcrt", None)
    provider = _ResumeProvider()
    with pytest.raises(RuntimeError, match="requires an operating-system"):
        run_v6_target_free_calibration(
            bank=bank,
            provider=provider,
            run_id="resume-test",
            out_dir=str(tmp_path),
            seed=20262001,
            mode=V6_POOL_MODE,
            provenance={"plan_audit": {"pass": True}},
        )
    assert provider.calls == 0


def test_launch_receipt_accepts_exact_resume_and_rejects_foreign_receipt(
    tmp_path, monkeypatch
):
    monkeypatch.syspath_prepend(str(ROOT / "scripts"))
    spec = importlib.util.spec_from_file_location(
        "run_v6_calibration_receipt_test", ROOT / "scripts" / "run_v6_calibration.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    receipt_path = tmp_path / "launch.json"
    payload = {"official_run_id": "frozen-run", "seed": 20262001}
    assert module._write_atomic_launch_receipt(str(receipt_path), payload) is True
    before = receipt_path.read_bytes()
    assert module._write_atomic_launch_receipt(str(receipt_path), payload) is False
    assert receipt_path.read_bytes() == before

    foreign = dict(payload)
    foreign["seed"] += 1
    with pytest.raises(ValueError, match="foreign run/config"):
        module._write_atomic_launch_receipt(str(receipt_path), foreign)

    external = tmp_path / "external-receipt.json"
    external.write_text(json.dumps(payload), encoding="utf-8")
    linked = tmp_path / "linked-launch.json"
    linked.symlink_to(external)
    with pytest.raises(ValueError, match="symlink"):
        module._write_atomic_launch_receipt(str(linked), payload)


def test_calibration_cli_rejects_copied_protocol_before_artifact_reads(
    tmp_path, monkeypatch
):
    monkeypatch.syspath_prepend(str(ROOT / "scripts"))
    spec = importlib.util.spec_from_file_location(
        "run_v6_calibration_protocol_path_test",
        ROOT / "scripts" / "run_v6_calibration.py",
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module._bootstrap, "ROOT", str(tmp_path))
    copied = tmp_path / "copied-protocol.json"
    copied.write_text("{}\n", encoding="utf-8")
    with pytest.raises(ValueError, match="canonical repository protocol"):
        module.main(
            [
                "--bank",
                str(tmp_path / "missing-bank.json"),
                "--protocol-spec",
                str(copied),
                "--mode",
                V6_POOL_MODE,
                "--run-id",
                "unauthorized",
                "--dry-run",
            ]
        )


def test_repository_terminal_protocol_blocks_calibration_before_model(
    monkeypatch,
):
    monkeypatch.syspath_prepend(str(ROOT / "scripts"))
    spec = importlib.util.spec_from_file_location(
        "run_v6_calibration_terminal_test",
        ROOT / "scripts" / "run_v6_calibration.py",
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module._bootstrap, "ROOT", str(ROOT))

    def must_not_run(*_args, **_kwargs):
        raise AssertionError("terminal V6 protocol reached model/runtime loading")

    monkeypatch.setattr(module, "collect_focal_runtime_evidence", must_not_run)
    monkeypatch.setattr(module, "HuggingFaceProvider", must_not_run)
    with pytest.raises(ValueError, match="planned V6 calibration differs"):
        module.main(
            [
                "--bank",
                str(POOL),
                "--mode",
                V6_POOL_MODE,
                "--run-id",
                "v6_pool_screening_qwen38_27b_20260902",
                "--dry-run",
            ]
        )
