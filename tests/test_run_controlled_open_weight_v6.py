from __future__ import annotations

import json
import sys
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

import pytest


ROOT = Path(__file__).parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import preflight_controlled_v6 as preflight  # noqa: E402
import run_controlled_open_weight_v6 as runner  # noqa: E402
from config import (  # noqa: E402
    CONTROLLED_V6_RANDOMIZATION_SEED,
    CONTROLLED_V6_VERSION,
)
from src.controlled_protocol import ControlledProtocol  # noqa: E402
from src.controlled_v6_messages import (  # noqa: E402
    V6_SELECTED_BANK_STATUS,
    V6TriadBank,
)
from src.scenarios import v6_scenario_sequence  # noqa: E402
from src.v6_calibration import bank_content_sha256  # noqa: E402


SOURCE_POOL = ROOT / "data" / "v6" / "v6_triad_pool_v1.json"
RUN_ID = "synthetic-v6-official-run"
MODEL_ID = "synthetic/model"
REVISION = "0123456789abcdef0123456789abcdef01234567"


def _write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


@pytest.fixture
def frozen_contract(tmp_path, monkeypatch):
    bank_payload = json.loads(SOURCE_POOL.read_text(encoding="utf-8"))
    bank_payload["pool_id"] = "synthetic-v6-selected-bank"
    bank_payload["status"] = V6_SELECTED_BANK_STATUS
    bank_payload["splits"]["development"] = bank_payload["splits"][
        "development"
    ][:6]
    bank_payload["splits"]["heldout"] = bank_payload["splits"]["heldout"][:4]
    bank_path = tmp_path / "artifacts" / "validated-bank.json"
    _write_json(bank_path, bank_payload)
    bank = V6TriadBank.load(str(bank_path))

    conditions = [
        "full_history",
        "no_history",
        "shuffled_history",
        "random_target",
        "swap",
        "swap_control",
    ]
    protocol_spec = {
        "primary_model": {"id": MODEL_ID, "revision": REVISION},
        "generation": {
            "temperature": 0.0,
            "top_p": 0.8,
            "top_k": 20,
            "max_tokens": 2,
            "dtype": "bfloat16",
            "enable_thinking": False,
            "activation_capture": False,
            "constrained_choices": ["1", "2", "3"],
            "invalid_output_policy": "abort; no fallback",
        },
        "confirmatory_design": {
            "target": {"p_match": 0.72, "p_mismatch": 0.38, "p_random": 0.5}
        },
    }
    protocol_path = tmp_path / "artifacts" / "protocol.json"
    _write_json(protocol_path, protocol_spec)
    prevalidation = {
        "calibration_protocol": {"path": "artifacts/protocol.json"}
    }
    prevalidation_path = tmp_path / "artifacts" / "prevalidation.json"
    _write_json(prevalidation_path, prevalidation)
    schedule = {
        "scenario_set": "confirmatory",
        "official_run_id": RUN_ID,
        "master_seed": 20262004,
        "randomization_seed": CONTROLLED_V6_RANDOMIZATION_SEED,
        "n_rounds": 6,
        "swap_round": 3,
        "heldout_start_round": 5,
        "conditions": conditions,
        "canonical_out_dir": runner.CONFIRMATORY_PATHS["out_dir"],
        "launch_receipt_path": runner.CONFIRMATORY_PATHS["receipt"],
        "paid_preflight_report_path": runner.CONFIRMATORY_PATHS["preflight"],
        "paid_preflight_receipt_path": runner.CONFIRMATORY_PATHS[
            "preflight_receipt"
        ],
        "selected_episode_seeds": 1,
        "n_episodes_by_episode_seed_count": {"1": 24},
        "schedule_sha256_by_episode_seed_count": {"1": "synthetic-schedule"},
        "selected_schedule_sha256": "synthetic-schedule",
        "selected_randomization_schedule_sha256": "synthetic-allocation",
        "contract_sha256": "synthetic-contract",
    }
    checkpoint = {
        "prevalidation_checkpoint": {"path": "artifacts/prevalidation.json"},
        "validated_bank": {"path": "artifacts/validated-bank.json"},
        "confirmatory_schedule": schedule,
    }
    checkpoint_path = tmp_path / "artifacts" / "final-checkpoint.json"
    _write_json(checkpoint_path, checkpoint)
    audit = {
        "pass": True,
        "checks": {"synthetic_final_graph": True},
        "checkpoint_canonical_sha256": "synthetic-checkpoint-canonical",
        "validated_bank_sha256": bank.sha256(),
        "validated_bank_content_sha256": bank_content_sha256(bank.payload),
        "confirmatory_schedule": schedule,
    }
    events = []

    def fake_audit(payload, repository_root):
        events.append("checkpoint_audit")
        assert payload == checkpoint
        assert repository_root == str(tmp_path.resolve())
        return deepcopy(audit)

    def fake_make_protocol(
        supplied_bank_path,
        require_validated=False,
        manifest_metadata=None,
        final_checkpoint_path=None,
        checkpoint_root=None,
        confirmatory_run_id=None,
        confirmatory_episode_seeds=None,
    ):
        events.append("make_v6_protocol")
        assert Path(supplied_bank_path).resolve() == bank_path.resolve()
        assert require_validated is True
        assert Path(final_checkpoint_path).resolve() == checkpoint_path.resolve()
        assert checkpoint_root == str(tmp_path.resolve())
        assert confirmatory_run_id == RUN_ID
        assert confirmatory_episode_seeds == 1
        metadata = deepcopy(dict(manifest_metadata or {}))
        metadata["v6_final_checkpoint"] = {
            "artifact_audit": deepcopy(audit),
            "canonical_sha256": audit["checkpoint_canonical_sha256"],
        }
        loaded = V6TriadBank.load(str(bank_path))
        return ControlledProtocol(
            version=CONTROLLED_V6_VERSION,
            candidate_builder=loaded.candidate_set,
            bank_manifest_builder=loaded.manifest,
            bank_hash_builder=loaded.sha256,
            strict_selection=True,
            constrained_choices=("1", "2", "3"),
            bank_source=str(bank_path),
            manifest_metadata=metadata,
            scenario_sequence_builder=lambda episode_index, n_rounds, seed: (
                v6_scenario_sequence(
                    "confirmatory", episode_index, n_rounds, seed
                )
            ),
        )

    monkeypatch.setattr(runner._bootstrap, "ROOT", str(tmp_path.resolve()))
    monkeypatch.setattr(runner, "audit_v6_final_checkpoint", fake_audit)
    monkeypatch.setattr(
        runner,
        "build_v6_confirmatory_schedule_metadata",
        lambda supplied_protocol, supplied_bank, selected_episode_seeds: (
            deepcopy(schedule)
        ),
    )
    monkeypatch.setattr(runner, "make_v6_protocol", fake_make_protocol)
    return SimpleNamespace(
        root=tmp_path,
        checkpoint_path=checkpoint_path,
        checkpoint=checkpoint,
        bank_path=bank_path,
        bank=bank,
        schedule=schedule,
        audit=audit,
        events=events,
    )


def _base_args(contract, *extra):
    return [
        "--final-checkpoint",
        str(contract.checkpoint_path),
        "--run-id",
        RUN_ID,
        *extra,
    ]


class FakeHuggingFaceProvider:
    instances = []
    output = "2"
    events = None

    def __init__(
        self,
        model,
        temperature=0.7,
        max_tokens=200,
        device="auto",
        dtype="bfloat16",
        layer_stride=1,
        capture=True,
        seed=0,
        enable_thinking=False,
        top_p=0.8,
        top_k=20,
        revision=None,
        constrained_choices=None,
    ):
        if self.events is not None:
            self.events.append("provider_constructed")
        self.model_id = model
        self.revision = revision
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.device = device
        self.dtype = dtype
        self.layer_stride = layer_stride
        self.capture = capture
        self.seed = seed
        self.enable_thinking = enable_thinking
        self.top_p = top_p
        self.top_k = top_k
        self.constrained_choices = tuple(constrained_choices or ())
        self.next_seed = None
        self.generate_calls = 0
        self.prompts = []
        type(self).instances.append(self)

    def describe(self):
        return {
            "provider": "huggingface",
            "model": self.model_id,
            "revision": self.revision,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "dtype": self.dtype,
            "layer_stride": self.layer_stride,
            "capture": self.capture,
            "torch_seed_base": self.seed,
            "enable_thinking": self.enable_thinking,
            "top_p": self.top_p,
            "top_k": self.top_k,
            "constrained_choices": list(self.constrained_choices),
            "invalid_output_policy": "provider error; no fallback",
            "architecture": "SyntheticArchitecture",
            "loaded_with": "SyntheticLoader",
            "processor": "SyntheticProcessor",
            "per_generation_seed_supported": True,
        }

    def set_next_seed(self, seed):
        self.next_seed = int(seed)

    def generate(self, prompt):
        if self.events is not None:
            self.events.append("model_generate")
        self.generate_calls += 1
        self.prompts.append(prompt)
        assert prompt.context == {}
        assert "--- Previous interactions ---" not in prompt.user
        return type(self).output


class DeterministicStrictProvider:
    """Cheap provider used to create a complete, replayable crash fixture."""

    name = "huggingface"
    model_id = MODEL_ID
    model = MODEL_ID

    def __init__(self, plan):
        self.plan = plan
        self.generate_calls = 0

    def set_next_seed(self, seed):
        self.next_seed = seed

    def generate(self, prompt):
        assert prompt.context == {}
        self.generate_calls += 1
        return "1"

    def describe(self):
        return {
            "provider": "huggingface",
            "model": MODEL_ID,
            "revision": REVISION,
            "temperature": self.plan.generation["temperature"],
            "max_tokens": self.plan.generation["max_tokens"],
            "dtype": self.plan.generation["dtype"],
            "capture": False,
            "torch_seed_base": self.plan.config.seed,
            "enable_thinking": self.plan.generation["enable_thinking"],
            "top_p": self.plan.generation["top_p"],
            "top_k": self.plan.generation["top_k"],
            "constrained_choices": ["1", "2", "3"],
            "invalid_output_policy": "provider error; no fallback",
        }


def _complete_unsealed_run(plan):
    provider = DeterministicStrictProvider(plan)
    paths = runner._official_run_paths(plan, create_parents=True)
    result = runner.run_controlled_experiment(
        plan.config,
        run_id=plan.run_id,
        provider=provider,
        progress=None,
        resume=False,
        protocol=plan.protocol,
        round_atomic=True,
        in_flight_path=paths["claim"],
    )
    manifest = json.loads(Path(result.manifest_path).read_text(encoding="utf-8"))
    assert manifest["run_status"] == "completed"
    assert "official_launch_receipt" not in manifest
    assert "completed_log" not in manifest
    return result, provider


def _install_fake_provider(monkeypatch, events, output="2"):
    FakeHuggingFaceProvider.instances = []
    FakeHuggingFaceProvider.output = output
    FakeHuggingFaceProvider.events = events
    monkeypatch.setattr(runner, "HuggingFaceProvider", FakeHuggingFaceProvider)


def test_v6_dry_run_audits_checkpoint_without_constructing_model(
    frozen_contract, monkeypatch, capsys
):
    class ForbiddenProvider:
        def __init__(self, *args, **kwargs):
            raise AssertionError("dry-run constructed the model provider")

    monkeypatch.setattr(runner, "HuggingFaceProvider", ForbiddenProvider)
    assert runner.main(_base_args(frozen_contract, "--dry-run")) == 0
    assert frozen_contract.events == ["checkpoint_audit", "make_v6_protocol"]
    output = capsys.readouterr().out
    assert "DRY RUN PASSED" in output
    assert "strict decoding: 1/2/3; activation capture: disabled" in output


@pytest.mark.parametrize(
    ("override", "message"),
    [
        (["--run-id", "replacement-run"], "run ID"),
        (["--model", "replacement/model"], "model"),
        (["--revision", "replacement-revision"], "revision"),
        (["--episode-seeds", "2"], "episode-seed count"),
        (["--seed", "7"], "master seed"),
        (["--conditions", "full_history"], "conditions"),
        (["--p-match", "0.5"], "p_match"),
        (["--temperature", "0.2"], "temperature"),
        (["--top-p", "0.7"], "top_p"),
        (["--max-tokens", "3"], "max_tokens"),
        (["--enable-thinking"], "thinking setting"),
        (["--constrained-choices", "1", "2"], "constrained choices"),
    ],
)
def test_v6_runner_rejects_every_frozen_contract_override(
    frozen_contract, override, message
):
    args = _base_args(frozen_contract, "--dry-run")
    if override[0] == "--run-id":
        args[3] = override[1]
    else:
        args.extend(override)
    with pytest.raises(ValueError, match=message):
        runner.main(args)


def test_v6_checkpoint_failure_precedes_provider_construction(
    frozen_contract, monkeypatch
):
    events = []

    def failed_audit(_payload, _root):
        events.append("checkpoint_audit_failed")
        return {"pass": False, "checks": {"validated_bank_hash": False}}

    class ForbiddenProvider:
        def __init__(self, *args, **kwargs):
            events.append("provider_constructed")

    monkeypatch.setattr(runner, "audit_v6_final_checkpoint", failed_audit)
    monkeypatch.setattr(runner, "HuggingFaceProvider", ForbiddenProvider)
    with pytest.raises(ValueError, match="validated_bank_hash"):
        runner.main(_base_args(frozen_contract))
    assert events == ["checkpoint_audit_failed"]


def test_v6_runner_rejects_schedule_that_does_not_regenerate(
    frozen_contract, monkeypatch
):
    mismatched = deepcopy(frozen_contract.schedule)
    mismatched["selected_schedule_sha256"] = "different-recomputed-schedule"
    monkeypatch.setattr(
        runner,
        "build_v6_confirmatory_schedule_metadata",
        lambda *_args, **_kwargs: mismatched,
    )

    class ForbiddenProvider:
        def __init__(self, *args, **kwargs):
            raise AssertionError("schedule mismatch constructed the provider")

    monkeypatch.setattr(runner, "HuggingFaceProvider", ForbiddenProvider)
    with pytest.raises(ValueError, match="does not exactly regenerate"):
        runner.main(_base_args(frozen_contract))


def test_v6_runner_rejects_preflight_receipt_path_drift(
    frozen_contract, monkeypatch
):
    mismatched = deepcopy(frozen_contract.schedule)
    mismatched["paid_preflight_receipt_path"] = (
        "results/v6_design/launch_receipts/second-preflight.json"
    )
    frozen_contract.checkpoint["confirmatory_schedule"] = mismatched
    frozen_contract.audit["confirmatory_schedule"] = mismatched
    _write_json(frozen_contract.checkpoint_path, frozen_contract.checkpoint)

    class ForbiddenProvider:
        def __init__(self, *args, **kwargs):
            raise AssertionError("preflight receipt drift constructed the provider")

    monkeypatch.setattr(runner, "HuggingFaceProvider", ForbiddenProvider)
    with pytest.raises(ValueError, match="paid preflight receipt"):
        runner.main(_base_args(frozen_contract))


def test_v6_runner_constructs_only_exact_no_capture_strict_provider(
    frozen_contract, monkeypatch
):
    _install_fake_provider(monkeypatch, frozen_contract.events)
    observed = {}

    def fake_run(
        cfg,
        run_id,
        provider,
        progress,
        resume,
        protocol,
        round_atomic,
        in_flight_path,
        artifact_root,
    ):
        observed.update(
            cfg=cfg,
            run_id=run_id,
            provider=provider,
            resume=resume,
            protocol=protocol,
            round_atomic=round_atomic,
            in_flight_path=in_flight_path,
            artifact_root=artifact_root,
        )
        return SimpleNamespace(
            n_records=108,
            log_path=str(Path(cfg.out_dir) / (run_id + ".jsonl")),
            manifest_path=str(Path(cfg.out_dir) / (run_id + ".manifest.json")),
        )

    monkeypatch.setattr(runner, "run_controlled_experiment", fake_run)
    monkeypatch.setattr(
        runner,
        "finalize_official_manifest",
        lambda plan, log_path, manifest_path, receipt: observed.update(
            finalized=True,
            receipt=receipt,
            log_path=log_path,
            manifest_path=manifest_path,
        ),
    )
    assert runner.main(_base_args(frozen_contract, "--quiet")) == 0
    provider = FakeHuggingFaceProvider.instances[0]
    assert provider.model_id == MODEL_ID
    assert provider.revision == REVISION
    assert provider.capture is False
    assert provider.constrained_choices == ("1", "2", "3")
    assert provider.max_tokens == 2
    assert provider.seed == 20262004
    assert observed["run_id"] == RUN_ID
    assert observed["cfg"].n_episode_seeds == 1
    assert observed["cfg"].target_params.as_dict() == {
        "p_match": 0.72,
        "p_mismatch": 0.38,
        "p_random": 0.5,
    }
    assert observed["round_atomic"] is True
    assert observed["in_flight_path"].endswith(runner.ROUND_CLAIM_SUFFIX)
    assert observed["artifact_root"] == str(frozen_contract.root)
    assert observed["finalized"] is True
    assert Path(frozen_contract.root / runner.CONFIRMATORY_PATHS["receipt"]).is_file()
    assert frozen_contract.events.index("checkpoint_audit") < (
        frozen_contract.events.index("provider_constructed")
    )


def test_v6_resume_rejects_different_checkpoint_provenance_before_provider(
    frozen_contract, monkeypatch
):
    out_dir = frozen_contract.root / runner.CONFIRMATORY_PATHS["out_dir"]
    parsed = runner.build_parser().parse_args(
        _base_args(
            frozen_contract,
            "--out-dir",
            runner.CONFIRMATORY_PATHS["out_dir"],
            "--resume",
        )
    )
    plan = runner.prepare_v6_confirmatory_plan(
        parsed, out_dir=runner.CONFIRMATORY_PATHS["out_dir"]
    )
    runner.claim_official_launch(plan, resume=False)
    manifest = {
        "task_version": CONTROLLED_V6_VERSION,
        "config": plan.config.as_dict(),
        "resume_policy": runner.controlled_resume_policy(True),
        "message_bank_sha256": plan.protocol.message_bank_sha256(),
        "selection_policy": plan.protocol.selection_policy_manifest(),
        "protocol_provenance": {"checkpoint_canonical_sha256": "different"},
    }
    _write_json(out_dir / (RUN_ID + ".manifest.json"), manifest)

    class ForbiddenProvider:
        def __init__(self, *args, **kwargs):
            raise AssertionError("resume mismatch constructed the provider")

    monkeypatch.setattr(runner, "HuggingFaceProvider", ForbiddenProvider)
    with pytest.raises(ValueError, match="final_checkpoint"):
        runner.main(
            _base_args(
                frozen_contract,
                "--out-dir",
                runner.CONFIRMATORY_PATHS["out_dir"],
                "--resume",
            )
        )


def test_v6_paid_preflight_generates_exactly_one_isolated_choice_and_report(
    frozen_contract, monkeypatch
):
    _install_fake_provider(monkeypatch, frozen_contract.events, output="2")
    report_path = frozen_contract.root / runner.CONFIRMATORY_PATHS["preflight"]
    assert (
        preflight.main(
            _base_args(
                frozen_contract,
                "--out",
                runner.CONFIRMATORY_PATHS["preflight"],
            )
        )
        == 0
    )
    assert len(FakeHuggingFaceProvider.instances) == 1
    provider = FakeHuggingFaceProvider.instances[0]
    assert provider.generate_calls == 1
    assert provider.capture is False
    assert provider.constrained_choices == ("1", "2", "3")
    assert provider.next_seed is not None
    assert frozen_contract.events.index("checkpoint_audit") < (
        frozen_contract.events.index("model_generate")
    )

    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["ok"] is True
    assert report["status"] == "PASS_V6_CONFIRMATORY_PAID_PREFLIGHT"
    assert report["generation_count"] == 1
    assert report["activation_capture"] is False
    assert report["target_outcome_generated"] is False
    assert report["confirmatory_log_written"] is False
    probe = report["sentinel_probe"]
    assert probe["focal_output_raw"] == "2"
    assert probe["selected_slot"] == 2
    assert probe["official_schedule_position"] is None
    assert probe["scenario_id"] == preflight.SENTINEL_SCENARIO.id
    assert probe["information_boundary"]["pass"] is True
    assert probe["information_boundary"]["prompt_context_keys"] == []
    assert probe["information_boundary"]["visible_history_entries"] == 0
    assert probe["disjointness_proof"]["overlap_checks"]["pass"] is True


def test_v6_paid_preflight_rejects_device_override_at_parse_time(frozen_contract):
    with pytest.raises(SystemExit):
        preflight.build_parser().parse_args(
            _base_args(frozen_contract, "--device", "cuda:0")
        )


def test_v6_paid_preflight_rejects_nonexact_choice_without_retry(
    frozen_contract, monkeypatch
):
    _install_fake_provider(monkeypatch, frozen_contract.events, output="2.")
    report_path = frozen_contract.root / runner.CONFIRMATORY_PATHS["preflight"]
    assert (
        preflight.main(
            _base_args(
                frozen_contract,
                "--out",
                runner.CONFIRMATORY_PATHS["preflight"],
            )
        )
        == 1
    )
    provider = FakeHuggingFaceProvider.instances[0]
    assert provider.generate_calls == 1
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["ok"] is False
    assert report["generation_count"] == 1
    assert report["status"] == "FAIL_V6_CONFIRMATORY_PAID_PREFLIGHT"
    assert "exact constrained choice" in report["issues"][0]

    assert preflight.main(
        _base_args(
            frozen_contract,
            "--out",
            runner.CONFIRMATORY_PATHS["preflight"],
        )
    ) == 1
    assert provider.generate_calls == 1


def test_v6_paid_preflight_replay_never_calls_provider_twice(
    frozen_contract, monkeypatch
):
    _install_fake_provider(monkeypatch, frozen_contract.events, output="2")
    args = _base_args(frozen_contract)
    assert preflight.main(args) == 0
    receipt_path = (
        frozen_contract.root / runner.CONFIRMATORY_PATHS["preflight_receipt"]
    )
    assert receipt_path.is_file()
    assert len(FakeHuggingFaceProvider.instances) == 1
    assert FakeHuggingFaceProvider.instances[0].generate_calls == 1

    assert preflight.main(args) == 0
    assert len(FakeHuggingFaceProvider.instances) == 1
    assert FakeHuggingFaceProvider.instances[0].generate_calls == 1


@pytest.mark.parametrize("passed", [True, False], ids=["pass", "fail"])
@pytest.mark.parametrize(
    "location,match",
    [
        ("top", "top-level schema"),
        ("probe", "sentinel.*schema"),
        ("provider", "provider evidence.*schema"),
    ],
)
def test_v6_paid_preflight_replay_rejects_schema_extras(
    frozen_contract, monkeypatch, passed, location, match
):
    _install_fake_provider(
        monkeypatch, frozen_contract.events, output="2" if passed else "2."
    )
    args = _base_args(frozen_contract)
    assert preflight.main(args) == (0 if passed else 1)
    report_path = frozen_contract.root / runner.CONFIRMATORY_PATHS["preflight"]
    report = json.loads(report_path.read_text(encoding="utf-8"))
    if location == "top":
        report["unregistered"] = "extra"
    elif location == "probe":
        report["sentinel_probe"]["unregistered"] = "extra"
    else:
        report["provider"]["unregistered"] = "extra"
    _write_json(report_path, report)

    with pytest.raises(ValueError, match=match):
        preflight.main(args)
    assert len(FakeHuggingFaceProvider.instances) == 1
    assert FakeHuggingFaceProvider.instances[0].generate_calls == 1


@pytest.mark.parametrize(
    "document,match",
    [
        ('{"ok": true, "ok": false}\n', "duplicate"),
        ('{"ok": NaN}\n', "non-finite"),
    ],
)
def test_v6_paid_preflight_replay_rejects_non_strict_report_json(
    frozen_contract, monkeypatch, document, match
):
    _install_fake_provider(monkeypatch, frozen_contract.events, output="2")
    args = _base_args(frozen_contract)
    assert preflight.main(args) == 0
    report_path = frozen_contract.root / runner.CONFIRMATORY_PATHS["preflight"]
    report_path.write_text(document, encoding="utf-8")

    with pytest.raises(ValueError, match=match):
        preflight.main(args)
    assert len(FakeHuggingFaceProvider.instances) == 1
    assert FakeHuggingFaceProvider.instances[0].generate_calls == 1


def test_v6_paid_preflight_replay_rejects_symlinked_report(
    frozen_contract, monkeypatch
):
    _install_fake_provider(monkeypatch, frozen_contract.events, output="2")
    args = _base_args(frozen_contract)
    assert preflight.main(args) == 0
    report_path = frozen_contract.root / runner.CONFIRMATORY_PATHS["preflight"]
    moved = frozen_contract.root / "moved-preflight.json"
    report_path.replace(moved)
    report_path.symlink_to(moved)

    with pytest.raises(ValueError, match="symlink"):
        preflight.main(args)
    assert len(FakeHuggingFaceProvider.instances) == 1
    assert FakeHuggingFaceProvider.instances[0].generate_calls == 1


def test_v6_paid_preflight_claim_without_report_is_terminally_ambiguous(
    frozen_contract, monkeypatch
):
    _install_fake_provider(monkeypatch, frozen_contract.events, output="2")
    parsed = preflight.build_parser().parse_args(_base_args(frozen_contract))
    plan = runner.prepare_v6_confirmatory_plan(parsed)
    prompt_data = preflight._sentinel_prompt(plan)
    claim = preflight._paid_call_claim(plan, prompt_data)
    receipt_path = (
        frozen_contract.root / runner.CONFIRMATORY_PATHS["preflight_receipt"]
    )
    _write_json(receipt_path, claim)

    with pytest.raises(RuntimeError, match="ambiguous.*must not be repeated"):
        preflight.main(_base_args(frozen_contract))
    assert FakeHuggingFaceProvider.instances == []


def test_v6_runner_rejects_alternate_output_directory_before_provider(
    frozen_contract, monkeypatch
):
    class ForbiddenProvider:
        def __init__(self, *args, **kwargs):
            raise AssertionError("alternate output path constructed provider")

    monkeypatch.setattr(runner, "HuggingFaceProvider", ForbiddenProvider)
    with pytest.raises(ValueError, match="output directory override is forbidden"):
        runner.main(
            _base_args(
                frozen_contract,
                "--out-dir",
                "data/raw/a-second-v6-run",
            )
        )
    assert not (
        frozen_contract.root / runner.CONFIRMATORY_PATHS["receipt"]
    ).exists()


def test_v6_paid_preflight_rejects_alternate_report_before_provider(
    frozen_contract, monkeypatch
):
    class ForbiddenProvider:
        def __init__(self, *args, **kwargs):
            raise AssertionError("alternate preflight path constructed provider")

    monkeypatch.setattr(runner, "HuggingFaceProvider", ForbiddenProvider)
    with pytest.raises(ValueError, match="report override is forbidden"):
        preflight.main(
            _base_args(
                frozen_contract,
                "--out",
                "results/v6_design/a-second-preflight.json",
            )
        )


def test_v6_atomic_launch_receipt_blocks_a_second_official_launch(
    frozen_contract
):
    parsed = runner.build_parser().parse_args(_base_args(frozen_contract))
    plan = runner.prepare_v6_confirmatory_plan(parsed)
    first = runner.claim_official_launch(plan, resume=False)
    receipt_path = frozen_contract.root / runner.CONFIRMATORY_PATHS["receipt"]
    assert receipt_path.is_file()
    assert first["official_run_id"] == RUN_ID
    assert first["canonical_out_dir"] == runner.CONFIRMATORY_PATHS["out_dir"]
    with pytest.raises(FileExistsError, match="already claimed"):
        runner.claim_official_launch(plan, resume=False)


def test_v6_resume_replays_existing_log_before_provider_construction(
    frozen_contract, monkeypatch
):
    parsed = runner.build_parser().parse_args(
        _base_args(frozen_contract, "--resume")
    )
    plan = runner.prepare_v6_confirmatory_plan(parsed)
    runner.claim_official_launch(plan, resume=False)
    out_dir = Path(plan.config.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    provider_manifest = {
        "provider": "huggingface",
        "model": plan.model_id,
        "revision": plan.revision,
        "temperature": plan.generation["temperature"],
        "max_tokens": plan.generation["max_tokens"],
        "enable_thinking": plan.generation["enable_thinking"],
        "top_p": plan.generation["top_p"],
        "top_k": plan.generation["top_k"],
        "dtype": plan.generation["dtype"],
        "capture": plan.generation["activation_capture"],
        "constrained_choices": ["1", "2", "3"],
    }
    manifest = {
        "task_version": CONTROLLED_V6_VERSION,
        "run_status": "running",
        "config": plan.config.as_dict(),
        "resume_policy": runner.controlled_resume_policy(True),
        "provider": provider_manifest,
        "message_bank_sha256": plan.protocol.message_bank_sha256(),
        "selection_policy": plan.protocol.selection_policy_manifest(),
        "protocol_provenance": plan.protocol.protocol_provenance_manifest(),
    }
    _write_json(out_dir / (RUN_ID + ".manifest.json"), manifest)
    (out_dir / (RUN_ID + ".jsonl")).write_text("{}\n", encoding="utf-8")

    class ForbiddenProvider:
        def __init__(self, *args, **kwargs):
            raise AssertionError("corrupt resume log constructed provider")

    monkeypatch.setattr(runner, "HuggingFaceProvider", ForbiddenProvider)
    with pytest.raises(ValueError, match="resume log failed"):
        runner.main(_base_args(frozen_contract, "--resume"))


def test_v6_completed_manifest_is_sealed_to_receipt_and_raw_log(
    frozen_contract,
):
    parsed = runner.build_parser().parse_args(_base_args(frozen_contract))
    plan = runner.prepare_v6_confirmatory_plan(parsed)
    receipt = runner.claim_official_launch(plan, resume=False)
    result, _provider = _complete_unsealed_run(plan)
    sealed = runner.finalize_official_manifest(
        plan, result.log_path, result.manifest_path, receipt
    )
    assert sealed["official_launch_receipt"]["receipt_id"] == receipt["receipt_id"]
    assert sealed["completed_log"]["n_records"] == plan.expected_n_records
    assert sealed["completed_log"]["file_sha256"] == runner.file_sha256(
        result.log_path
    )
    assert sealed["completed_log"][
        "reconstructed_records_canonical_sha256"
    ]
    assert runner.assert_resume_checkpoint_binding(plan) == "completed"


def test_v6_resume_finalize_only_recovers_crash_without_model_calls(
    frozen_contract, monkeypatch
):
    parsed = runner.build_parser().parse_args(_base_args(frozen_contract))
    plan = runner.prepare_v6_confirmatory_plan(parsed)
    receipt = runner.claim_official_launch(plan, resume=False)
    result, paid_provider = _complete_unsealed_run(plan)
    expected_calls = plan.expected_n_records - (
        2 * plan.config.n_rounds * plan.config.n_episode_seeds
    )
    assert paid_provider.generate_calls == expected_calls

    monkeypatch.setattr(
        runner,
        "make_confirmatory_provider",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("finalize-only recovery loaded the model")
        ),
    )
    monkeypatch.setattr(
        runner,
        "run_controlled_experiment",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("finalize-only recovery queried the model")
        ),
    )
    assert runner.main(_base_args(frozen_contract, "--resume", "--quiet")) == 0

    sealed = json.loads(Path(result.manifest_path).read_text(encoding="utf-8"))
    assert sealed["official_launch_receipt"]["receipt_id"] == receipt["receipt_id"]
    assert sealed["completed_log"]["file_sha256"] == runner.file_sha256(
        result.log_path
    )
    assert sealed["completed_log"]["n_records"] == plan.expected_n_records


def test_v6_sealed_resume_is_idempotent_and_never_loads_model(
    frozen_contract, monkeypatch
):
    parsed = runner.build_parser().parse_args(_base_args(frozen_contract))
    plan = runner.prepare_v6_confirmatory_plan(parsed)
    receipt = runner.claim_official_launch(plan, resume=False)
    result, _provider = _complete_unsealed_run(plan)
    runner.finalize_official_manifest(
        plan, result.log_path, result.manifest_path, receipt
    )
    before = Path(result.manifest_path).read_bytes()

    monkeypatch.setattr(
        runner,
        "make_confirmatory_provider",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("idempotent verification loaded the model")
        ),
    )
    assert runner.main(_base_args(frozen_contract, "--resume", "--quiet")) == 0
    assert Path(result.manifest_path).read_bytes() == before


def test_v6_manifest_seal_replacement_crash_preserves_unsealed_manifest(
    frozen_contract, monkeypatch
):
    parsed = runner.build_parser().parse_args(_base_args(frozen_contract))
    plan = runner.prepare_v6_confirmatory_plan(parsed)
    receipt = runner.claim_official_launch(plan, resume=False)
    result, _provider = _complete_unsealed_run(plan)
    manifest_path = Path(result.manifest_path)
    before = manifest_path.read_bytes()
    real_replace = runner.os.replace

    def crash_before_manifest_replace(source, destination, **kwargs):
        if Path(destination) in {manifest_path, Path(manifest_path.name)}:
            raise OSError("simulated atomic seal crash")
        return real_replace(source, destination, **kwargs)

    with monkeypatch.context() as patcher:
        patcher.setattr(runner.os, "replace", crash_before_manifest_replace)
        with pytest.raises(OSError, match="simulated atomic seal crash"):
            runner.finalize_official_manifest(
                plan, result.log_path, result.manifest_path, receipt
            )
    assert manifest_path.read_bytes() == before
    assert not list(manifest_path.parent.glob(".v6-manifest-*"))

    recovered = runner.finalize_official_manifest(
        plan, result.log_path, result.manifest_path, receipt
    )
    assert recovered["completed_log"]["n_records"] == plan.expected_n_records


def test_v6_finalize_only_rejects_partial_log_before_model_load(
    frozen_contract, monkeypatch
):
    parsed = runner.build_parser().parse_args(_base_args(frozen_contract))
    plan = runner.prepare_v6_confirmatory_plan(parsed)
    runner.claim_official_launch(plan, resume=False)
    result, _provider = _complete_unsealed_run(plan)
    log_path = Path(result.log_path)
    rows = log_path.read_text(encoding="utf-8").splitlines()
    log_path.write_text("\n".join(rows[:-1]) + "\n", encoding="utf-8")

    monkeypatch.setattr(
        runner,
        "make_confirmatory_provider",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("invalid completed log loaded the model")
        ),
    )
    with pytest.raises(ValueError, match="completed V6 log failed exact replay"):
        runner.main(_base_args(frozen_contract, "--resume", "--quiet"))
    manifest = json.loads(Path(result.manifest_path).read_text(encoding="utf-8"))
    assert "official_launch_receipt" not in manifest
    assert "completed_log" not in manifest


def test_v6_finalize_only_rejects_half_sealed_or_tampered_seal(
    frozen_contract,
):
    parsed = runner.build_parser().parse_args(_base_args(frozen_contract))
    plan = runner.prepare_v6_confirmatory_plan(parsed)
    receipt = runner.claim_official_launch(plan, resume=False)
    result, _provider = _complete_unsealed_run(plan)
    manifest_path = Path(result.manifest_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["official_launch_receipt"] = {
        "path": plan.launch_receipt_relative,
        "file_sha256": runner.file_sha256(plan.launch_receipt_path),
        "receipt_id": receipt["receipt_id"],
    }
    _write_json(manifest_path, manifest)
    with pytest.raises(ValueError, match="partial official seal"):
        runner.assert_resume_checkpoint_binding(plan)

    manifest.pop("official_launch_receipt")
    _write_json(manifest_path, manifest)
    sealed = runner.finalize_official_manifest(
        plan, result.log_path, result.manifest_path, receipt
    )
    sealed["completed_log"]["file_sha256"] = "0" * 64
    _write_json(manifest_path, sealed)
    with pytest.raises(ValueError, match="sealed V6 manifest drifted"):
        runner.finalize_official_manifest(
            plan, result.log_path, result.manifest_path, receipt
        )


def test_v6_receipt_publication_crash_never_leaves_torn_canonical_file(
    frozen_contract, monkeypatch
):
    parsed = runner.build_parser().parse_args(_base_args(frozen_contract))
    plan = runner.prepare_v6_confirmatory_plan(parsed)
    receipt_path = Path(plan.launch_receipt_path)
    real_link = runner.os.link

    def crash_before_receipt_link(source, destination, **kwargs):
        if Path(destination) in {receipt_path, Path(receipt_path.name)}:
            raise OSError("simulated receipt publication crash")
        return real_link(source, destination, **kwargs)

    with monkeypatch.context() as patcher:
        patcher.setattr(runner.os, "link", crash_before_receipt_link)
        with pytest.raises(OSError, match="receipt publication crash"):
            runner.claim_official_launch(plan, resume=False)
    assert not receipt_path.exists()
    assert not list(receipt_path.parent.glob(".v6-receipt-*"))

    receipt = runner.claim_official_launch(plan, resume=False)
    assert json.loads(receipt_path.read_text(encoding="utf-8")) == receipt


def test_v6_prepare_rejects_symlinked_canonical_output_directory(
    frozen_contract,
):
    outside = frozen_contract.root / "outside-output"
    outside.mkdir()
    canonical = frozen_contract.root / runner.CONFIRMATORY_PATHS["out_dir"]
    canonical.parent.mkdir(parents=True, exist_ok=True)
    canonical.symlink_to(outside, target_is_directory=True)

    parsed = runner.build_parser().parse_args(_base_args(frozen_contract))
    with pytest.raises(ValueError, match="symlink"):
        runner.prepare_v6_confirmatory_plan(parsed)


def test_v6_finalize_rejects_symlinked_canonical_log(frozen_contract):
    parsed = runner.build_parser().parse_args(_base_args(frozen_contract))
    plan = runner.prepare_v6_confirmatory_plan(parsed)
    receipt = runner.claim_official_launch(plan, resume=False)
    result, _provider = _complete_unsealed_run(plan)
    log_path = Path(result.log_path)
    copied = frozen_contract.root / "copied-log.jsonl"
    copied.write_bytes(log_path.read_bytes())
    log_path.unlink()
    log_path.symlink_to(copied)

    with pytest.raises(ValueError, match="symlink"):
        runner.finalize_official_manifest(
            plan, result.log_path, result.manifest_path, receipt
        )


def test_v6_main_refuses_concurrent_resume_before_provider(
    frozen_contract, monkeypatch
):
    parsed = runner.build_parser().parse_args(_base_args(frozen_contract))
    plan = runner.prepare_v6_confirmatory_plan(parsed)
    paths = runner._official_run_paths(plan, create_parents=True)

    monkeypatch.setattr(
        runner,
        "make_confirmatory_provider",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("concurrent runner constructed provider")
        ),
    )
    with runner.ExclusiveFileLock(paths["lock"], label="test owner"):
        with pytest.raises(RuntimeError, match="another process holds"):
            runner.main(_base_args(frozen_contract))
    assert not Path(paths["receipt"]).exists()


def test_v6_ambiguous_round_claim_stops_before_provider_construction(
    frozen_contract, monkeypatch
):
    parsed = runner.build_parser().parse_args(_base_args(frozen_contract))
    plan = runner.prepare_v6_confirmatory_plan(parsed)
    runner.claim_official_launch(plan, resume=False)
    paths = runner._official_run_paths(plan)
    provider_manifest = DeterministicStrictProvider(plan).describe()
    manifest = {
        "task_version": CONTROLLED_V6_VERSION,
        "run_status": "running",
        "config": plan.config.as_dict(),
        "resume_policy": runner.controlled_resume_policy(True),
        "provider": provider_manifest,
        "message_bank_sha256": plan.protocol.message_bank_sha256(),
        "selection_policy": plan.protocol.selection_policy_manifest(),
        "protocol_provenance": plan.protocol.protocol_provenance_manifest(),
        "n_records": 0,
    }
    _write_json(Path(paths["manifest"]), manifest)
    claim = {
        "kind": "controlled_round_in_flight",
        "schema_version": "1.0",
        "run_id": plan.run_id,
        "task_version": CONTROLLED_V6_VERSION,
        "condition": "full_history",
        "episode_id": "full_history-000-fairness",
        "episode_index": 0,
        "round": 1,
        "round_seed": 123,
        "scenario_id": "sentinel",
        "candidate_ids": ["a", "b", "c"],
        "visible_history_sha256": "0" * 64,
    }
    _write_json(Path(paths["claim"]), claim)
    monkeypatch.setattr(
        runner,
        "make_confirmatory_provider",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("ambiguous resume constructed provider")
        ),
    )

    with pytest.raises(RuntimeError, match="ambiguous in-flight paid generation"):
        runner.main(_base_args(frozen_contract, "--resume", "--quiet"))


def test_v6_main_resumes_one_partial_episode_at_next_round(
    frozen_contract, monkeypatch
):
    parsed = runner.build_parser().parse_args(_base_args(frozen_contract))
    plan = runner.prepare_v6_confirmatory_plan(parsed)
    receipt = runner.claim_official_launch(plan, resume=False)
    paths = runner._official_run_paths(plan)
    initial_provider = DeterministicStrictProvider(plan)
    completed_rounds = 0

    def die_after_tenth_durable_row(_message):
        nonlocal completed_rounds
        completed_rounds += 1
        if completed_rounds == 10:
            raise RuntimeError("simulated partial-episode crash")

    with pytest.raises(RuntimeError, match="partial-episode crash"):
        runner.run_controlled_experiment(
            plan.config,
            run_id=plan.run_id,
            provider=initial_provider,
            progress=die_after_tenth_durable_row,
            resume=False,
            protocol=plan.protocol,
            round_atomic=True,
            in_flight_path=paths["claim"],
        )
    assert initial_provider.generate_calls == 10
    assert not Path(paths["claim"]).exists()

    resumed_provider = DeterministicStrictProvider(plan)
    monkeypatch.setattr(
        runner,
        "make_confirmatory_provider",
        lambda *_args, **_kwargs: resumed_provider,
    )
    assert runner.main(_base_args(frozen_contract, "--resume", "--quiet")) == 0
    expected_calls = plan.expected_n_records - (
        2 * plan.config.n_rounds * plan.config.n_episode_seeds
    )
    assert resumed_provider.generate_calls == expected_calls - 10
    rows = [json.loads(line) for line in Path(paths["log"]).read_text().splitlines()]
    assert len(rows) == plan.expected_n_records
    assert len({(row["episode_id"], row["round"]) for row in rows}) == len(rows)
    sealed = json.loads(Path(paths["manifest"]).read_text(encoding="utf-8"))
    assert sealed["official_launch_receipt"]["receipt_id"] == receipt["receipt_id"]
