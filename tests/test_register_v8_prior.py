"""Registration must reproduce V5's published Qwen shares from the raw log, and refuse bad logs."""

from __future__ import annotations

import copy
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
from register_v8_prior import register  # noqa: E402
from src.controlled_v5_messages import V5MessageBank  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPEC = json.load(open(os.path.join(ROOT, "docs", "v8_protocol.json")))
BANK = V5MessageBank.load(os.path.join(ROOT, SPEC["selected_bank"]["path"]))
LOG = os.path.join(ROOT, "data", "calibration", "qwen38_27b_v5_selected_bank_validation_20260901.jsonl")
RECORDS = [json.loads(l) for l in open(LOG) if l.strip()]


def test_reproduces_the_published_v5_qwen_counts_exactly():
    spec = copy.deepcopy(SPEC)
    out = register(spec, RECORDS, BANK, "qwen38_27b", LOG, None)
    assert out["sections"]["overall"]["counts"] == {"fairness": 79, "risk": 197, "expertise": 300}
    assert out["sections"]["heldout"]["counts"] == {"fairness": 33, "risk": 62, "expertise": 49}
    assert out["default_frame"] == "expertise"
    m = spec["models"]["qwen38_27b"]
    assert m["prior_measured"] is True and m["registered_default_frame"] == "expertise"
    assert m["measured_no_history_shares"]["expertise"] == pytest.approx(300 / 576)
    ids = [c["cell_id"] for c in spec["nuisance_cells_measured"]]
    assert ids == ["qwen38_27b_v5bank_overall", "qwen38_27b_v5bank_heldout"]


def test_registration_is_idempotent():
    spec = copy.deepcopy(SPEC)
    register(spec, RECORDS, BANK, "qwen38_27b", LOG, None)
    register(spec, RECORDS, BANK, "qwen38_27b", LOG, None)
    assert len(spec["nuisance_cells_measured"]) == 2


def test_refuses_a_log_from_the_wrong_model():
    spec = copy.deepcopy(SPEC)
    with pytest.raises(ValueError, match="does not match"):
        register(spec, RECORDS, BANK, "gemma4_31b", LOG, None)


def test_refuses_invalid_or_fallback_records():
    spec = copy.deepcopy(SPEC)
    bad = copy.deepcopy(RECORDS); bad[7]["selection_valid"] = False
    with pytest.raises(ValueError, match="invalid"):
        register(spec, bad, BANK, "qwen38_27b", LOG, None)
    bad = copy.deepcopy(RECORDS); bad[3]["fallback_used"] = True
    with pytest.raises(ValueError, match="invalid"):
        register(spec, bad, BANK, "qwen38_27b", LOG, None)


def test_refuses_wrong_record_count():
    spec = copy.deepcopy(SPEC)
    with pytest.raises(ValueError, match="expected 576"):
        register(spec, RECORDS[:-1], BANK, "qwen38_27b", LOG, None)
