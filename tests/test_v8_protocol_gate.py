"""The V8 measurement audit must pass on the real spec and fail on any drift."""

from __future__ import annotations

import copy
import json
import os
import subprocess
import sys

import pytest

from src.controlled_v5_messages import V5MessageBank
from src.hf_provider import HuggingFaceProvider
from src.v8_protocol_gate import audit_v8_measurement_plan

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPEC = json.load(open(os.path.join(ROOT, "docs", "v8_protocol.json")))
BANK = V5MessageBank.load(os.path.join(ROOT, SPEC["selected_bank"]["path"]))


def _provider_desc(model_key):
    m, g, s = SPEC["models"][model_key], SPEC["generation"], SPEC["prior_measurement_schedule"]
    return HuggingFaceProvider(model=m["id"], revision=m["revision"], temperature=g["temperature"],
                               max_tokens=g["max_tokens"], dtype=g["dtype"], capture=False, seed=s["seed"],
                               enable_thinking=g["enable_thinking"], top_p=g["top_p"], top_k=g["top_k"],
                               constrained_choices=tuple(g["constrained_choices"])).describe()


def _audit(spec, model_key, provider=None):
    s = spec["prior_measurement_schedule"]
    return audit_v8_measurement_plan(spec=spec, bank=BANK, provider=provider or _provider_desc(model_key),
                                     model_key=model_key, n_episode_blocks=s["n_episode_blocks"], n_rounds=s["n_rounds"],
                                     heldout_start_round=s["heldout_start_round"], seed=s["seed"], repository_root=ROOT)


@pytest.mark.parametrize("model_key", ["qwen38_27b", "gemma4_31b"])
def test_real_spec_passes_for_both_registered_models(model_key):
    out = _audit(SPEC, model_key)
    assert out["pass"], sorted(k for k, v in out["checks"].items() if not v)


def test_unregistered_model_key_fails():
    assert _audit(SPEC, "llama_whatever")["checks"]["model_key_registered"] is False


def test_wrong_revision_fails():
    spec = copy.deepcopy(SPEC); spec["models"]["gemma4_31b"]["revision"] = "deadbeef"
    out = _audit(spec, "gemma4_31b", provider=_provider_desc("gemma4_31b"))
    assert not out["pass"] and out["checks"]["model_revision"] is False


def test_status_and_declaration_are_enforced():
    spec = copy.deepcopy(SPEC); spec["status"] = "SOMETHING_ELSE"; spec["overrides_v6_terminal_clause"] = False
    out = _audit(spec, "qwen38_27b")
    assert out["checks"]["protocol_status"] is False and out["checks"]["milestone_declared"] is False


def test_bank_hash_is_pinned():
    spec = copy.deepcopy(SPEC); spec["selected_bank"]["file_sha256"] = "0" * 64
    assert _audit(spec, "qwen38_27b")["checks"]["bank_file_hash"] is False


def test_thinking_or_capture_enabled_fails():
    desc = dict(_provider_desc("gemma4_31b")); desc["enable_thinking"] = True
    assert _audit(SPEC, "gemma4_31b", provider=desc)["checks"]["thinking_disabled"] is False
    desc = dict(_provider_desc("gemma4_31b")); desc["capture"] = True
    assert _audit(SPEC, "gemma4_31b", provider=desc)["checks"]["capture_disabled"] is False


def test_dry_run_of_the_exact_gemma_command_passes_locally():
    """No torch, no GPU, no model: the audit runs against the real provider description."""
    out = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "run_v8_prior_measurement.py"),
                          "--model-key", "gemma4_31b", "--run-id", "v8-gemma4-prior-dryrun", "--dry-run"],
                         capture_output=True, text=True, cwd=ROOT)
    assert out.returncode == 0, out.stdout + out.stderr
    assert "DRY RUN PASSED" in out.stdout and "V8 protocol audit: PASS" in out.stdout
