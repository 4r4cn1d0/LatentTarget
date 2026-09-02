"""Blind Codex-CLI judge contracts, validation, and resumability."""

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

from src.v6_semantic_validation import (
    audit_v6_semantic_validation_summary,
    evaluate_v6_semantic_validation,
    semantic_candidate_rows,
)
from src.blind_judge import (
    CODEX_JUDGE_RUBRIC,
    CodexBlindJudge,
    PaidBatchReconciliationError,
    attest_codex_executable,
    audit_codex_judge_run,
    audit_codex_artifacts,
    build_blind_batches,
    build_codex_batch_plan,
    build_codex_prompt,
    canonical_json_sha256,
    codex_judge_contract,
    codex_output_schema,
    enforce_frozen_judge_contract,
    load_frozen_judge_contract,
    make_sample,
    publish_exact_json,
    require_v6_judge_protocol_open,
    replay_codex_judge_run_from_manifest,
    run_codex_batch,
    sanitize_codex_meta,
    validate_codex_payload,
)


def test_terminal_v6_protocol_blocks_judge_dispatch():
    with pytest.raises(RuntimeError, match="does not authorize"):
        require_v6_judge_protocol_open(
            {"status": "STOP_V6_UNDERPOWERED_FINAL"}
        )
    with pytest.raises(RuntimeError, match="does not authorize"):
        require_v6_judge_protocol_open({})
    require_v6_judge_protocol_open(
        {
            "status": "READY_FOR_TARGET_FREE_JUDGES",
            "power_design": {
                "result": {
                    "status": "PASS_V6_PROSPECTIVE_BUNDLE_POWER",
                    "pass": True,
                    "selected_episode_seeds": 24,
                }
            },
        }
    )


def _result(sample_id, primary="other"):
    return {
        "sample_id": sample_id,
        "fairness": 1.0 if primary == "fairness" else 0.0,
        "risk": 1.0 if primary == "risk" else 0.0,
        "expertise": 1.0 if primary == "expertise" else 0.0,
        "other": 1.0 if primary == "other" else 0.0,
        "primary_strategy": primary,
        "confidence": 0.9,
    }


def test_blind_batches_are_deduplicated_seeded_and_metadata_free():
    messages = ["alpha", "beta", "alpha", "gamma"]
    first = build_blind_batches(messages, "judge", batch_size=2, seed=17)
    second = build_blind_batches(messages, "judge", batch_size=2, seed=17)
    assert [[s.sample_id for s in b] for b in first] == [[s.sample_id for s in b] for b in second]
    assert sum(len(batch) for batch in first) == 3
    prompt = build_codex_prompt(first[0])
    for sample in first[0]:
        assert sample.message in prompt
    for forbidden in ("hidden_target_type", "condition", "target_choice", "round_seed"):
        assert forbidden not in prompt


def test_judge_rubric_does_not_reference_experimental_answers():
    text = CODEX_JUDGE_RUBRIC.lower()
    for forbidden in ("hidden", "condition", "experiment", "target type", "correct strategy"):
        assert forbidden not in text


def test_output_schema_requires_one_row_per_expected_id():
    schema = codex_output_schema(["m_a", "m_b"])
    array = schema["properties"]["classifications"]
    assert array["minItems"] == array["maxItems"] == 2
    assert array["items"]["properties"]["sample_id"]["enum"] == ["m_a", "m_b"]


def test_payload_validation_accepts_complete_batch():
    payload = {"classifications": [_result("m_a", "fairness"), _result("m_b", "risk")]}
    out = validate_codex_payload(payload, ["m_a", "m_b"])
    assert out["m_a"]["primary_strategy"] == "fairness"
    assert out["m_b"]["risk"] == 1.0


@pytest.mark.parametrize(
    "payload,error",
    [
        ({"classifications": [_result("m_a")]}, "omitted"),
        ({"classifications": [_result("m_a"), _result("m_a")]}, "duplicate"),
        (
            {"classifications": [{**_result("m_a"), "risk": 1.5}, _result("m_b")]},
            "outside",
        ),
    ],
)
def test_payload_validation_fails_closed(payload, error):
    with pytest.raises(ValueError, match=error):
        validate_codex_payload(payload, ["m_a", "m_b"])


def test_codex_judge_caches_and_resumes_without_new_calls(tmp_path):
    calls = []

    def fake_runner(samples, model, executable, artifact_dir, timeout_s):
        calls.append([sample.sample_id for sample in samples])
        return {sample.sample_id: _result(sample.sample_id, "expertise") for sample in samples}

    cache = tmp_path / "cache.jsonl"
    judge = CodexBlindJudge(
        model="judge",
        cache_path=str(cache),
        artifact_dir=str(tmp_path / "batches"),
        batch_size=2,
        seed=4,
        batch_runner=fake_runner,
    )
    first = judge.classify_messages(["one", "two", "three", "one"])
    assert len(first) == 3
    assert judge.n_judged == 3
    assert len(calls) == 2

    def must_not_run(*args, **kwargs):
        raise AssertionError("cache was not used")

    resumed = CodexBlindJudge(
        model="judge",
        cache_path=str(cache),
        artifact_dir=str(tmp_path / "batches"),
        batch_size=2,
        seed=4,
        batch_runner=must_not_run,
    )
    second = resumed.classify_messages(["one", "two", "three", "one"])
    assert first == second
    assert resumed.n_cached == 3
    assert len(cache.read_text().strip().splitlines()) == 3
    for line in cache.read_text().splitlines():
        record = json.loads(line)
        assert record["prompt_version"] == "codex-blind-v1"
        assert record["message_sha256"]
        assert record["prompt_template_sha256"]
        assert record["rubric_sha256"]
        assert record["value_sha256"]


def test_artifact_audit_verifies_blind_keys_hashes_and_outputs(tmp_path):
    from src.blind_judge import _sha256, make_sample

    artifact_dir = tmp_path / "batches"
    artifact_dir.mkdir()
    sample = make_sample("Treat everyone equally.", "judge-model")
    batch_id = "batch_" + _sha256(sample.sample_id)[:16]
    prompt = build_codex_prompt([sample])
    output = json.dumps({"classifications": [_result(sample.sample_id, "fairness")]})
    (artifact_dir / (batch_id + ".input.json")).write_text(
        json.dumps(
            {
                "batch_id": batch_id,
                "model": "judge-model",
                "prompt_version": "codex-blind-v1",
                "samples": [sample.judge_dict()],
            }
        )
    )
    (artifact_dir / (batch_id + ".output.json")).write_text(output + "\n")
    (artifact_dir / (batch_id + ".meta.json")).write_text(
        json.dumps(
            {
                "returncode": 0,
                "sample_ids": [sample.sample_id],
                "prompt_sha256": _sha256(prompt),
                "output_sha256": _sha256(output),
                "process_logs_retained": False,
            }
        )
    )
    audit = audit_codex_artifacts(str(artifact_dir))
    assert audit["ok"] is True
    assert audit["sample_keys_visible_to_judge"] == ["message", "sample_id"]
    assert audit["metadata_fields_visible_to_judge"] == []
    assert audit["result_map"] == {
        sample.message: {
            "fairness": 1.0,
            "risk": 0.0,
            "expertise": 0.0,
            "other": 0.0,
            "primary_strategy": "fairness",
            "confidence": 0.9,
        }
    }
    assert audit["result_map_sha256"]
    assert audit["result_binding_map"][sample.message]["output_sha256"]


def test_artifact_audit_rejects_nonblind_sample_field(tmp_path):
    artifact_dir = tmp_path / "batches"
    artifact_dir.mkdir()
    (artifact_dir / "batch_bad.input.json").write_text(
        json.dumps(
            {
                "batch_id": "batch_bad",
                "model": "judge-model",
                "prompt_version": "codex-blind-v1",
                "samples": [
                    {"sample_id": "m_bad", "message": "hello", "condition": "full_history"}
                ],
            }
        )
    )
    (artifact_dir / "batch_bad.output.json").write_text("{}")
    (artifact_dir / "batch_bad.meta.json").write_text("{}")
    with pytest.raises(ValueError, match="non-blind fields"):
        audit_codex_artifacts(str(artifact_dir))


def test_metadata_sanitizer_removes_local_logs_and_paths():
    clean = sanitize_codex_meta(
        {
            "stdout": "result",
            "stderr": "session id: local-secret-like-id",
            "command_flags": ["--output-schema", "/tmp/judge/schema.json"],
        }
    )
    assert "stdout" not in clean and "stderr" not in clean
    assert clean["stdout_bytes"] == len("result")
    assert clean["stderr_sha256"]
    assert clean["command_flags"] == ["--output-schema", "<temporary>/schema.json"]
    assert clean["process_logs_retained"] is False


def test_exact_json_publication_is_atomic_idempotent_and_tamper_evident(
    tmp_path,
):
    path = tmp_path / "summary.json"
    payload = {"pass": True, "nested": {"count": 3}}

    assert publish_exact_json(str(path), payload) is True
    original = path.read_bytes()
    assert publish_exact_json(str(path), payload) is False
    assert path.read_bytes() == original
    assert not list(tmp_path.glob(".*.publish-*"))

    path.write_text(json.dumps({"pass": False}), encoding="utf-8")
    with pytest.raises(ValueError, match="differs from recomputation"):
        publish_exact_json(str(path), payload)


@pytest.mark.parametrize(
    "malformed",
    ['{"pass":true,"pass":false}', '{"pass":NaN}'],
)
def test_summary_publication_strict_load_rejects_duplicate_keys_and_nan(
    tmp_path, malformed
):
    path = tmp_path / "summary.json"
    path.write_text(malformed, encoding="utf-8")
    with pytest.raises(ValueError, match="unreadable"):
        publish_exact_json(str(path), {"pass": True})


def test_semantic_cli_summary_publication_is_idempotent_and_tamper_evident(
    tmp_path, monkeypatch, capsys
):
    repository_root = Path(__file__).parents[1]
    script = repository_root / "scripts" / "validate_v6_semantic_bank.py"
    monkeypatch.syspath_prepend(str(script.parent))
    spec = importlib.util.spec_from_file_location(
        "validate_v6_semantic_bank_recovery_test", script
    )
    assert spec is not None and spec.loader is not None
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)
    monkeypatch.setattr(cli, "ROOT", str(tmp_path))

    pool_path = repository_root / "data" / "v6" / "v6_triad_pool_v1.json"
    pool = json.loads(pool_path.read_text(encoding="utf-8"))
    labels = {
        row["message"]: row["intended_frame"]
        for row in semantic_candidate_rows(pool)
    }
    calls = []

    class FakeJudge:
        def __init__(self, model):
            self.model = model

        def describe(self):
            prompt = codex_judge_contract()
            return {
                "provider": "test",
                "model": self.model,
                "judge_prompt_version": prompt["prompt_version"],
                "judge_prompt_sha256": prompt["prompt_sha256"],
                "judge_rubric_sha256": prompt["rubric_sha256"],
            }

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
        calls.append(model)
        results = {
            message: _result(make_sample(message, model).sample_id, labels[message])
            for message in messages
        }
        public = {
            message: {
                key: value
                for key, value in result.items()
                if key != "sample_id"
            }
            for message, result in results.items()
        }
        prompt = codex_judge_contract()
        audit = {
            "ok": True,
            "frozen_schedule_enforced": True,
            "cache_reconciled": True,
            "judge_run_manifest": {"manifest_sha256": model},
            "models": [model],
            "prompt_version": prompt["prompt_version"],
            "prompt_sha256": prompt["prompt_sha256"],
            "rubric_sha256": prompt["rubric_sha256"],
            "result_map": public,
            "result_map_sha256": canonical_json_sha256(public),
        }
        return FakeJudge(model), results, audit

    monkeypatch.setattr(cli, "_run_judge", fake_run_judge)
    out_dir = tmp_path / "semantic-out"
    cache_dir = tmp_path / "semantic-cache"
    prompt = codex_judge_contract()
    copied_pool_path = tmp_path / "data" / "v6" / pool_path.name
    copied_pool_path.parent.mkdir(parents=True, exist_ok=True)
    copied_pool_path.write_bytes(pool_path.read_bytes())
    runtime = {
        "codex_executable": "codex",
        "codex_cli_version": "codex-cli test",
        "codex_executable_sha256": "c" * 64,
    }
    pool_contract = {
        "path": "data/v6/%s" % pool_path.name,
        "file_sha256": hashlib.sha256(copied_pool_path.read_bytes()).hexdigest(),
        "canonical_sha256": canonical_json_sha256(pool),
    }
    frozen = {
        "models": ["judge-a", "judge-b"],
        "seeds": [101, 102],
        "batch_size": 20,
        **prompt,
    }
    official = {
        "contract_version": "v6-official-codex-judge-contract-v1",
        "kind": "semantic",
        **frozen,
        "candidate_pool": pool_contract,
        "codex_runtime": runtime,
    }
    contract_path = tmp_path / "docs" / "v6_calibration_protocol.json"
    contract_path.parent.mkdir(parents=True, exist_ok=True)
    contract_path.write_text(
        json.dumps(
            {
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
                "judge_runtime": runtime,
                "semantic_validation": {
                    "canonical_out_dir": "semantic-out",
                    "canonical_cache_dir": "semantic-cache",
                    "judge_contract": {
                        **frozen,
                        "official_contract_sha256": canonical_json_sha256(
                            official
                        ),
                    },
                },
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        cli,
        "attest_codex_executable",
        lambda *_args, **_kwargs: {
            **runtime,
            "resolved_executable": "/test/codex",
        },
    )
    args = [
        "--bank",
        str(copied_pool_path),
        "--primary-model",
        "judge-a",
        "--sensitivity-model",
        "judge-b",
        "--primary-seed",
        "101",
        "--sensitivity-seed",
        "102",
        "--judge-contract",
        str(contract_path),
        "--out-dir",
        str(out_dir),
        "--cache-dir",
        str(cache_dir),
    ]

    assert cli.main(args) == 0
    first = (out_dir / "summary.json").read_bytes()
    assert cli.main(args) == 0
    assert (out_dir / "summary.json").read_bytes() == first
    assert calls == ["judge-a", "judge-b", "judge-a", "judge-b"]
    assert "verified existing" in capsys.readouterr().out

    tampered = json.loads((out_dir / "summary.json").read_text())
    tampered["pass"] = False
    (out_dir / "summary.json").write_text(
        json.dumps(tampered), encoding="utf-8"
    )
    with pytest.raises(ValueError, match="differs from recomputation"):
        cli.main(args)


def test_nested_frozen_judge_contract_accepts_exact_runtime_values():
    prompt = codex_judge_contract()
    payload = {
        "semantic_validation": {"status": "planned"},
        "judge_contracts": {
            "semantic": {
                "judge_models": ["judge-a", "judge-b"],
                "shuffle_seeds": [10, 11],
                "judge_batch_size": 4,
                "judge_prompt_version": prompt["prompt_version"],
                "judge_prompt_sha256": prompt["prompt_sha256"],
                "judge_rubric_sha256": prompt["rubric_sha256"],
            }
        },
    }
    result = enforce_frozen_judge_contract(
        json.dumps(payload),
        "semantic",
        {
            "primary_model": "judge-a",
            "sensitivity_model": "judge-b",
            "primary_seed": 10,
            "sensitivity_seed": 11,
            "batch_size": 4,
        },
        prompt,
    )

    assert result["enforced"] is True
    assert result["models"] == ["judge-a", "judge-b"]
    assert result["contract_sha256"]


@pytest.mark.parametrize(
    "malformed",
    ['{"models":[],"models":[]}', '{"models":NaN}'],
)
def test_judge_contract_strict_json_rejects_duplicate_keys_and_nan(malformed):
    with pytest.raises(ValueError):
        load_frozen_judge_contract(malformed)


def test_official_codex_attestation_rejects_fake_binary_hash_and_version(
    tmp_path, monkeypatch
):
    fake = tmp_path / "codex"
    fake.write_text("#!/bin/sh\necho 'codex-cli fake'\n", encoding="utf-8")
    fake.chmod(0o755)
    monkeypatch.setenv("PATH", str(tmp_path))
    fake_sha256 = hashlib.sha256(fake.read_bytes()).hexdigest()

    with pytest.raises(ValueError, match="SHA-256"):
        attest_codex_executable(
            "codex",
            {
                "codex_executable": "codex",
                "codex_cli_version": "codex-cli official",
                "codex_executable_sha256": "0" * 64,
            },
        )
    with pytest.raises(ValueError, match="--version differs"):
        attest_codex_executable(
            "codex",
            {
                "codex_executable": "codex",
                "codex_cli_version": "codex-cli official",
                "codex_executable_sha256": fake_sha256,
            },
        )


def test_official_codex_attestation_forbids_arbitrary_override():
    with pytest.raises(ValueError, match="forbids --codex-executable"):
        attest_codex_executable(
            "/tmp/fake-codex",
            {
                "codex_executable": "codex",
                "codex_cli_version": "codex-cli official",
                "codex_executable_sha256": "0" * 64,
            },
        )


def test_semantic_process_failure_never_exposes_raw_stderr(tmp_path):
    sample = make_sample("A private message.", "judge-a")
    secret = "SECRET_STDERR_PAYLOAD"

    def fake_process(command, **kwargs):
        return subprocess.CompletedProcess(command, 7, stdout="", stderr=secret)

    with pytest.raises(RuntimeError) as raised:
        run_codex_batch(
            [sample],
            "judge-a",
            "codex",
            str(tmp_path / "artifacts"),
            30,
            process_runner=fake_process,
        )

    assert secret not in str(raised.value)
    assert "stderr sha256" in str(raised.value)
    meta_path = next((tmp_path / "artifacts").glob("*.meta.json"))
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    assert "stderr" not in meta
    assert meta["stderr_sha256"]
    state = json.loads(
        next((tmp_path / "artifacts").glob(".*.provider-state.json")).read_text(
            encoding="utf-8"
        )
    )
    assert state["status"] == "failed"
    assert state["failure_kind"] == "nonzero_exit"


def test_semantic_cache_record_matches_audited_batch_binding(tmp_path):
    def fake_process(command, **kwargs):
        schema_path = Path(command[command.index("--output-schema") + 1])
        final_path = Path(command[command.index("--output-last-message") + 1])
        sample_ids = json.loads(schema_path.read_text(encoding="utf-8"))[
            "properties"
        ]["classifications"]["items"]["properties"]["sample_id"]["enum"]
        final_path.write_text(
            json.dumps(
                {"classifications": [_result(sample_id) for sample_id in sample_ids]}
            ),
            encoding="utf-8",
        )
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    def bound_runner(samples, model, executable, artifact_dir, timeout_s):
        return run_codex_batch(
            samples,
            model,
            executable,
            artifact_dir,
            timeout_s,
            process_runner=fake_process,
        )

    cache = tmp_path / "cache.jsonl"
    artifacts = tmp_path / "artifacts"
    judge = CodexBlindJudge(
        model="judge-a",
        cache_path=str(cache),
        artifact_dir=str(artifacts),
        batch_runner=bound_runner,
    )
    judge.classify_messages(["one"])
    record = json.loads(cache.read_text(encoding="utf-8"))
    audit = audit_codex_artifacts(str(artifacts))

    assert record["cache_record_version"] == 2
    assert record["artifact_binding"] == audit["result_binding_map"]["one"]


def test_semantic_cache_rejects_tampered_model_and_message_hash(tmp_path):
    cache = tmp_path / "cache.jsonl"
    sample = make_sample("one", "judge-a")
    record = {
        "key": sample.cache_key,
        "message_sha256": "0" * 64,
        "model": "judge-a",
        "prompt_version": "codex-blind-v1",
        "value": _result(sample.sample_id),
    }
    cache.write_text(json.dumps(record) + "\n", encoding="utf-8")
    judge = CodexBlindJudge(
        model="judge-a",
        cache_path=str(cache),
        artifact_dir=str(tmp_path / "artifacts"),
        batch_runner=lambda *args: {},
    )
    with pytest.raises(ValueError, match="message hash mismatch"):
        judge.classify_messages(["one"])

    record["model"] = "judge-b"
    cache.write_text(json.dumps(record) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="different judge model"):
        CodexBlindJudge(
            model="judge-a",
            cache_path=str(cache),
            artifact_dir=str(tmp_path / "artifacts"),
            batch_runner=lambda *args: {},
        )


def test_legacy_semantic_cache_record_remains_readable(tmp_path):
    cache = tmp_path / "legacy-cache.jsonl"
    sample = make_sample("one", "judge-a")
    cache.write_text(
        json.dumps(
            {
                "key": sample.cache_key,
                "message_sha256": hashlib.sha256(b"one").hexdigest(),
                "model": "judge-a",
                "prompt_version": "codex-blind-v1",
                "value": _result(sample.sample_id),
            }
        )
        + "\n",
        encoding="utf-8",
    )

    def must_not_run(*args, **kwargs):
        raise AssertionError("legacy cache was not used")

    judge = CodexBlindJudge(
        model="judge-a",
        cache_path=str(cache),
        artifact_dir=str(tmp_path / "artifacts"),
        batch_runner=must_not_run,
    )

    assert judge.classify_messages(["one"])["one"]["sample_id"] == sample.sample_id


@pytest.mark.parametrize(
    "malformed",
    [
        '{"key":"first","key":"second"}\n',
        '{"key":NaN}\n',
    ],
)
def test_semantic_cache_strict_jsonl_rejects_duplicate_keys_and_nan(
    tmp_path, malformed
):
    cache = tmp_path / "cache.jsonl"
    cache.write_text(malformed, encoding="utf-8")
    with pytest.raises(ValueError, match="invalid strict JSON"):
        CodexBlindJudge(
            model="judge-a",
            cache_path=str(cache),
            artifact_dir=str(tmp_path / "artifacts"),
            batch_runner=lambda *args: {},
        )


def _write_frozen_semantic_run(
    root: Path,
    messages,
    *,
    model="judge-a",
    batch_size=2,
    seed=17,
    labels=None,
    repository_root=None,
):
    artifacts = root / "artifacts"
    cache = root / "cache.jsonl"
    plan = build_codex_batch_plan(messages, model, batch_size, seed)
    context_by_ids = {
        tuple(row["sample_ids"]): row for row in plan
    }
    labels = labels or {}

    def bound_runner(samples, selected_model, executable, artifact_dir, timeout_s):
        context = context_by_ids[tuple(sample.sample_id for sample in samples)]

        def fake_process(command, **kwargs):
            final_path = Path(command[command.index("--output-last-message") + 1])
            final_path.write_text(
                json.dumps(
                    {
                        "classifications": [
                            _result(
                                sample.sample_id,
                                labels.get(sample.message, "other"),
                            )
                            for sample in samples
                        ]
                    }
                ),
                encoding="utf-8",
            )
            return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

        return run_codex_batch(
            samples,
            selected_model,
            executable,
            artifact_dir,
            timeout_s,
            process_runner=fake_process,
            batch_context=context,
        )

    judge = CodexBlindJudge(
        model=model,
        cache_path=str(cache),
        artifact_dir=str(artifacts),
        batch_size=batch_size,
        seed=seed,
        batch_runner=bound_runner,
    )
    judge.classify_messages(messages)
    replay = audit_codex_judge_run(
        messages,
        model,
        batch_size,
        seed,
        str(artifacts),
        str(cache),
        repository_root=str(repository_root or root),
    )
    return judge, replay, artifacts, cache


def _write_recoverable_semantic_batch(root, messages, model="judge-a", seed=17):
    artifacts = root / "artifacts"
    cache = root / "cache.jsonl"
    plan = build_codex_batch_plan(messages, model, len(messages), seed)
    row = plan[0]

    def fake_process(command, **kwargs):
        final_path = Path(command[command.index("--output-last-message") + 1])
        final_path.write_text(
            json.dumps(
                {
                    "classifications": [
                        _result(sample.sample_id, "risk")
                        for sample in row["samples"]
                    ]
                }
            ),
            encoding="utf-8",
        )
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    run_codex_batch(
        row["samples"],
        model,
        "codex",
        str(artifacts),
        30,
        process_runner=fake_process,
        batch_context=row,
    )
    return artifacts, cache, row


def test_semantic_post_return_pre_journal_crash_recovers_without_dispatch(
    tmp_path, monkeypatch
):
    messages = ["one", "two"]
    model = "judge-a"
    row = build_codex_batch_plan(messages, model, 2, 17)[0]
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
                    "classifications": [
                        _result(sample.sample_id, "risk")
                        for sample in row["samples"]
                    ]
                }
            ),
            encoding="utf-8",
        )
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    original_atomic_write = blind_judge_module._atomic_write_json

    def crash_before_journal(path, payload):
        if str(path).endswith(".recovery.json"):
            raise OSError("simulated post-return journal crash")
        return original_atomic_write(path, payload)

    monkeypatch.setattr(
        blind_judge_module, "_atomic_write_json", crash_before_journal
    )
    with pytest.raises(OSError, match="post-return journal crash"):
        run_codex_batch(
            row["samples"],
            model,
            "codex",
            str(artifacts),
            30,
            process_runner=fake_process,
            batch_context=row,
        )

    assert calls == 1
    assert len(list(artifacts.glob(".*.provider-claim.json"))) == 1
    assert len(list(artifacts.glob(".*.provider-output.json"))) == 1
    assert len(list(artifacts.glob(".*.provider-state.json"))) == 1
    assert not list(artifacts.glob("*.input.json"))

    monkeypatch.setattr(
        blind_judge_module, "_atomic_write_json", original_atomic_write
    )

    def must_not_dispatch(*args, **kwargs):
        raise AssertionError("a completed paid semantic call was repeated")

    recovered = run_codex_batch(
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
    assert next(artifacts.glob("*.meta.json")).exists()


def test_semantic_schema_valid_direct_output_recovers_without_state_or_call(
    tmp_path, monkeypatch
):
    messages = ["one", "two"]
    model = "judge-a"
    row = build_codex_batch_plan(messages, model, 2, 17)[0]
    artifacts = tmp_path / "artifacts"

    def fake_process(command, **kwargs):
        provider_path = Path(
            command[command.index("--output-last-message") + 1]
        )
        provider_path.write_text(
            json.dumps(
                {
                    "classifications": [
                        _result(sample.sample_id, "expertise")
                        for sample in row["samples"]
                    ]
                }
            ),
            encoding="utf-8",
        )
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    original_publish_state = blind_judge_module._publish_paid_batch_state

    def crash_before_state(*args, **kwargs):
        raise OSError("simulated state-publication crash")

    monkeypatch.setattr(
        blind_judge_module, "_publish_paid_batch_state", crash_before_state
    )
    with pytest.raises(OSError, match="state-publication crash"):
        run_codex_batch(
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
        blind_judge_module,
        "_publish_paid_batch_state",
        original_publish_state,
    )

    def must_not_dispatch(*args, **kwargs):
        raise AssertionError("durable semantic provider output was ignored")

    recovered = run_codex_batch(
        row["samples"],
        model,
        "codex",
        str(artifacts),
        30,
        process_runner=must_not_dispatch,
        batch_context=row,
    )
    assert {
        value["primary_strategy"] for value in recovered.values()
    } == {"expertise"}
    state = json.loads(
        next(artifacts.glob(".*.provider-state.json")).read_text(
            encoding="utf-8"
        )
    )
    assert state["status"] == "succeeded"
    assert state["recovered_from_durable_output"] is True


def test_semantic_ambiguous_preexisting_claim_is_terminal_and_never_retried(
    tmp_path, monkeypatch
):
    row = build_codex_batch_plan(["one"], "judge-a", 1, 17)[0]
    artifacts = tmp_path / "artifacts"

    def uncertain_dispatch(command, **kwargs):
        assert list(artifacts.glob(".*.provider-claim.json"))
        raise OSError("uncertain transport failure")

    original_publish_state = blind_judge_module._publish_paid_batch_state

    def lose_failure_state(*args, **kwargs):
        raise OSError("simulated failure-state crash")

    monkeypatch.setattr(
        blind_judge_module, "_publish_paid_batch_state", lose_failure_state
    )
    with pytest.raises(OSError, match="failure-state crash"):
        run_codex_batch(
            row["samples"],
            "judge-a",
            "codex",
            str(artifacts),
            30,
            process_runner=uncertain_dispatch,
            batch_context=row,
        )
    monkeypatch.setattr(
        blind_judge_module,
        "_publish_paid_batch_state",
        original_publish_state,
    )

    def must_not_dispatch(*args, **kwargs):
        raise AssertionError("an ambiguous semantic call was repeated")

    with pytest.raises(
        PaidBatchReconciliationError, match="terminal manual reconciliation"
    ):
        run_codex_batch(
            row["samples"],
            "judge-a",
            "codex",
            str(artifacts),
            30,
            process_runner=must_not_dispatch,
            batch_context=row,
        )


def test_semantic_cache_write_crash_recovers_without_repeating_paid_call(
    tmp_path, monkeypatch
):
    messages = ["one", "two", "three"]
    artifacts, cache, _ = _write_recoverable_semantic_batch(
        tmp_path, messages
    )
    journal = next(artifacts.glob(".*.recovery.json"))
    # Simulate interruption while publishing the whole-batch cache.  The old
    # cache remains absent and the atomic paid-result journal remains durable.
    original_atomic_write = blind_judge_module._atomic_write_jsonl

    def interrupted_cache_write(path, records):
        raise OSError("simulated cache publication interruption")

    monkeypatch.setattr(
        blind_judge_module, "_atomic_write_jsonl", interrupted_cache_write
    )
    interrupted = CodexBlindJudge(
        model="judge-a",
        cache_path=str(cache),
        artifact_dir=str(artifacts),
        batch_size=3,
        seed=17,
        executable="must-not-be-called",
    )
    with pytest.raises(OSError, match="simulated"):
        interrupted.classify_messages(messages)
    assert not cache.exists()
    assert journal.exists()

    monkeypatch.setattr(
        blind_judge_module, "_atomic_write_jsonl", original_atomic_write
    )
    resumed = CodexBlindJudge(
        model="judge-a",
        cache_path=str(cache),
        artifact_dir=str(artifacts),
        batch_size=3,
        seed=17,
        executable="must-not-be-called",
    )
    result = resumed.classify_messages(messages)

    assert set(result) == set(messages)
    assert {row["primary_strategy"] for row in result.values()} == {"risk"}
    assert resumed.n_judged == 0
    assert resumed.n_cached == 3
    assert len(cache.read_text(encoding="utf-8").splitlines()) == 3
    assert journal.exists()
    assert audit_codex_judge_run(
        messages,
        "judge-a",
        3,
        17,
        str(artifacts),
        str(cache),
        repository_root=str(tmp_path),
    )["cache_reconciled"] is True


def test_semantic_recovery_rebuilds_missing_triplet_file_from_atomic_journal(
    tmp_path,
):
    messages = ["one", "two"]
    artifacts, cache, row = _write_recoverable_semantic_batch(
        tmp_path, messages
    )
    meta_path = artifacts / row["meta_filename"]
    meta_path.unlink()

    judge = CodexBlindJudge(
        model="judge-a",
        cache_path=str(cache),
        artifact_dir=str(artifacts),
        batch_size=2,
        seed=17,
        executable="must-not-be-called",
    )
    judge.classify_messages(messages)

    assert meta_path.exists()
    assert judge.n_judged == 0
    assert list(artifacts.glob(".*.recovery.json"))


def test_semantic_recovery_rejects_tampered_journal_without_call_or_cache(
    tmp_path,
):
    messages = ["one", "two"]
    artifacts, cache, _ = _write_recoverable_semantic_batch(
        tmp_path, messages
    )
    journal = next(artifacts.glob(".*.recovery.json"))
    payload = json.loads(journal.read_text(encoding="utf-8"))
    payload["meta"]["output_sha256"] = "0" * 64
    journal.write_text(json.dumps(payload), encoding="utf-8")

    judge = CodexBlindJudge(
        model="judge-a",
        cache_path=str(cache),
        artifact_dir=str(artifacts),
        batch_size=2,
        seed=17,
        executable="must-not-be-called",
    )
    with pytest.raises(ValueError, match="journal hash mismatch"):
        judge.classify_messages(messages)
    assert not cache.exists()


def test_semantic_full_triplet_reconstructs_missing_cache_idempotently(tmp_path):
    messages = ["one", "two", "three", "four"]
    _, _, artifacts, cache = _write_frozen_semantic_run(tmp_path, messages)
    cache.unlink()

    recovered = CodexBlindJudge(
        model="judge-a",
        cache_path=str(cache),
        artifact_dir=str(artifacts),
        batch_size=2,
        seed=17,
        executable="must-not-be-called",
    )
    recovered.classify_messages(messages)
    first_bytes = cache.read_bytes()
    again = CodexBlindJudge(
        model="judge-a",
        cache_path=str(cache),
        artifact_dir=str(artifacts),
        batch_size=2,
        seed=17,
        executable="must-not-be-called",
    )
    again.classify_messages(messages)

    assert recovered.n_judged == again.n_judged == 0
    assert cache.read_bytes() == first_bytes


def test_semantic_legacy_partial_batch_cache_is_completed_from_triplet(tmp_path):
    messages = ["one", "two", "three", "four"]
    _, _, artifacts, cache = _write_frozen_semantic_run(tmp_path, messages)
    records = cache.read_text(encoding="utf-8").splitlines()
    cache.write_text(records[0] + "\n", encoding="utf-8")

    recovered = CodexBlindJudge(
        model="judge-a",
        cache_path=str(cache),
        artifact_dir=str(artifacts),
        batch_size=2,
        seed=17,
        executable="must-not-be-called",
    )
    recovered.classify_messages(messages)

    assert len(cache.read_text(encoding="utf-8").splitlines()) == 4
    assert recovered.n_judged == 0
    assert audit_codex_judge_run(
        messages,
        "judge-a",
        2,
        17,
        str(artifacts),
        str(cache),
        repository_root=str(tmp_path),
    )["cache_reconciled"] is True


def test_semantic_triplet_tamper_fails_closed_before_cache_recovery(tmp_path):
    messages = ["one", "two"]
    _, _, artifacts, cache = _write_frozen_semantic_run(tmp_path, messages)
    cache.unlink()
    output_path = next(artifacts.glob("*.output.json"))
    output_path.write_text("{}", encoding="utf-8")

    recovered = CodexBlindJudge(
        model="judge-a",
        cache_path=str(cache),
        artifact_dir=str(artifacts),
        batch_size=2,
        seed=17,
        executable="must-not-be-called",
    )
    with pytest.raises(
        ValueError, match="output hash mismatch|journal/triplet divergence"
    ):
        recovered.classify_messages(messages)
    assert not cache.exists()


def test_frozen_semantic_replay_binds_seed_partition_order_and_paths(tmp_path):
    messages = ["one", "two", "three", "four"]
    _, replay, _, _ = _write_frozen_semantic_run(tmp_path, messages)

    manifest = replay["judge_run_manifest"]
    assert manifest["frozen_schedule_enforced"] is True
    assert manifest["cache_reconciled"] is True
    assert manifest["artifact_dir"] == "artifacts"
    assert manifest["cache_path"] == "cache.jsonl"
    assert len(manifest["artifact_file_manifest"]) == 14
    assert {
        ".provider-claim.json",
        ".provider-output.json",
        ".provider-state.json",
        ".recovery.json",
    } == {
        next(
            suffix
            for suffix in (
                ".provider-claim.json",
                ".provider-output.json",
                ".provider-state.json",
                ".recovery.json",
            )
            if row["path"].endswith(suffix)
        )
        for row in manifest["artifact_file_manifest"]
        if row["path"].split("/")[-1].startswith(".")
    }
    assert all(not Path(row["path"]).is_absolute() for row in manifest["artifact_file_manifest"])

    with pytest.raises(ValueError, match="file set|frozen"):
        audit_codex_judge_run(
            messages,
            "judge-a",
            2,
            18,
            str(tmp_path / "artifacts"),
            str(tmp_path / "cache.jsonl"),
            repository_root=str(tmp_path),
        )


def test_official_identity_is_bound_through_claim_manifest_and_replay(tmp_path):
    messages = ["one"]
    model = "judge-a"
    seed = 17
    batch_size = 2
    executable = tmp_path / "codex-resolved"
    executable.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    executable.chmod(0o755)
    runtime = {
        "codex_executable": "codex",
        "codex_cli_version": "codex-cli test",
        "codex_executable_sha256": hashlib.sha256(
            executable.read_bytes()
        ).hexdigest(),
    }
    prompt = codex_judge_contract()
    official_without_hash = {
        "contract_version": "v6-official-codex-judge-contract-v1",
        "kind": "semantic",
        "models": [model, "judge-b"],
        "seeds": [seed, seed + 1],
        "batch_size": batch_size,
        **prompt,
        "candidate_pool": {
            "path": "data/v6/pool.json",
            "file_sha256": "d" * 64,
            "canonical_sha256": "e" * 64,
        },
        "codex_runtime": runtime,
    }
    official = {
        **official_without_hash,
        "official_contract_sha256": canonical_json_sha256(
            official_without_hash
        ),
    }
    artifacts = tmp_path / "artifacts"
    cache = tmp_path / "cache.jsonl"
    plan = build_codex_batch_plan(messages, model, batch_size, seed)

    def bound_runner(samples, selected_model, _token, artifact_dir, timeout_s):
        def fake_process(command, **kwargs):
            final_path = Path(command[command.index("--output-last-message") + 1])
            final_path.write_text(
                json.dumps(
                    {
                        "classifications": [
                            _result(sample.sample_id) for sample in samples
                        ]
                    }
                ),
                encoding="utf-8",
            )
            return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

        return run_codex_batch(
            samples,
            selected_model,
            str(executable),
            artifact_dir,
            timeout_s,
            process_runner=fake_process,
            batch_context=plan[0],
            official_contract=official,
        )

    judge = CodexBlindJudge(
        model=model,
        cache_path=str(cache),
        artifact_dir=str(artifacts),
        batch_size=batch_size,
        seed=seed,
        executable=str(executable),
        batch_runner=bound_runner,
        official_contract=official,
    )
    judge.classify_messages(messages)
    replay = audit_codex_judge_run(
        messages,
        model,
        batch_size,
        seed,
        str(artifacts),
        str(cache),
        repository_root=str(tmp_path),
        official_contract=official,
    )
    manifest = replay["judge_run_manifest"]
    claim = json.loads(
        next(artifacts.glob(".*.provider-claim.json")).read_text(encoding="utf-8")
    )
    assert claim["claim_version"] == "v6-paid-codex-claim-v2"
    assert claim["official_contract_sha256"] == official[
        "official_contract_sha256"
    ]
    assert manifest["manifest_version"] == "v6-semantic-judge-run-v2"
    assert manifest["official_contract"] == official
    assert replay_codex_judge_run_from_manifest(
        messages, manifest, str(tmp_path)
    )["judge_run_manifest"] == manifest


def test_frozen_semantic_replay_rejects_reordered_self_consistent_input(tmp_path):
    messages = ["one", "two", "three", "four"]
    _, _, artifacts, cache = _write_frozen_semantic_run(tmp_path, messages)
    input_path = next(artifacts.glob("*.input.json"))
    supplied = json.loads(input_path.read_text(encoding="utf-8"))
    supplied["samples"] = list(reversed(supplied["samples"]))
    input_path.write_text(json.dumps(supplied), encoding="utf-8")

    with pytest.raises(ValueError, match="frozen seed/batch schedule"):
        audit_codex_judge_run(
            messages,
            "judge-a",
            2,
            17,
            str(artifacts),
            str(cache),
            repository_root=str(tmp_path),
        )


@pytest.mark.parametrize("mutation", ["missing", "extra"])
def test_frozen_semantic_replay_rejects_missing_or_extra_artifact(
    tmp_path, mutation
):
    messages = ["one", "two", "three", "four"]
    _, _, artifacts, cache = _write_frozen_semantic_run(tmp_path, messages)
    if mutation == "missing":
        next(artifacts.glob("*.output.json")).unlink()
    else:
        (artifacts / "unregistered.json").write_text("{}", encoding="utf-8")

    with pytest.raises(ValueError, match="artifact file set"):
        audit_codex_judge_run(
            messages,
            "judge-a",
            2,
            17,
            str(artifacts),
            str(cache),
            repository_root=str(tmp_path),
        )


@pytest.mark.parametrize(
    "suffix",
    [
        ".provider-claim.json",
        ".provider-output.json",
        ".provider-state.json",
        ".recovery.json",
    ],
)
def test_strict_semantic_replay_requires_each_hidden_evidence_file(
    tmp_path, suffix
):
    messages = ["one", "two"]
    _, _, artifacts, cache = _write_frozen_semantic_run(tmp_path, messages)
    next(artifacts.glob(".*" + suffix)).unlink()

    with pytest.raises(ValueError, match="artifact file set.*missing"):
        audit_codex_judge_run(
            messages,
            "judge-a",
            2,
            17,
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
def test_strict_semantic_replay_descriptor_opens_all_seven_artifacts(
    tmp_path, suffix, replacement
):
    messages = ["alpha"]
    _, _, artifacts, cache = _write_frozen_semantic_run(tmp_path, messages)
    target = next(
        path for path in artifacts.iterdir() if path.name.endswith(suffix)
    )
    original = target.read_bytes()
    target.unlink()
    if replacement == "symlink":
        backing = tmp_path / ("backing" + suffix.replace("/", "_"))
        backing.write_bytes(original)
        target.symlink_to(backing)
    else:
        os.mkfifo(target)

    started = time.monotonic()
    with pytest.raises((ValueError, FileNotFoundError)):
        audit_codex_judge_run(
            messages,
            "judge-a",
            2,
            17,
            str(artifacts),
            str(cache),
            repository_root=str(tmp_path),
        )
    assert time.monotonic() - started < 1.0


def test_strict_semantic_replay_rejects_tampered_direct_provider_output(
    tmp_path,
):
    messages = ["one", "two"]
    _, _, artifacts, cache = _write_frozen_semantic_run(tmp_path, messages)
    provider_output = next(artifacts.glob(".*.provider-output.json"))
    provider_output.write_text(
        provider_output.read_text(encoding="utf-8") + " ",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="provider output (byte count|hash)"):
        audit_codex_judge_run(
            messages,
            "judge-a",
            2,
            17,
            str(artifacts),
            str(cache),
            repository_root=str(tmp_path),
        )


@pytest.mark.parametrize(
    "malformed",
    [
        '{"claim_version":"first","claim_version":"second"}',
        '{"claim_version":NaN}',
    ],
)
def test_strict_semantic_replay_rejects_non_strict_provider_claim(
    tmp_path, malformed
):
    messages = ["one"]
    _, _, artifacts, cache = _write_frozen_semantic_run(tmp_path, messages)
    claim = next(artifacts.glob(".*.provider-claim.json"))
    claim.write_text(malformed, encoding="utf-8")
    with pytest.raises(ValueError, match="provider claim is unreadable"):
        audit_codex_judge_run(
            messages,
            "judge-a",
            2,
            17,
            str(artifacts),
            str(cache),
            repository_root=str(tmp_path),
        )


@pytest.mark.parametrize(
    "malformed",
    [
        '{"classifications":[],"classifications":[]}',
        '{"classifications":NaN}',
    ],
)
def test_semantic_artifact_audit_strict_loads_raw_output(tmp_path, malformed):
    sample = make_sample("one", "judge-a")
    artifacts = tmp_path / "artifacts"

    def fake_process(command, **kwargs):
        final_path = Path(command[command.index("--output-last-message") + 1])
        final_path.write_text(
            json.dumps({"classifications": [_result(sample.sample_id)]}),
            encoding="utf-8",
        )
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    run_codex_batch(
        [sample],
        "judge-a",
        "codex",
        str(artifacts),
        30,
        process_runner=fake_process,
    )
    output_path = next(artifacts.glob("*.output.json"))
    meta_path = next(artifacts.glob("*.meta.json"))
    output_path.write_text(malformed, encoding="utf-8")
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    meta["output_sha256"] = hashlib.sha256(malformed.encode("utf-8")).hexdigest()
    meta_path.write_text(json.dumps(meta), encoding="utf-8")
    with pytest.raises(ValueError, match="invalid saved judge output"):
        audit_codex_artifacts(str(artifacts))


@pytest.mark.parametrize(
    ("pattern", "hash_field", "error"),
    [
        (".*.provider-claim.json", "claim_sha256", "provider claim hash"),
        (".*.recovery.json", "recovery_sha256", "recovery journal hash"),
    ],
)
def test_strict_semantic_replay_parses_hidden_json_hashes(
    tmp_path, pattern, hash_field, error
):
    messages = ["one", "two"]
    _, _, artifacts, cache = _write_frozen_semantic_run(tmp_path, messages)
    evidence_path = next(artifacts.glob(pattern))
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    evidence[hash_field] = "0" * 64
    evidence_path.write_text(json.dumps(evidence), encoding="utf-8")

    with pytest.raises(ValueError, match=error):
        audit_codex_judge_run(
            messages,
            "judge-a",
            2,
            17,
            str(artifacts),
            str(cache),
            repository_root=str(tmp_path),
        )


def test_strict_semantic_replay_rejects_hash_valid_failed_provider_state(
    tmp_path,
):
    messages = ["one", "two"]
    _, _, artifacts, cache = _write_frozen_semantic_run(tmp_path, messages)
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
        audit_codex_judge_run(
            messages,
            "judge-a",
            2,
            17,
            str(artifacts),
            str(cache),
            repository_root=str(tmp_path),
        )


def test_strict_semantic_replay_excludes_only_the_named_operational_lock(
    tmp_path,
):
    messages = ["one", "two"]
    _, before, artifacts, cache = _write_frozen_semantic_run(tmp_path, messages)
    lock_path = artifacts / ".semantic-validation.lock"
    lock_path.write_text("mutable lock owner metadata\n", encoding="utf-8")

    replay = audit_codex_judge_run(
        messages,
        "judge-a",
        2,
        17,
        str(artifacts),
        str(cache),
        repository_root=str(tmp_path),
    )
    assert replay["operational_exclusions"] == {
        "run_lock_filenames": [".semantic-validation.lock"],
        "excluded_from_artifact_manifest": True,
    }
    assert all(
        row["path"] != "artifacts/.semantic-validation.lock"
        for row in replay["artifact_file_manifest"]
    )
    assert replay["judge_run_manifest"] == before["judge_run_manifest"]

    (artifacts / ".unregistered.lock").write_text("extra", encoding="utf-8")
    with pytest.raises(ValueError, match="artifact file set.*extra"):
        audit_codex_judge_run(
            messages,
            "judge-a",
            2,
            17,
            str(artifacts),
            str(cache),
            repository_root=str(tmp_path),
        )


def test_frozen_semantic_replay_rejects_cache_artifact_divergence(tmp_path):
    messages = ["one", "two", "three", "four"]
    _, _, artifacts, cache = _write_frozen_semantic_run(tmp_path, messages)
    records = [json.loads(line) for line in cache.read_text().splitlines()]
    records[0]["artifact_binding"]["output_sha256"] = "0" * 64
    cache.write_text(
        "".join(json.dumps(record) + "\n" for record in records),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="cache/artifact binding divergence"):
        audit_codex_judge_run(
            messages,
            "judge-a",
            2,
            17,
            str(artifacts),
            str(cache),
            repository_root=str(tmp_path),
        )


def test_semantic_summary_audit_recomputes_raw_runs_and_rejects_forged_pass(
    tmp_path,
):
    pool_path = Path(__file__).parents[1] / "data" / "v6" / "v6_triad_pool_v1.json"
    pool = json.loads(pool_path.read_text(encoding="utf-8"))
    rows = semantic_candidate_rows(pool)
    messages = [row["message"] for row in rows]
    labels = {row["message"]: row["intended_frame"] for row in rows}
    primary_judge, primary, _, _ = _write_frozen_semantic_run(
        tmp_path / "primary",
        messages,
        model="judge-a",
        batch_size=20,
        seed=101,
        labels=labels,
        repository_root=tmp_path,
    )
    sensitivity_judge, sensitivity, _, _ = _write_frozen_semantic_run(
        tmp_path / "sensitivity",
        messages,
        model="judge-b",
        batch_size=20,
        seed=102,
        labels=labels,
        repository_root=tmp_path,
    )
    summary = evaluate_v6_semantic_validation(
        pool,
        primary["result_map"],
        sensitivity["result_map"],
        primary_judge.describe(),
        sensitivity_judge.describe(),
        primary,
        sensitivity,
    )
    prompt_contract = codex_judge_contract()
    frozen_contract = {
        "models": ["judge-a", "judge-b"],
        "seeds": [101, 102],
        "batch_size": 20,
        **prompt_contract,
    }
    summary["judge_contract"] = {
        **frozen_contract,
        "kind": "semantic",
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

    replay = audit_v6_semantic_validation_summary(summary, pool, str(tmp_path))
    assert replay["ok"] is True
    assert replay["pass"] is True

    forged = json.loads(json.dumps(summary))
    forged["pass"] = False
    with pytest.raises(ValueError, match="raw-file recomputation"):
        audit_v6_semantic_validation_summary(forged, pool, str(tmp_path))
