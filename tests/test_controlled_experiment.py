from __future__ import annotations

import dataclasses
import json
from copy import deepcopy

import pytest

import src.controlled_experiment as controlled_experiment
import src.logging_utils as logging_utils
from config import (
    CONTROLLED_CONDITIONS,
    ControlledExperimentConfig,
    ModelConfig,
    STRATEGIES,
)
from src.controlled_experiment import (
    CONTROLLED_REQUIRED_FIELDS,
    build_controlled_episode_specs,
    controlled_round_identity,
    run_controlled_experiment,
    validate_controlled_record,
)
from src.focal_agent import BaseProvider


def _config(tmp_path, conditions, provider="mock:v4_bayesian", n_seeds=1):
    return ControlledExperimentConfig(
        experiment_id="v4-test",
        n_rounds=8,
        swap_round=4,
        heldout_start_round=7,
        n_episode_seeds=n_seeds,
        seed=2026,
        conditions=list(conditions),
        model=ModelConfig(provider=provider, model="mock", max_tokens=16),
        out_dir=str(tmp_path),
    )


def test_v4_episode_specs_balance_types_and_all_ordered_swaps(tmp_path):
    stable = build_controlled_episode_specs(_config(tmp_path, ["full_history"], n_seeds=2))
    assert len(stable) == 2 * 3
    swaps = build_controlled_episode_specs(_config(tmp_path, ["swap"], n_seeds=2))
    assert len(swaps) == 2 * 6
    pairs = {(spec.initial_target_type, spec.final_target_type) for spec in swaps}
    assert pairs == {(a, b) for a in STRATEGIES for b in STRATEGIES if a != b}


def test_v4_shuffled_history_requires_prior_full_history(tmp_path):
    with pytest.raises(ValueError, match="requires full_history"):
        build_controlled_episode_specs(_config(tmp_path, ["shuffled_history"]))
    with pytest.raises(ValueError, match="precede"):
        build_controlled_episode_specs(
            _config(tmp_path, ["shuffled_history", "full_history"])
        )


def test_controlled_artifact_root_rejects_symlinked_output_before_writing(tmp_path):
    root = tmp_path / "root"
    outside = tmp_path / "outside"
    root.mkdir()
    outside.mkdir()
    linked_output = root / "linked-output"
    linked_output.symlink_to(outside, target_is_directory=True)
    cfg = _config(linked_output, ["full_history"])

    with pytest.raises(ValueError, match="symlinked"):
        run_controlled_experiment(
            cfg,
            run_id="must-not-escape",
            artifact_root=str(root),
        )

    assert list(outside.iterdir()) == []


def _matches_manifest_phase(payload, phase):
    if phase == "initial":
        return payload["run_status"] == "running" and payload["n_records"] == 0
    if phase == "progress":
        return payload["run_status"] == "running" and payload["n_records"] > 0
    return payload["run_status"] == "completed"


@pytest.mark.parametrize("phase", ["initial", "progress", "final"])
def test_controlled_manifest_rejects_symlinked_ancestor_at_each_publication(
    tmp_path, monkeypatch, phase
):
    root = tmp_path / "root"
    output = root / "output"
    detached = root / "detached-output"
    outside = tmp_path / "outside"
    output.mkdir(parents=True)
    outside.mkdir()
    cfg = _config(output, ["full_history"])
    real_write_manifest = controlled_experiment.write_manifest
    swapped = False

    def swap_before_manifest(path, payload, *, root=None):
        nonlocal swapped
        if not swapped and _matches_manifest_phase(payload, phase):
            output.rename(detached)
            output.symlink_to(outside, target_is_directory=True)
            swapped = True
        return real_write_manifest(path, payload, root=root)

    monkeypatch.setattr(
        controlled_experiment, "write_manifest", swap_before_manifest
    )
    with pytest.raises(ValueError, match="symlink"):
        run_controlled_experiment(
            cfg,
            run_id="symlink-%s" % phase,
            artifact_root=str(root),
        )

    assert swapped
    assert list(outside.iterdir()) == []


@pytest.mark.parametrize("phase", ["initial", "progress", "final"])
def test_controlled_manifest_retains_parent_during_each_ancestor_swap(
    tmp_path, monkeypatch, phase
):
    root = tmp_path / "root"
    output = root / "output"
    detached = root / "detached-output"
    outside = tmp_path / "outside"
    output.mkdir(parents=True)
    outside.mkdir()
    cfg = _config(output, ["full_history"])
    real_write_manifest = controlled_experiment.write_manifest
    real_replace = logging_utils.os.replace
    state = {"armed": False, "swapped": False}

    def swap_during_replace(source, destination, *args, **kwargs):
        if (
            state["armed"]
            and not state["swapped"]
            and kwargs.get("src_dir_fd") is not None
        ):
            output.rename(detached)
            output.symlink_to(outside, target_is_directory=True)
            state["swapped"] = True
        return real_replace(source, destination, *args, **kwargs)

    def arm_manifest_swap(path, payload, *, root=None):
        if _matches_manifest_phase(payload, phase):
            state["armed"] = True
        result = real_write_manifest(path, payload, root=root)
        if state["swapped"]:
            raise RuntimeError("stop after adversarial ancestor swap")
        return result

    monkeypatch.setattr(logging_utils.os, "replace", swap_during_replace)
    monkeypatch.setattr(
        controlled_experiment, "write_manifest", arm_manifest_swap
    )
    with pytest.raises(RuntimeError, match="adversarial ancestor swap"):
        run_controlled_experiment(
            cfg,
            run_id="swap-%s" % phase,
            artifact_root=str(root),
        )

    assert state["swapped"]
    assert list(outside.iterdir()) == []
    manifest = json.loads(
        (detached / ("swap-%s.manifest.json" % phase)).read_text(
            encoding="utf-8"
        )
    )
    assert _matches_manifest_phase(manifest, phase)


def test_round_claim_rejects_symlinked_ancestor_without_outside_write(
    tmp_path,
):
    root = tmp_path / "root"
    output = root / "output"
    outside = tmp_path / "outside"
    output.mkdir(parents=True)
    outside.mkdir()
    linked_claims = root / "linked-claims"
    linked_claims.symlink_to(outside, target_is_directory=True)

    with pytest.raises(ValueError, match="symlinked"):
        run_controlled_experiment(
            _config(output, ["full_history"]),
            run_id="claim-symlink",
            round_atomic=True,
            in_flight_path=str(linked_claims / "round.claim.json"),
            artifact_root=str(root),
        )

    assert list(outside.iterdir()) == []


def test_round_claim_retains_parent_during_ancestor_swap(tmp_path, monkeypatch):
    root = tmp_path / "root"
    output = root / "output"
    claims = root / "claims"
    detached_claims = root / "detached-claims"
    outside = tmp_path / "outside"
    output.mkdir(parents=True)
    claims.mkdir()
    outside.mkdir()
    claim_path = claims / "round.claim.json"
    real_link = logging_utils.os.link
    swapped = False

    def swap_during_link(source, destination, *args, **kwargs):
        nonlocal swapped
        if not swapped and kwargs.get("src_dir_fd") is not None:
            claims.rename(detached_claims)
            claims.symlink_to(outside, target_is_directory=True)
            swapped = True
        return real_link(source, destination, *args, **kwargs)

    monkeypatch.setattr(logging_utils.os, "link", swap_during_link)
    with pytest.raises(ValueError, match="symlink"):
        run_controlled_experiment(
            _config(output, ["full_history"]),
            run_id="claim-swap",
            provider=ContextBoundaryProvider(),
            round_atomic=True,
            in_flight_path=str(claim_path),
            artifact_root=str(root),
        )

    assert swapped
    assert (detached_claims / claim_path.name).is_file()
    assert list(outside.iterdir()) == []


def test_complete_v4_mock_run_has_schema_and_condition_semantics(tmp_path):
    cfg = _config(
        tmp_path,
        ["full_history", "no_history", "shuffled_history", "random_target", "swap",
         "elicited_full_history", "elicited_swap"],
    )
    result = run_controlled_experiment(cfg, run_id="complete")
    assert result.n_episodes == 27
    assert result.n_records == 27 * 8
    assert set(CONTROLLED_REQUIRED_FIELDS) <= set(result.records[0])
    for record in result.records:
        validate_controlled_record(record)

    no_history = [row for row in result.records if row["condition"] == "no_history"]
    assert all(row["visible_history"] == [] for row in no_history)
    assert all("Previous interactions" not in row["focal_user_prompt"] for row in no_history)

    random_rows = [row for row in result.records if row["condition"] == "random_target"]
    assert {row["target_p_a"] for row in random_rows} == {0.5}

    swap_rows = [row for row in result.records if row["condition"] == "swap"]
    assert all(
        row["hidden_target_type"]
        == (row["initial_target_type"] if row["round"] <= 4 else row["final_target_type"])
        for row in swap_rows
    )


def test_candidate_and_scenario_schedule_is_identical_across_conditions_and_types(tmp_path):
    cfg = _config(
        tmp_path,
        ["full_history", "no_history", "shuffled_history", "random_target", "swap"],
    )
    rows = run_controlled_experiment(cfg, run_id="schedule").records
    signatures = {}
    for row in rows:
        key = (row["episode_index"], row["round"])
        signature = (
            row["scenario_id"],
            tuple((candidate["slot"], candidate["candidate_id"], candidate["message"])
                  for candidate in row["candidates"]),
        )
        signatures.setdefault(key, signature)
        assert signatures[key] == signature


def test_v6_generation_rng_is_attached_to_physical_slot_not_condition(tmp_path):
    cfg = dataclasses.replace(
        _config(
            tmp_path,
            ["full_history", "no_history", "swap", "swap_control"],
        ),
        randomization_seed=20262006,
    )
    specs = build_controlled_episode_specs(cfg)
    full = next(
        spec
        for spec in specs
        if spec.condition.name == "full_history"
        and spec.initial_target_type == "fairness"
    )
    synthetic_control_same_slot = dataclasses.replace(
        full,
        condition=CONTROLLED_CONDITIONS["no_history"],
        assigned_regime="no_history",
    )
    full_identity = controlled_round_identity(
        full, cfg, "controlled-choice-v6.0", 5
    )
    control_identity = controlled_round_identity(
        synthetic_control_same_slot, cfg, "controlled-choice-v6.0", 5
    )
    assert full_identity[:2] == control_identity[:2]

    observed_control = next(
        spec
        for spec in specs
        if spec.condition.name == "no_history"
        and spec.initial_target_type == "fairness"
    )
    assert observed_control.pair_slot != full.pair_slot
    assert controlled_round_identity(
        observed_control, cfg, "controlled-choice-v6.0", 5
    )[0] != full_identity[0]


def test_v6_no_history_generates_once_then_reuses_exact_bytes(tmp_path):
    cfg = dataclasses.replace(
        _config(
            tmp_path,
            ["full_history", "no_history", "swap", "swap_control"],
        ),
        randomization_seed=20262006,
    )
    provider = ContextBoundaryProvider()
    result = run_controlled_experiment(
        cfg, run_id="v6-byte-reuse", provider=provider
    )
    saved_calls = (len(STRATEGIES) - 1) * cfg.n_rounds
    assert len(provider.prompts) == result.n_records - saved_calls
    groups = {}
    for row in result.records:
        group = row["replication_group_id"]
        if group is not None:
            groups.setdefault(group, []).append(row)
    assert len(groups) == cfg.n_rounds
    for rows in groups.values():
        assert len(rows) == len(STRATEGIES)
        assert len(
            {
                (
                    row["focal_system_prompt"],
                    row["focal_user_prompt"],
                    row["focal_output_raw"],
                )
                for row in rows
            }
        ) == 1


def test_shuffled_history_uses_different_target_donor(tmp_path):
    cfg = _config(tmp_path, ["full_history", "shuffled_history"])
    rows = run_controlled_experiment(cfg, run_id="donors").records
    shuffled = [row for row in rows if row["condition"] == "shuffled_history"]
    for row in shuffled:
        if row["round"] == 1:
            assert row["visible_history"] == []
        else:
            assert len(row["visible_history"]) == row["round"] - 1
        donor_type = row["history_source_episode_id"].rsplit("-", 1)[-1]
        assert donor_type != row["hidden_target_type"]


class ContextBoundaryProvider(BaseProvider):
    name = "context-boundary-spy"
    model = "spy"

    def __init__(self):
        self.contexts = []
        self.prompts = []

    def generate(self, prompt):
        self.contexts.append(prompt.context)
        self.prompts.append(prompt)
        return "1"


class FailAfterProvider(ContextBoundaryProvider):
    name = "fail-after"

    def __init__(self, fail_after):
        super().__init__()
        self.fail_after = fail_after

    def generate(self, prompt):
        if len(self.contexts) >= self.fail_after:
            raise RuntimeError("simulated provider interruption")
        return super().generate(prompt)


def test_real_provider_boundary_receives_no_mock_metadata(tmp_path):
    cfg = _config(tmp_path, ["full_history"])
    provider = ContextBoundaryProvider()
    run_controlled_experiment(cfg, run_id="boundary", provider=provider)
    assert provider.contexts
    assert all(context == {} for context in provider.contexts)


def test_logged_visible_history_omits_registered_frame_ground_truth(tmp_path):
    cfg = _config(tmp_path, ["full_history", "elicited_full_history"])
    rows = run_controlled_experiment(cfg, run_id="visible-boundary").records
    histories = [entry for row in rows for entry in row["visible_history"]]
    assert histories
    assert all("selected_frame" not in entry for entry in histories)
    spontaneous = [
        entry for row in rows if row["focal_mode"] == "spontaneous"
        for entry in row["visible_history"]
    ]
    assert all(set(entry) == {
        "round", "scenario_title", "selected_message", "choice"
    } for entry in spontaneous)
    elicited = [
        entry for row in rows if row["focal_mode"] == "elicited"
        for entry in row["visible_history"]
    ]
    assert all(set(entry) == {
        "round", "scenario_title", "selected_message", "choice",
        "predicted_p_a", "candidate_messages",
    } for entry in elicited)


def test_invalid_outputs_are_preserved_and_use_seeded_fallback(tmp_path):
    cfg = _config(tmp_path, ["full_history"], provider="mock:v4_invalid")
    rows = run_controlled_experiment(cfg, run_id="invalid").records
    assert all(row["focal_output_raw"] == "I recommend the second message." for row in rows)
    assert all(not row["selection_valid"] and row["fallback_used"] for row in rows)


def test_v4_run_is_reproducible_and_refuses_overwrite(tmp_path):
    cfg = _config(tmp_path, ["full_history", "no_history"])
    first = run_controlled_experiment(cfg, run_id="first")
    second = run_controlled_experiment(cfg, run_id="second")
    volatile = {"run_id", "timestamp"}
    for left, right in zip(first.records, second.records):
        assert {k: v for k, v in left.items() if k not in volatile} == {
            k: v for k, v in right.items() if k not in volatile
        }
    with pytest.raises(FileExistsError, match="overwrite"):
        run_controlled_experiment(cfg, run_id="first")


def test_v4_run_resumes_at_episode_boundary_without_duplicates(tmp_path):
    cfg = _config(tmp_path, ["full_history"])
    with pytest.raises(RuntimeError, match="interruption"):
        run_controlled_experiment(
            cfg, run_id="resumable", provider=FailAfterProvider(9)
        )
    from src.logging_utils import read_jsonl

    partial = list(read_jsonl(str(tmp_path / "resumable.jsonl")))
    assert len(partial) == 8  # one complete episode; the interrupted one was not appended
    resumed = run_controlled_experiment(
        cfg,
        run_id="resumable",
        provider=FailAfterProvider(1000),
        resume=True,
    )
    assert resumed.n_records == 3 * 8
    assert len({(row["episode_id"], row["round"]) for row in resumed.records}) == 3 * 8
    manifest = json.load(open(resumed.manifest_path, encoding="utf-8"))
    assert manifest["run_status"] == "completed"


def test_v4_resume_rejects_provider_setting_drift(tmp_path):
    cfg = _config(tmp_path, ["full_history"])
    with pytest.raises(RuntimeError, match="interruption"):
        run_controlled_experiment(
            cfg, run_id="provider-drift", provider=FailAfterProvider(9)
        )
    with pytest.raises(ValueError, match="provider settings"):
        run_controlled_experiment(
            cfg,
            run_id="provider-drift",
            provider=ContextBoundaryProvider(),
            resume=True,
        )


def test_v4_resume_rejects_message_bank_manifest_drift(tmp_path):
    cfg = _config(tmp_path, ["full_history"])
    with pytest.raises(RuntimeError, match="interruption"):
        run_controlled_experiment(
            cfg, run_id="bank-drift", provider=FailAfterProvider(9)
        )
    manifest_path = tmp_path / "bank-drift.manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["message_bank_sha256"] = "tampered"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    with pytest.raises(ValueError, match="message bank"):
        run_controlled_experiment(
            cfg,
            run_id="bank-drift",
            provider=FailAfterProvider(1000),
            resume=True,
        )


def test_controlled_record_validation_detects_selected_candidate_tampering(tmp_path):
    cfg = _config(tmp_path, ["full_history"])
    record = run_controlled_experiment(cfg, run_id="tamper").records[0]
    changed = dict(record, selected_message="not the registered message")
    with pytest.raises(ValueError, match="selected candidate"):
        validate_controlled_record(changed)


def test_v4_manifest_contains_exact_prompts_banks_and_revision(tmp_path):
    cfg = dataclasses.replace(
        _config(tmp_path, ["full_history"]),
        model=ModelConfig(
            provider="mock:v4_random", model="mock", revision="immutable-revision"
        ),
    )
    result = run_controlled_experiment(cfg, run_id="manifest")
    manifest = json.load(open(result.manifest_path, encoding="utf-8"))
    assert manifest["task_version"] == "controlled-choice-v4.0"
    assert manifest["config"]["model"]["revision"] == "immutable-revision"
    assert len(manifest["message_banks"]["development"]["fairness"]) == 10
    assert "spontaneous_system_rendered" in manifest["focal_prompt_templates"]
    assert manifest["message_bank_sha256"]


def test_controlled_record_rejects_json_type_coercions(tmp_path):
    cfg = _config(tmp_path, ["full_history"])
    base = run_controlled_experiment(cfg, run_id="strict-types").records[0]

    adversarial = []
    changed = deepcopy(base)
    changed["selected_slot"] = True
    adversarial.append(changed)
    changed = deepcopy(base)
    changed["candidates"][0]["slot"] = "1"
    adversarial.append(changed)
    changed = deepcopy(base)
    changed["visible_candidates"][0]["slot"] = True
    adversarial.append(changed)
    changed = deepcopy(base)
    changed["swap_condition"] = 0
    adversarial.append(changed)
    changed = deepcopy(base)
    changed["target_p_a"] = 1
    adversarial.append(changed)
    changed = deepcopy(base)
    changed["target_uniform_draw"] = str(base["target_uniform_draw"])
    adversarial.append(changed)
    changed = deepcopy(base)
    changed["round"] = True
    adversarial.append(changed)
    changed = deepcopy(base)
    changed["episode_index"] = "0"
    adversarial.append(changed)
    changed = deepcopy(base)
    changed["round_seed"] = True
    adversarial.append(changed)

    for record in adversarial:
        with pytest.raises(ValueError, match="JSON type"):
            validate_controlled_record(record)


@pytest.mark.parametrize(
    ("conditions", "crash_after"),
    [
        (["full_history"], 10),
        (["full_history", "shuffled_history"], 26),
    ],
)
def test_round_atomic_resume_reconstructs_partial_history_exactly(
    tmp_path, conditions, crash_after
):
    cfg = _config(tmp_path, conditions)
    claim_path = tmp_path / "round-prefix.inflight.json"
    calls = 0

    def interrupt_after_durable_row(_message):
        nonlocal calls
        calls += 1
        if calls == crash_after:
            raise RuntimeError("simulated post-row process death")

    with pytest.raises(RuntimeError, match="post-row process death"):
        run_controlled_experiment(
            cfg,
            run_id="round-prefix",
            provider=ContextBoundaryProvider(),
            progress=interrupt_after_durable_row,
            round_atomic=True,
            in_flight_path=str(claim_path),
        )
    from src.logging_utils import read_jsonl

    durable_prefix = list(read_jsonl(str(tmp_path / "round-prefix.jsonl")))
    assert len(durable_prefix) == crash_after
    assert not claim_path.exists()

    resumed_provider = ContextBoundaryProvider()
    resumed = run_controlled_experiment(
        cfg,
        run_id="round-prefix",
        provider=resumed_provider,
        resume=True,
        round_atomic=True,
        in_flight_path=str(claim_path),
    )
    baseline = run_controlled_experiment(
        dataclasses.replace(cfg, out_dir=str(tmp_path / "baseline")),
        run_id="baseline",
        provider=ContextBoundaryProvider(),
    )
    volatile = {"run_id", "timestamp"}
    assert [
        {key: value for key, value in row.items() if key not in volatile}
        for row in resumed.records
    ] == [
        {key: value for key, value in row.items() if key not in volatile}
        for row in baseline.records
    ]
    assert len(resumed_provider.prompts) == resumed.n_records - crash_after


def test_round_atomic_unlogged_provider_result_is_ambiguous(tmp_path, monkeypatch):
    cfg = _config(tmp_path, ["full_history"])
    claim_path = tmp_path / "ambiguous.inflight.json"
    real_write = controlled_experiment.JsonlWriter.write
    writes = 0

    def die_before_tenth_row(writer, record):
        nonlocal writes
        writes += 1
        if writes == 10:
            raise RuntimeError("simulated death before durable row")
        return real_write(writer, record)

    monkeypatch.setattr(
        controlled_experiment.JsonlWriter, "write", die_before_tenth_row
    )
    first_provider = ContextBoundaryProvider()
    with pytest.raises(RuntimeError, match="before durable row"):
        run_controlled_experiment(
            cfg,
            run_id="ambiguous",
            provider=first_provider,
            round_atomic=True,
            in_flight_path=str(claim_path),
        )
    assert len(first_provider.prompts) == 10
    assert claim_path.is_file()

    monkeypatch.setattr(controlled_experiment.JsonlWriter, "write", real_write)
    resumed_provider = ContextBoundaryProvider()
    with pytest.raises(RuntimeError, match="ambiguous in-flight paid generation"):
        run_controlled_experiment(
            cfg,
            run_id="ambiguous",
            provider=resumed_provider,
            resume=True,
            round_atomic=True,
            in_flight_path=str(claim_path),
        )
    assert resumed_provider.prompts == []


def test_round_atomic_logged_claim_is_recovered_without_duplicate_call(
    tmp_path, monkeypatch
):
    cfg = _config(tmp_path, ["full_history"])
    claim_path = tmp_path / "recoverable.inflight.json"
    real_clear = controlled_experiment._clear_round_claim
    clears = 0

    def die_after_tenth_row(path, claim, *, root=None):
        nonlocal clears
        clears += 1
        if clears == 10:
            raise RuntimeError("simulated death after durable row")
        return real_clear(path, claim, root=root)

    monkeypatch.setattr(controlled_experiment, "_clear_round_claim", die_after_tenth_row)
    with pytest.raises(RuntimeError, match="after durable row"):
        run_controlled_experiment(
            cfg,
            run_id="recoverable",
            provider=ContextBoundaryProvider(),
            round_atomic=True,
            in_flight_path=str(claim_path),
        )
    assert claim_path.is_file()

    monkeypatch.setattr(controlled_experiment, "_clear_round_claim", real_clear)
    resumed_provider = ContextBoundaryProvider()
    result = run_controlled_experiment(
        cfg,
        run_id="recoverable",
        provider=resumed_provider,
        resume=True,
        round_atomic=True,
        in_flight_path=str(claim_path),
    )
    assert result.n_records == 24
    assert len(resumed_provider.prompts) == 14
    assert not claim_path.exists()
