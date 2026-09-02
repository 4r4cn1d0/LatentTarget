"""Model-free adversarial coverage for the frozen V6 focal runtime."""

from __future__ import annotations

import json
import sys
from copy import deepcopy
from pathlib import Path

import pytest


ROOT = Path(__file__).parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import run_controlled_open_weight_v6 as confirmatory_runner  # noqa: E402
import run_v6_calibration as calibration_runner  # noqa: E402
import src.v6_protocol_gate as gate  # noqa: E402
from src.focal_agent import ProviderError  # noqa: E402
from src.hf_provider import (  # noqa: E402
    HuggingFaceProvider,
    collect_focal_runtime_evidence,
)


def _protocol():
    return json.loads(
        (ROOT / "docs" / "v6_calibration_protocol.json").read_text(
            encoding="utf-8"
        )
    )


@pytest.fixture
def runtime_evidence():
    return {
        "evidence_version": "v6-focal-runtime-evidence-1.0",
        "requested_device": "auto",
        "resolved_device_type": "cuda",
        "python": {
            "implementation": "CPython",
            "version": "3.12.11",
            "version_info": [3, 12, 11],
        },
        "packages": {
            # A CUDA wheel may record a local build suffix.  The preregistered
            # release is still 2.9.1; the suffix is retained for stage equality.
            "torch": "2.9.1+cu128",
            "torchvision": "0.24.1+cu128",
            "torchaudio": "2.9.1+cu128",
            "transformers": "5.16.1",
            "accelerate": "1.14.0",
            "numpy": "2.3.4",
            "sentencepiece": "0.2.1",
        },
        "module_versions": {
            "numpy": "2.3.4",
            "torch": "2.9.1+cu128",
            "transformers": "5.16.1",
            "accelerate": "1.14.0",
        },
        "cuda": {
            "available": True,
            "torch_build_version": "12.8",
            "runtime_version": 12080,
            "device_count": 1,
            "bfloat16_supported": True,
        },
        "devices": [
            {
                "index": 0,
                "name": "NVIDIA A100-SXM4-80GB",
                "compute_capability": [8, 0],
                "total_memory_bytes": 85_056_798_720,
            }
        ],
    }


def test_protocol_carries_the_exact_code_frozen_runtime_contract():
    protocol = _protocol()
    assert protocol["focal_runtime"] == gate.V6_FROZEN_FOCAL_RUNTIME_CONTRACT


def test_injected_runtime_probe_is_model_free(runtime_evidence):
    calls = []

    def probe(device):
        calls.append(device)
        return runtime_evidence

    observed = collect_focal_runtime_evidence(device="auto", probe=probe)
    assert observed == runtime_evidence
    assert observed is not runtime_evidence
    assert calls == ["auto"]

    with pytest.raises(ValueError, match="overrides are forbidden"):
        collect_focal_runtime_evidence(device="cuda:0", probe=probe)
    assert calls == ["auto"]


def test_official_a100_runtime_passes_and_binds_provider(runtime_evidence):
    protocol = _protocol()
    audit = gate.require_v6_focal_runtime(protocol, runtime_evidence)
    assert audit["pass"] is True
    assert audit["evidence_sha256"]

    provider = HuggingFaceProvider(
        model="Qwen/Qwen3.8-27B",
        revision="1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0",
        device="auto",
        temperature=0.0,
        max_tokens=2,
        dtype="bfloat16",
        capture=False,
        constrained_choices=("1", "2", "3"),
    )
    provider.bind_runtime_evidence(runtime_evidence)
    description = provider.describe()
    assert description["device"] == "auto"
    assert description["focal_runtime_evidence"] == runtime_evidence

    drifted = deepcopy(runtime_evidence)
    drifted["packages"]["numpy"] = "2.3.5"
    with pytest.raises(ProviderError, match="already bound differently"):
        provider.bind_runtime_evidence(drifted)


@pytest.mark.parametrize(
    ("mutate", "failed_check"),
    [
        (
            lambda value: value["packages"].__setitem__("torch", "2.9.0"),
            "exact_package_versions",
        ),
        (
            lambda value: value["python"]["version_info"].__setitem__(1, 11),
            "python_family",
        ),
        (
            lambda value: value["cuda"].__setitem__("available", False),
            "cuda_available",
        ),
        (
            lambda value: value["cuda"].__setitem__(
                "bfloat16_supported", False
            ),
            "bfloat16_supported",
        ),
        (
            lambda value: value["devices"][0].__setitem__(
                "name", "NVIDIA H100 80GB HBM3"
            ),
            "nvidia_a100_name",
        ),
        (
            lambda value: value["devices"][0].__setitem__(
                "compute_capability", [9, 0]
            ),
            "compute_capability",
        ),
        (
            lambda value: value["devices"][0].__setitem__(
                "total_memory_bytes", 40_000_000_000
            ),
            "a100_80gb_memory",
        ),
    ],
)
def test_runtime_contract_fails_closed_on_software_or_hardware_drift(
    runtime_evidence, mutate, failed_check
):
    drifted = deepcopy(runtime_evidence)
    mutate(drifted)
    audit = gate.audit_v6_focal_runtime(
        _protocol()["focal_runtime"], drifted
    )
    assert audit["pass"] is False
    assert audit["checks"][failed_check] is False


@pytest.mark.parametrize(
    "mutate",
    [
        lambda value: value["packages"].__setitem__("numpy", "2.3.5"),
        lambda value: value["python"].update(
            {"version": "3.12.12", "version_info": [3, 12, 12]}
        ),
        lambda value: value["cuda"].__setitem__("runtime_version", 12090),
        lambda value: value["devices"][0].__setitem__(
            "name", "NVIDIA A100 80GB PCIe"
        ),
        lambda value: value["devices"][0].__setitem__(
            "total_memory_bytes", 85_056_798_719
        ),
    ],
)
def test_validation_and_confirmatory_require_exact_pool_evidence(
    runtime_evidence, mutate
):
    later_stage = deepcopy(runtime_evidence)
    mutate(later_stage)
    audit = gate.audit_v6_focal_runtime(
        _protocol()["focal_runtime"],
        later_stage,
        expected_evidence=runtime_evidence,
    )
    assert audit["pass"] is False
    assert audit["checks"]["cross_stage_exact"] is False


def test_checkpoint_runtime_rejects_missing_or_tampered_evidence(runtime_evidence):
    protocol = _protocol()
    checkpoint = gate.build_v6_focal_runtime_checkpoint(
        protocol, runtime_evidence
    )
    assert gate.audit_v6_focal_runtime_checkpoint(
        checkpoint, protocol, expected_evidence=runtime_evidence
    )["pass"] is True

    missing = gate.audit_v6_focal_runtime_checkpoint({}, protocol)
    assert missing["pass"] is False

    tampered = deepcopy(checkpoint)
    tampered["evidence"]["packages"]["numpy"] = "2.3.5"
    audit = gate.audit_v6_focal_runtime_checkpoint(
        tampered, protocol, expected_evidence=runtime_evidence
    )
    assert audit["pass"] is False
    assert audit["checks"]["cross_stage_exact"] is False
    assert audit["checks"]["evidence_hash"] is False


def test_v6_clis_reject_arbitrary_device_overrides_before_any_probe(monkeypatch):
    def forbidden_probe(*_args, **_kwargs):
        raise AssertionError("invalid --device reached the runtime probe")

    monkeypatch.setattr(
        calibration_runner, "collect_focal_runtime_evidence", forbidden_probe
    )
    monkeypatch.setattr(
        confirmatory_runner, "collect_focal_runtime_evidence", forbidden_probe
    )
    with pytest.raises(SystemExit):
        calibration_runner.main(
            [
                "--bank",
                "unused.json",
                "--mode",
                "pool_screening",
                "--run-id",
                "unused",
                "--device",
                "cuda:0",
            ]
        )
    with pytest.raises(SystemExit):
        confirmatory_runner.build_parser().parse_args(
            ["--run-id", "unused", "--device", "cpu"]
        )


@pytest.mark.parametrize(
    ("document", "message"),
    [
        ('{"protocol_version": "a", "protocol_version": "b"}', "duplicate"),
        ('{"value": NaN}', "non-finite"),
        ('{"value": Infinity}', "non-finite"),
    ],
)
def test_v6_gate_json_loaders_reject_duplicates_and_nonfinite_constants(
    tmp_path, document, message
):
    path = tmp_path / "artifact.json"
    path.write_text(document, encoding="utf-8")
    reference = {"path": path.name}

    with pytest.raises(ValueError, match=message):
        gate._load_reference(reference, str(tmp_path))

    payload, checks, _ = gate._load_checkpoint_json_reference(
        reference, str(tmp_path)
    )
    assert payload == {}
    assert checks["json_object"] is False
