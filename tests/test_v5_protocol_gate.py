from __future__ import annotations

import json
from pathlib import Path

from src.controlled_v5_messages import V5MessageBank
from src.v5_protocol_gate import audit_v5_calibration_plan


ROOT = Path(__file__).parents[1]
POOL = ROOT / "data" / "v5" / "v5_candidate_pool_v1.json"
SPEC = ROOT / "docs" / "v5_calibration_protocol.json"


def _provider(spec, seed):
    generation = spec["generation"]
    model = spec["primary_model"]
    return {
        "provider": "huggingface",
        "model": model["id"],
        "revision": model["revision"],
        "temperature": generation["temperature"],
        "top_p": generation["top_p"],
        "top_k": generation["top_k"],
        "max_tokens": generation["max_tokens"],
        "dtype": generation["dtype"],
        "enable_thinking": False,
        "capture": False,
        "constrained_choices": ["1", "2", "3"],
        "torch_seed_base": seed,
    }


def test_frozen_v5_pool_calibration_plan_passes_exactly():
    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    schedule = spec["pool_calibration_schedule"]
    audit = audit_v5_calibration_plan(
        spec,
        V5MessageBank.load(str(POOL)),
        _provider(spec, schedule["seed"]),
        "pool_calibration",
        schedule["n_episode_blocks"],
        schedule["n_rounds"],
        schedule["heldout_start_round"],
        schedule["seed"],
        str(ROOT),
    )
    assert audit["pass"] is True
    assert all(audit["checks"].values())


def test_v5_calibration_plan_rejects_revision_or_schedule_drift():
    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    schedule = spec["pool_calibration_schedule"]
    provider = _provider(spec, schedule["seed"])
    provider["revision"] = "drifted"
    audit = audit_v5_calibration_plan(
        spec,
        V5MessageBank.load(str(POOL)),
        provider,
        "pool_calibration",
        schedule["n_episode_blocks"] + 1,
        schedule["n_rounds"],
        schedule["heldout_start_round"],
        schedule["seed"],
        str(ROOT),
    )
    assert audit["pass"] is False
    assert audit["checks"]["model_revision"] is False
    assert audit["checks"]["episode_blocks"] is False
