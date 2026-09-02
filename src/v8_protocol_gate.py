"""V8 protocol audit for the target-free prior measurement.

Mirrors ``v5_protocol_gate.audit_v5_calibration_plan`` check for check, with
three differences: the model comes from ``spec["models"][model_key]`` rather
than ``primary_model``; the literals are V8's; and the selected bank is pinned
by file hash. Everything else -- pool and semantic-validation hashes, generation
settings, schedule, provider identity -- is compared exactly as V5 did.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, Mapping

from config import CONTROLLED_V5_VERSION
from .controlled_v5_messages import V5MessageBank
from .v5_protocol_gate import _resolve, canonical_sha256, file_sha256

V8_PROTOCOL_VERSION = "v8-protocol-1.0"
V8_READY_STATUS = "V8_DECLARED_READY_FOR_PRIOR_MEASUREMENT"


def audit_v8_measurement_plan(
    spec: Mapping[str, Any],
    bank: V5MessageBank,
    provider: Mapping[str, Any],
    model_key: str,
    n_episode_blocks: int,
    n_rounds: int,
    heldout_start_round: int,
    seed: int,
    repository_root: str,
) -> Dict[str, Any]:
    pool = spec.get("candidate_pool", {})
    semantic_ref = spec.get("semantic_validation", {})
    bank_ref = spec.get("selected_bank", {})
    models = spec.get("models", {})
    model = models.get(model_key, {}) if isinstance(models, dict) else {}
    generation = spec.get("generation", {})
    schedule = spec.get("prior_measurement_schedule", {})
    semantic_path = _resolve(repository_root, str(semantic_ref.get("path", "")))
    pool_path = _resolve(repository_root, str(pool.get("path", "")))
    bank_path = _resolve(repository_root, str(bank_ref.get("path", "")))
    declaration_path = _resolve(repository_root, str(spec.get("declaration", "")))
    semantic: Dict[str, Any] = {}
    if os.path.isfile(semantic_path):
        with open(semantic_path, "r", encoding="utf-8") as handle:
            semantic = json.load(handle)

    checks = {
        "protocol_version": spec.get("protocol_version") == V8_PROTOCOL_VERSION,
        "task_version": spec.get("task_version") == CONTROLLED_V5_VERSION,
        "pre_focal_calibration": spec.get("pre_focal_calibration") is True,
        "protocol_status": spec.get("status") == V8_READY_STATUS,
        "milestone_declared": spec.get("overrides_v6_terminal_clause") is True
        and os.path.isfile(declaration_path),
        "model_key_registered": model_key in models,
        "pool_file_exists": os.path.isfile(pool_path),
        "pool_file_hash": os.path.isfile(pool_path)
        and file_sha256(pool_path) == pool.get("file_sha256"),
        "semantic_file_exists": os.path.isfile(semantic_path),
        "semantic_file_hash": os.path.isfile(semantic_path)
        and file_sha256(semantic_path) == semantic_ref.get("file_sha256"),
        "semantic_canonical_hash": bool(semantic)
        and canonical_sha256(semantic) == semantic_ref.get("canonical_sha256"),
        "semantic_gate_pass": semantic.get("pass") is True,
        "bank_file_hash": os.path.isfile(bank_path)
        and file_sha256(bank_path) == bank_ref.get("file_sha256"),
        "bank_pending": bank.payload.get("status") == bank_ref.get("required_status"),
        "bank_source_pool": bank.payload.get("source_pool_sha256") == pool.get("sha256"),
        "bank_semantic_hash": bank.payload.get("semantic_validation_sha256")
        == semantic_ref.get("canonical_sha256"),
        "model_id": provider.get("model") == model.get("id"),
        "model_revision": provider.get("revision") == model.get("revision"),
        "provider_kind": provider.get("provider") == "huggingface",
        "temperature": provider.get("temperature") == generation.get("temperature"),
        "top_p": provider.get("top_p") == generation.get("top_p"),
        "top_k": provider.get("top_k") == generation.get("top_k"),
        "max_tokens": provider.get("max_tokens") == generation.get("max_tokens"),
        "dtype": provider.get("dtype") == generation.get("dtype"),
        "thinking_disabled": provider.get("enable_thinking") is False
        and generation.get("enable_thinking") is False,
        "capture_disabled": provider.get("capture") is False
        and generation.get("activation_capture") is False,
        "constrained_choices": list(provider.get("constrained_choices") or [])
        == list(generation.get("constrained_choices") or []),
        "provider_seed": provider.get("torch_seed_base") == seed,
        "schedule_mode": schedule.get("mode") == "selected_bank_validation",
        "schedule_is_not_a_gate": schedule.get("is_gate") is False,
        "episode_blocks": n_episode_blocks == schedule.get("n_episode_blocks"),
        "rounds": n_rounds == schedule.get("n_rounds"),
        "heldout_start": heldout_start_round == schedule.get("heldout_start_round"),
        "schedule_seed": seed == schedule.get("seed"),
        "record_count": n_episode_blocks * n_rounds == schedule.get("n_records"),
        "history_absent": schedule.get("history_present") is False,
        "target_absent": schedule.get("target_simulator_present") is False,
    }
    return {
        "pass": all(checks.values()),
        "model_key": model_key,
        "checks": checks,
        "protocol_version": V8_PROTOCOL_VERSION,
        "protocol_canonical_sha256": canonical_sha256(dict(spec)),
        "semantic_validation_path": semantic_path,
        "bank_path": bank_path,
    }
