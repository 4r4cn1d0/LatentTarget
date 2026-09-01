"""V6 blind quality-judge contracts, gates, artifacts, and CLI behavior."""

from __future__ import annotations

import importlib.util
import json
import subprocess
from pathlib import Path

import pytest

from config import CONTROLLED_V6_QUALITY_THRESHOLDS
from src.v6_quality_validation import (
    CODEX_QUALITY_PROMPT_VERSION,
    QUALITY_ISSUE_CODES,
    QUALITY_SCORE_FIELDS,
    CodexQualityJudge,
    audit_quality_artifacts,
    build_quality_batches,
    build_quality_prompt,
    evaluate_v6_quality_validation,
    make_quality_sample,
    quality_candidate_rows,
    quality_output_schema,
    run_quality_codex_batch,
    validate_quality_payload,
)


ROOT = Path(__file__).parents[1]
POOL = ROOT / "data" / "v6" / "v6_triad_pool_v1.json"


def _pool():
    return json.loads(POOL.read_text(encoding="utf-8"))


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


def _evaluate(pool, primary, sensitivity, **kwargs):
    return evaluate_v6_quality_validation(
        pool,
        primary,
        sensitivity,
        kwargs.pop("primary_description", _description("judge-a")),
        kwargs.pop("sensitivity_description", _description("judge-b")),
        kwargs.pop("primary_artifact_audit", {"ok": True}),
        kwargs.pop("sensitivity_artifact_audit", {"ok": True}),
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
    defaults = cli.build_parser().parse_args([])
    assert defaults.primary_model == "gpt-5.6-sol"
    assert defaults.sensitivity_model == "gpt-5.6-luna"

    calls = []

    class FakeJudge:
        def __init__(self, model):
            self.model = model

        def describe(self):
            return _description(self.model)

    def fake_run_judge(
        messages, model, cache, artifacts, batch_size, seed, executable, timeout
    ):
        messages = list(messages)
        calls.append((model, messages))
        assert len(messages) == 60
        assert all(isinstance(message, str) for message in messages)
        return (
            FakeJudge(model),
            {
                message: _result(make_quality_sample(message, model).sample_id)
                for message in messages
            },
            {"ok": True, "models": [model]},
        )

    monkeypatch.setattr(cli, "_run_judge", fake_run_judge)
    out_dir = tmp_path / "out"
    cache_dir = tmp_path / "cache"
    exit_code = cli.main(
        [
            "--bank",
            str(POOL),
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
    assert "PASS" in capsys.readouterr().out
    with pytest.raises(FileExistsError, match="refusing to overwrite"):
        cli.main(
            [
                "--bank",
                str(POOL),
                "--out-dir",
                str(out_dir),
                "--cache-dir",
                str(cache_dir),
            ]
        )
