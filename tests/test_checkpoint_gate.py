from __future__ import annotations

import copy
import json
from pathlib import Path

from config import STRATEGIES
from src.checkpoint_gate import (
    CHECKPOINT_VERSION,
    EXPECTED_CONDITIONS,
    EXPECTED_EPISODES,
    EXPECTED_RECORDS,
    THRESHOLDS,
    evaluate_behavioral_checkpoint,
)


def _manifest():
    return {
        "n_records": 312,
        "n_episodes": 36,
        "config": {
            "conditions": [
                "full_history", "no_history", "shuffled_history",
                "random_target", "swap",
            ],
            "n_episode_seeds": 2,
            "n_rounds": 8,
            "swap_round": 5,
            "seed": 20260901,
            "model": {"model": "Qwen/Qwen3.8-27B"},
        },
        "provider": {
            "model": "Qwen/Qwen3.8-27B", "enable_thinking": False,
            "temperature": 0.7, "top_p": 0.8, "top_k": 20,
            "capture": False,
        },
        "target_scorer": {
            "version": "semantic-nli-v3",
            "revision": "cf44676c28ba7312e5c5f8f8d2c22b3e0c9cdae2",
        },
    }


def _record(condition, index, target, round_no, label, final=None, donor=None):
    final = final or target
    is_swap = condition == "swap"
    episode_id = (
        "swap-%03d-%s-to-%s" % (index, target, final)
        if is_swap else "%s-%03d-%s" % (condition, index, target)
    )
    active = final if is_swap and round_no > 5 else target
    return {
        "condition": condition,
        "episode_id": episode_id,
        "episode_index": index,
        "round": round_no,
        "n_rounds": 10 if is_swap else 8,
        "hidden_target_type": active,
        "initial_target_type": target,
        "final_target_type": final,
        "swap_round": 5 if is_swap else None,
        "master_seed": 20260901,
        "model_name": "Qwen/Qwen3.8-27B",
        "primary_strategy": label,
        "classifier_ok": True,
        "history_source_episode_id": donor or episode_id,
        "focal_system_prompt": "Neutral repeated interaction objective.",
        "focal_user_prompt": "scenario-%d-%d" % (index, round_no),
        "scenario_id": "scenario-%d-%d" % (index, round_no),
    }


def _passing_records():
    rows = []
    donor_for = {"fairness": "risk", "risk": "expertise", "expertise": "fairness"}
    for condition in ("full_history", "no_history", "random_target"):
        for index in range(2):
            for target in STRATEGIES:
                for round_no in range(1, 9):
                    if condition == "full_history":
                        label = "other" if round_no <= 2 else target
                    elif condition == "no_history":
                        label = "other"
                    else:
                        label = target if round_no <= 2 else "other"
                    rows.append(_record(condition, index, target, round_no, label))
    for index in range(2):
        for target in STRATEGIES:
            donor_type = donor_for[target]
            donor = "full_history-%03d-%s" % (index, donor_type)
            for round_no in range(1, 9):
                label = "other" if round_no == 1 else donor_type
                rows.append(
                    _record("shuffled_history", index, target, round_no, label, donor=donor)
                )
    for index in range(2):
        for old in STRATEGIES:
            for new in STRATEGIES:
                if old == new:
                    continue
                for round_no in range(1, 11):
                    label = old if round_no <= 5 else new
                    rows.append(_record("swap", index, old, round_no, label, final=new))
    return rows


def _audit():
    return {
        "sample_keys_visible_to_judge": ["message", "sample_id"],
        "n_unique_messages": 300,
    }


def test_documented_checkpoint_matches_executable_constants():
    path = Path(__file__).parents[1] / "docs" / "behavioral_checkpoint_v3.json"
    spec = json.loads(path.read_text(encoding="utf-8"))
    assert spec["version"] == CHECKPOINT_VERSION
    assert tuple(spec["experiment"]["conditions"]) == EXPECTED_CONDITIONS
    assert {
        key: value for key, value in spec["experiment"]["expected_records"].items()
        if key != "total"
    } == EXPECTED_RECORDS
    assert {
        key: value for key, value in spec["experiment"]["expected_episodes"].items()
        if key != "total"
    } == EXPECTED_EPISODES
    assert spec["thresholds"] == THRESHOLDS


def test_complete_control_pattern_passes():
    result = evaluate_behavioral_checkpoint(_passing_records(), _manifest(), _audit())
    assert result["pass"] is True
    assert result["decision"] == "GO_FOR_MECHANISTIC_EXPLORATION"
    assert all(result["gates"].values())


def test_random_target_learning_stops_mechanistic_run():
    rows = _passing_records()
    for row in rows:
        if row["condition"] == "random_target":
            row["primary_strategy"] = (
                "other" if row["round"] <= 2 else row["hidden_target_type"]
            )
    result = evaluate_behavioral_checkpoint(rows, _manifest(), _audit())
    assert result["pass"] is False
    assert result["gates"]["random_response_control"] is False


def test_prompt_leakage_fails_design_integrity():
    rows = _passing_records()
    changed = copy.deepcopy(rows)
    changed[0]["focal_system_prompt"] = "Infer the hidden target type."
    result = evaluate_behavioral_checkpoint(changed, _manifest(), _audit())
    assert result["gates"]["design_integrity"] is False
