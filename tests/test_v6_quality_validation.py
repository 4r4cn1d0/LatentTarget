"""V6 blind quality-judge contracts, gates, artifacts, and CLI behavior."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import subprocess
import time
from pathlib import Path

import pytest

import src.blind_judge as blind_judge_module
import src.v6_quality_validation as quality_validation_module

from config import CONTROLLED_V6_QUALITY_THRESHOLDS
from src.blind_judge import PaidBatchReconciliationError, canonical_json_sha256
from src.v6_quality_validation import (
    CODEX_QUALITY_PROMPT_VERSION,
    QUALITY_ISSUE_CODES,
    QUALITY_SCORE_FIELDS,
    CodexQualityJudge,
    audit_quality_judge_run,
    audit_quality_artifacts,
    audit_v6_quality_validation_summary,
    build_quality_batch_plan,
    build_quality_batches,
    build_quality_prompt,
    canonical_quality_result_map,
    evaluate_v6_quality_validation,
    make_quality_sample,
    quality_candidate_rows,
    quality_output_schema,
    quality_judge_contract,
    replay_quality_judge_run_from_manifest,
    run_quality_codex_batch,
    validate_quality_payload,
)


ROOT = Path(__file__).parents[1]
POOL = ROOT / "data" / "v6" / "v6_triad_pool_v1.json"


def _pool():
    return json.loads(POOL.read_text(encoding="utf-8"))


_TEST_CODEX_RUNTIME = {
    "codex_executable": "codex",
    "codex_cli_version": "codex-cli test",
    "codex_executable_sha256": "b" * 64,
}


def _official_quality_fixture(
    cli,
    tmp_path,
    monkeypatch,
    *,
    models=("gpt-5.6-sol", "gpt-5.6-luna"),
    seeds=(20261002, 20261003),
    batch_size=20,
    out_dir="out",
    cache_dir="cache",
):
    bank_path = tmp_path / "data" / "v6" / POOL.name
    bank_path.parent.mkdir(parents=True, exist_ok=True)
    bank_path.write_bytes(POOL.read_bytes())
    pool = _pool()
    pool_contract = {
        "path": "data/v6/%s" % POOL.name,
        "file_sha256": hashlib.sha256(bank_path.read_bytes()).hexdigest(),
        "canonical_sha256": canonical_json_sha256(pool),
    }
    prompt = quality_judge_contract()
    frozen = {
        "models": list(models),
        "seeds": list(seeds),
        "batch_size": batch_size,
        **prompt,
    }
    official = {
        "contract_version": "v6-official-codex-judge-contract-v1",
        "kind": "quality",
        **frozen,
        "candidate_pool": pool_contract,
        "codex_runtime": _TEST_CODEX_RUNTIME,
    }
    contract = {
        "status": "READY_FOR_TARGET_FREE_JUDGES",
        "power_design": {
            "result": {
                "status": "PASS_V6_PROSPECTIVE_BUNDLE_POWER",
                "pass": True,
                "selected_episode_seeds": 24,
            }
        },
        "candidate_pool": {
            "path": pool_contract["path"],
            "file_sha256": pool_contract["file_sha256"],
            "sha256": pool_contract["canonical_sha256"],
        },
        "judge_runtime": dict(_TEST_CODEX_RUNTIME),
        "quality_validation": {
            "canonical_out_dir": out_dir,
            "canonical_cache_dir": cache_dir,
            "judge_contract": {
                **frozen,
                "official_contract_sha256": canonical_json_sha256(official),
            },
        },
    }
    contract_path = tmp_path / "docs" / "v6_calibration_protocol.json"
    contract_path.parent.mkdir(parents=True, exist_ok=True)
    contract_path.write_text(json.dumps(contract), encoding="utf-8")
    monkeypatch.setattr(
        cli,
        "attest_codex_executable",
        lambda *_args, **_kwargs: {
            **_TEST_CODEX_RUNTIME,
            "resolved_executable": "/test/codex",
        },
    )
    return bank_path, contract_path, contract


def _result(
    sample_id,
    score=0.90,
    overall_quality=None,
    issue_code="none",
    **overrides,
):
    result = {
        "sample_id": sample_id,
        **{field: score for field in QUALITY_SCORE_FIELDS},
        "issue_code": issue_code,
    }
    if overall_quality is not None:
        result["overall_quality"] = overall_quality
    result.update(overrides)
    return result


def _perfect_results(pool, model="judge"):
    return {
        row["message"]: _result(make_quality_sample(row["message"], model).sample_id)
        for row in quality_candidate_rows(pool)
    }


def _description(model):
    return {
        "provider": "test",
        "model": model,
        "judge_prompt_version": CODEX_QUALITY_PROMPT_VERSION,
    }


def _artifact_audit(results, model, ok=True):
    clean = canonical_quality_result_map(results)
    return {
        "ok": ok,
        "frozen_schedule_enforced": True,
        "cache_reconciled": True,
        "judge_run_manifest": {"manifest_sha256": "test"},
        "models": [model],
        "prompt_version": CODEX_QUALITY_PROMPT_VERSION,
        "result_map": clean,
        "result_map_sha256": canonical_json_sha256(clean),
    }


def _evaluate(pool, primary, sensitivity, **kwargs):
    primary_description = kwargs.pop(
        "primary_description", _description("judge-a")
    )
    sensitivity_description = kwargs.pop(
        "sensitivity_description", _description("judge-b")
    )
    return evaluate_v6_quality_validation(
        pool,
        primary,
        sensitivity,
        primary_description,
        sensitivity_description,
        kwargs.pop(
            "primary_artifact_audit",
            _artifact_audit(primary, primary_description["model"]),
        ),
        kwargs.pop(
            "sensitivity_artifact_audit",
            _artifact_audit(sensitivity, sensitivity_description["model"]),
        ),
        **kwargs,
    )


def test_pool_rows_render_all_messages_but_prompt_exposes_only_blind_fields():
    pool = _pool()
    rows = quality_candidate_rows(pool)
    assert len(rows) == 60
    assert len({row["candidate_id"] for row in rows}) == 60
    assert len({row["message"] for row in rows}) == 60
    assert all("{a}" not in row["message"] for row in rows)
    assert all("Option A" in row["message"] for row in rows)

    batches = build_quality_batches(
        [row["message"] for row in rows], "judge-a", batch_size=17, seed=11
    )
    first_order = [[sample.sample_id for sample in batch] for batch in batches]
    second_order = [
        [sample.sample_id for sample in batch]
        for batch in build_quality_batches(
            [row["message"] for row in rows],
            "judge-a",
            batch_size=17,
            seed=11,
        )
    ]
    assert first_order == second_order
    prompt = build_quality_prompt(batches[0])
    for forbidden in (
        '"candidate_id"',
        '"intended_frame"',
        '"triad_id"',
        '"split"',
        "hidden target",
    ):
        assert forbidden not in prompt.lower()
    assert all(
        set(sample.judge_dict()) == {"sample_id", "message"}
        for sample in batches[0]
    )


def test_quality_schema_is_strict_bounded_and_uses_fixed_issue_enum():
    schema = quality_output_schema(["q_a", "q_b"])
    assessments = schema["properties"]["assessments"]
    item = assessments["items"]
    assert assessments["minItems"] == assessments["maxItems"] == 2
    assert item["additionalProperties"] is False
    assert set(item["required"]) == {
        "sample_id",
        *QUALITY_SCORE_FIELDS,
        "issue_code",
    }
    assert item["properties"]["sample_id"]["enum"] == ["q_a", "q_b"]
    assert item["properties"]["issue_code"]["enum"] == list(QUALITY_ISSUE_CODES)
    for field in QUALITY_SCORE_FIELDS:
        assert item["properties"][field]["minimum"] == 0.0
        assert item["properties"][field]["maximum"] == 1.0


def test_quality_payload_validation_accepts_complete_schema_valid_batch():
    payload = {"assessments": [_result("q_a"), _result("q_b", issue_code="clarity")]}
    clean = validate_quality_payload(payload, ["q_a", "q_b"])
    assert clean["q_a"]["overall_quality"] == 0.9
    assert clean["q_b"]["issue_code"] == "clarity"


@pytest.mark.parametrize(
    "payload,error",
    [
        ({"assessments": [_result("q_a")]}, "omitted"),
        (
            {"assessments": [_result("q_a"), _result("q_a")]},
            "duplicate",
        ),
        (
            {
                "assessments": [
                    {**_result("q_a"), "unexpected": 1},
                    _result("q_b"),
                ]
            },
            "fields",
        ),
        (
            {
                "assessments": [
                    {**_result("q_a"), "grammar": 1.01},
                    _result("q_b"),
                ]
            },
            "outside",
        ),
        (
            {
                "assessments": [
                    {**_result("q_a"), "clarity": True},
                    _result("q_b"),
                ]
            },
            "not numeric",
        ),
        (
            {
                "assessments": [
                    _result("q_a", issue_code="free-form explanation"),
                    _result("q_b"),
                ]
            },
            "issue_code",
        ),
        (
            {"assessments": [_result("q_a"), _result("q_b")], "extra": []},
            "only",
        ),
    ],
)
def test_quality_payload_validation_fails_closed(payload, error):
    with pytest.raises(ValueError, match=error):
        validate_quality_payload(payload, ["q_a", "q_b"])


def test_quality_judge_cache_resumes_without_new_runner_calls(tmp_path):
    calls = []

    def fake_batch_runner(samples, model, executable, artifact_dir, timeout_s):
        calls.append([sample.judge_dict() for sample in samples])
        return {
            sample.sample_id: _result(sample.sample_id) for sample in samples
        }

    cache = tmp_path / "quality-cache.jsonl"
    judge = CodexQualityJudge(
        model="judge-a",
        cache_path=str(cache),
        artifact_dir=str(tmp_path / "batches"),
        batch_size=2,
        seed=4,
        batch_runner=fake_batch_runner,
    )
    first = judge.score_messages(["one", "two", "three", "one"])
    assert set(first) == {"one", "two", "three"}
    assert judge.n_judged == 3
    assert len(calls) == 2
    assert all(set(row) == {"sample_id", "message"} for call in calls for row in call)

    def must_not_run(*args, **kwargs):
        raise AssertionError("quality cache was not used")

    resumed = CodexQualityJudge(
        model="judge-a",
        cache_path=str(cache),
        artifact_dir=str(tmp_path / "batches"),
        batch_size=2,
        seed=4,
        batch_runner=must_not_run,
    )
    second = resumed.score_messages(["one", "two", "three", "one"])
    assert first == second
    assert resumed.n_cached == 3
    records = [json.loads(line) for line in cache.read_text().splitlines()]
    assert len(records) == 3
    assert {record["prompt_version"] for record in records} == {
        CODEX_QUALITY_PROMPT_VERSION
    }
    assert {record["model"] for record in records} == {"judge-a"}
    assert all(record["prompt_template_sha256"] for record in records)
    assert all(record["rubric_sha256"] for record in records)
    assert all(record["value_sha256"] for record in records)


def test_real_batch_path_with_fake_process_preserves_and_audits_artifacts(tmp_path):
    samples = [
        make_quality_sample("First message.", "judge-a"),
        make_quality_sample("Second message.", "judge-a"),
    ]
    observed = {}

    def fake_process(command, **kwargs):
        observed["command"] = command
        observed["prompt"] = kwargs["input"]
        schema_path = Path(command[command.index("--output-schema") + 1])
        final_path = Path(command[command.index("--output-last-message") + 1])
        schema = json.loads(schema_path.read_text())
        assert schema["additionalProperties"] is False
        assert schema["properties"]["assessments"]["minItems"] == 2
        raw = json.dumps(
            {"assessments": [_result(sample.sample_id) for sample in samples]},
            separators=(",", ":"),
        )
        final_path.write_text(raw, encoding="utf-8")
        return subprocess.CompletedProcess(
            command,
            0,
            stdout="local process output",
            stderr="session id: should-not-be-retained",
        )

    artifact_dir = tmp_path / "artifacts"
    results = run_quality_codex_batch(
        samples,
        "judge-a",
        "codex",
        str(artifact_dir),
        30,
        process_runner=fake_process,
    )
    assert set(results) == {sample.sample_id for sample in samples}
    assert all(result["_batch_id"].startswith("batch_") for result in results.values())
    assert all(result["_artifact_binding"] for result in results.values())
    assert '"triad_id"' not in observed["prompt"]
    assert '"split"' not in observed["prompt"]

    input_path = next(artifact_dir.glob("*.input.json"))
    output_path = next(artifact_dir.glob("*.output.json"))
    meta_path = next(artifact_dir.glob("*.meta.json"))
    supplied = json.loads(input_path.read_text())
    assert all(set(row) == {"sample_id", "message"} for row in supplied["samples"])
    assert json.loads(output_path.read_text())["assessments"][0]["sample_id"]
    meta = json.loads(meta_path.read_text())
    assert "stdout" not in meta and "stderr" not in meta
    assert meta["stdout_sha256"] and meta["stderr_sha256"]
    assert meta["process_logs_retained"] is False
    assert not any(Path(value).is_absolute() for value in meta["command_flags"])

    audit = audit_quality_artifacts(str(artifact_dir))
    assert audit["ok"] is True
    assert audit["n_unique_messages"] == 2
    assert audit["sample_keys_visible_to_judge"] == ["message", "sample_id"]
    assert audit["metadata_fields_visible_to_judge"] == []
    assert set(audit["result_map"]) == {sample.message for sample in samples}
    assert audit["result_map_sha256"] == canonical_json_sha256(
        audit["result_map"]
    )
    assert audit["result_binding_map_sha256"] == canonical_json_sha256(
        audit["result_binding_map"]
    )

    cache = tmp_path / "quality-cache.jsonl"

    def bound_runner(requested, model, executable, path, timeout_s):
        assert {sample.sample_id for sample in requested} == set(results)
        return results

    judge = CodexQualityJudge(
        model="judge-a",
        cache_path=str(cache),
        artifact_dir=str(artifact_dir),
        batch_runner=bound_runner,
    )
    judge.score_messages([sample.message for sample in samples])
    records = [json.loads(line) for line in cache.read_text().splitlines()]
    assert {record["cache_record_version"] for record in records} == {2}
    assert {
        record["artifact_binding"]["result_sha256"] for record in records
    } == {
        binding["result_sha256"]
        for binding in audit["result_binding_map"].values()
    }


def test_quality_nonzero_process_persists_terminal_failed_state(tmp_path):
    sample = make_quality_sample("A private quality message.", "judge-a")

    def fake_process(command, **kwargs):
        return subprocess.CompletedProcess(
            command, 9, stdout="", stderr="private provider failure"
        )

    artifacts = tmp_path / "artifacts"
    with pytest.raises(RuntimeError, match="failed with exit 9"):
        run_quality_codex_batch(
            [sample],
            "judge-a",
            "codex",
            str(artifacts),
            30,
            process_runner=fake_process,
        )
    state = json.loads(
        next(artifacts.glob(".*.provider-state.json")).read_text(
            encoding="utf-8"
        )
    )
    assert state["status"] == "failed"
    assert state["failure_kind"] == "nonzero_exit"
    assert state["process"]["returncode"] == 9


def test_artifact_audit_rejects_joined_metadata(tmp_path):
    sample = make_quality_sample("A message.", "judge-a")

    def fake_process(command, **kwargs):
        final_path = Path(command[command.index("--output-last-message") + 1])
        final_path.write_text(
            json.dumps({"assessments": [_result(sample.sample_id)]}),
            encoding="utf-8",
        )
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    artifact_dir = tmp_path / "artifacts"
    run_quality_codex_batch(
        [sample],
        "judge-a",
        "codex",
        str(artifact_dir),
        30,
        process_runner=fake_process,
    )
    input_path = next(artifact_dir.glob("*.input.json"))
    supplied = json.loads(input_path.read_text())
    supplied["samples"][0]["triad_id"] = "must-remain-hidden"
    input_path.write_text(json.dumps(supplied), encoding="utf-8")
    with pytest.raises(ValueError, match="non-blind fields"):
        audit_quality_artifacts(str(artifact_dir))


def test_quality_cache_rejects_tampered_value_hash(tmp_path):
    cache = tmp_path / "quality-cache.jsonl"

    def fake_batch_runner(samples, model, executable, artifact_dir, timeout_s):
        return {
            sample.sample_id: _result(sample.sample_id) for sample in samples
        }

    judge = CodexQualityJudge(
        model="judge-a",
        cache_path=str(cache),
        artifact_dir=str(tmp_path / "artifacts"),
        batch_runner=fake_batch_runner,
    )
    judge.score_messages(["one"])
    record = json.loads(cache.read_text(encoding="utf-8"))
    record["value"]["clarity"] = 0.0
    cache.write_text(json.dumps(record) + "\n", encoding="utf-8")

    with pytest.raises(ValueError, match="value hash mismatch"):
        CodexQualityJudge(
            model="judge-a",
            cache_path=str(cache),
            artifact_dir=str(tmp_path / "artifacts"),
            batch_runner=fake_batch_runner,
        )


def test_legacy_quality_cache_record_remains_readable(tmp_path):
    cache = tmp_path / "legacy-quality-cache.jsonl"
    sample = make_quality_sample("one", "judge-a")
    cache.write_text(
        json.dumps(
            {
                "key": sample.cache_key,
                "message_sha256": hashlib.sha256(b"one").hexdigest(),
                "model": "judge-a",
                "prompt_version": CODEX_QUALITY_PROMPT_VERSION,
                "value": _result(sample.sample_id),
            }
        )
        + "\n",
        encoding="utf-8",
    )

    def must_not_run(*args, **kwargs):
        raise AssertionError("legacy quality cache was not used")

    judge = CodexQualityJudge(
        model="judge-a",
        cache_path=str(cache),
        artifact_dir=str(tmp_path / "artifacts"),
        batch_runner=must_not_run,
    )

    assert judge.score_messages(["one"])["one"]["sample_id"] == sample.sample_id


@pytest.mark.parametrize(
    "malformed",
    [
        '{"key":"first","key":"second"}\n',
        '{"key":NaN}\n',
    ],
)
def test_quality_cache_strict_jsonl_rejects_duplicate_keys_and_nan(
    tmp_path, malformed
):
    cache = tmp_path / "cache.jsonl"
    cache.write_text(malformed, encoding="utf-8")
    with pytest.raises(ValueError, match="invalid strict JSON"):
        CodexQualityJudge(
            model="judge-a",
            cache_path=str(cache),
            artifact_dir=str(tmp_path / "artifacts"),
            batch_runner=lambda *args: {},
        )


def test_two_distinct_judges_pass_clean_pool_and_join_metadata_after_calls():
    pool = _pool()
    primary = _perfect_results(pool, "judge-a")
    sensitivity = _perfect_results(pool, "judge-b")
    summary = _evaluate(pool, primary, sensitivity)
    assert summary["pass"] is True
    assert summary["n_triads"] == 20
    assert summary["n_candidates"] == 60
    assert len(summary["eligible_triad_ids"]) == 20
    assert len(summary["eligible_candidate_ids"]) == 60
    assert summary["eligible_counts"] == {"development": 12, "heldout": 8}
    assert summary["both_judges_candidate_pass_rate"] == 1.0
    assert summary["interjudge_candidate_pass_rate"] == 1.0
    assert summary["judge_visible_fields"] == ["sample_id", "message"]
    assert summary["intended_metadata_supplied_to_judges"] is False
    assert summary["metadata_joined_after_both_judge_calls"] is True
    assert summary["intended_metadata_fields"] == [
        "intended_frame",
        "triad_id",
        "split",
    ]


@pytest.mark.parametrize(
    "field",
    [
        "grammar",
        "clarity",
        "generic_applicability",
        "persuasive_strength",
        "overall_quality",
    ],
)
def test_each_frozen_candidate_minimum_is_required_for_triad_eligibility(field):
    pool = _pool()
    primary = _perfect_results(pool, "judge-a")
    sensitivity = _perfect_results(pool, "judge-b")
    message = quality_candidate_rows(pool)[0]["message"]
    primary[message][field] = (
        CONTROLLED_V6_QUALITY_THRESHOLDS["minimum_candidate_%s" % field] - 0.01
    )
    summary = _evaluate(pool, primary, sensitivity)
    assert summary["pass"] is True
    assert summary["gates"]["interjudge_candidate_pass_rate"] is True
    candidate = next(
        row for row in summary["candidate_results"] if row["message"] == message
    )
    assert candidate["primary_checks"][field] is False
    assert candidate["passes_both_judges"] is False
    assert candidate["triad_eligible"] is False


def test_quality_gate_rejects_result_sample_id_that_does_not_match_message():
    pool = _pool()
    primary = _perfect_results(pool, "judge-a")
    sensitivity = _perfect_results(pool, "judge-b")
    primary[next(iter(primary))]["sample_id"] = "q_wrong"
    with pytest.raises(ValueError, match="sample id does not match"):
        _evaluate(pool, primary, sensitivity)


def test_within_triad_gap_accepts_exact_boundary_and_rejects_above_it():
    pool = _pool()
    rows = quality_candidate_rows(pool)
    triad_id = rows[0]["triad_id"]
    messages = [row["message"] for row in rows if row["triad_id"] == triad_id]

    primary = _perfect_results(pool, "judge-a")
    sensitivity = _perfect_results(pool, "judge-b")
    for message, value in zip(messages, (0.75, 0.85, 0.95)):
        primary[message]["overall_quality"] = value
    boundary = _evaluate(pool, primary, sensitivity)
    triad = next(
        row for row in boundary["triad_results"] if row["triad_id"] == triad_id
    )
    assert boundary["pass"] is True
    assert triad["primary_gap_pass"] is True
    assert triad["primary_overall_quality_gap"] == pytest.approx(0.20)

    sensitivity[messages[-1]]["overall_quality"] = 0.951
    sensitivity[messages[0]]["overall_quality"] = 0.75
    above = _evaluate(pool, primary, sensitivity)
    triad = next(row for row in above["triad_results"] if row["triad_id"] == triad_id)
    assert above["pass"] is True
    assert above["eligible_counts"]["development"] == 11
    assert triad["sensitivity_gap_pass"] is False
    assert triad["sensitivity_overall_quality_gap"] == pytest.approx(0.201)


def test_quality_gate_requires_broad_candidate_quality_and_enough_complete_triads():
    pool = _pool()
    rows = quality_candidate_rows(pool)
    primary = _perfect_results(pool, "judge-a")
    sensitivity = _perfect_results(pool, "judge-b")

    # One failed member in seven distinct development triads leaves only five
    # complete development triads, while the broad 53/60 pass rate still holds.
    damaged = []
    seen = set()
    for row in rows:
        if row["split"] == "development" and row["triad_id"] not in seen:
            damaged.append(row["message"])
            seen.add(row["triad_id"])
        if len(damaged) == 7:
            break
    for message in damaged:
        primary[message]["clarity"] = 0.0
    insufficient = _evaluate(pool, primary, sensitivity)
    assert insufficient["pass"] is False
    assert insufficient["gates"]["interjudge_candidate_pass_rate"] is True
    assert insufficient["gates"]["enough_development_triads"] is False

    # Thirteen failures take the joint pass rate below the frozen 0.80 floor.
    primary = _perfect_results(pool, "judge-a")
    for row in rows[:13]:
        primary[row["message"]]["clarity"] = 0.0
    broad_failure = _evaluate(pool, primary, sensitivity)
    assert broad_failure["pass"] is False
    assert broad_failure["gates"]["interjudge_candidate_pass_rate"] is False


def test_quality_gate_fails_same_model_or_failed_artifact_audit():
    pool = _pool()
    primary = _perfect_results(pool, "same")
    sensitivity = _perfect_results(pool, "same")
    summary = _evaluate(
        pool,
        primary,
        sensitivity,
        primary_description=_description("same"),
        sensitivity_description=_description("same"),
        sensitivity_artifact_audit={"ok": False},
    )
    assert summary["pass"] is False
    assert summary["gates"]["judge_models_distinct"] is False
    assert summary["gates"]["both_artifact_audits_pass"] is False


def test_quality_gate_rejects_self_consistent_artifacts_with_different_results():
    pool = _pool()
    primary = _perfect_results(pool, "judge-a")
    sensitivity = _perfect_results(pool, "judge-b")
    forged = canonical_quality_result_map(primary)
    message = next(iter(forged))
    forged[message]["clarity"] = 0.0
    forged_audit = {
        "ok": True,
        "result_map": forged,
        "result_map_sha256": canonical_json_sha256(forged),
    }

    summary = _evaluate(
        pool,
        primary,
        sensitivity,
        primary_artifact_audit=forged_audit,
    )

    assert summary["pass"] is False
    assert summary["gates"]["both_artifact_audits_pass"] is True
    assert summary["gates"]["primary_artifact_results_match_evaluator"] is False


def test_quality_gate_requires_exact_message_coverage():
    pool = _pool()
    primary = _perfect_results(pool, "judge-a")
    sensitivity = _perfect_results(pool, "judge-b")
    primary.pop(next(iter(primary)))
    with pytest.raises(ValueError, match="exactly cover"):
        _evaluate(pool, primary, sensitivity)


def _load_cli_module(monkeypatch):
    script = ROOT / "scripts" / "validate_v6_quality_bank.py"
    monkeypatch.syspath_prepend(str(script.parent))
    spec = importlib.util.spec_from_file_location(
        "validate_v6_quality_bank_test", script
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_cli_defaults_and_full_flow_use_fake_message_only_judges(
    tmp_path, monkeypatch, capsys
):
    cli = _load_cli_module(monkeypatch)
    monkeypatch.setattr(cli, "ROOT", str(tmp_path))
    defaults = cli.build_parser().parse_args([])
    assert defaults.primary_model == "gpt-5.6-sol"
    assert defaults.sensitivity_model == "gpt-5.6-luna"
    assert defaults.judge_contract == "docs/v6_calibration_protocol.json"

    calls = []

    class FakeJudge:
        def __init__(self, model):
            self.model = model

        def describe(self):
            return _description(self.model)

    def fake_run_judge(
        messages,
        model,
        cache,
        artifacts,
        batch_size,
        seed,
        executable,
        timeout,
        official_contract,
    ):
        messages = list(messages)
        calls.append((model, messages))
        assert len(messages) == 60
        assert all(isinstance(message, str) for message in messages)
        return (
            FakeJudge(model),
            (results := {
                message: _result(make_quality_sample(message, model).sample_id)
                for message in messages
            }),
            _artifact_audit(results, model),
        )

    monkeypatch.setattr(cli, "_run_judge", fake_run_judge)
    out_dir = tmp_path / "out"
    cache_dir = tmp_path / "cache"
    bank_path, contract_path, _ = _official_quality_fixture(
        cli, tmp_path, monkeypatch
    )
    exit_code = cli.main(
        [
            "--bank",
            str(bank_path),
            "--judge-contract",
            str(contract_path),
            "--out-dir",
            str(out_dir),
            "--cache-dir",
            str(cache_dir),
        ]
    )
    assert exit_code == 0
    assert [model for model, _ in calls] == ["gpt-5.6-sol", "gpt-5.6-luna"]
    summary = json.loads((out_dir / "summary.json").read_text())
    assert summary["pass"] is True
    assert summary["primary_judge"]["model"] == "gpt-5.6-sol"
    assert summary["sensitivity_judge"]["model"] == "gpt-5.6-luna"
    assert summary["pool_source_file_sha256"]
    assert summary["judge_contract"]["enforced"] is True
    assert "PASS" in capsys.readouterr().out
    repeated_args = [
        "--bank",
        str(bank_path),
        "--judge-contract",
        str(contract_path),
        "--out-dir",
        str(out_dir),
        "--cache-dir",
        str(cache_dir),
    ]
    assert cli.main(repeated_args) == 0
    assert len(calls) == 4
    assert "verified existing" in capsys.readouterr().out

    tampered = json.loads((out_dir / "summary.json").read_text())
    tampered["pass"] = False
    (out_dir / "summary.json").write_text(
        json.dumps(tampered), encoding="utf-8"
    )
    with pytest.raises(ValueError, match="differs from recomputation"):
        cli.main(repeated_args)


def test_quality_cli_frozen_judge_contract_is_enforced_before_calls(
    tmp_path, monkeypatch
):
    cli = _load_cli_module(monkeypatch)
    monkeypatch.setattr(cli, "ROOT", str(tmp_path))
    bank_path, contract_path, contract = _official_quality_fixture(
        cli, tmp_path, monkeypatch
    )
    contract["quality_validation"]["judge_contract"][
        "prompt_sha256"
    ] = "f" * 64
    contract_path.write_text(json.dumps(contract), encoding="utf-8")
    called = False

    def must_not_run(*args, **kwargs):
        nonlocal called
        called = True
        raise AssertionError("judge must not run for a mismatched contract")

    monkeypatch.setattr(cli, "_run_judge", must_not_run)
    with pytest.raises(ValueError, match="mismatch for prompt_sha256"):
        cli.main(
            [
                "--bank",
                str(bank_path),
                "--judge-contract",
                str(contract_path),
                "--out-dir",
                str(tmp_path / "out"),
                "--cache-dir",
                str(tmp_path / "cache"),
            ]
        )
    assert called is False


def test_quality_cli_complete_run_lock_blocks_concurrent_dispatch(
    tmp_path, monkeypatch
):
    cli = _load_cli_module(monkeypatch)
    monkeypatch.setattr(cli, "ROOT", str(tmp_path))
    out_dir = tmp_path / "out"
    cache_dir = tmp_path / "cache"
    out_dir.mkdir()
    bank_path, contract_path, _ = _official_quality_fixture(
        cli, tmp_path, monkeypatch
    )
    called = False

    def must_not_run(*args, **kwargs):
        nonlocal called
        called = True
        raise AssertionError("concurrent quality validator dispatched a batch")

    monkeypatch.setattr(cli, "_run_judge", must_not_run)
    lock_path = out_dir / ".quality-validation.lock"
    with cli.ExclusiveFileLock(str(lock_path), label="quality test holder"):
        with pytest.raises(RuntimeError, match="another process holds"):
            cli.main(
                [
                    "--bank",
                        str(bank_path),
                    "--judge-contract",
                    str(contract_path),
                    "--out-dir",
                    str(out_dir),
                    "--cache-dir",
                    str(cache_dir),
                ]
            )
    assert called is False


def test_quality_cli_rejects_alternate_cache_directory_before_calls(
    tmp_path, monkeypatch
):
    cli = _load_cli_module(monkeypatch)
    monkeypatch.setattr(cli, "ROOT", str(tmp_path))
    bank_path, contract_path, _ = _official_quality_fixture(
        cli,
        tmp_path,
        monkeypatch,
        out_dir="official-out",
        cache_dir="official-cache",
    )
    called = False

    def must_not_run(*args, **kwargs):
        nonlocal called
        called = True
        raise AssertionError("alternate directory must fail before judging")

    monkeypatch.setattr(cli, "_run_judge", must_not_run)
    with pytest.raises(ValueError, match="canonical_cache_dir"):
        cli.main(
            [
                "--bank",
                str(bank_path),
                "--judge-contract",
                str(contract_path),
                "--out-dir",
                str(tmp_path / "official-out"),
                "--cache-dir",
                str(tmp_path / "alternate-cache"),
            ]
        )
    assert called is False


def _write_frozen_quality_run(
    root: Path,
    messages,
    *,
    model="judge-a",
    batch_size=2,
    seed=31,
    repository_root=None,
    executable="codex",
    official_contract=None,
):
    artifacts = root / "artifacts"
    cache = root / "cache.jsonl"
    plan = build_quality_batch_plan(messages, model, batch_size, seed)
    context_by_ids = {
        tuple(row["sample_ids"]): row for row in plan
    }

    def bound_runner(samples, selected_model, executable, artifact_dir, timeout_s):
        context = context_by_ids[tuple(sample.sample_id for sample in samples)]

        def fake_process(command, **kwargs):
            final_path = Path(command[command.index("--output-last-message") + 1])
            final_path.write_text(
                json.dumps(
                    {
                        "assessments": [
                            _result(sample.sample_id) for sample in samples
                        ]
                    }
                ),
                encoding="utf-8",
            )
            return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

        return run_quality_codex_batch(
            samples,
            selected_model,
            executable,
            artifact_dir,
            timeout_s,
            process_runner=fake_process,
            batch_context=context,
            official_contract=official_contract,
        )

    judge = CodexQualityJudge(
        model=model,
        cache_path=str(cache),
        artifact_dir=str(artifacts),
        batch_size=batch_size,
        seed=seed,
        executable=executable,
        batch_runner=bound_runner,
        official_contract=official_contract,
    )
    judge.score_messages(messages)
    replay = audit_quality_judge_run(
        messages,
        model,
        batch_size,
        seed,
        str(artifacts),
        str(cache),
        repository_root=str(repository_root or root),
        official_contract=official_contract,
    )
    return judge, replay, artifacts, cache


def _write_recoverable_quality_batch(root, messages, model="judge-a", seed=31):
    artifacts = root / "artifacts"
    cache = root / "cache.jsonl"
    plan = build_quality_batch_plan(messages, model, len(messages), seed)
    row = plan[0]

    def fake_process(command, **kwargs):
        final_path = Path(command[command.index("--output-last-message") + 1])
        final_path.write_text(
            json.dumps(
                {
                    "assessments": [
                        _result(sample.sample_id) for sample in row["samples"]
                    ]
                }
            ),
            encoding="utf-8",
        )
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    run_quality_codex_batch(
        row["samples"],
        model,
        "codex",
        str(artifacts),
        30,
        process_runner=fake_process,
        batch_context=row,
    )
    return artifacts, cache, row


def test_quality_post_return_pre_journal_crash_recovers_without_dispatch(
    tmp_path, monkeypatch
):
    messages = ["one", "two"]
    model = "judge-a"
    row = build_quality_batch_plan(messages, model, 2, 31)[0]
    artifacts = tmp_path / "artifacts"
    calls = 0

    def fake_process(command, **kwargs):
        nonlocal calls
        calls += 1
        provider_path = Path(
            command[command.index("--output-last-message") + 1]
        )
        assert provider_path.parent == artifacts
        provider_path.write_text(
            json.dumps(
                {
                    "assessments": [
                        _result(sample.sample_id) for sample in row["samples"]
                    ]
                }
            ),
            encoding="utf-8",
        )
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    original_atomic_write = blind_judge_module._atomic_write_json

    def crash_before_journal(path, payload):
        if str(path).endswith(".recovery.json"):
            raise OSError("simulated quality post-return journal crash")
        return original_atomic_write(path, payload)

    monkeypatch.setattr(
        blind_judge_module, "_atomic_write_json", crash_before_journal
    )
    with pytest.raises(OSError, match="post-return journal crash"):
        run_quality_codex_batch(
            row["samples"],
            model,
            "codex",
            str(artifacts),
            30,
            process_runner=fake_process,
            batch_context=row,
        )
    assert calls == 1
    assert list(artifacts.glob(".*.provider-claim.json"))
    assert list(artifacts.glob(".*.provider-output.json"))
    assert list(artifacts.glob(".*.provider-state.json"))

    monkeypatch.setattr(
        blind_judge_module, "_atomic_write_json", original_atomic_write
    )

    def must_not_dispatch(*args, **kwargs):
        raise AssertionError("a completed paid quality call was repeated")

    recovered = run_quality_codex_batch(
        row["samples"],
        model,
        "codex",
        str(artifacts),
        30,
        process_runner=must_not_dispatch,
        batch_context=row,
    )
    assert calls == 1
    assert set(recovered) == set(row["sample_ids"])


def test_quality_schema_valid_direct_output_recovers_without_state_or_call(
    tmp_path, monkeypatch
):
    messages = ["one", "two"]
    model = "judge-a"
    row = build_quality_batch_plan(messages, model, 2, 31)[0]
    artifacts = tmp_path / "artifacts"

    def fake_process(command, **kwargs):
        provider_path = Path(
            command[command.index("--output-last-message") + 1]
        )
        provider_path.write_text(
            json.dumps(
                {
                    "assessments": [
                        _result(sample.sample_id) for sample in row["samples"]
                    ]
                }
            ),
            encoding="utf-8",
        )
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    original_publish_state = quality_validation_module._publish_paid_batch_state

    def crash_before_state(*args, **kwargs):
        raise OSError("simulated quality state-publication crash")

    monkeypatch.setattr(
        quality_validation_module,
        "_publish_paid_batch_state",
        crash_before_state,
    )
    with pytest.raises(OSError, match="state-publication crash"):
        run_quality_codex_batch(
            row["samples"],
            model,
            "codex",
            str(artifacts),
            30,
            process_runner=fake_process,
            batch_context=row,
        )
    assert list(artifacts.glob(".*.provider-output.json"))
    assert not list(artifacts.glob(".*.provider-state.json"))

    monkeypatch.setattr(
        quality_validation_module,
        "_publish_paid_batch_state",
        original_publish_state,
    )

    def must_not_dispatch(*args, **kwargs):
        raise AssertionError("durable quality provider output was ignored")

    recovered = run_quality_codex_batch(
        row["samples"],
        model,
        "codex",
        str(artifacts),
        30,
        process_runner=must_not_dispatch,
        batch_context=row,
    )
    assert set(recovered) == set(row["sample_ids"])
    state = json.loads(
        next(artifacts.glob(".*.provider-state.json")).read_text(
            encoding="utf-8"
        )
    )
    assert state["status"] == "succeeded"
    assert state["recovered_from_durable_output"] is True


def test_quality_ambiguous_preexisting_claim_is_terminal_and_never_retried(
    tmp_path, monkeypatch
):
    row = build_quality_batch_plan(["one"], "judge-a", 1, 31)[0]
    artifacts = tmp_path / "artifacts"

    def uncertain_dispatch(command, **kwargs):
        assert list(artifacts.glob(".*.provider-claim.json"))
        raise OSError("uncertain quality transport failure")

    original_publish_state = quality_validation_module._publish_paid_batch_state

    def lose_failure_state(*args, **kwargs):
        raise OSError("simulated quality failure-state crash")

    monkeypatch.setattr(
        quality_validation_module,
        "_publish_paid_batch_state",
        lose_failure_state,
    )
    with pytest.raises(OSError, match="failure-state crash"):
        run_quality_codex_batch(
            row["samples"],
            "judge-a",
            "codex",
            str(artifacts),
            30,
            process_runner=uncertain_dispatch,
            batch_context=row,
        )
    monkeypatch.setattr(
        quality_validation_module,
        "_publish_paid_batch_state",
        original_publish_state,
    )

    def must_not_dispatch(*args, **kwargs):
        raise AssertionError("an ambiguous quality call was repeated")

    with pytest.raises(
        PaidBatchReconciliationError, match="terminal manual reconciliation"
    ):
        run_quality_codex_batch(
            row["samples"],
            "judge-a",
            "codex",
            str(artifacts),
            30,
            process_runner=must_not_dispatch,
            batch_context=row,
        )


def test_quality_cache_write_crash_recovers_without_repeating_paid_call(
    tmp_path, monkeypatch
):
    messages = ["one", "two", "three"]
    artifacts, cache, _ = _write_recoverable_quality_batch(tmp_path, messages)
    journal = next(artifacts.glob(".*.recovery.json"))
    original_atomic_write = quality_validation_module._atomic_write_jsonl

    def interrupted_cache_write(path, records):
        raise OSError("simulated quality cache publication interruption")

    monkeypatch.setattr(
        quality_validation_module,
        "_atomic_write_jsonl",
        interrupted_cache_write,
    )
    interrupted = CodexQualityJudge(
        model="judge-a",
        cache_path=str(cache),
        artifact_dir=str(artifacts),
        batch_size=3,
        seed=31,
        executable="must-not-be-called",
    )
    with pytest.raises(OSError, match="simulated"):
        interrupted.score_messages(messages)
    assert not cache.exists()
    assert journal.exists()

    monkeypatch.setattr(
        quality_validation_module, "_atomic_write_jsonl", original_atomic_write
    )
    resumed = CodexQualityJudge(
        model="judge-a",
        cache_path=str(cache),
        artifact_dir=str(artifacts),
        batch_size=3,
        seed=31,
        executable="must-not-be-called",
    )
    result = resumed.score_messages(messages)

    assert set(result) == set(messages)
    assert resumed.n_judged == 0
    assert resumed.n_cached == 3
    assert len(cache.read_text(encoding="utf-8").splitlines()) == 3
    assert journal.exists()
    assert audit_quality_judge_run(
        messages,
        "judge-a",
        3,
        31,
        str(artifacts),
        str(cache),
        repository_root=str(tmp_path),
    )["cache_reconciled"] is True


def test_quality_recovery_rebuilds_triplet_and_rejects_tampered_journal(
    tmp_path,
):
    messages = ["one", "two"]
    artifacts, cache, row = _write_recoverable_quality_batch(tmp_path, messages)
    meta_path = artifacts / row["meta_filename"]
    meta_path.unlink()

    judge = CodexQualityJudge(
        model="judge-a",
        cache_path=str(cache),
        artifact_dir=str(artifacts),
        batch_size=2,
        seed=31,
        executable="must-not-be-called",
    )
    judge.score_messages(messages)
    assert meta_path.exists()
    assert judge.n_judged == 0

    # Recreate the pre-cache state, alter the atomic journal, and verify that
    # recovery fails closed instead of silently making another judge call.
    artifacts, cache, _ = _write_recoverable_quality_batch(
        tmp_path / "tampered", messages
    )
    journal = next(artifacts.glob(".*.recovery.json"))
    payload = json.loads(journal.read_text(encoding="utf-8"))
    payload["output_text"] = "{}"
    journal.write_text(json.dumps(payload), encoding="utf-8")
    tampered = CodexQualityJudge(
        model="judge-a",
        cache_path=str(cache),
        artifact_dir=str(artifacts),
        batch_size=2,
        seed=31,
        executable="must-not-be-called",
    )
    with pytest.raises(ValueError, match="journal hash mismatch"):
        tampered.score_messages(messages)
    assert not cache.exists()


def test_quality_full_triplet_reconstructs_missing_cache_idempotently(tmp_path):
    messages = ["one", "two", "three", "four"]
    _, _, artifacts, cache = _write_frozen_quality_run(tmp_path, messages)
    cache.unlink()

    recovered = CodexQualityJudge(
        model="judge-a",
        cache_path=str(cache),
        artifact_dir=str(artifacts),
        batch_size=2,
        seed=31,
        executable="must-not-be-called",
    )
    recovered.score_messages(messages)
    first_bytes = cache.read_bytes()
    again = CodexQualityJudge(
        model="judge-a",
        cache_path=str(cache),
        artifact_dir=str(artifacts),
        batch_size=2,
        seed=31,
        executable="must-not-be-called",
    )
    again.score_messages(messages)

    assert recovered.n_judged == again.n_judged == 0
    assert cache.read_bytes() == first_bytes


def test_quality_legacy_partial_batch_cache_is_completed_from_triplet(tmp_path):
    messages = ["one", "two", "three", "four"]
    _, _, artifacts, cache = _write_frozen_quality_run(tmp_path, messages)
    records = cache.read_text(encoding="utf-8").splitlines()
    cache.write_text(records[0] + "\n", encoding="utf-8")

    recovered = CodexQualityJudge(
        model="judge-a",
        cache_path=str(cache),
        artifact_dir=str(artifacts),
        batch_size=2,
        seed=31,
        executable="must-not-be-called",
    )
    recovered.score_messages(messages)

    assert len(cache.read_text(encoding="utf-8").splitlines()) == 4
    assert recovered.n_judged == 0
    assert audit_quality_judge_run(
        messages,
        "judge-a",
        2,
        31,
        str(artifacts),
        str(cache),
        repository_root=str(tmp_path),
    )["cache_reconciled"] is True


def test_quality_triplet_tamper_fails_closed_before_cache_recovery(tmp_path):
    messages = ["one", "two"]
    _, _, artifacts, cache = _write_frozen_quality_run(tmp_path, messages)
    cache.unlink()
    output_path = next(artifacts.glob("*.output.json"))
    output_path.write_text("{}", encoding="utf-8")

    recovered = CodexQualityJudge(
        model="judge-a",
        cache_path=str(cache),
        artifact_dir=str(artifacts),
        batch_size=2,
        seed=31,
        executable="must-not-be-called",
    )
    with pytest.raises(
        ValueError, match="output hash mismatch|journal/triplet divergence"
    ):
        recovered.score_messages(messages)
    assert not cache.exists()


def test_frozen_quality_replay_rejects_different_partition_and_cache_divergence(
    tmp_path,
):
    messages = ["one", "two", "three", "four"]
    _, replay, artifacts, cache = _write_frozen_quality_run(tmp_path, messages)
    manifest = replay["judge_run_manifest"]
    assert manifest["artifact_dir"] == "artifacts"
    assert manifest["cache_path"] == "cache.jsonl"
    assert len(manifest["artifact_file_manifest"]) == 14

    with pytest.raises(ValueError, match="file set|frozen"):
        audit_quality_judge_run(
            messages,
            "judge-a",
            3,
            31,
            str(artifacts),
            str(cache),
            repository_root=str(tmp_path),
        )

    records = [json.loads(line) for line in cache.read_text().splitlines()]
    records[0]["artifact_binding"]["result_sha256"] = "f" * 64
    cache.write_text(
        "".join(json.dumps(record) + "\n" for record in records),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="cache/artifact binding divergence"):
        audit_quality_judge_run(
            messages,
            "judge-a",
            2,
            31,
            str(artifacts),
            str(cache),
            repository_root=str(tmp_path),
        )


def test_official_quality_identity_is_bound_through_manifest_and_replay(tmp_path):
    executable = tmp_path / "codex-quality-resolved"
    executable.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    executable.chmod(0o755)
    prompt = quality_judge_contract()
    official_without_hash = {
        "contract_version": "v6-official-codex-judge-contract-v1",
        "kind": "quality",
        "models": ["judge-a", "judge-b"],
        "seeds": [31, 32],
        "batch_size": 2,
        **prompt,
        "candidate_pool": {
            "path": "data/v6/pool.json",
            "file_sha256": "1" * 64,
            "canonical_sha256": "2" * 64,
        },
        "codex_runtime": {
            "codex_executable": "codex",
            "codex_cli_version": "codex-cli test",
            "codex_executable_sha256": hashlib.sha256(
                executable.read_bytes()
            ).hexdigest(),
        },
    }
    official = {
        **official_without_hash,
        "official_contract_sha256": canonical_json_sha256(
            official_without_hash
        ),
    }
    messages = ["one"]
    _, replay, artifacts, _ = _write_frozen_quality_run(
        tmp_path,
        messages,
        executable=str(executable),
        official_contract=official,
    )
    claim = json.loads(
        next(artifacts.glob(".*.provider-claim.json")).read_text(encoding="utf-8")
    )
    manifest = replay["judge_run_manifest"]
    assert claim["official_contract"] == official
    assert manifest["manifest_version"] == "v6-quality-judge-run-v2"
    assert replay_quality_judge_run_from_manifest(
        messages, manifest, str(tmp_path)
    )["judge_run_manifest"] == manifest

@pytest.mark.parametrize(
    "suffix",
    [
        ".provider-claim.json",
        ".provider-output.json",
        ".provider-state.json",
        ".recovery.json",
    ],
)
def test_strict_quality_replay_requires_each_hidden_evidence_file(
    tmp_path, suffix
):
    messages = ["one", "two"]
    _, _, artifacts, cache = _write_frozen_quality_run(tmp_path, messages)
    next(artifacts.glob(".*" + suffix)).unlink()

    with pytest.raises(ValueError, match="artifact file set.*missing"):
        audit_quality_judge_run(
            messages,
            "judge-a",
            2,
            31,
            str(artifacts),
            str(cache),
            repository_root=str(tmp_path),
        )


@pytest.mark.parametrize(
    "suffix",
    [
        ".input.json",
        ".output.json",
        ".meta.json",
        ".provider-claim.json",
        ".provider-output.json",
        ".provider-state.json",
        ".recovery.json",
    ],
)
@pytest.mark.parametrize("replacement", ["symlink", "fifo"])
def test_strict_quality_replay_descriptor_opens_all_seven_artifacts(
    tmp_path, suffix, replacement
):
    messages = ["alpha"]
    _, _, artifacts, cache = _write_frozen_quality_run(tmp_path, messages)
    target = next(
        path for path in artifacts.iterdir() if path.name.endswith(suffix)
    )
    original = target.read_bytes()
    target.unlink()
    if replacement == "symlink":
        backing = tmp_path / ("quality-backing" + suffix.replace("/", "_"))
        backing.write_bytes(original)
        target.symlink_to(backing)
    else:
        os.mkfifo(target)

    started = time.monotonic()
    with pytest.raises((ValueError, FileNotFoundError)):
        audit_quality_judge_run(
            messages,
            "judge-a",
            2,
            31,
            str(artifacts),
            str(cache),
            repository_root=str(tmp_path),
        )
    assert time.monotonic() - started < 1.0


def test_strict_quality_replay_rejects_tampered_direct_provider_output(
    tmp_path,
):
    messages = ["one", "two"]
    _, _, artifacts, cache = _write_frozen_quality_run(tmp_path, messages)
    provider_output = next(artifacts.glob(".*.provider-output.json"))
    provider_output.write_text(
        provider_output.read_text(encoding="utf-8") + " ",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="provider output (byte count|hash)"):
        audit_quality_judge_run(
            messages,
            "judge-a",
            2,
            31,
            str(artifacts),
            str(cache),
            repository_root=str(tmp_path),
        )


@pytest.mark.parametrize(
    ("pattern", "hash_field", "error"),
    [
        (".*.provider-claim.json", "claim_sha256", "provider claim hash"),
        (".*.recovery.json", "recovery_sha256", "recovery journal hash"),
    ],
)
def test_strict_quality_replay_parses_hidden_json_hashes(
    tmp_path, pattern, hash_field, error
):
    messages = ["one", "two"]
    _, _, artifacts, cache = _write_frozen_quality_run(tmp_path, messages)
    evidence_path = next(artifacts.glob(pattern))
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    evidence[hash_field] = "0" * 64
    evidence_path.write_text(json.dumps(evidence), encoding="utf-8")

    with pytest.raises(ValueError, match=error):
        audit_quality_judge_run(
            messages,
            "judge-a",
            2,
            31,
            str(artifacts),
            str(cache),
            repository_root=str(tmp_path),
        )


def test_strict_quality_replay_rejects_hash_valid_failed_provider_state(
    tmp_path,
):
    messages = ["one", "two"]
    _, _, artifacts, cache = _write_frozen_quality_run(tmp_path, messages)
    state_path = next(artifacts.glob(".*.provider-state.json"))
    state = json.loads(state_path.read_text(encoding="utf-8"))
    state["status"] = "failed"
    state["failure_kind"] = "schema_validation"
    state["state_sha256"] = canonical_json_sha256(
        {key: value for key, value in state.items() if key != "state_sha256"}
    )
    state_path.write_text(json.dumps(state), encoding="utf-8")

    batch_id = state_path.name[1 : -len(".provider-state.json")]
    meta_path = artifacts / (batch_id + ".meta.json")
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    meta["provider_state_sha256"] = state["state_sha256"]
    meta_path.write_text(json.dumps(meta), encoding="utf-8")
    recovery_path = artifacts / (".%s.recovery.json" % batch_id)
    recovery = json.loads(recovery_path.read_text(encoding="utf-8"))
    recovery["meta"] = meta
    recovery["recovery_sha256"] = canonical_json_sha256(
        {
            key: value
            for key, value in recovery.items()
            if key != "recovery_sha256"
        }
    )
    recovery_path.write_text(json.dumps(recovery), encoding="utf-8")

    with pytest.raises(ValueError, match="provider state is not successful"):
        audit_quality_judge_run(
            messages,
            "judge-a",
            2,
            31,
            str(artifacts),
            str(cache),
            repository_root=str(tmp_path),
        )


def test_strict_quality_replay_excludes_only_the_named_operational_lock(
    tmp_path,
):
    messages = ["one", "two"]
    _, before, artifacts, cache = _write_frozen_quality_run(tmp_path, messages)
    lock_path = artifacts / ".quality-validation.lock"
    lock_path.write_text("mutable lock owner metadata\n", encoding="utf-8")

    replay = audit_quality_judge_run(
        messages,
        "judge-a",
        2,
        31,
        str(artifacts),
        str(cache),
        repository_root=str(tmp_path),
    )
    assert replay["operational_exclusions"] == {
        "run_lock_filenames": [".quality-validation.lock"],
        "excluded_from_artifact_manifest": True,
    }
    assert all(
        row["path"] != "artifacts/.quality-validation.lock"
        for row in replay["artifact_file_manifest"]
    )
    assert replay["judge_run_manifest"] == before["judge_run_manifest"]

    (artifacts / ".unregistered.lock").write_text("extra", encoding="utf-8")
    with pytest.raises(ValueError, match="artifact file set.*extra"):
        audit_quality_judge_run(
            messages,
            "judge-a",
            2,
            31,
            str(artifacts),
            str(cache),
            repository_root=str(tmp_path),
        )


def test_quality_summary_audit_recomputes_raw_runs_and_rejects_forgery(tmp_path):
    bank = _pool()
    rows = quality_candidate_rows(bank)
    messages = [row["message"] for row in rows]
    primary_judge, primary, _, _ = _write_frozen_quality_run(
        tmp_path / "primary",
        messages,
        model="judge-a",
        batch_size=20,
        seed=201,
        repository_root=tmp_path,
    )
    sensitivity_judge, sensitivity, _, _ = _write_frozen_quality_run(
        tmp_path / "sensitivity",
        messages,
        model="judge-b",
        batch_size=20,
        seed=202,
        repository_root=tmp_path,
    )
    summary = evaluate_v6_quality_validation(
        bank,
        primary["result_map"],
        sensitivity["result_map"],
        primary_judge.describe(),
        sensitivity_judge.describe(),
        primary,
        sensitivity,
    )
    frozen_contract = {
        "models": ["judge-a", "judge-b"],
        "seeds": [201, 202],
        "batch_size": 20,
        **quality_judge_contract(),
    }
    summary["judge_contract"] = {
        **frozen_contract,
        "kind": "quality",
        "contract_sha256": canonical_json_sha256(frozen_contract),
        "enforced": True,
    }
    summary["raw_judge_run_manifests"] = {
        "primary": primary["judge_run_manifest"],
        "sensitivity": sensitivity["judge_run_manifest"],
    }
    evaluation = {
        key: value
        for key, value in summary.items()
        if key not in {"judge_contract", "raw_judge_run_manifests"}
    }
    summary["recomputed_evaluation_sha256"] = canonical_json_sha256(evaluation)

    replay = audit_v6_quality_validation_summary(summary, bank, str(tmp_path))
    assert replay["ok"] is True
    assert replay["pass"] is True

    forged = json.loads(json.dumps(summary))
    forged["gates"]["pool_schema_valid"] = False
    with pytest.raises(ValueError, match="raw-file recomputation"):
        audit_v6_quality_validation_summary(forged, bank, str(tmp_path))
