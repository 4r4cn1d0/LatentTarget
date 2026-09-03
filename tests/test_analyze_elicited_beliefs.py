import importlib.util
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location("analyze_elicited_beliefs", os.path.join(ROOT, "scripts", "analyze_elicited_beliefs.py"))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def _rec(ep, rd, belief, choice, target, swap=False, since=None, init=None, final=None, p=None, slot=1):
    return {
        "condition": "elicited_swap" if swap else "elicited_full_history", "episode_id": ep, "round": rd,
        "beliefs_valid": True, "selection_valid": True, "fallback_used": False,
        "belief_primary_frame": belief, "selected_frame": choice, "hidden_target_type": target,
        "swap_condition": swap, "swap_has_occurred": bool(since is not None and since >= 1),
        "rounds_since_swap": since if since is not None else -rd, "initial_target_type": init or target, "final_target_type": final or target,
        "predicted_p_a": p or {"1": 0.7, "2": 0.4, "3": 0.4}, "selected_slot": slot, "target_p_a": 0.72,
        "selected_prediction_brier": 0.0, "candidates": [],
    }


def test_by_round_means_and_belief_minus_choice_are_exact_with_no_bootstrap():
    recs = [
        _rec("e1", 1, "risk", "risk", "risk"), _rec("e2", 1, "risk", "fairness", "risk"),
        _rec("e1", 2, "fairness", "risk", "risk"), _rec("e2", 2, "risk", "risk", "risk"),
    ]
    s = mod.analyze(recs, n_boot=0)
    block = s["per_condition"]["elicited_full_history"]
    r1, r2 = block["by_round"]
    assert r1["belief_matches_target"]["mean"] == 1.0 and r1["choice_matches_target"]["mean"] == 0.5
    assert r1["belief_minus_choice"]["mean"] == 0.5 and r1["belief_choice_agreement"]["mean"] == 0.5
    assert r2["belief_matches_target"]["mean"] == 0.5 and r2["choice_matches_target"]["mean"] == 1.0
    assert r2["belief_minus_choice"]["mean"] == -0.5
    assert block["n_episodes"] == 2
    assert block["stated_p_a_selected"]["mean_stated"]["mean"] == 0.7


def test_swap_block_uses_new_and_old_frames_and_post_swap_window():
    recs = []
    for k in range(1, 7):  # rounds since swap 1..6; belief moves to new at k>=2, choice at k>=4
        recs.append(_rec("s1", 10 + k, "risk" if k >= 2 else "fairness", "risk" if k >= 4 else "fairness", "risk",
                         swap=True, since=k, init="fairness", final="risk"))
    s = mod.analyze(recs, n_boot=0)
    block = s["per_condition"]["elicited_swap"]
    rows = {r["rounds_since_swap"]: r for r in block["by_rounds_since_swap"]}
    assert rows[1]["belief_matches_new"]["mean"] == 0.0 and rows[1]["belief_matches_old"]["mean"] == 1.0
    assert rows[3]["belief_matches_new"]["mean"] == 1.0 and rows[3]["choice_matches_new"]["mean"] == 0.0
    assert rows[5]["choice_matches_new"]["mean"] == 1.0
    d = block["post_swap_rounds_1_to_5_belief_minus_choice_new"]
    assert abs(d["mean"] - (4 / 5 - 2 / 5)) < 1e-12 and d["n_episodes"] == 1
    assert block["by_transition"]["fairness_to_risk"]["n_records"] == 5


def test_invalid_records_are_excluded_but_counted_in_validity():
    recs = [_rec("e1", 1, "risk", "risk", "risk"), dict(_rec("e2", 1, "risk", "risk", "risk"), beliefs_valid=False)]
    s = mod.analyze(recs, n_boot=0)
    assert s["belief_validity"]["beliefs_valid_rate"] == 0.5 and s["belief_validity"]["n_fully_valid"] == 1
    assert s["per_condition"]["elicited_full_history"]["n_records"] == 1
