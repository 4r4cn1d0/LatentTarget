"""Primary (choice) analysis for the elicited-belief arm (Arm E1, docs/V4_REPLICATION_DECLARATION.md).

The frozen V4 evaluator (`evaluate_controlled_checkpoint`) refuses a log that lacks
the five V4 conditions, and Arm E1 deliberately runs only `elicited_full_history`
and `elicited_swap` (a different prompt; not pooled with V4).  This driver therefore
computes the *same* V4 metrics with the *same* frozen functions and thresholds --
`_stable_episode_summaries`, `_swap_episode_summaries`, `_bootstrap_mean`,
`_sign_flip_test`, `CONTROLLED_GATE_THRESHOLDS` -- on the elicited conditions, and
reports the V4 gates that are computable within the arm:

  * full-history learning gain (late held-out - early) with bootstrap CI and
    one-sided sign-flip p;
  * swap new-target gain, old-target drop, late new-over-old (V4 thresholds and
    the V4 one-sided alpha).

Gates that need V4's control conditions (no-history difference-in-differences,
shuffled specificity, random-target control) are NOT computable within E1; the
V4 spontaneous arm's `full_history` and `swap` episodes are loaded as the
declared *cross-prompt* comparison (different prompt, same design, seeds,
targets), with an unpaired episode bootstrap on the difference.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from src.controlled_analysis import (  # noqa: E402
    _bootstrap_mean, _condition_rows, _mean, _positive_beyond_roundoff,
    _sign_flip_test, _stable_episode_summaries, _swap_episode_summaries, _trajectory,
)
from config import CONTROLLED_GATE_THRESHOLDS  # noqa: E402

V4_LOG = os.path.join(ROOT, "data", "raw", "qwen38_27b_v4_checkpoint_20260902.jsonl")


def load(path):
    with open(path, "r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _unpaired_diff(a, b, n_boot, seed):
    rng = np.random.default_rng(seed)
    a = np.asarray(a, dtype=float); b = np.asarray(b, dtype=float)
    diff = float(a.mean() - b.mean())
    if n_boot <= 0 or len(a) < 2 or len(b) < 2:
        return {"mean": diff, "ci_lo": diff, "ci_hi": diff, "n_a": len(a), "n_b": len(b)}
    boot = a[rng.integers(0, len(a), (n_boot, len(a)))].mean(1) - b[rng.integers(0, len(b), (n_boot, len(b)))].mean(1)
    lo, hi = np.percentile(boot, [2.5, 97.5])
    return {"mean": diff, "ci_lo": float(lo), "ci_hi": float(hi), "n_a": len(a), "n_b": len(b)}


def _stable_block(summaries, n_boot, n_perm, seed):
    eps = list(summaries.values())
    gains = [r["learning_gain"] for r in eps]
    return {
        "n_episodes": len(eps),
        "early_match": _bootstrap_mean([r["early_match"] for r in eps], n_boot, seed),
        "late_heldout_match": _bootstrap_mean([r["late_heldout_match"] for r in eps], n_boot, seed + 1),
        "late_development_match": _bootstrap_mean([r["late_development_match"] for r in eps], n_boot, seed + 2),
        "learning_gain": {**_bootstrap_mean(gains, n_boot, seed + 3), **_sign_flip_test(gains, n_perm, seed + 4)},
        "success": _bootstrap_mean([r["success"] for r in eps], n_boot, seed + 5),
        "valid_selection": _mean(r["valid_selection"] for r in eps),
    }


def _swap_block(summaries, n_boot, n_perm, seed):
    return {
        "n_episodes": len(summaries),
        "pre_new_match": _mean(r["pre_new_match"] for r in summaries),
        "pre_old_match": _mean(r["pre_old_match"] for r in summaries),
        "late_new_match": _mean(r["late_new_match"] for r in summaries),
        "late_old_match": _mean(r["late_old_match"] for r in summaries),
        "new_target_gain": {**_bootstrap_mean([r["new_target_gain"] for r in summaries], n_boot, seed + 200),
                            **_sign_flip_test([r["new_target_gain"] for r in summaries], n_perm, seed + 201)},
        "old_target_drop": _bootstrap_mean([r["old_target_drop"] for r in summaries], n_boot, seed + 202),
        "late_new_over_old": {**_bootstrap_mean([r["late_new_over_old"] for r in summaries], n_boot, seed + 203),
                              **_sign_flip_test([r["late_new_over_old"] for r in summaries], n_perm, seed + 204)},
        "n_adapted": sum(r["rounds_to_adapt"] is not None for r in summaries),
        "median_rounds_to_adapt": (float(np.median([r["rounds_to_adapt"] for r in summaries if r["rounds_to_adapt"] is not None]))
                                   if any(r["rounds_to_adapt"] is not None for r in summaries) else None),
        "by_transition": {
            "%s_to_%s" % tr: {
                "n": len(sub), "new_target_gain": _mean(r["new_target_gain"] for r in sub),
                "old_target_drop": _mean(r["old_target_drop"] for r in sub),
                "n_adapted": sum(r["rounds_to_adapt"] is not None for r in sub),
            }
            for tr in sorted({(r["old_type"], r["new_type"]) for r in summaries})
            for sub in [[r for r in summaries if (r["old_type"], r["new_type"]) == tr]]
        },
    }


def analyze(records, manifest, v4_records=None, n_boot=5000, n_perm=10000, seed=20260902):
    heldout_start = int(manifest["config"]["heldout_start_round"])
    th = dict(CONTROLLED_GATE_THRESHOLDS); alpha = th["confirmatory_alpha_one_sided"]
    fh = _condition_rows(records, "elicited_full_history"); sw = _condition_rows(records, "elicited_swap")
    if not fh or not sw:
        raise ValueError("E1 log must contain elicited_full_history and elicited_swap")
    elicited = [r for r in records if r["focal_mode"] == "elicited"]
    valid_rate = _mean(float(r["selection_valid"]) for r in elicited)
    belief_valid_rate = _mean(float(bool(r.get("beliefs_valid"))) for r in elicited)
    fallback_rate = _mean(float(bool(r.get("fallback_used"))) for r in elicited)
    stable_summ = _stable_episode_summaries(fh, heldout_start)
    swap_summ = _swap_episode_summaries(sw, heldout_start)
    stable = _stable_block(stable_summ, n_boot, n_perm, seed)
    swap = _swap_block(swap_summ, n_boot, n_perm, seed)
    gates = {
        "valid_selection_rate": valid_rate >= th["minimum_valid_selection_rate"],
        "full_history_late_level": stable["late_heldout_match"]["mean"] >= th["minimum_full_history_late_match"],
        "full_history_learning_gain_positive": _positive_beyond_roundoff(stable["learning_gain"]["mean"]),
        "full_history_learning_gain_sign_flip_test": stable["learning_gain"]["p_value_one_sided"] <= alpha,
        "silent_swap_new_target_gain": swap["new_target_gain"]["mean"] >= th["minimum_swap_new_target_gain"],
        "silent_swap_old_target_drop": swap["old_target_drop"]["mean"] >= th["minimum_swap_old_target_drop"],
        "silent_swap_new_over_old": _positive_beyond_roundoff(swap["late_new_over_old"]["mean"]),
        "swap_revision_randomization_test": swap["late_new_over_old"]["p_value_one_sided"] <= alpha,
    }
    not_computable = ["full_history_difference_in_differences", "full_over_no_history", "shuffled_history_specificity",
                      "random_response_control", "multiple_target_types", "stable_primary_randomization_test"]
    out = {
        "arm": "E1 elicited-belief (Qwen3.8-27B), frozen V4 design, elicited conditions only",
        "analysis": "frozen V4 functions and thresholds applied within-arm; no pooling with V4",
        "thresholds_frozen": th, "heldout_start_round": heldout_start,
        "n_records": len(records), "valid_selection_rate": valid_rate,
        "belief_valid_rate": belief_valid_rate, "fallback_rate": fallback_rate,
        "stable_condition_metrics": {"elicited_full_history": stable},
        "swap_metrics": swap, "swap_episode_summaries": swap_summ,
        "effect_gates_within_arm": gates,
        "gates_not_computable_within_arm": not_computable,
        "revision_pass_within_arm": all(gates[k] for k in ("silent_swap_new_target_gain", "silent_swap_old_target_drop",
                                                             "silent_swap_new_over_old", "swap_revision_randomization_test")),
        "learning_pass_within_arm": all(gates[k] for k in ("full_history_learning_gain_positive", "full_history_learning_gain_sign_flip_test")),
        "trajectories": {c: {"match": _trajectory(_condition_rows(records, c), "strategy_match"),
                             "success": _trajectory(_condition_rows(records, c), "target_success")} for c in ("elicited_full_history", "elicited_swap")},
    }
    out["verdict"] = ("ELICITED_LEARNING_%s_REVISION_%s" % ("PASS" if out["learning_pass_within_arm"] else "FAIL",
                                                           "PASS" if out["revision_pass_within_arm"] else "FAIL"))
    if v4_records:
        v4_fh = _stable_episode_summaries(_condition_rows(v4_records, "full_history"), heldout_start)
        v4_sw = _swap_episode_summaries(_condition_rows(v4_records, "swap"), heldout_start)
        out["cross_prompt_comparison_vs_v4_spontaneous"] = {
            "note": "different prompt (elicited JSON vs bare 1|2|3); same design, seeds, targets; unpaired episode bootstrap of (elicited - spontaneous)",
            "v4_full_history": _stable_block(v4_fh, n_boot, n_perm, seed + 1000),
            "v4_swap": _swap_block(v4_sw, n_boot, n_perm, seed + 1000),
            "learning_gain_diff": _unpaired_diff([r["learning_gain"] for r in stable_summ.values()], [r["learning_gain"] for r in v4_fh.values()], n_boot, seed + 2000),
            "late_heldout_match_diff": _unpaired_diff([r["late_heldout_match"] for r in stable_summ.values()], [r["late_heldout_match"] for r in v4_fh.values()], n_boot, seed + 2001),
            "swap_new_target_gain_diff": _unpaired_diff([r["new_target_gain"] for r in swap_summ], [r["new_target_gain"] for r in v4_sw], n_boot, seed + 2002),
            "swap_late_new_over_old_diff": _unpaired_diff([r["late_new_over_old"] for r in swap_summ], [r["late_new_over_old"] for r in v4_sw], n_boot, seed + 2003),
        }
    return out


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--log", required=True); p.add_argument("--manifest", required=True); p.add_argument("--out-dir", required=True)
    p.add_argument("--v4-log", default=V4_LOG); p.add_argument("--no-v4", action="store_true")
    p.add_argument("--n-boot", type=int, default=5000); p.add_argument("--n-perm", type=int, default=10000); p.add_argument("--seed", type=int, default=20260902)
    a = p.parse_args(argv)
    records = load(a.log); manifest = json.load(open(a.manifest))
    v4 = None if (a.no_v4 or not os.path.exists(a.v4_log)) else load(a.v4_log)
    out = analyze(records, manifest, v4, a.n_boot, a.n_perm, a.seed); out["log"] = a.log; out["v4_log"] = None if v4 is None else a.v4_log
    os.makedirs(os.path.join(a.out_dir, "tables"), exist_ok=True)
    json.dump(out, open(os.path.join(a.out_dir, "elicited_choice_summary.json"), "w"), indent=2, sort_keys=True)
    with open(os.path.join(a.out_dir, "tables", "elicited_swap_episodes.csv"), "w", newline="") as h:
        w = csv.DictWriter(h, fieldnames=list(out["swap_episode_summaries"][0].keys())); w.writeheader(); w.writerows(out["swap_episode_summaries"])
    with open(os.path.join(a.out_dir, "tables", "elicited_round_trajectories.csv"), "w", newline="") as h:
        w = csv.writer(h); w.writerow(["condition", "metric", "round", "mean", "n"])
        for c, d in out["trajectories"].items():
            for m, rows in d.items():
                for r in rows: w.writerow([c, m, r["round"], r["mean"], r["n"]])
    s = out["stable_condition_metrics"]["elicited_full_history"]; g = s["learning_gain"]; sw = out["swap_metrics"]
    print("E1 verdict: %s  (valid %.3f, beliefs valid %.3f, fallback %.3f)" % (out["verdict"], out["valid_selection_rate"], out["belief_valid_rate"], out["fallback_rate"]))
    print("  elicited_full_history: early %.3f -> late held-out %.3f; gain %.3f [%.3f, %.3f] p=%.4f (n=%d)" % (s["early_match"]["mean"], s["late_heldout_match"]["mean"], g["mean"], g["ci_lo"], g["ci_hi"], g["p_value_one_sided"], s["n_episodes"]))
    print("  elicited_swap: new gain %.3f, old drop %.3f, new-over-old %.3f p=%.4f, adapted %d/%d" % (sw["new_target_gain"]["mean"], sw["old_target_drop"]["mean"], sw["late_new_over_old"]["mean"], sw["late_new_over_old"]["p_value_one_sided"], sw["n_adapted"], sw["n_episodes"]))
    if "cross_prompt_comparison_vs_v4_spontaneous" in out:
        c = out["cross_prompt_comparison_vs_v4_spontaneous"]
        print("  vs V4 spontaneous: learning gain diff %.3f [%.3f, %.3f]; swap new-gain diff %.3f [%.3f, %.3f]" % (c["learning_gain_diff"]["mean"], c["learning_gain_diff"]["ci_lo"], c["learning_gain_diff"]["ci_hi"], c["swap_new_target_gain_diff"]["mean"], c["swap_new_target_gain_diff"]["ci_lo"], c["swap_new_target_gain_diff"]["ci_hi"]))
    print("wrote", os.path.join(a.out_dir, "elicited_choice_summary.json")); return 0


if __name__ == "__main__":
    raise SystemExit(main())
