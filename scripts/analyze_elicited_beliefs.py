"""Secondary analysis for the elicited-belief arm (V4_REPLICATION_DECLARATION, Arm E1).

The frozen V4 analyzer (scripts/analyze_controlled_v4.py) remains the primary
analysis of the elicited arm's *choices*. This script reads the same log and
adds the pre-declared secondary readouts about the *stated* beliefs:

  * belief validity and fallback rates;
  * stated-belief accuracy (argmax p_a frame == hidden target frame) by round,
    against the choice accuracy on the same records;
  * belief/choice agreement by round;
  * after the silent swap: share of stated beliefs and of choices that match
    the NEW target frame, by rounds since swap, plus their difference
    (belief minus choice) -- a positive value means the stated belief moves to
    the new frame before the choice does;
  * stated p_a of the selected candidate vs the realized target P(A) (calibration)
    and the mean Brier score of the selected candidate's stated probability.

Uncertainty: percentile bootstrap over episodes (episodes are the exchangeable
unit).  No first-crossing statistic is computed (declaration: its lag is biased
under an uninformative probe).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def load_records(path: str) -> list[dict]:
    with open(path, "r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _episode_bootstrap(per_episode: dict[str, list[float]], n_boot: int, rng: np.random.Generator):
    """Mean of per-record values, CI from resampling episodes with replacement."""
    keys = sorted(per_episode)
    if not keys:
        return None, None, None, 0
    sums = np.asarray([float(np.sum(per_episode[k])) for k in keys])
    counts = np.asarray([len(per_episode[k]) for k in keys], dtype=float)
    mean = float(sums.sum() / counts.sum())
    if n_boot <= 0 or len(keys) < 2:
        return mean, mean, mean, int(counts.sum())
    idx = rng.integers(0, len(keys), size=(n_boot, len(keys)))
    boot = sums[idx].sum(axis=1) / counts[idx].sum(axis=1)
    lo, hi = np.percentile(boot, [2.5, 97.5])
    return mean, float(lo), float(hi), int(counts.sum())


def _paired_diff_bootstrap(per_episode_a, per_episode_b, n_boot, rng):
    """Bootstrap over episodes of mean(a) - mean(b) where both are keyed by episode."""
    keys = sorted(set(per_episode_a) & set(per_episode_b))
    if not keys:
        return None, None, None, 0
    sa = np.asarray([float(np.sum(per_episode_a[k])) for k in keys])
    ca = np.asarray([len(per_episode_a[k]) for k in keys], dtype=float)
    sb = np.asarray([float(np.sum(per_episode_b[k])) for k in keys])
    cb = np.asarray([len(per_episode_b[k]) for k in keys], dtype=float)
    diff = float(sa.sum() / ca.sum() - sb.sum() / cb.sum())
    if n_boot <= 0 or len(keys) < 2:
        return diff, diff, diff, len(keys)
    idx = rng.integers(0, len(keys), size=(n_boot, len(keys)))
    boot = sa[idx].sum(axis=1) / ca[idx].sum(axis=1) - sb[idx].sum(axis=1) / cb[idx].sum(axis=1)
    lo, hi = np.percentile(boot, [2.5, 97.5])
    return diff, float(lo), float(hi), len(keys)


def _by_key(records, key_fn, value_fn):
    out: dict = defaultdict(lambda: defaultdict(list))
    for r in records:
        k = key_fn(r)
        if k is None:
            continue
        v = value_fn(r)
        if v is None:
            continue
        out[k][r["episode_id"]].append(float(v))
    return out


def _stated_p_selected(r):
    p = r.get("predicted_p_a")
    slot = r.get("selected_slot")
    if slot is None:
        # recover the selected slot from the candidates list
        for c in r.get("candidates", []):
            if c.get("candidate_id") == r.get("selected_candidate_id"):
                slot = c.get("slot")
                break
    if not isinstance(p, dict) or slot is None:
        return None
    try:
        return float(p[str(slot)])
    except (KeyError, TypeError, ValueError):
        return None


def analyze(records: list[dict], n_boot: int = 5000, seed: int = 20260903) -> dict:
    rng = np.random.default_rng(seed)
    conditions = sorted({r["condition"] for r in records})
    elicited = [r for r in records if r["condition"].startswith("elicited_")]
    out: dict = {
        "n_records": len(records),
        "n_elicited_records": len(elicited),
        "conditions": conditions,
        "n_boot": n_boot,
        "seed": seed,
    }
    # validity
    valid = [r for r in elicited if r.get("beliefs_valid") and r.get("selection_valid") and not r.get("fallback_used")]
    out["belief_validity"] = {
        "beliefs_valid_rate": float(np.mean([bool(r.get("beliefs_valid")) for r in elicited])) if elicited else None,
        "selection_valid_rate": float(np.mean([bool(r.get("selection_valid")) for r in elicited])) if elicited else None,
        "fallback_rate": float(np.mean([bool(r.get("fallback_used")) for r in elicited])) if elicited else None,
        "n_fully_valid": len(valid),
    }
    per_condition = {}
    for cond in conditions:
        rows = [r for r in valid if r["condition"] == cond]
        if not rows:
            continue
        block: dict = {"n_records": len(rows), "n_episodes": len({r["episode_id"] for r in rows})}
        # by round: belief accuracy vs choice accuracy, agreement
        bel_by_round = _by_key(rows, lambda r: r["round"], lambda r: r["belief_primary_frame"] == r["hidden_target_type"])
        cho_by_round = _by_key(rows, lambda r: r["round"], lambda r: r["selected_frame"] == r["hidden_target_type"])
        agree_by_round = _by_key(rows, lambda r: r["round"], lambda r: r["belief_primary_frame"] == r["selected_frame"])
        block["by_round"] = []
        for rd in sorted(bel_by_round):
            b = _episode_bootstrap(bel_by_round[rd], n_boot, rng)
            c = _episode_bootstrap(cho_by_round[rd], n_boot, rng)
            a = _episode_bootstrap(agree_by_round[rd], n_boot, rng)
            d = _paired_diff_bootstrap(bel_by_round[rd], cho_by_round[rd], n_boot, rng)
            block["by_round"].append({
                "round": rd, "n": b[3],
                "belief_matches_target": {"mean": b[0], "ci_low": b[1], "ci_high": b[2]},
                "choice_matches_target": {"mean": c[0], "ci_low": c[1], "ci_high": c[2]},
                "belief_choice_agreement": {"mean": a[0], "ci_low": a[1], "ci_high": a[2]},
                "belief_minus_choice": {"mean": d[0], "ci_low": d[1], "ci_high": d[2]},
            })
        # swap: by rounds since swap, matches NEW (final) target
        if any(r.get("swap_condition") for r in rows):
            bel_new = _by_key(rows, lambda r: r["rounds_since_swap"], lambda r: r["belief_primary_frame"] == r["final_target_type"])
            cho_new = _by_key(rows, lambda r: r["rounds_since_swap"], lambda r: r["selected_frame"] == r["final_target_type"])
            bel_old = _by_key(rows, lambda r: r["rounds_since_swap"], lambda r: r["belief_primary_frame"] == r["initial_target_type"])
            cho_old = _by_key(rows, lambda r: r["rounds_since_swap"], lambda r: r["selected_frame"] == r["initial_target_type"])
            block["by_rounds_since_swap"] = []
            for k in sorted(bel_new):
                bn = _episode_bootstrap(bel_new[k], n_boot, rng)
                cn = _episode_bootstrap(cho_new[k], n_boot, rng)
                bo = _episode_bootstrap(bel_old[k], n_boot, rng)
                co = _episode_bootstrap(cho_old[k], n_boot, rng)
                d = _paired_diff_bootstrap(bel_new[k], cho_new[k], n_boot, rng)
                block["by_rounds_since_swap"].append({
                    "rounds_since_swap": k, "n": bn[3],
                    "belief_matches_new": {"mean": bn[0], "ci_low": bn[1], "ci_high": bn[2]},
                    "choice_matches_new": {"mean": cn[0], "ci_low": cn[1], "ci_high": cn[2]},
                    "belief_matches_old": {"mean": bo[0], "ci_low": bo[1], "ci_high": bo[2]},
                    "choice_matches_old": {"mean": co[0], "ci_low": co[1], "ci_high": co[2]},
                    "belief_minus_choice_new": {"mean": d[0], "ci_low": d[1], "ci_high": d[2]},
                })
            # pre-declared summary: mean over post-swap rounds 1..5 of (belief_new - choice_new)
            early_post = [r for r in rows if r.get("swap_has_occurred") and 1 <= r["rounds_since_swap"] <= 5]
            bn = _by_key(early_post, lambda r: "all", lambda r: r["belief_primary_frame"] == r["final_target_type"])
            cn = _by_key(early_post, lambda r: "all", lambda r: r["selected_frame"] == r["final_target_type"])
            d = _paired_diff_bootstrap(bn.get("all", {}), cn.get("all", {}), n_boot, rng)
            block["post_swap_rounds_1_to_5_belief_minus_choice_new"] = {"mean": d[0], "ci_low": d[1], "ci_high": d[2], "n_episodes": d[3]}
            # by transition
            block["by_transition"] = {}
            for tr in sorted({(r["initial_target_type"], r["final_target_type"]) for r in rows if r.get("swap_condition")}):
                sub = [r for r in early_post if (r["initial_target_type"], r["final_target_type"]) == tr]
                bn = _by_key(sub, lambda r: "all", lambda r: r["belief_primary_frame"] == r["final_target_type"])
                cn = _by_key(sub, lambda r: "all", lambda r: r["selected_frame"] == r["final_target_type"])
                b = _episode_bootstrap(bn.get("all", {}), n_boot, rng)
                c = _episode_bootstrap(cn.get("all", {}), n_boot, rng)
                block["by_transition"]["%s_to_%s" % tr] = {
                    "n_records": len(sub), "n_episodes": len({r["episode_id"] for r in sub}),
                    "belief_matches_new": {"mean": b[0], "ci_low": b[1], "ci_high": b[2]},
                    "choice_matches_new": {"mean": c[0], "ci_low": c[1], "ci_high": c[2]},
                }
        # calibration of the stated p_a for the selected candidate
        stated = [(_stated_p_selected(r), r.get("target_p_a"), r.get("selected_prediction_brier"), r["episode_id"]) for r in rows]
        stated = [s for s in stated if s[0] is not None and s[1] is not None]
        if stated:
            by_ep_stated = defaultdict(list); by_ep_real = defaultdict(list); by_ep_brier = defaultdict(list)
            for p, q, br, ep in stated:
                by_ep_stated[ep].append(p); by_ep_real[ep].append(q)
                if br is not None:
                    by_ep_brier[ep].append(br)
            s = _episode_bootstrap(by_ep_stated, n_boot, rng)
            q = _episode_bootstrap(by_ep_real, n_boot, rng)
            b = _episode_bootstrap(by_ep_brier, n_boot, rng)
            # does the stated p_a discriminate the realized target regime (0.72 vs 0.38)?
            hi = [p for p, qq, _, _ in stated if qq >= 0.5]; lo = [p for p, qq, _, _ in stated if qq < 0.5]
            block["stated_p_a_selected"] = {
                "mean_stated": {"mean": s[0], "ci_low": s[1], "ci_high": s[2]},
                "mean_realized_target_p_a": {"mean": q[0], "ci_low": q[1], "ci_high": q[2]},
                "brier_selected": {"mean": b[0], "ci_low": b[1], "ci_high": b[2]},
                "mean_stated_when_match_regime": float(np.mean(hi)) if hi else None,
                "mean_stated_when_mismatch_regime": float(np.mean(lo)) if lo else None,
                "n": len(stated),
            }
        per_condition[cond] = block
    out["per_condition"] = per_condition
    return out


def make_figure(summary: dict, path: str) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    conds = [c for c in summary["per_condition"] if "by_round" in summary["per_condition"][c]]
    n_panels = len(conds) + (1 if any("by_rounds_since_swap" in summary["per_condition"][c] for c in conds) else 0)
    fig, axes = plt.subplots(1, max(n_panels, 1), figsize=(5.2 * max(n_panels, 1), 3.8))
    axes = np.atleast_1d(axes)
    i = 0
    for cond in conds:
        block = summary["per_condition"][cond]
        ax = axes[i]; i += 1
        rows = block["by_round"]
        x = [r["round"] for r in rows]
        for key, label, color in (("belief_matches_target", "stated belief = target frame", "#1f77b4"),
                                  ("choice_matches_target", "choice = target frame", "#d62728"),
                                  ("belief_choice_agreement", "belief = choice", "#7f7f7f")):
            m = [r[key]["mean"] for r in rows]; lo = [r[key]["ci_low"] for r in rows]; hi = [r[key]["ci_high"] for r in rows]
            ax.plot(x, m, marker="o", ms=3, color=color, label=label)
            ax.fill_between(x, lo, hi, color=color, alpha=0.15)
        ax.axhline(1 / 3, ls=":", color="k", lw=0.8)
        ax.set_ylim(0, 1); ax.set_xlabel("round"); ax.set_title(cond, fontsize=10)
        ax.set_ylabel("share of episodes"); ax.legend(fontsize=7, loc="lower right")
    for cond in conds:
        block = summary["per_condition"][cond]
        if "by_rounds_since_swap" not in block:
            continue
        ax = axes[i]
        rows = block["by_rounds_since_swap"]
        x = [r["rounds_since_swap"] for r in rows]
        for key, label, color in (("belief_matches_new", "stated belief = NEW frame", "#1f77b4"),
                                  ("choice_matches_new", "choice = NEW frame", "#d62728")):
            m = [r[key]["mean"] for r in rows]; lo = [r[key]["ci_low"] for r in rows]; hi = [r[key]["ci_high"] for r in rows]
            ax.plot(x, m, marker="o", ms=3, color=color, label=label)
            ax.fill_between(x, lo, hi, color=color, alpha=0.15)
        ax.axvline(0.5, ls="--", color="k", lw=0.8); ax.axhline(1 / 3, ls=":", color="k", lw=0.8)
        ax.set_ylim(0, 1); ax.set_xlabel("rounds since silent swap"); ax.set_title("%s: revision" % cond, fontsize=10)
        ax.legend(fontsize=7, loc="lower right")
        break
    fig.tight_layout(); fig.savefig(path, dpi=150); plt.close(fig)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--n-boot", type=int, default=5000)
    parser.add_argument("--seed", type=int, default=20260903)
    args = parser.parse_args(argv)
    records = load_records(args.log)
    summary = analyze(records, n_boot=args.n_boot, seed=args.seed)
    summary["log"] = args.log
    os.makedirs(args.out_dir, exist_ok=True)
    with open(os.path.join(args.out_dir, "elicited_belief_summary.json"), "w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2, sort_keys=True)
    make_figure(summary, os.path.join(args.out_dir, "fig_elicited_beliefs.png"))
    v = summary["belief_validity"]
    print("records: %d (elicited %d); beliefs_valid %.3f  selection_valid %.3f  fallback %.3f" % (
        summary["n_records"], summary["n_elicited_records"], v["beliefs_valid_rate"] or 0, v["selection_valid_rate"] or 0, v["fallback_rate"] or 0))
    for cond, block in summary["per_condition"].items():
        last = block["by_round"][-1]
        print("%s: n_ep=%d  last round belief=target %.3f  choice=target %.3f  agreement %.3f" % (
            cond, block["n_episodes"], last["belief_matches_target"]["mean"], last["choice_matches_target"]["mean"], last["belief_choice_agreement"]["mean"]))
        if "post_swap_rounds_1_to_5_belief_minus_choice_new" in block:
            d = block["post_swap_rounds_1_to_5_belief_minus_choice_new"]
            print("  post-swap rounds 1-5: belief_new - choice_new = %.3f [%.3f, %.3f] (n_ep=%d)" % (d["mean"], d["ci_low"], d["ci_high"], d["n_episodes"]))
        if "stated_p_a_selected" in block:
            s = block["stated_p_a_selected"]
            print("  stated p_a(selected) mean %.3f vs realized %.3f; Brier %.3f; stated|match %.3f stated|mismatch %.3f" % (
                s["mean_stated"]["mean"], s["mean_realized_target_p_a"]["mean"], s["brier_selected"]["mean"] or 0,
                s["mean_stated_when_match_regime"] or 0, s["mean_stated_when_mismatch_regime"] or 0))
    print("wrote", os.path.join(args.out_dir, "elicited_belief_summary.json"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
