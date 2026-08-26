"""Blind Codex-CLI judge contracts, validation, and resumability."""

from __future__ import annotations

import json

import pytest

from src.blind_judge import (
    CODEX_JUDGE_RUBRIC,
    CodexBlindJudge,
    audit_codex_artifacts,
    build_blind_batches,
    build_codex_prompt,
    codex_output_schema,
    sanitize_codex_meta,
    validate_codex_payload,
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
        assert json.loads(line)["prompt_version"] == "codex-blind-v1"


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
