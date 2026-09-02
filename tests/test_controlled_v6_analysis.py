from __future__ import annotations

import copy
import hashlib
import json
import os
import stat
import sys
from pathlib import Path

import pytest

import src.controlled_v6_analysis as v6_analysis
from config import (
    CONTROLLED_V6_ANALYSIS_CONFIG,
    CONTROLLED_V6_GATE_THRESHOLDS,
    CONTROLLED_V6_PAID_PREFLIGHT_RECEIPT_PATH,
    CONTROLLED_V6_RANDOMIZATION_SEED,
    CONTROLLED_V6_VERSION,
    STRATEGIES,
    ControlledExperimentConfig,
    ModelConfig,
)
from src.controlled_experiment import run_controlled_experiment
from src.controlled_v6_analysis import (
    V6_CO_PRIMARY_MINIMUMS,
    V6_CONFIRMATORY_SCENARIO_IDS,
    V6_CONFIRMATORY_SCENARIO_SHA256,
    V6_FROZEN_CHECKPOINT_STATUS,
    V6_REQUIRED_CONDITIONS,
    _canonical_sha256,
    audit_v6_launch_receipt_payload,
    evaluate_controlled_v6_checkpoint,
)
from src.controlled_v6_messages import (
    V6_SELECTED_BANK_STATUS,
    V6TriadBank,
    make_v6_protocol,
)
from src.controlled_v6_randomization import v6_allocation_schedule
from src.scenarios import V6_VALIDATION_SCENARIOS


ROOT = Path(__file__).parents[1]
POOL = ROOT / "data" / "v6" / "v6_triad_pool_v1.json"
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from analyze_controlled_v6 import (  # noqa: E402
    V6_FIGURE_STEMS,
    V6_SUMMARY_NAME,
    V6_TABLE_NAMES,
    _publish_staged_analysis,
    main as analyze_v6_main,
)
import analyze_controlled_v6 as analyze_v6_module  # noqa: E402


@pytest.fixture(scope="module", autouse=True)
def _pin_explicit_v6_co_primary_contract():
    """Keep these tests scoped to the frozen V6 .10/.15 observed gates."""
    original = {
        key: CONTROLLED_V6_GATE_THRESHOLDS.get(key)
        for key in V6_CO_PRIMARY_MINIMUMS
    }
    CONTROLLED_V6_GATE_THRESHOLDS.update(V6_CO_PRIMARY_MINIMUMS)
    try:
        yield
    finally:
        CONTROLLED_V6_GATE_THRESHOLDS.update(original)


@pytest.fixture(scope="module", autouse=True)
def _synthetic_final_checkpoint_audit():
    """Isolate analysis tests; the real artifact replay has its own E2E suite."""
    patcher = pytest.MonkeyPatch()

    def fake_audit(checkpoint, _repository_root):
        contract = checkpoint.get("analysis_contract", {})
        declared = contract.get("contract_sha256")
        calculated = _canonical_sha256(
            {key: value for key, value in contract.items() if key != "contract_sha256"}
        )
        passed = (
            checkpoint.get("synthetic_analysis_fixture") is True
            and checkpoint.get("status") == V6_FROZEN_CHECKPOINT_STATUS
            and checkpoint.get("pre_confirmatory_outcomes") is True
            and declared == calculated
        )
        return {
            "pass": passed,
            "checks": {"synthetic_analysis_fixture": passed},
            "checkpoint_canonical_sha256": _canonical_sha256(checkpoint),
            "analysis_contract": contract if passed else {},
        }

    patcher.setattr(v6_analysis, "audit_v6_final_checkpoint", fake_audit)
    try:
        yield
    finally:
        patcher.undo()


def _selected_bank(path: Path) -> V6TriadBank:
    payload = json.loads(POOL.read_text(encoding="utf-8"))
    payload["pool_id"] = "v6-synthetic-selected-bank"
    payload["status"] = V6_SELECTED_BANK_STATUS
    payload["splits"]["development"] = payload["splits"]["development"][:6]
    payload["splits"]["heldout"] = payload["splits"]["heldout"][:4]
    path.write_text(json.dumps(payload), encoding="utf-8")
    return V6TriadBank.load(str(path))


def _config(tmp_path: Path, provider: str) -> ControlledExperimentConfig:
    return ControlledExperimentConfig(
        experiment_id="controlled_v6_checkpoint",
        n_rounds=24,
        swap_round=12,
        heldout_start_round=19,
        n_episode_seeds=8,
        seed=20262004,
        randomization_seed=CONTROLLED_V6_RANDOMIZATION_SEED,
        conditions=list(V6_REQUIRED_CONDITIONS),
        model=ModelConfig(provider=provider, model="mock", max_tokens=2),
        out_dir=str(tmp_path / "official"),
    )


def _checkpoint(
    cfg: ControlledExperimentConfig,
    bank_sha256: str,
    run_id: str,
    records,
    checkpoint_path: Path,
    bank_path: str,
):
    n_episodes = cfg.n_episode_seeds * 24
    schedule_rows = []
    for row in records:
        schedule_rows.append(
            {
                "episode_id": row["episode_id"],
                "condition": row["condition"],
                "episode_index": row["episode_index"],
                "initial_target_type": row["initial_target_type"],
                "final_target_type": row["final_target_type"],
                "pair_family": row["pair_family"],
                "pair_id": row["pair_id"],
                "pair_slot": row["pair_slot"],
                "allocation_bit": row["allocation_bit"],
                "assigned_regime": row["assigned_regime"],
                "stable_counterfactual": row["stable_counterfactual"],
                "nominal_transition": row["nominal_transition"],
                "round": row["round"],
                "scenario_id": row["scenario_id"],
                "candidate_ids_by_slot": [
                    candidate["candidate_id"]
                    for candidate in sorted(
                        row["candidates"], key=lambda item: int(item["slot"])
                    )
                ],
            }
        )
    contract = {
        "version": CONTROLLED_V6_VERSION,
        "status": V6_FROZEN_CHECKPOINT_STATUS,
        "pre_confirmatory_outcome": True,
        "outcome_blind_freeze": True,
        "official_run_id": run_id,
        "experiment": {
            "conditions": list(V6_REQUIRED_CONDITIONS),
            "n_episode_seeds": cfg.n_episode_seeds,
            "n_rounds": 24,
            "swap_round": 12,
            "heldout_start_round": 19,
            "master_seed": cfg.seed,
            "randomization_seed": CONTROLLED_V6_RANDOMIZATION_SEED,
            "randomization_schedule_sha256": v6_allocation_schedule(
                cfg.n_episode_seeds
            )["schedule_sha256"],
            "record_counts": {"total": n_episodes * 24},
            "episode_counts": {"total": n_episodes},
            "scenario_set": "confirmatory",
            "scenario_ids": list(V6_CONFIRMATORY_SCENARIO_IDS),
            "scenario_set_canonical_sha256": (
                V6_CONFIRMATORY_SCENARIO_SHA256
            ),
            "full_schedule_sha256": _canonical_sha256(schedule_rows),
            "canonical_out_dir": "official",
            "launch_receipt_path": "launch/receipt.json",
            "paid_preflight_report_path": (
                "results/v6_design/confirmatory_paid_preflight.json"
            ),
            "paid_preflight_receipt_path": (
                CONTROLLED_V6_PAID_PREFLIGHT_RECEIPT_PATH
            ),
            "single_official_run": True,
        },
        "primary_model": {"id": "mock", "revision": None},
        "generation": {
            "temperature": cfg.model.temperature,
            "max_tokens": cfg.model.max_tokens,
            "enable_thinking": False,
            "top_p": 0.8,
            "top_k": 20,
            "activation_capture": False,
            "dtype": "synthetic",
            "constrained_choices": ["1", "2", "3"],
            "invalid_output_policy": "abort; no fallback",
        },
        "target": cfg.target_params.as_dict(),
        "message_bank": {"sha256": bank_sha256},
        "thresholds": dict(CONTROLLED_V6_GATE_THRESHOLDS),
        "analysis": copy.deepcopy(CONTROLLED_V6_ANALYSIS_CONFIG),
    }
    contract["contract_sha256"] = _canonical_sha256(contract)
    return {
        "checkpoint_version": "v6-final-checkpoint-1.0",
        "status": V6_FROZEN_CHECKPOINT_STATUS,
        "pre_confirmatory_outcomes": True,
        "synthetic_analysis_fixture": True,
        "synthetic_fixture_path": str(checkpoint_path),
        "validated_bank": {
            "path": os.path.relpath(bank_path, checkpoint_path.parent)
        },
        "analysis_contract": contract,
    }


def _run_and_evaluate(tmp_path: Path, provider: str, run_id: str):
    bank = _selected_bank(tmp_path / (run_id + "-bank.json"))
    cfg = _config(tmp_path, provider)
    protocol = make_v6_protocol(
        bank.source_path,
    )
    result = run_controlled_experiment(cfg, run_id=run_id, protocol=protocol)
    manifest = json.loads(Path(result.manifest_path).read_text(encoding="utf-8"))
    checkpoint_path = tmp_path / (run_id + "-checkpoint.json")
    checkpoint = _checkpoint(
        cfg,
        bank.sha256(),
        run_id,
        result.records,
        checkpoint_path,
        bank.source_path,
    )
    checkpoint_path.write_text(json.dumps(checkpoint), encoding="utf-8")
    checkpoint_file_sha256 = hashlib.sha256(
        checkpoint_path.read_bytes()
    ).hexdigest()
    checkpoint_canonical_sha256 = _canonical_sha256(checkpoint)
    manifest["protocol_provenance"] = {
        "v6_final_checkpoint": {
            "path": str(checkpoint_path),
            "file_sha256": checkpoint_file_sha256,
            "canonical_sha256": checkpoint_canonical_sha256,
            "artifact_audit": {
                "pass": True,
                "checks": {"synthetic_fixture": True},
            },
        }
    }
    receipt_path = tmp_path / "launch" / "receipt.json"
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt = {
        "kind": "controlled_v6_official_launch_receipt",
        "schema_version": "2.0",
        "status": "OFFICIAL_RUN_RESERVED",
        "official_run_id": run_id,
        "canonical_out_dir": "official",
        "final_checkpoint_file_sha256": checkpoint_file_sha256,
        "final_checkpoint_canonical_sha256": checkpoint_canonical_sha256,
        "selected_schedule_sha256": checkpoint["analysis_contract"]["experiment"][
            "full_schedule_sha256"
        ],
        "randomization_schedule_sha256": checkpoint["analysis_contract"][
            "experiment"
        ]["randomization_schedule_sha256"],
        "validated_bank_sha256": bank.sha256(),
        "model": {"id": "mock", "revision": None},
        "config_canonical_sha256": _canonical_sha256(manifest["config"]),
        "created_at_utc": "2026-09-02T00:00:00+00:00",
        "launch_nonce": "1" * 64,
    }
    receipt["receipt_id"] = _canonical_sha256(receipt)
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
    receipt_file_sha256 = hashlib.sha256(receipt_path.read_bytes()).hexdigest()
    log_file_sha256 = hashlib.sha256(Path(result.log_path).read_bytes()).hexdigest()
    manifest["official_launch_receipt"] = {
        "path": "launch/receipt.json",
        "file_sha256": receipt_file_sha256,
        "receipt_id": receipt["receipt_id"],
    }
    manifest["completed_log"] = {
        "path": "official/%s.jsonl" % run_id,
        "file_sha256": log_file_sha256,
        "n_records": len(result.records),
        "reconstructed_records_canonical_sha256": _canonical_sha256(
            result.records
        ),
    }
    Path(result.manifest_path).write_text(json.dumps(manifest), encoding="utf-8")
    summary = evaluate_controlled_v6_checkpoint(
        result.records,
        manifest,
        n_boot=120,
        n_perm=400,
        seed=29,
        frozen_spec=checkpoint,
        checkpoint_root=str(tmp_path),
        checkpoint_file_sha256=checkpoint_file_sha256,
        log_path=result.log_path,
        log_file_sha256=log_file_sha256,
    )
    return result, manifest, checkpoint, summary


@pytest.fixture(scope="module")
def positive_bundle(tmp_path_factory):
    return _run_and_evaluate(
        tmp_path_factory.mktemp("v6-positive"),
        "mock:v5_bayesian",
        "positive",
    )


@pytest.fixture(scope="module")
def null_bundle(tmp_path_factory):
    return _run_and_evaluate(
        tmp_path_factory.mktemp("v6-null"),
        "mock:v4_random",
        "null",
    )


def _reevaluate(records, manifest, checkpoint):
    checkpoint_path = Path(checkpoint["synthetic_fixture_path"])
    log_path = checkpoint_path.parent / manifest["completed_log"]["path"]

    return evaluate_controlled_v6_checkpoint(
        records,
        manifest,
        n_boot=40,
        n_perm=100,
        seed=31,
        frozen_spec=checkpoint,
        checkpoint_root=str(checkpoint_path.parent),
        checkpoint_file_sha256=hashlib.sha256(
            checkpoint_path.read_bytes()
        ).hexdigest(),
        log_path=str(log_path),
        log_file_sha256=hashlib.sha256(log_path.read_bytes()).hexdigest(),
    )


def test_v6_synthetic_positive_uses_randomized_bundle_estimands(positive_bundle):
    result, manifest, _, summary = positive_bundle
    assert result.n_episodes == 24 * 8
    assert result.n_records == 24 * 8 * 24
    assert manifest["task_version"] == CONTROLLED_V6_VERSION
    assert summary["task_version"] == CONTROLLED_V6_VERSION
    assert summary["input_valid"] is True, {
        "failed": [
            name
            for name, passed in summary["design_integrity"]["checks"].items()
            if not passed
        ],
        "replay": summary["design_integrity"]["raw_record_replay"],
    }
    assert summary["status"] == "mock-only V6 validation"
    assert summary["decision"] == "MOCK_V6_PIPELINE_PASS_NOT_SCIENTIFIC_EVIDENCE"
    assert summary["pattern_pass"] is True
    assert summary["scientific_pass"] is False
    assert summary["thresholds"][
        "minimum_stable_difference_in_differences"
    ] == 0.10
    assert summary["thresholds"]["minimum_revision_shift"] == 0.15
    assert summary["primary_contrasts"][
        "stable_full_vs_no_difference_in_differences"
    ]["n_randomized_bundles"] == 8
    assert summary["swap_metrics"]["revision_shift"][
        "n_randomized_bundles"
    ] == 8
    assert summary["swap_metrics"]["revision_shift"]["n_episode_values"] == 48
    assert len(summary["swap_metrics"]["transition_metrics"]) == 6
    assert summary["design_integrity"]["v5_estimand_reuse"]["pass"] is True
    assert summary["design_integrity"]["v5_estimand_reuse"]["checks"][
        "manifest_rewritten_as_v5"
    ] is False
    assert summary["analysis_contract"]["outcome_triggered_behavior"] is False
    assert summary["analysis_contract"]["adaptive_actions"] == []


def test_v6_synthetic_null_is_final_fixed_pattern_failure(null_bundle):
    _, _, _, summary = null_bundle
    assert summary["input_valid"] is True, {
        "failed": [
            name
            for name, passed in summary["design_integrity"]["checks"].items()
            if not passed
        ],
        "replication": summary["design_integrity"].get("replication_audit"),
        "randomization": summary["design_integrity"].get("randomization_audit"),
    }
    assert summary["pattern_pass"] is False
    assert summary["decision"] == "MOCK_V6_PIPELINE_PATTERN_FAIL"
    assert not (
        summary["effect_gates"]["stable_difference_in_differences"]
        and summary["effect_gates"]["swap_vs_stable_adjusted_revision"]
    )
    assert set(summary["stable_condition_metrics"]) == set(
        V6_REQUIRED_CONDITIONS[:4]
    )
    assert len(summary["swap_metrics"]["transition_metrics"]) == 6


def test_v6_analysis_rejects_wrong_version(positive_bundle):
    result, manifest, checkpoint, _ = positive_bundle
    changed_records = [dict(row) for row in result.records]
    changed_records[0]["task_version"] = "controlled-choice-v5.0"
    changed_manifest = copy.deepcopy(manifest)
    changed_manifest["task_version"] = "controlled-choice-v5.0"
    summary = _reevaluate(changed_records, changed_manifest, checkpoint)
    assert summary["input_valid"] is False
    assert summary["decision"] == "ALLOCATION_OR_PROVENANCE_INVALID"
    assert summary["design_integrity"]["checks"]["task_version"] is False
    assert summary["design_integrity"]["checks"][
        "manifest_task_version"
    ] is False


def test_v6_analysis_rejects_nonconfirmatory_scenario(positive_bundle):
    result, manifest, checkpoint, _ = positive_bundle
    changed = [dict(row) for row in result.records]
    wrong = V6_VALIDATION_SCENARIOS[0]
    changed[0]["scenario_id"] = wrong.id
    changed[0]["scenario"] = wrong.as_dict()
    summary = _reevaluate(changed, manifest, checkpoint)
    scenario_audit = summary["design_integrity"][
        "sealed_confirmatory_scenarios"
    ]
    assert summary["input_valid"] is False
    assert summary["decision"] == "ALLOCATION_OR_PROVENANCE_INVALID"
    assert scenario_audit["checks"][
        "sealed_confirmatory_scenario_ids_only"
    ] is False
    assert wrong.id in scenario_audit["observed_ids"]


def test_v6_analysis_rejects_fallback_or_invalid_choice(positive_bundle):
    result, manifest, checkpoint, _ = positive_bundle
    changed = [dict(row) for row in result.records]
    changed[0]["fallback_used"] = True
    changed[0]["selection_valid"] = False
    summary = _reevaluate(changed, manifest, checkpoint)
    assert summary["input_valid"] is False
    assert summary["decision"] == "ALLOCATION_OR_PROVENANCE_INVALID"
    assert summary["effect_gates"]["all_selections_valid"] is False
    assert summary["effect_gates"]["no_fallback"] is False
    assert summary["design_integrity"]["checks"]["no_fallback_used"] is False


def test_v6_analysis_rejects_checkpoint_provenance_tamper(positive_bundle):
    result, manifest, checkpoint, _ = positive_bundle
    changed_manifest = copy.deepcopy(manifest)
    changed_manifest["protocol_provenance"]["v6_final_checkpoint"][
        "canonical_sha256"
    ] = "0" * 64
    summary = _reevaluate(result.records, changed_manifest, checkpoint)
    frozen = summary["design_integrity"]["frozen_v6_checkpoint"]
    assert summary["input_valid"] is False
    assert summary["decision"] == "ALLOCATION_OR_PROVENANCE_INVALID"
    assert frozen["pass"] is False
    assert frozen["checks"]["checkpoint_provenance"] is False


def test_v6_analysis_fails_closed_if_named_gate_constant_drifts(positive_bundle):
    result, manifest, checkpoint, _ = positive_bundle
    original = CONTROLLED_V6_GATE_THRESHOLDS[
        "minimum_stable_difference_in_differences"
    ]
    CONTROLLED_V6_GATE_THRESHOLDS[
        "minimum_stable_difference_in_differences"
    ] = 0.20
    try:
        with pytest.raises(ValueError, match="CONTROLLED_V6_GATE_THRESHOLDS drifted"):
            _reevaluate(result.records, manifest, checkpoint)
    finally:
        CONTROLLED_V6_GATE_THRESHOLDS[
            "minimum_stable_difference_in_differences"
        ] = original


def test_v6_cli_emits_all_fixed_metrics_tables_and_figures(
    positive_bundle, tmp_path, monkeypatch
):
    result, _, checkpoint, baseline_summary = positive_bundle
    checkpoint_path = Path(checkpoint["synthetic_fixture_path"])
    monkeypatch.setattr(
        analyze_v6_module._bootstrap, "ROOT", str(checkpoint_path.parent)
    )
    cli_summary = copy.deepcopy(baseline_summary)
    cli_summary["analysis_execution"] = {
        **{
            key: CONTROLLED_V6_ANALYSIS_CONFIG[key]
            for key in ("n_boot", "n_perm", "seed")
        },
        "matches_frozen_parameters": True,
        "canonical_out_dir": CONTROLLED_V6_ANALYSIS_CONFIG[
            "canonical_out_dir"
        ],
        "figure_bootstrap": copy.deepcopy(
            CONTROLLED_V6_ANALYSIS_CONFIG["figure_bootstrap"]
        ),
    }
    monkeypatch.setattr(
        analyze_v6_module,
        "evaluate_controlled_v6_checkpoint",
        lambda *_args, **_kwargs: copy.deepcopy(cli_summary),
    )
    out_dir = checkpoint_path.parent / str(
        CONTROLLED_V6_ANALYSIS_CONFIG["canonical_out_dir"]
    )
    cli_args = [
        "--log",
        result.log_path,
        "--manifest",
        result.manifest_path,
        "--checkpoint-spec",
        str(checkpoint_path),
        "--out-dir",
        str(out_dir),
    ]
    exit_code = analyze_v6_main(cli_args)
    assert exit_code == 0
    summary = json.loads(
        (out_dir / "v6_checkpoint_summary.json").read_text(encoding="utf-8")
    )
    assert summary["task_version"] == CONTROLLED_V6_VERSION
    assert summary["analysis_execution"]["n_boot"] == 5000
    assert summary["analysis_execution"]["n_perm"] == 10000
    assert summary["analysis_execution"]["seed"] == 20262004
    assert summary["status"] == "mock-only V6 validation"
    assert set(summary["stable_condition_metrics"]) == set(
        V6_REQUIRED_CONDITIONS[:4]
    )
    assert len(summary["swap_metrics"]["transition_metrics"]) == 6
    assert all((out_dir / "tables" / name).is_file() for name in V6_TABLE_NAMES)
    assert all(
        (out_dir / "figures" / (stem + extension)).is_file()
        for stem in V6_FIGURE_STEMS
        for extension in (".pdf", ".png")
    )
    expected_files = {
        V6_SUMMARY_NAME,
        *{"tables/%s" % name for name in V6_TABLE_NAMES},
        *{
            "figures/%s.%s" % (stem, extension)
            for stem in V6_FIGURE_STEMS
            for extension in ("pdf", "png")
        },
    }
    assert {
        path.relative_to(out_dir).as_posix()
        for path in out_dir.rglob("*")
        if path.is_file()
    } == expected_files
    assert summary["artifacts"]["sha256"] == {
        relative: hashlib.sha256((out_dir / relative).read_bytes()).hexdigest()
        for relative in sorted(expected_files - {V6_SUMMARY_NAME})
    }
    first_hashes = {
        relative: hashlib.sha256((out_dir / relative).read_bytes()).hexdigest()
        for relative in sorted(expected_files)
    }
    assert analyze_v6_main(cli_args) == 0
    assert {
        relative: hashlib.sha256((out_dir / relative).read_bytes()).hexdigest()
        for relative in sorted(expected_files)
    } == first_hashes


def test_v6_analysis_derives_selection_from_raw_output(positive_bundle):
    result, manifest, checkpoint, baseline = positive_bundle
    changed = copy.deepcopy(result.records)
    changed[0]["selected_slot"] = 3 if changed[0]["selected_slot"] != 3 else 2
    summary = _reevaluate(changed, manifest, checkpoint)
    replay = summary["design_integrity"]["raw_record_replay"]
    assert summary["input_valid"] is False
    assert replay["pass"] is False
    assert replay["checks"]["every_record_passes_base_schema"] is False
    assert replay["checks"]["all_replayed_fields_exact"] is False
    assert {
        name: metric["mean"]
        for name, metric in summary["primary_contrasts"].items()
    } == {
        name: metric["mean"]
        for name, metric in baseline["primary_contrasts"].items()
    }


def test_v6_analysis_rejects_raw_choice_tamper(positive_bundle):
    result, manifest, checkpoint, _ = positive_bundle
    changed = copy.deepcopy(result.records)
    original = changed[0]["focal_output_raw"]
    changed[0]["focal_output_raw"] = next(
        value for value in ("1", "2", "3") if value != original
    )
    summary = _reevaluate(changed, manifest, checkpoint)
    replay = summary["design_integrity"]["raw_record_replay"]
    assert summary["input_valid"] is False
    assert replay["pass"] is False
    assert any(
        item["field"] in {"selected_slot", "focal_user_prompt"}
        for item in replay["mismatches"]
    )


def test_v6_analysis_regenerates_target_probability_draw_and_choice(
    positive_bundle,
):
    result, manifest, checkpoint, _ = positive_bundle
    for field, replacement in (
        ("target_p_a", 0.123456),
        ("target_uniform_draw", 0.987654),
        ("target_choice", "B" if result.records[0]["target_choice"] == "A" else "A"),
    ):
        changed = copy.deepcopy(result.records)
        changed[0][field] = replacement
        summary = _reevaluate(changed, manifest, checkpoint)
        replay = summary["design_integrity"]["raw_record_replay"]
        assert summary["input_valid"] is False
        assert replay["pass"] is False
        assert any(item["field"] == field for item in replay["mismatches"])


def test_v6_analysis_rejects_candidate_and_prompt_visible_tamper(positive_bundle):
    result, manifest, checkpoint, _ = positive_bundle
    for mutate in (
        lambda row: row["candidates"][0].update(message="tampered candidate"),
        lambda row: row.update(focal_user_prompt="tampered prompt"),
        lambda row: row.pop("visible_history"),
    ):
        changed = copy.deepcopy(result.records)
        mutate(changed[0])
        summary = _reevaluate(changed, manifest, checkpoint)
        replay = summary["design_integrity"]["raw_record_replay"]
        assert summary["input_valid"] is False
        assert replay["pass"] is False


@pytest.mark.parametrize(
    "mutate",
    [
        lambda records: records[0].update(
            episode_index=float(records[0]["episode_index"])
        ),
        lambda records: records[0].update(
            selection_valid=int(records[0]["selection_valid"])
        ),
        lambda records: records[0]["candidates"][0].update(
            slot=float(records[0]["candidates"][0]["slot"])
        ),
        lambda records: records[1]["visible_history"][0].update(
            round=float(records[1]["visible_history"][0]["round"])
        ),
    ],
)
def test_v6_analysis_rejects_json_type_coercions(positive_bundle, mutate):
    result, manifest, checkpoint, _ = positive_bundle
    changed = copy.deepcopy(result.records)
    mutate(changed)
    summary = _reevaluate(changed, manifest, checkpoint)
    replay = summary["design_integrity"]["raw_record_replay"]
    assert summary["input_valid"] is False
    assert replay["checks"]["all_replayed_fields_exact"] is False


def test_v6_analysis_rejects_no_history_replication_divergence(
    positive_bundle,
):
    result, manifest, checkpoint, _ = positive_bundle
    changed = [copy.deepcopy(row) for row in result.records]
    row = next(
        item
        for item in changed
        if item["condition"] == "no_history"
        and item["episode_index"] == 0
        and item["round"] == 2
        and item["initial_target_type"] == STRATEGIES[0]
    )
    row["focal_output_raw"] = "1" if row["focal_output_raw"] != "1" else "2"
    summary = _reevaluate(changed, manifest, checkpoint)
    replication = summary["design_integrity"]["deterministic_replication"]
    assert summary["input_valid"] is False
    assert replication["checks"]["no_history_target_rows_identical"] is False


def test_v6_analysis_rejects_prospective_allocation_tamper(positive_bundle):
    result, manifest, checkpoint, _ = positive_bundle
    changed = [copy.deepcopy(row) for row in result.records]
    row = next(item for item in changed if item["pair_family"] is not None)
    row["allocation_bit"] = 1 - row["allocation_bit"]
    summary = _reevaluate(changed, manifest, checkpoint)
    allocation = summary["design_integrity"]["prospective_randomization"]
    assert summary["input_valid"] is False
    assert allocation["checks"]["all_record_assignments_exact"] is False


@pytest.mark.parametrize(
    "mutate",
    [
        lambda records: records[0].update(unregistered="extra"),
        lambda records: records[0]["candidates"][0].update(unregistered="extra"),
        lambda records: records[1]["visible_history"][0].update(
            unregistered="extra"
        ),
    ],
)
def test_v6_analysis_rejects_extra_record_or_nested_keys(
    positive_bundle, mutate
):
    result, manifest, checkpoint, _ = positive_bundle
    changed = copy.deepcopy(result.records)
    mutate(changed)
    summary = _reevaluate(changed, manifest, checkpoint)
    replay = summary["design_integrity"]["raw_record_replay"]
    assert summary["input_valid"] is False
    assert replay["checks"]["every_record_passes_base_schema"] is False


def test_v6_analysis_requires_actual_completed_log_hash(positive_bundle):
    result, manifest, checkpoint, _ = positive_bundle
    changed_manifest = copy.deepcopy(manifest)
    changed_manifest["completed_log"]["file_sha256"] = "0" * 64
    summary = _reevaluate(result.records, changed_manifest, checkpoint)
    frozen = summary["design_integrity"]["frozen_v6_checkpoint"]
    assert summary["input_valid"] is False
    assert frozen["checks"]["completed_log_hash"] is False


def test_v6_analysis_requires_bound_launch_receipt(positive_bundle):
    result, manifest, checkpoint, _ = positive_bundle
    changed_manifest = copy.deepcopy(manifest)
    changed_manifest["official_launch_receipt"]["receipt_id"] = "0" * 64
    summary = _reevaluate(result.records, changed_manifest, checkpoint)
    frozen = summary["design_integrity"]["frozen_v6_checkpoint"]
    assert summary["input_valid"] is False
    assert frozen["checks"]["launch_receipt_id"] is False


def _launch_receipt_audit_fixture():
    config = {"seed": 7, "enabled": True}
    arguments = {
        "official_run_id": "official-run",
        "canonical_out_dir": "data/raw/official",
        "checkpoint_file_sha256": "1" * 64,
        "checkpoint_canonical_sha256": "2" * 64,
        "selected_schedule_sha256": "3" * 64,
        "randomization_schedule_sha256": "5" * 64,
        "validated_bank_sha256": "4" * 64,
        "model_id": "model/id",
        "revision": 1,
        "config": config,
    }
    receipt = {
        "kind": "controlled_v6_official_launch_receipt",
        "schema_version": "2.0",
        "status": "OFFICIAL_RUN_RESERVED",
        "official_run_id": arguments["official_run_id"],
        "canonical_out_dir": arguments["canonical_out_dir"],
        "final_checkpoint_file_sha256": arguments[
            "checkpoint_file_sha256"
        ],
        "final_checkpoint_canonical_sha256": arguments[
            "checkpoint_canonical_sha256"
        ],
        "selected_schedule_sha256": arguments["selected_schedule_sha256"],
        "randomization_schedule_sha256": arguments[
            "randomization_schedule_sha256"
        ],
        "validated_bank_sha256": arguments["validated_bank_sha256"],
        "model": {"id": arguments["model_id"], "revision": 1},
        "config_canonical_sha256": _canonical_sha256(config),
        "created_at_utc": "2026-09-02T00:00:00+00:00",
        "launch_nonce": "a" * 64,
    }
    receipt["receipt_id"] = _canonical_sha256(receipt)
    return receipt, arguments


def _reseal_launch_receipt(receipt):
    receipt.pop("receipt_id", None)
    receipt["receipt_id"] = _canonical_sha256(receipt)


def test_v6_launch_receipt_requires_exact_schema_and_json_types():
    receipt, arguments = _launch_receipt_audit_fixture()
    assert audit_v6_launch_receipt_payload(receipt, **arguments)["pass"] is True

    extra_top = copy.deepcopy(receipt)
    extra_top["unregistered"] = "extra"
    _reseal_launch_receipt(extra_top)
    top_audit = audit_v6_launch_receipt_payload(extra_top, **arguments)
    assert top_audit["pass"] is False
    assert top_audit["checks"]["top_level_schema"] is False

    extra_nested = copy.deepcopy(receipt)
    extra_nested["model"]["unregistered"] = "extra"
    _reseal_launch_receipt(extra_nested)
    nested_audit = audit_v6_launch_receipt_payload(extra_nested, **arguments)
    assert nested_audit["pass"] is False
    assert nested_audit["checks"]["model_schema"] is False

    coerced = copy.deepcopy(receipt)
    coerced["model"]["revision"] = True
    _reseal_launch_receipt(coerced)
    type_audit = audit_v6_launch_receipt_payload(coerced, **arguments)
    assert type_audit["pass"] is False
    assert type_audit["checks"]["model"] is False


def test_v6_launch_receipt_versions_and_binds_focal_runtime_exactly():
    receipt, arguments = _launch_receipt_audit_fixture()
    runtime = {
        "contract_version": "v6-focal-runtime-contract-1.0",
        "evidence": {"python_version": "3.12.9", "device": "A100"},
    }
    receipt["schema_version"] = "2.0"
    receipt["focal_runtime"] = copy.deepcopy(runtime)
    _reseal_launch_receipt(receipt)
    arguments["expected_focal_runtime"] = runtime
    assert audit_v6_launch_receipt_payload(receipt, **arguments)["pass"] is True

    changed = copy.deepcopy(receipt)
    changed["focal_runtime"]["evidence"]["device"] = "other"
    _reseal_launch_receipt(changed)
    audit = audit_v6_launch_receipt_payload(changed, **arguments)
    assert audit["pass"] is False
    assert audit["checks"]["focal_runtime"] is False


@pytest.mark.parametrize(
    "field,value,failed_check",
    [
        ("created_at_utc", "2026-09-02T00:00:00Z", "created_at_utc"),
        ("created_at_utc", "2026-09-02T05:30:00+05:30", "created_at_utc"),
        ("launch_nonce", "a" * 63, "launch_nonce"),
        ("launch_nonce", "g" * 64, "launch_nonce"),
        ("launch_nonce", "A" * 64, "launch_nonce"),
    ],
)
def test_v6_launch_receipt_requires_canonical_utc_and_exact_nonce(
    field, value, failed_check
):
    receipt, arguments = _launch_receipt_audit_fixture()
    receipt[field] = value
    _reseal_launch_receipt(receipt)
    audit = audit_v6_launch_receipt_payload(receipt, **arguments)
    assert audit["pass"] is False
    assert audit["checks"][failed_check] is False


def test_v6_cli_returns_nonzero_and_skips_plots_for_invalid_input(
    tmp_path, monkeypatch
):
    log_path = tmp_path / "invalid.jsonl"
    manifest_path = tmp_path / "invalid.manifest.json"
    checkpoint_path = tmp_path / "checkpoint.json"
    monkeypatch.setattr(analyze_v6_module._bootstrap, "ROOT", str(tmp_path))
    out_dir = tmp_path / str(CONTROLLED_V6_ANALYSIS_CONFIG["canonical_out_dir"])
    log_path.write_text("{}\n", encoding="utf-8")
    manifest_path.write_text("{}", encoding="utf-8")
    checkpoint_path.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(
        analyze_v6_module,
        "evaluate_controlled_v6_checkpoint",
        lambda *_args, **_kwargs: {
            "status": "invalid V6 confirmatory input",
            "decision": "V6_CONFIRMATORY_INPUT_INVALID",
            "input_valid": False,
            "effect_gates": {},
            "inference_gates": {},
        },
    )
    exit_code = analyze_v6_main(
        [
            "--log",
            str(log_path),
            "--manifest",
            str(manifest_path),
            "--checkpoint-spec",
            str(checkpoint_path),
            "--out-dir",
            str(out_dir),
        ]
    )
    assert exit_code == 2
    summary = json.loads(
        (out_dir / "v6_checkpoint_summary.json").read_text(encoding="utf-8")
    )
    assert summary["artifacts"]["tables"] == []
    assert summary["artifacts"]["figures"] == []
    assert summary["artifacts"]["sha256"] == {}
    assert not (out_dir / "tables").exists()
    assert not (out_dir / "figures").exists()
    assert [path.name for path in out_dir.iterdir()] == [V6_SUMMARY_NAME]


def test_v6_cli_rejects_analysis_parameter_override_with_auditable_summary(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(analyze_v6_module._bootstrap, "ROOT", str(tmp_path))
    log_path = tmp_path / "unused.jsonl"
    manifest_path = tmp_path / "unused.manifest.json"
    checkpoint_path = tmp_path / "unused-checkpoint.json"
    out_dir = tmp_path / str(CONTROLLED_V6_ANALYSIS_CONFIG["canonical_out_dir"])
    exit_code = analyze_v6_main(
        [
            "--log",
            str(log_path),
            "--manifest",
            str(manifest_path),
            "--checkpoint-spec",
            str(checkpoint_path),
            "--out-dir",
            str(out_dir),
            "--n-boot",
            "4999",
        ]
    )
    assert exit_code == 2
    summary = json.loads((out_dir / V6_SUMMARY_NAME).read_text(encoding="utf-8"))
    assert summary["decision"] == "V6_CONFIRMATORY_INPUT_INVALID"
    assert summary["analysis_execution"]["matches_frozen_parameters"] is False
    assert "differ from the frozen contract" in summary["invalid_input"]["message"]


@pytest.mark.parametrize("log_contents", ["", "{not-json}\n"])
def test_v6_cli_malformed_or_empty_log_returns_two_and_writes_minimal_summary(
    tmp_path, monkeypatch, log_contents
):
    case_root = tmp_path / ("empty" if not log_contents else "malformed")
    case_root.mkdir()
    monkeypatch.setattr(analyze_v6_module._bootstrap, "ROOT", str(case_root))
    log_path = case_root / "input.jsonl"
    manifest_path = case_root / "input.manifest.json"
    checkpoint_path = case_root / "checkpoint.json"
    log_path.write_text(log_contents, encoding="utf-8")
    manifest_path.write_text("{}", encoding="utf-8")
    checkpoint_path.write_text("{}", encoding="utf-8")
    out_dir = case_root / str(CONTROLLED_V6_ANALYSIS_CONFIG["canonical_out_dir"])
    assert analyze_v6_main(
        [
            "--log",
            str(log_path),
            "--manifest",
            str(manifest_path),
            "--checkpoint-spec",
            str(checkpoint_path),
            "--out-dir",
            str(out_dir),
        ]
    ) == 2
    summary = json.loads((out_dir / V6_SUMMARY_NAME).read_text(encoding="utf-8"))
    assert summary["input_valid"] is False
    assert summary["decision"] == "V6_CONFIRMATORY_INPUT_INVALID"
    assert set(path.name for path in out_dir.iterdir()) == {V6_SUMMARY_NAME}


@pytest.mark.parametrize(
    "input_name,document,message",
    [
        ("log", '{"value": 1, "value": 2}\n', "duplicate"),
        ("log", '{"value": NaN}\n', "non-finite"),
        ("manifest", '{"value": 1, "value": 2}\n', "duplicate"),
        ("manifest", '{"value": Infinity}\n', "non-finite"),
        ("checkpoint", '{"value": 1, "value": 2}\n', "duplicate"),
        ("checkpoint", '{"value": -Infinity}\n', "non-finite"),
    ],
)
def test_v6_cli_rejects_duplicate_and_nonfinite_json_inputs(
    tmp_path, monkeypatch, input_name, document, message
):
    monkeypatch.setattr(analyze_v6_module._bootstrap, "ROOT", str(tmp_path))
    paths = {
        "log": tmp_path / "input.jsonl",
        "manifest": tmp_path / "input.manifest.json",
        "checkpoint": tmp_path / "checkpoint.json",
    }
    paths["log"].write_text("{}\n", encoding="utf-8")
    paths["manifest"].write_text("{}\n", encoding="utf-8")
    paths["checkpoint"].write_text("{}\n", encoding="utf-8")
    paths[input_name].write_text(document, encoding="utf-8")
    out_dir = tmp_path / str(CONTROLLED_V6_ANALYSIS_CONFIG["canonical_out_dir"])

    assert analyze_v6_main(
        [
            "--log",
            str(paths["log"]),
            "--manifest",
            str(paths["manifest"]),
            "--checkpoint-spec",
            str(paths["checkpoint"]),
            "--out-dir",
            str(out_dir),
        ]
    ) == 2
    summary = json.loads((out_dir / V6_SUMMARY_NAME).read_text(encoding="utf-8"))
    assert message in summary["invalid_input"]["message"]


def test_v6_analysis_json_reader_rejects_symlink_and_fifo(tmp_path):
    target = tmp_path / "target.json"
    target.write_text("{}\n", encoding="utf-8")
    link = tmp_path / "link.json"
    link.symlink_to(target)
    with pytest.raises(ValueError, match="symlink"):
        analyze_v6_module._load_json_object(
            str(link), "test input", root=str(tmp_path)
        )

    fifo = tmp_path / "input.fifo"
    os.mkfifo(fifo)
    with pytest.raises(ValueError, match="regular file"):
        analyze_v6_module._load_json_object(
            str(fifo), "test input", root=str(tmp_path)
        )


def test_v6_cli_rejects_symlinked_canonical_output_ancestor(
    tmp_path, monkeypatch
):
    repository = tmp_path / "repository"
    repository.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (repository / "results").symlink_to(outside, target_is_directory=True)
    monkeypatch.setattr(analyze_v6_module._bootstrap, "ROOT", str(repository))
    out_dir = repository / str(
        CONTROLLED_V6_ANALYSIS_CONFIG["canonical_out_dir"]
    )

    assert analyze_v6_main(
        [
            "--log",
            str(repository / "input.jsonl"),
            "--checkpoint-spec",
            str(repository / "checkpoint.json"),
            "--out-dir",
            str(out_dir),
        ]
    ) == 2
    assert list(outside.iterdir()) == []


def test_v6_cli_rejects_resolved_alias_outside_repository(
    tmp_path, monkeypatch
):
    repository = tmp_path / "repository"
    canonical = repository / str(
        CONTROLLED_V6_ANALYSIS_CONFIG["canonical_out_dir"]
    )
    canonical.mkdir(parents=True)
    alias = tmp_path / "outside-alias"
    alias.symlink_to(canonical, target_is_directory=True)
    monkeypatch.setattr(analyze_v6_module._bootstrap, "ROOT", str(repository))

    assert analyze_v6_main(
        [
            "--log",
            str(repository / "input.jsonl"),
            "--checkpoint-spec",
            str(repository / "checkpoint.json"),
            "--out-dir",
            str(alias),
        ]
    ) == 2
    assert list(canonical.iterdir()) == []


def test_v6_analysis_rejects_incomplete_or_extra_staged_artifacts_without_publish(
    positive_bundle, tmp_path, monkeypatch
):
    result, _, checkpoint, baseline_summary = positive_bundle
    checkpoint_path = Path(checkpoint["synthetic_fixture_path"])
    monkeypatch.setattr(analyze_v6_module._bootstrap, "ROOT", str(tmp_path))
    out_dir = tmp_path / str(
        CONTROLLED_V6_ANALYSIS_CONFIG["canonical_out_dir"]
    )
    out_dir.mkdir(parents=True)
    old_summary = b'{"status":"previous complete analysis"}\n'
    (out_dir / V6_SUMMARY_NAME).write_bytes(old_summary)
    (out_dir / "tables").mkdir()
    (out_dir / "tables" / "old.csv").write_text("old", encoding="utf-8")

    def incomplete_figures(_records, _summary, figure_dir, _n_boot, _seed):
        Path(figure_dir).mkdir(parents=True)
        (Path(figure_dir) / "unexpected.txt").write_text(
            "not a registered figure", encoding="utf-8"
        )

    monkeypatch.setattr(analyze_v6_module, "make_figures", incomplete_figures)
    monkeypatch.setattr(
        analyze_v6_module,
        "evaluate_controlled_v6_checkpoint",
        lambda *_args, **_kwargs: copy.deepcopy(baseline_summary),
    )
    assert analyze_v6_main(
        [
            "--log",
            result.log_path,
            "--manifest",
            result.manifest_path,
            "--checkpoint-spec",
            str(checkpoint_path),
            "--out-dir",
            str(out_dir),
        ]
    ) == 2
    assert (out_dir / V6_SUMMARY_NAME).read_bytes() == old_summary
    assert (out_dir / "tables" / "old.csv").is_file()


def _make_publication_stage(tmp_path, name, *, table="new", summary="new summary"):
    root = tmp_path / name
    (root / "tables").mkdir(parents=True)
    (root / "figures").mkdir()
    (root / "tables" / "new.csv").write_text(table, encoding="utf-8")
    (root / "figures" / "new.png").write_bytes(b"new")
    (root / V6_SUMMARY_NAME).write_text(summary, encoding="utf-8")
    expected = ("tables/new.csv", "figures/new.png")
    hashes = {
        relative: hashlib.sha256((root / relative).read_bytes()).hexdigest()
        for relative in expected
    }
    summary_hash = hashlib.sha256((root / V6_SUMMARY_NAME).read_bytes()).hexdigest()
    return root, expected, hashes, summary_hash


def test_v6_analysis_publication_exact_retry_is_idempotent(tmp_path):
    out_dir = tmp_path / "analysis"
    stage, expected, hashes, summary_hash = _make_publication_stage(
        tmp_path, "stage-one"
    )
    first = _publish_staged_analysis(
        str(stage), str(out_dir), expected, hashes, summary_hash
    )
    before = {
        relative: hashlib.sha256((out_dir / relative).read_bytes()).hexdigest()
        for relative in (*expected, V6_SUMMARY_NAME)
    }
    retry, _, retry_hashes, retry_summary_hash = _make_publication_stage(
        tmp_path, "stage-two"
    )
    second = _publish_staged_analysis(
        str(retry), str(out_dir), expected, retry_hashes, retry_summary_hash
    )
    after = {
        relative: hashlib.sha256((out_dir / relative).read_bytes()).hexdigest()
        for relative in (*expected, V6_SUMMARY_NAME)
    }
    assert first == second
    assert before == after
    assert all(
        stat.S_IMODE((out_dir / relative).stat().st_mode) == 0o444
        for relative in (*expected, V6_SUMMARY_NAME)
    )


def test_v6_analysis_completed_summary_never_recovers_deleted_sibling(tmp_path):
    out_dir = tmp_path / "analysis"
    stage, expected, hashes, summary_hash = _make_publication_stage(
        tmp_path, "completed-stage"
    )
    _publish_staged_analysis(
        str(stage), str(out_dir), expected, hashes, summary_hash
    )
    missing = out_dir / "tables" / "new.csv"
    missing.unlink()

    retry, _, retry_hashes, retry_summary_hash = _make_publication_stage(
        tmp_path, "completed-retry"
    )
    with pytest.raises(RuntimeError, match="completed.*not exact"):
        _publish_staged_analysis(
            str(retry),
            str(out_dir),
            expected,
            retry_hashes,
            retry_summary_hash,
        )
    assert not missing.exists()
    assert (out_dir / V6_SUMMARY_NAME).is_file()


def test_v6_analysis_publication_rejects_writable_existing_artifact(tmp_path):
    out_dir = tmp_path / "analysis"
    stage, expected, hashes, summary_hash = _make_publication_stage(
        tmp_path, "mode-stage"
    )
    _publish_staged_analysis(
        str(stage), str(out_dir), expected, hashes, summary_hash
    )
    writable = out_dir / "tables" / "new.csv"
    writable.chmod(0o644)

    retry, _, retry_hashes, retry_summary_hash = _make_publication_stage(
        tmp_path, "mode-retry"
    )
    with pytest.raises(RuntimeError, match="not read-only"):
        _publish_staged_analysis(
            str(retry),
            str(out_dir),
            expected,
            retry_hashes,
            retry_summary_hash,
        )


def test_v6_analysis_publication_recovers_matching_missing_siblings(
    tmp_path, monkeypatch
):
    out_dir = tmp_path / "analysis"
    stage, expected, hashes, summary_hash = _make_publication_stage(
        tmp_path, "crash-stage"
    )
    real_link = analyze_v6_module._link_create_once

    def crash_on_table(source, target):
        if str(target).endswith("tables/new.csv"):
            raise OSError("simulated publication crash")
        real_link(source, target)

    with monkeypatch.context() as patcher:
        patcher.setattr(analyze_v6_module, "_link_create_once", crash_on_table)
        with pytest.raises(OSError, match="simulated publication crash"):
            _publish_staged_analysis(
                str(stage), str(out_dir), expected, hashes, summary_hash
            )
    assert (out_dir / "figures" / "new.png").is_file()
    assert not (out_dir / "tables" / "new.csv").exists()
    assert not (out_dir / V6_SUMMARY_NAME).exists()

    recovered, _, recovered_hashes, recovered_summary_hash = (
        _make_publication_stage(tmp_path, "recovery-stage")
    )
    summary_path = _publish_staged_analysis(
        str(recovered),
        str(out_dir),
        expected,
        recovered_hashes,
        recovered_summary_hash,
    )
    assert Path(summary_path).read_text(encoding="utf-8") == "new summary"
    assert {
        path.relative_to(out_dir).as_posix()
        for path in out_dir.rglob("*")
        if path.is_file()
    } == {V6_SUMMARY_NAME, *expected}


def test_v6_analysis_publication_rejects_conflicting_retry(tmp_path):
    out_dir = tmp_path / "analysis"
    stage, expected, hashes, summary_hash = _make_publication_stage(
        tmp_path, "original-stage"
    )
    _publish_staged_analysis(
        str(stage), str(out_dir), expected, hashes, summary_hash
    )
    conflicting, _, conflict_hashes, conflict_summary_hash = (
        _make_publication_stage(
            tmp_path,
            "conflicting-stage",
            table="different",
            summary="different summary",
        )
    )
    with pytest.raises(RuntimeError, match="conflicting existing"):
        _publish_staged_analysis(
            str(conflicting),
            str(out_dir),
            expected,
            conflict_hashes,
            conflict_summary_hash,
        )
    assert (out_dir / "tables" / "new.csv").read_text(encoding="utf-8") == "new"


def test_v6_analysis_publication_rejects_extra_file(tmp_path):
    out_dir = tmp_path / "analysis"
    out_dir.mkdir()
    (out_dir / "unrelated.txt").write_text("do not sweep me", encoding="utf-8")
    stage, expected, hashes, summary_hash = _make_publication_stage(
        tmp_path, "extra-stage"
    )
    with pytest.raises(RuntimeError, match="unregistered artifacts"):
        _publish_staged_analysis(
            str(stage), str(out_dir), expected, hashes, summary_hash
        )
    assert (out_dir / "unrelated.txt").read_text(encoding="utf-8") == "do not sweep me"
