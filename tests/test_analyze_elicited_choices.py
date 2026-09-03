import importlib.util
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location("analyze_elicited_choices", os.path.join(ROOT, "scripts", "analyze_elicited_choices.py"))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

MANIFEST = {"config": {"heldout_start_round": 16}}


def _episode(cond, idx, target, frames, swap=None):
    rows = []
    for rd, frame in enumerate(frames, start=1):
        r = {"condition": cond, "episode_id": "%s-%03d" % (cond, idx), "episode_index": idx, "round": rd,
             "focal_mode": "elicited", "selection_valid": True, "beliefs_valid": True, "fallback_used": False,
             "hidden_target_type": target, "selected_frame": frame, "strategy_match": float(frame == target),
             "target_success": 1.0, "candidates": [{"split": "development" if rd < 16 else "heldout"}],
             "initial_target_type": swap[0] if swap else target, "final_target_type": swap[1] if swap else target,
             "swap_round": 10 if swap else None, "swap_condition": bool(swap)}
        if swap:
            r["hidden_target_type"] = swap[0] if rd <= 10 else swap[1]
            r["strategy_match"] = float(frame == r["hidden_target_type"])
        rows.append(r)
    return rows


def test_learner_passes_learning_and_revision_gates_within_arm():
    recs = []
    for i in range(12):  # learns by round 6; revises fully after swap
        recs += _episode("elicited_full_history", i, "risk", ["fairness"] * 5 + ["risk"] * 15)
        recs += _episode("elicited_swap", i, None, ["fairness"] * 10 + ["risk"] * 10, swap=("fairness", "risk"))
    out = mod.analyze(recs, MANIFEST, None, n_boot=200, n_perm=500)
    assert out["verdict"] == "ELICITED_LEARNING_PASS_REVISION_PASS"
    s = out["stable_condition_metrics"]["elicited_full_history"]
    assert s["learning_gain"]["mean"] == 1.0 and s["n_episodes"] == 12
    assert out["swap_metrics"]["n_adapted"] == 12 and out["swap_metrics"]["by_transition"]["fairness_to_risk"]["n"] == 12
    assert "cross_prompt_comparison_vs_v4_spontaneous" not in out


def test_non_reviser_fails_revision_and_records_uncomputable_gates():
    recs = []
    for i in range(12):
        recs += _episode("elicited_full_history", i, "risk", ["fairness"] * 5 + ["risk"] * 15)
        recs += _episode("elicited_swap", i, None, ["fairness"] * 20, swap=("fairness", "risk"))
    out = mod.analyze(recs, MANIFEST, None, n_boot=200, n_perm=500)
    assert out["verdict"] == "ELICITED_LEARNING_PASS_REVISION_FAIL"
    assert out["effect_gates_within_arm"]["silent_swap_new_target_gain"] is False
    assert "full_history_difference_in_differences" in out["gates_not_computable_within_arm"]


def test_cross_prompt_comparison_is_unpaired_difference_of_episode_means():
    e1 = []; v4 = []
    for i in range(6):
        e1 += _episode("elicited_full_history", i, "risk", ["fairness"] * 5 + ["risk"] * 15)
        e1 += _episode("elicited_swap", i, None, ["fairness"] * 10 + ["risk"] * 10, swap=("fairness", "risk"))
        v4 += [dict(r, condition="full_history", focal_mode="spontaneous") for r in _episode("full_history", i, "risk", ["fairness"] * 20)]
        v4 += [dict(r, condition="swap", focal_mode="spontaneous") for r in _episode("swap", i, None, ["fairness"] * 20, swap=("fairness", "risk"))]
    out = mod.analyze(e1, MANIFEST, v4, n_boot=0, n_perm=100)
    c = out["cross_prompt_comparison_vs_v4_spontaneous"]
    assert c["learning_gain_diff"]["mean"] == 1.0 and c["swap_new_target_gain_diff"]["mean"] == 1.0
    assert c["learning_gain_diff"]["n_a"] == 6 and c["learning_gain_diff"]["n_b"] == 6
