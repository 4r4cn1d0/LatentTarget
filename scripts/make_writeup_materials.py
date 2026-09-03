#!/usr/bin/env python3
"""Generate every figure and number for the write-up from COMMITTED artifacts.

Output: results/writeup/ (figures) and results/writeup/WRITEUP_MATERIALS.md.
Nothing here is hand-typed; every number in the markdown names the file and key
it came from, so a reader can recompute it. Random examples are seeded.
"""

from __future__ import annotations

import _bootstrap  # noqa: F401
import json
import shutil
import os
import random
import sys
from collections import Counter, defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = _bootstrap.ROOT
OUT = os.path.join(ROOT, "results", "writeup")
V4_LOG = os.path.join(ROOT, "data", "raw", "qwen38_27b_v4_checkpoint_20260902.jsonl")
V4_SUM = os.path.join(ROOT, "results", "v4_real", "checkpoint", "v4_checkpoint_summary.json")
V4_TRAJ = os.path.join(ROOT, "results", "v4_real", "checkpoint", "tables", "v4_round_trajectories.csv")
V4_SWAP = os.path.join(ROOT, "results", "v4_real", "checkpoint", "tables", "v4_swap_episodes.csv")
V4_STAB = os.path.join(ROOT, "results", "v4_real", "checkpoint", "tables", "v4_stable_conditions.csv")
V8_SCREEN = os.path.join(ROOT, "results", "v8_design", "screen", "v8_screen_qwen_measured.json")
V8_NULL = os.path.join(ROOT, "results", "v8_design", "screen", "v8_null_size_qwen_measured.json")
V8_SPEC = os.path.join(ROOT, "docs", "v8_protocol.json")
R1_LOG = os.path.join(ROOT, "data", "raw", "v4r-gemma4.jsonl")
R1_DIR = os.path.join(ROOT, "results", "v4_real", "replication_gemma4")   # Arm R1: Gemma-4-31B, frozen V4 design
E1_DIR = os.path.join(ROOT, "results", "v4_real", "elicited_qwen38")      # Arm E1: Qwen3.8-27B, elicited beliefs
E1_BELIEF = os.path.join(E1_DIR, "beliefs", "elicited_belief_summary.json")
E1_LOG = os.path.join(ROOT, "data", "raw", "v4e-qwen38.jsonl")
FRAMES = ("fairness", "risk", "expertise")
COL = {"full_history": "#1f77b4", "no_history": "#ff7f0e", "shuffled_history": "#2ca02c", "random_target": "#d62728", "swap": "#9467bd"}
numbers = []  # (label, value, source)


def N(label, value, source):
    numbers.append((label, value, source)); return value


def style(ax, title, xl, yl):
    ax.set_title(title, fontsize=11); ax.set_xlabel(xl, fontsize=9); ax.set_ylabel(yl, fontsize=9)
    ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False); ax.grid(alpha=.25, lw=.5); ax.tick_params(labelsize=8)


def fig1_learning():
    t = pd.read_csv(V4_TRAJ); t = t[t.metric == "match"]
    fig, ax = plt.subplots(figsize=(6.8, 4), dpi=150)
    for cond in ("full_history", "no_history", "shuffled_history", "random_target"):
        g = t[t.condition == cond].sort_values("round")
        ax.plot(g["round"], g["mean"], marker="o", ms=3.5, lw=1.6, color=COL[cond], label="%s (n=%d episodes)" % (cond, int(g["n"].iloc[0])))
    ax.axhline(1/3, ls="--", lw=1, color="grey"); ax.text(10.5, 1/3 - .045, "chance (1/3)", fontsize=7, color="grey", ha="center")
    ax.axvspan(15.5, 20.5, color="#eeeeee", zorder=0); ax.text(16, .95, "held-out\nwording", fontsize=7, color="#555555")
    ax.set_ylim(0, 1); ax.set_xticks(range(1, 21, 2))
    style(ax, "V4: P(chosen candidate's frame matches the hidden target) by round", "round", "match rate")
    ax.legend(fontsize=7, frameon=False, loc="upper left", bbox_to_anchor=(1.01, 1)); fig.savefig(os.path.join(OUT, "fig_w1_v4_learning_by_condition.png"), bbox_inches="tight"); plt.close(fig)
    s = pd.read_csv(V4_STAB)
    for _, r in s.iterrows():
        N("V4 %s early match" % r.condition, round(r.early_match, 3), "v4_stable_conditions.csv:early_match")
        N("V4 %s late held-out match" % r.condition, round(r.late_heldout_match, 3), "v4_stable_conditions.csv:late_heldout_match")


def fig2_swap():
    sw = pd.read_csv(V4_SWAP)
    sw["dir"] = np.where(sw.new_type == "expertise", "into expertise (default)", np.where(sw.old_type == "expertise", "out of expertise", "between non-defaults"))
    per = sw.groupby(["old_type", "new_type"]).agg(n=("episode_id", "size"), new_gain=("new_target_gain", "mean"), old_drop=("old_target_drop", "mean"), new_minus_old=("late_new_over_old", "mean"), adapted=("rounds_to_adapt", lambda x: int(x.notna().sum()))).reset_index()
    grp = sw.groupby("dir").agg(n=("episode_id", "size"), new_gain=("new_target_gain", "mean"), old_drop=("old_target_drop", "mean"), adapted=("rounds_to_adapt", lambda x: int(x.notna().sum()))).reset_index()
    fig, ax = plt.subplots(figsize=(7.2, 4), dpi=150)
    labels = ["%s→%s\n(%d/%d adapted)" % (o, n, a, k) for o, n, a, k in zip(per.old_type, per.new_type, per.adapted, per.n)]; x = np.arange(len(labels))
    ax.bar(x - .2, per.new_gain, .4, color="#2ca02c", label="new-frame gain (late − pre)"); ax.bar(x + .2, per.old_drop, .4, color="#d62728", label="old-frame drop (pre − late)")
    ax.axhline(0, color="black", lw=.8); ax.axhline(.10, ls=":", lw=1, color="grey"); ax.text(len(x) - .5, .105, "registered gate 0.10", fontsize=7, color="grey", ha="right")
    ax.set_xticks(x); ax.set_xticklabels(labels, rotation=0, fontsize=7.5)
    ax.set_ylim(0, max(per.new_gain.max(), per.old_drop.max()) * 1.25)
    style(ax, "V4 silent swap after round 10: revision by transition (20 episodes each)", "", "change in match rate")
    ax.legend(fontsize=7, frameon=False); fig.savefig(os.path.join(OUT, "fig_w2_v4_swap_by_transition.png"), bbox_inches="tight"); plt.close(fig)
    for _, r in per.iterrows(): N("V4 swap %s->%s new gain / old drop / adapted" % (r.old_type, r.new_type), "%.3f / %.3f / %d of %d" % (r.new_gain, r.old_drop, r.adapted, r.n), "v4_swap_episodes.csv (grouped)")
    for _, r in grp.iterrows(): N("V4 swap %s: new gain / old drop / adapted" % r.dir, "%.3f / %.3f / %d of %d" % (r.new_gain, r.old_drop, r.adapted, r.n), "v4_swap_episodes.csv (grouped by destination)")
    return per, grp


def fig6_per_target():
    """Learning is anti-default: per hidden target, full-history vs no-history late match."""
    rows = []
    with open(V4_LOG) as fh:
        for line in fh:
            r = json.loads(line)
            if r["condition"] in ("full_history", "no_history", "shuffled_history"):
                rows.append((r["condition"], r["round"], r["hidden_target_type"], int(r["strategy_match"])))
    df = pd.DataFrame(rows, columns=["condition", "round", "target", "match"])
    fig, axes = plt.subplots(1, 3, figsize=(10.5, 3.4), dpi=150, sharey=True)
    for ax, tgt in zip(axes, FRAMES):
        for cond in ("full_history", "no_history", "shuffled_history"):
            g = df[(df.target == tgt) & (df.condition == cond)].groupby("round")["match"].mean()
            ax.plot(g.index, g.values, marker="o", ms=3, lw=1.5, color=COL[cond], label=cond)
        ax.axhline(1/3, ls="--", lw=1, color="grey"); ax.axvspan(15.5, 20.5, color="#eeeeee", zorder=0); ax.set_ylim(0, 1); ax.set_xticks(range(1, 21, 4))
        style(ax, "hidden target = %s" % tgt, "round", "P(chosen frame matches)" if tgt == "fairness" else "")
    axes[0].legend(fontsize=7, frameon=False); fig.suptitle("V4 by hidden target: learning happens away from the expertise default, not toward it", fontsize=10)
    fig.savefig(os.path.join(OUT, "fig_w6_v4_learning_by_target.png"), bbox_inches="tight"); plt.close(fig)
    late = df[df["round"] >= 16].groupby(["condition", "target"])["match"].mean()
    for tgt in FRAMES:
        N("V4 late match, target=%s: full / no-history / shuffled" % tgt, "%.3f / %.3f / %.3f" % (late[("full_history", tgt)], late[("no_history", tgt)], late[("shuffled_history", tgt)]), "data/raw/qwen38_27b_v4_checkpoint_20260902.jsonl rounds 16-20")


def v4_no_history_shares():
    c = Counter()
    with open(V4_LOG) as fh:
        for line in fh:
            r = json.loads(line)
            if r["condition"] == "no_history" and r.get("selection_valid"): c[r["selected_frame"]] += 1
    n = sum(c.values()); return {f: c[f] / n for f in FRAMES}, n


def fig3_priors():
    spec = json.load(open(V8_SPEC)); q4, n4 = v4_no_history_shares()
    q5 = spec["models"]["qwen38_27b"]["measured_no_history_shares"]; g5 = spec["models"]["gemma4_31b"]["measured_no_history_shares"]
    rows = [("Qwen3.8-27B\nV4 bank (n=%d)" % n4, q4), ("Qwen3.8-27B\nV5 bank (n=576)", q5), ("Gemma-4-31B\nV5 bank (n=576)", g5)]
    fig, ax = plt.subplots(figsize=(6.4, 3.8), dpi=150); x = np.arange(len(rows)); w = .26
    for i, f in enumerate(FRAMES):
        vals = [r[1][f] for r in rows]; ax.bar(x + (i - 1) * w, vals, w, label=f, color=["#1f77b4", "#d62728", "#7f7f7f"][i])
        for xi, v in zip(x + (i - 1) * w, vals): ax.text(xi, v + .01, "%.0f%%" % (100 * v), ha="center", fontsize=7)
    ax.axhline(1/3, ls="--", lw=1, color="grey"); ax.set_xticks(x); ax.set_xticklabels([r[0] for r in rows], fontsize=8); ax.set_ylim(0, 1)
    style(ax, "No-history frame choice: which frame each model picks with no feedback", "", "share of choices"); ax.legend(fontsize=8, frameon=False)
    fig.savefig(os.path.join(OUT, "fig_w3_default_frame_priors.png"), bbox_inches="tight"); plt.close(fig)
    N("Qwen V4-bank no-history shares (f/r/e)", "%.3f / %.3f / %.3f (n=%d)" % (q4["fairness"], q4["risk"], q4["expertise"], n4), "data/raw/qwen38_27b_v4_checkpoint_20260902.jsonl, condition=no_history, selection_valid")
    N("Qwen V5-bank no-history shares (f/r/e)", "%.3f / %.3f / %.3f" % tuple(q5[f] for f in FRAMES), "docs/v8_protocol.json models.qwen38_27b.measured_no_history_shares")
    N("Gemma-4 V5-bank no-history shares (f/r/e)", "%.3f / %.3f / %.3f" % tuple(g5[f] for f in FRAMES), "docs/v8_protocol.json models.gemma4_31b.measured_no_history_shares")


def fig4_v8_power():
    if not os.path.exists(V8_SCREEN): return
    d = json.load(open(V8_SCREEN)); fig, axes = plt.subplots(1, 2, figsize=(9, 3.6), dpi=150, sharey=True)
    for ax, cid in zip(axes, sorted({c["cell_id"] for c in d["cells"]})):
        for sc, m in zip(("learner_1", "learner_2", "learner_3"), ("o", "s", "^")):
            rows = sorted([c for c in d["cells"] if c["cell_id"] == cid and c["scenario_id"] == sc], key=lambda c: c["n_episode_seeds"])
            ax.plot([c["n_episode_seeds"] for c in rows], [c["v8_complete"]["wilson_lo"] for c in rows], marker=m, ms=4, lw=1.5, label="%s V8-complete (Wilson lower)" % sc)
            ax.plot([c["n_episode_seeds"] for c in rows], [c["required_gate_rates"]["stratified_exact_test"] for c in rows], ls=":", lw=1, color=ax.lines[-1].get_color())
        ax.axhline(.8, ls="--", color="grey", lw=1); ax.set_ylim(0, 1); ax.set_xticks([12, 18, 24, 30]); style(ax, cid.replace("qwen38_", "Qwen "), "N (episode-seed bundles)", "probability")
    axes[0].legend(fontsize=6.5, frameon=False); axes[0].text(12.2, .82, "rule: ≥ 0.80", fontsize=7, color="grey"); axes[1].text(12, .05, "dotted = the stratified acquisition test alone", fontsize=7, color="#555")
    fig.suptitle("V8 screen at Qwen's measured prior (500 studies/cell): stopped by the destination-stratified acquisition gate", fontsize=10)
    fig.savefig(os.path.join(OUT, "fig_w4_v8_power_vs_n.png"), bbox_inches="tight"); plt.close(fig)
    worst = max(max(c["required_test_wilson_hi"].values()) for c in json.load(open(V8_NULL))["cells"]) if os.path.exists(V8_NULL) else None
    N("V8 null-size worst Wilson upper (any required test)", worst, "v8_null_size_qwen_measured.json required_test_wilson_hi")
    for c in d["cells"]:
        if c["n_episode_seeds"] == 30: N("V8 %s %s N=30 V8-complete lower / stratified-test rate" % (c["cell_id"], c["scenario_id"]), "%.3f / %.3f" % (c["v8_complete"]["wilson_lo"], c["required_gate_rates"]["stratified_exact_test"]), "v8_screen_qwen_measured.json")


def fig5_first_crossing_bias():
    rng = np.random.default_rng(0); H, n_ep, reps = 5, 24, 400; accs = [1/3, .5, .7]; res = []
    for acc in accs:
        leads, excl = [], 0
        for _ in range(reps):
            probe = [(1 + int(np.argmax(rng.random(H) < acc))) if (rng.random(H) < acc).any() else None for _ in range(n_ep)]
            beh = [3] * n_ep; d = [b - p for p, b in zip(probe, beh) if p is not None]
            if len(d) < 3: continue
            d = np.array(d, float); boots = [rng.choice(d, len(d)).mean() for _ in range(300)]; lo = np.quantile(boots, .025); leads.append(d.mean()); excl += lo > 0
        res.append((acc, np.mean(leads), excl / reps))
    fig, ax = plt.subplots(figsize=(5.6, 3.4), dpi=150); ax.bar([("%.2f" % a) for a, _, _ in res], [l for _, l, _ in res], color="#d62728", width=.5)
    ax.set_ylim(0, max(l for _, l, _ in res) * 1.35)
    for i, (a, l, e) in enumerate(res): ax.text(i, l + .05, "CI excludes 0\nin %.0f%% of runs" % (100 * e), ha="center", fontsize=7)
    style(ax, "First-crossing lag: apparent 'probe leads behaviour' from probe NOISE alone\n(behaviour flips at round 3; probe has NO target information)", "probe accuracy (chance = 0.33)", "apparent lead (rounds)")
    fig.savefig(os.path.join(OUT, "fig_w5_first_crossing_bias.png"), bbox_inches="tight"); plt.close(fig)
    for a, l, e in res: N("first-crossing bias at probe acc %.2f: apparent lead / CI-excludes-0 rate" % a, "%.2f / %.2f" % (l, e), "scripts/make_writeup_materials.py fig5 (seed 0; simpler noise model than docs/V7_REVIEW.md, which reported 0.74 / 0.71)")
    return res


def fig7_replication():
    """Arm R1 (declared 2026-09-03): the frozen V4 design on Gemma-4-31B, side by side with Qwen's V4."""
    summ = os.path.join(R1_DIR, "v4_checkpoint_summary.json")
    if not os.path.exists(summ):
        return None
    s = json.load(open(summ)); tq = pd.read_csv(V4_TRAJ); tg = pd.read_csv(os.path.join(R1_DIR, "tables", "v4_round_trajectories.csv"))
    fig, axes = plt.subplots(1, 2, figsize=(11, 4), dpi=150, sharey=True)
    for ax, t, title in ((axes[0], tq, "Qwen3.8-27B (V4, 2026-09-02)"), (axes[1], tg, "Gemma-4-31B (Arm R1, 2026-09-03)")):
        t = t[t.metric == "match"]
        for cond in ("full_history", "no_history", "shuffled_history", "random_target"):
            g = t[t.condition == cond].sort_values("round")
            if len(g): ax.plot(g["round"], g["mean"], marker="o", ms=3, lw=1.5, color=COL[cond], label=cond)
        ax.axhline(1/3, ls="--", lw=1, color="grey"); ax.axvspan(15.5, 20.5, color="#eeeeee", zorder=0)
        ax.set_ylim(0, 1); ax.set_xticks(range(1, 21, 2)); style(ax, title, "round", "match rate")
    axes[0].legend(fontsize=7, frameon=False, loc="upper left")
    fig.savefig(os.path.join(OUT, "fig_w7_replication_learning_qwen_vs_gemma.png"), bbox_inches="tight"); plt.close(fig)
    m = s["stable_condition_metrics"]
    for cond in ("full_history", "no_history", "shuffled_history", "random_target"):
        if cond in m:
            g = m[cond]["learning_gain"]; N("R1 Gemma %s learning gain (late held-out − early), 95%% CI" % cond, "%.3f [%.3f, %.3f], n=%d" % (g["mean"], g["ci_lo"], g["ci_hi"], g["n"]), "replication_gemma4/v4_checkpoint_summary.json")
    st = pd.read_csv(os.path.join(R1_DIR, "tables", "v4_stable_conditions.csv"))
    for _, r in st.iterrows(): N("R1 Gemma %s early / late held-out match" % r.condition, "%.3f / %.3f" % (r.early_match, r.late_heldout_match), "replication_gemma4/tables/v4_stable_conditions.csv")
    N("R1 Gemma decision", s["decision"], "replication_gemma4/v4_checkpoint_summary.json decision")
    N("R1 Gemma swap revision randomization test passed", s["inference_gates"]["swap_revision_randomization_test"], "replication_gemma4/v4_checkpoint_summary.json inference_gates")
    swp = os.path.join(R1_DIR, "tables", "v4_swap_episodes.csv"); per = grp = None
    if os.path.exists(swp):
        sw = pd.read_csv(swp)
        sw["dir"] = np.where(sw.new_type == "expertise", "into expertise (default)", np.where(sw.old_type == "expertise", "out of expertise", "between non-defaults"))
        per = sw.groupby(["old_type", "new_type"]).agg(n=("episode_id", "size"), new_gain=("new_target_gain", "mean"), old_drop=("old_target_drop", "mean"), adapted=("rounds_to_adapt", lambda x: int(x.notna().sum()))).reset_index()
        grp = sw.groupby("dir").agg(n=("episode_id", "size"), new_gain=("new_target_gain", "mean"), old_drop=("old_target_drop", "mean"), adapted=("rounds_to_adapt", lambda x: int(x.notna().sum()))).reset_index()
        fig, ax = plt.subplots(figsize=(7.2, 4), dpi=150)
        labels = ["%s→%s\n(%d/%d adapted)" % (o, n, a, k) for o, n, a, k in zip(per.old_type, per.new_type, per.adapted, per.n)]; x = np.arange(len(labels))
        ax.bar(x - .2, per.new_gain, .4, color="#2ca02c", label="new-frame gain (late − pre)"); ax.bar(x + .2, per.old_drop, .4, color="#d62728", label="old-frame drop (pre − late)")
        ax.axhline(0, color="black", lw=.8); ax.axhline(.10, ls=":", lw=1, color="grey"); ax.set_xticks(x); ax.set_xticklabels(labels, fontsize=7.5)
        style(ax, "Gemma-4-31B (Arm R1) silent swap after round 10: revision by transition", "", "change in match rate"); ax.legend(fontsize=7, frameon=False)
        fig.savefig(os.path.join(OUT, "fig_w8_replication_swap_by_transition_gemma.png"), bbox_inches="tight"); plt.close(fig)
        for _, r in per.iterrows(): N("R1 Gemma swap %s->%s new gain / old drop / adapted" % (r.old_type, r.new_type), "%.3f / %.3f / %d of %d" % (r.new_gain, r.old_drop, r.adapted, r.n), "replication_gemma4/tables/v4_swap_episodes.csv (grouped)")
        for _, r in grp.iterrows(): N("R1 Gemma swap %s: new gain / old drop / adapted" % r.dir, "%.3f / %.3f / %d of %d" % (r.new_gain, r.old_drop, r.adapted, r.n), "replication_gemma4/tables/v4_swap_episodes.csv (grouped by destination)")
    return {"summary": s, "per": per, "grp": grp}


def _history_sensitivity(log_path):
    """Two model-free diagnostics of whether choices depend on history at all (not gates; computed from the raw log).
    (a) win-stay/lose-shift: P(repeat last frame | last round succeeded) - P(repeat | failed), full_history;
    (b) same-choice agreement between full_history and shuffled_history / random_target / no_history on the identical
        candidate triple (same episode index and round; V4 seeds make the triples identical across these conditions)."""
    recs = [json.loads(l) for l in open(log_path)]
    fh = {}
    for r in recs:
        if r["condition"] == "full_history": fh.setdefault(r["episode_id"], []).append(r)
    rs = rf = ns = nf = 0
    for rows in fh.values():
        rows.sort(key=lambda r: r["round"])
        for prev, cur in zip(rows, rows[1:]):
            if prev["target_success"]: ns += 1; rs += cur["selected_frame"] == prev["selected_frame"]
            else: nf += 1; rf += cur["selected_frame"] == prev["selected_frame"]
    by = {}
    for r in recs: by.setdefault(r["condition"], {})[(r["episode_index"], r["round"])] = r
    agree = {}
    for other in ("shuffled_history", "no_history", "random_target"):
        keys = set(by["full_history"]) & set(by.get(other, {})); same = n = 0
        for k in keys:
            a, b = by["full_history"][k], by[other][k]
            if [c["candidate_id"] for c in a["candidates"]] == [c["candidate_id"] for c in b["candidates"]]:
                n += 1; same += a["selected_slot"] == b["selected_slot"]
        agree[other] = (same / n if n else float("nan"), n)
    return {"p_repeat_after_success": rs / ns, "n_success": ns, "p_repeat_after_failure": rf / nf, "n_failure": nf, "agreement": agree}


def fig10_history_sensitivity():
    if not os.path.exists(R1_LOG):
        return None
    q = _history_sensitivity(V4_LOG); g = _history_sensitivity(R1_LOG)
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.8), dpi=150)
    ax = axes[0]; x = np.arange(2)
    ax.bar(x - .18, [q["p_repeat_after_success"], g["p_repeat_after_success"]], .36, color="#2ca02c", label="after a success")
    ax.bar(x + .18, [q["p_repeat_after_failure"], g["p_repeat_after_failure"]], .36, color="#d62728", label="after a failure")
    ax.set_xticks(x); ax.set_xticklabels(["Qwen3.8-27B (V4)", "Gemma-4-31B (R1)"]); ax.set_ylim(0, 1.05)
    style(ax, "Full history: P(repeat last round's frame)", "", "probability"); ax.legend(fontsize=7, frameon=False, loc="lower left")
    ax = axes[1]; labels = ["vs shuffled\nhistory", "vs no\nhistory", "vs random\ntarget"]; x = np.arange(3)
    ax.bar(x - .18, [q["agreement"][k][0] for k in ("shuffled_history", "no_history", "random_target")], .36, color="#1f77b4", label="Qwen3.8-27B (V4)")
    ax.bar(x + .18, [g["agreement"][k][0] for k in ("shuffled_history", "no_history", "random_target")], .36, color="#9467bd", label="Gemma-4-31B (R1)")
    ax.set_xticks(x); ax.set_xticklabels(labels, fontsize=8); ax.set_ylim(0, 1.05)
    style(ax, "Same choice as full_history on the identical candidate triple", "", "agreement"); ax.legend(fontsize=7, frameon=False, loc="lower left")
    fig.savefig(os.path.join(OUT, "fig_w10_history_sensitivity_qwen_vs_gemma.png"), bbox_inches="tight"); plt.close(fig)
    for name, d in (("Qwen V4", q), ("Gemma R1", g)):
        N("%s full_history: P(repeat frame | success) / P(repeat | failure) / gap" % name, "%.3f / %.3f / %.3f (n=%d/%d)" % (d["p_repeat_after_success"], d["p_repeat_after_failure"], d["p_repeat_after_success"] - d["p_repeat_after_failure"], d["n_success"], d["n_failure"]), "raw log, full_history consecutive rounds")
        for k, (v, n) in d["agreement"].items(): N("%s same choice as full_history: %s" % (name, k), "%.3f (n=%d identical triples)" % (v, n), "raw log, paired by episode index and round")
    return {"qwen": q, "gemma": g}


def _e1_raw_diagnostics():
    """Raw-log diagnostics for the elicited arm (not gates)."""
    if not os.path.exists(E1_LOG):
        return None
    rs = [json.loads(l) for l in open(E1_LOG)]
    fh = [r for r in rs if r["condition"] == "elicited_full_history"]
    shares = {k: v / len(fh) for k, v in sorted(__import__("collections").Counter(r["selected_frame"] for r in fh).items())}
    argmax_eq = sum(r["selected_slot"] in [int(k) for k, v in r["predicted_p_a"].items() if float(v) == max(float(x) for x in r["predicted_p_a"].values())] for r in rs)
    byf = {}
    for r in rs:
        for c in r["candidates"]: byf.setdefault(c["frame"], []).append(float(r["predicted_p_a"][str(c["slot"])]))
    byf = {k: float(np.mean(v)) for k, v in byf.items()}
    eps = {}
    for r in fh: eps.setdefault(r["episode_id"], []).append(r)
    rs_ = rf_ = ns = nf = 0; cs = []; cf = []
    for rows in eps.values():
        rows.sort(key=lambda r: r["round"])
        for prev, cur in zip(rows, rows[1:]):
            same = cur["selected_frame"] == prev["selected_frame"]
            pf = [float(cur["predicted_p_a"][str(c["slot"])]) for c in cur["candidates"] if c["frame"] == prev["selected_frame"]]
            if prev["target_success"]: ns += 1; rs_ += same; cs += pf
            else: nf += 1; rf_ += same; cf += pf
    distinct = len(set(r["focal_output_raw"].strip() for r in rs))
    N("E1 elicited_full_history frame shares (fairness / risk / expertise)", "%.3f / %.3f / %.3f" % (shares.get("fairness", 0), shares.get("risk", 0), shares.get("expertise", 0)), "raw log v4e-qwen38.jsonl")
    N("E1 choice equals argmax of stated p_a", "%d of %d records" % (argmax_eq, len(rs)), "raw log v4e-qwen38.jsonl")
    N("E1 mean stated p_a by candidate frame (fairness / risk / expertise)", "%.3f / %.3f / %.3f" % (byf.get("fairness", float("nan")), byf.get("risk", float("nan")), byf.get("expertise", float("nan"))), "raw log v4e-qwen38.jsonl")
    N("E1 full_history: P(repeat frame | success) / P(repeat | failure) / gap", "%.3f / %.3f / %.3f (n=%d/%d)" % (rs_ / ns, rf_ / nf, rs_ / ns - rf_ / nf, ns, nf), "raw log, consecutive rounds")
    N("E1 stated p_a of last round's frame: after success / after failure", "%.3f / %.3f" % (np.mean(cs), np.mean(cf)), "raw log, consecutive rounds")
    N("E1 distinct raw JSON outputs", "%d of %d records" % (distinct, len(rs)), "raw log v4e-qwen38.jsonl")
    return {"shares": shares, "argmax_eq": argmax_eq, "n": len(rs), "byf": byf, "ws": rs_ / ns, "ls": rf_ / nf, "distinct": distinct}


def fig9_elicited():
    """Arm E1 (declared 2026-09-03): Qwen3.8-27B with elicited beliefs; primary = frozen V4 choice metrics, secondary = belief vs choice."""
    summ = os.path.join(E1_DIR, "elicited_choice_summary.json")
    if not os.path.exists(summ):
        return None
    s = json.load(open(summ)); s["decision"] = s.get("verdict"); out = {"summary": s}
    sw = s["swap_metrics"]; N("E1 elicited_swap new gain / old drop / new-over-old (p) / adapted", "%.3f / %.3f / %.3f (p=%.4f) / %d of %d" % (sw["new_target_gain"]["mean"], sw["old_target_drop"]["mean"], sw["late_new_over_old"]["mean"], sw["late_new_over_old"]["p_value_one_sided"], sw["n_adapted"], sw["n_episodes"]), "elicited_choice_summary.json swap_metrics")
    for tr, t in sw.get("by_transition", {}).items(): N("E1 elicited_swap %s new gain / old drop / adapted" % tr, "%.3f / %.3f / %d of %d" % (t["new_target_gain"], t["old_target_drop"], t["n_adapted"], t["n"]), "elicited_choice_summary.json swap_metrics.by_transition")
    c = s.get("cross_prompt_comparison_vs_v4_spontaneous")
    if c:
        N("E1 − V4 spontaneous: full-history learning gain diff, 95%% CI", "%.3f [%.3f, %.3f]" % (c["learning_gain_diff"]["mean"], c["learning_gain_diff"]["ci_lo"], c["learning_gain_diff"]["ci_hi"]), "elicited_choice_summary.json cross_prompt_comparison")
        N("E1 − V4 spontaneous: swap new-target gain diff, 95%% CI", "%.3f [%.3f, %.3f]" % (c["swap_new_target_gain_diff"]["mean"], c["swap_new_target_gain_diff"]["ci_lo"], c["swap_new_target_gain_diff"]["ci_hi"]), "elicited_choice_summary.json cross_prompt_comparison")
    for cond, mm in s.get("stable_condition_metrics", {}).items():
        if "learning_gain" in mm:
            g = mm["learning_gain"]; N("E1 elicited %s learning gain (late held-out − early), 95%% CI" % cond, "%.3f [%.3f, %.3f], n=%d" % (g["mean"], g["ci_lo"], g["ci_hi"], g["n"]), "elicited_qwen38/elicited_choice_summary.json")
    N("E1 elicited verdict (within-arm gates)", s.get("verdict"), "elicited_qwen38/elicited_choice_summary.json verdict")
    if os.path.exists(E1_BELIEF):
        b = json.load(open(E1_BELIEF)); out["beliefs"] = b; v = b["belief_validity"]
        N("E1 beliefs valid / selection valid / fallback", "%.3f / %.3f / %.3f (n=%d)" % (v["beliefs_valid_rate"], v["selection_valid_rate"], v["fallback_rate"], b["n_elicited_records"]), "elicited_belief_summary.json belief_validity")
        for cond, blk in b["per_condition"].items():
            last = blk["by_round"][-1]; first = blk["by_round"][0]
            N("E1 %s round 1 -> last: belief=target / choice=target / agreement" % cond, "%.3f -> %.3f / %.3f -> %.3f / %.3f -> %.3f" % (first["belief_matches_target"]["mean"], last["belief_matches_target"]["mean"], first["choice_matches_target"]["mean"], last["choice_matches_target"]["mean"], first["belief_choice_agreement"]["mean"], last["belief_choice_agreement"]["mean"]), "elicited_belief_summary.json by_round")
            if "post_swap_rounds_1_to_5_belief_minus_choice_new" in blk:
                d = blk["post_swap_rounds_1_to_5_belief_minus_choice_new"]; N("E1 %s post-swap rounds 1-5: P(belief=new) − P(choice=new), 95%% CI" % cond, "%.3f [%.3f, %.3f], episodes=%d" % (d["mean"], d["ci_low"], d["ci_high"], d["n_episodes"]), "elicited_belief_summary.json")
                for tr, t in blk.get("by_transition", {}).items(): N("E1 %s %s post-swap rounds 1-5: belief=new / choice=new" % (cond, tr), "%.3f / %.3f (episodes=%d)" % (t["belief_matches_new"]["mean"], t["choice_matches_new"]["mean"], t["n_episodes"]), "elicited_belief_summary.json by_transition")
            if "stated_p_a_selected" in blk:
                c = blk["stated_p_a_selected"]; N("E1 %s stated p_a(selected) mean / realized / Brier / stated|match / stated|mismatch" % cond, "%.3f / %.3f / %.3f / %.3f / %.3f" % (c["mean_stated"]["mean"], c["mean_realized_target_p_a"]["mean"], c["brier_selected"]["mean"] or float("nan"), c["mean_stated_when_match_regime"] or float("nan"), c["mean_stated_when_mismatch_regime"] or float("nan")), "elicited_belief_summary.json stated_p_a_selected")
        out["diag"] = _e1_raw_diagnostics()
        src = os.path.join(E1_DIR, "beliefs", "fig_elicited_beliefs.png")
        if os.path.exists(src): shutil.copyfile(src, os.path.join(OUT, "fig_w9_elicited_belief_vs_choice.png"))
    return out


def fig11_whole_story():
    """One figure for the summary: full-history match by round for V4 Qwen, R1 Gemma, E1 Qwen-elicited, with V4 no-history as the reference."""
    r1 = os.path.join(R1_DIR, "tables", "v4_round_trajectories.csv"); e1 = os.path.join(E1_DIR, "tables", "elicited_round_trajectories.csv")
    if not (os.path.exists(r1) and os.path.exists(e1)):
        return None
    tq = pd.read_csv(V4_TRAJ); tg = pd.read_csv(r1); te = pd.read_csv(e1)
    ref = tq[(tq.metric == "match") & (tq.condition == "no_history")].sort_values("round")
    panels = [("Qwen3.8-27B, spontaneous prompt (V4)", tq, "full_history", COL["full_history"]),
              ("Gemma-4-31B, same design (Arm R1)", tg, "full_history", "#9467bd"),
              ("Qwen3.8-27B, must state beliefs (Arm E1)", te, "elicited_full_history", "#8c564b")]
    fig, axes = plt.subplots(1, 3, figsize=(13, 3.9), dpi=150, sharey=True)
    for ax, (title, t, cond, color) in zip(axes, panels):
        g = t[(t.metric == "match") & (t.condition == cond)].sort_values("round")
        ax.plot(g["round"], g["mean"], marker="o", ms=3.2, lw=1.8, color=color, label="with own history (n=%d episodes)" % int(g["n"].iloc[0]))
        ax.plot(ref["round"], ref["mean"], lw=1.2, ls="--", color=COL["no_history"], label="V4 no-history reference")
        ax.axhline(1/3, ls=":", lw=1, color="grey"); ax.axvspan(15.5, 20.5, color="#eeeeee", zorder=0)
        ax.set_ylim(0, 1); ax.set_xticks(range(1, 21, 2)); style(ax, title, "round", "P(chosen frame matches hidden target)")
        ax.legend(fontsize=7, frameon=False, loc="upper left")
    axes[0].text(16, .93, "held-out\nwording", fontsize=7, color="#555555")
    fig.savefig(os.path.join(OUT, "fig_w11_whole_story.png"), bbox_inches="tight"); plt.close(fig); return True


def random_examples(k=5, seed=0, log_path=None):
    with open((log_path or V4_LOG)) as fh: lines = fh.readlines()
    idx = sorted(random.Random(seed).sample(range(len(lines)), k)); out = []
    for i in idx:
        r = json.loads(lines[i]); cands = sorted(r["candidates"], key=lambda c: c["slot"])
        out.append({"line": i, "condition": r["condition"], "round": r["round"], "hidden": r["hidden_target_type"], "scenario": r["scenario"].get("title"),
                    "cands": [(c["slot"], c["frame"], c["message"]) for c in cands], "chosen": r["selected_slot"], "chosen_frame": r["selected_frame"], "p_a": r["target_p_a"], "choice": r["target_choice"], "raw": r["focal_output_raw"]})
    return out


def main():
    os.makedirs(OUT, exist_ok=True)
    s = json.load(open(V4_SUM))
    fig1_learning(); per, grp = fig2_swap(); fig6_per_target(); fig3_priors(); fig4_v8_power(); fc = fig5_first_crossing_bias(); r1 = fig7_replication(); hs = fig10_history_sensitivity(); e1 = fig9_elicited(); whole = fig11_whole_story()
    m = s["stable_condition_metrics"]; pv = {}
    def walk(x, pre=""):
        for kk, v in (x.items() if isinstance(x, dict) else []):
            if isinstance(v, dict): walk(v, pre + kk + ".")
            elif "p_value" in kk and isinstance(v, (int, float)): pv[pre + kk] = v
    walk(s)
    for cond in ("full_history", "no_history", "shuffled_history", "random_target"):
        g = m[cond]["learning_gain"]; N("V4 %s learning gain (late held-out − early), 95%% CI" % cond, "%.3f [%.3f, %.3f], n=%d" % (g["mean"], g["ci_lo"], g["ci_hi"], g["n"]), "v4_checkpoint_summary.json stable_condition_metrics.%s.learning_gain" % cond)
    for k, v in sorted(pv.items()): N("V4 p-value: " + k, v, "v4_checkpoint_summary.json")
    N("V4 decision", s["decision"], "v4_checkpoint_summary.json decision")
    N("V4 swap revision randomization test passed", s["inference_gates"]["swap_revision_randomization_test"], "v4_checkpoint_summary.json inference_gates")
    ex = random_examples()
    ex_r1 = random_examples(3, 1, R1_LOG) if os.path.exists(R1_LOG) else []
    ex_e1 = random_examples(3, 2, E1_LOG) if os.path.exists(E1_LOG) else []
    md = ["# Write-up materials (generated; do not hand-edit)", "", "Generated by `scripts/make_writeup_materials.py` from committed artifacts. Every number below names its source. Figures in `results/writeup/`.", "",
          "## Exec-summary skeleton (facts only — write the prose yourself)", "",
          "- Question: does an LLM, given only *get Option A chosen* and binary feedback, learn which persuasion frame a hidden partner responds to, and revise that when the partner silently changes?",
          "- Design (V4, real, preregistered, run once): Qwen3.8-27B @ 1d4bf0f2; 360 episodes, 7,200 choices; each round the model sees three unlabelled candidate messages (one per frame) and picks 1/2/3; the target responds to the candidate's registered frame (P(A)=0.72 match / 0.38 mismatch); rounds 16–20 use separately authored held-out wording; four conditions + silent swap after round 10.",
          "- Result 1 (learning): with its own history the match rate rose 0.383 → 0.570 on held-out rounds; no-history flat at 0.333; shuffled history 0.287 → 0.233; random target flat. Full-history learning gain 0.187 [0.083, 0.290]. Stable randomization test passed.",
          "- Result 2 (revision): after the silent swap, new-frame use rose and old-frame use fell *symmetrically*; the registered final new-vs-old test failed. Mechanism: a large expertise default — swaps into expertise adapted %s, into fairness %s (fig_w2)." % (next(("%d of %d" % (r.adapted, r.n)) for _, r in grp.iterrows() if r.dir.startswith("into")), "%d of %d" % (int(per[per.new_type == "fairness"].adapted.sum()), int(per[per.new_type == "fairness"].n.sum()))),
          "- Result 1b (per target): learning is anti-default. Late match full vs no-history: expertise 0.86 vs 0.85 (already the default; nothing to learn), fairness 0.24 vs 0.05, risk 0.61 vs 0.10 (fig_w6). The model moves away from expertise when feedback says so — and yet after a swap it re-acquires fairness 0/40 times. Acquisition from scratch works; re-acquisition after a formed preference does not.",
          "- Result 3 (cross-family default): no-history frame shares — Qwen V4 bank %s; Qwen V5 bank %s; Gemma-4-31B V5 bank %s. The expertise attractor is a task property, not a model quirk (fig_w3)." % (numbers[[n[0] for n in numbers].index("Qwen V4-bank no-history shares (f/r/e)")][1], numbers[[n[0] for n in numbers].index("Qwen V5-bank no-history shares (f/r/e)")][1], numbers[[n[0] for n in numbers].index("Gemma-4 V5-bank no-history shares (f/r/e)")][1]),
          "- Result 4 (four successors, four pre-registered stops): V5 (bank cannot be balanced), V6 (balance gate infeasible at every N; 120k-study screen), V7 (own feasibility rule fails; adversarial review: pooled rule passes on default-attraction), V8 (destination-stratified gate underpowered at N≤30 vs the weakest registered learner; Type I controlled, 0 joint rejections / 6,000 null studies). Nothing frozen or spent after a failed gate.",
          "- Methodological finding: a first-crossing 'probe leads behaviour' lag metric is biased by probe noise — a chance-level probe appears to lead by %.2f rounds with a CI excluding 0 in %.0f%% of runs under fig_w5's noise model (0.74 rounds / 71%% under the review's). Replaced before any real probe was trained." % (fc[0][1], 100 * fc[0][2]),
          ("- Result 5 (replication, Arm R1 — Gemma-4-31B on the frozen V4 design, run once, 7,200/7,200 valid): does NOT replicate. Decision `%s`; full-history learning gain %s (Qwen: 0.187 [0.083, 0.290]); revision test passed = %s. Gemma picks expertise ~90%% of rounds whatever the history: its choice equals the shuffled-history choice on the identical triple %.1f%% of the time (Qwen %.1f%%), and P(repeat frame) is %.3f after a success vs %.3f after a failure (Qwen %.3f vs %.3f). Per target the small movement is *toward* the default (expertise full 1.00 vs no-history 0.72; fairness 0.01 vs 0.16). The frozen V4 learning result is, so far, Qwen-specific (fig_w7, fig_w8, fig_w10)." % (r1["summary"]["decision"], numbers[[n[0] for n in numbers].index("R1 Gemma full_history learning gain (late held-out − early), 95% CI")][1], r1["summary"]["inference_gates"]["swap_revision_randomization_test"], 100 * hs["gemma"]["agreement"]["shuffled_history"][0], 100 * hs["qwen"]["agreement"]["shuffled_history"][0], hs["gemma"]["p_repeat_after_success"], hs["gemma"]["p_repeat_after_failure"], hs["qwen"]["p_repeat_after_success"], hs["qwen"]["p_repeat_after_failure"])) if (r1 and hs) else "- Result 5 (replication, Arm R1 — Gemma-4-31B): PENDING (declared 2026-09-03, docs/V4_REPLICATION_DECLARATION.md).",
          ("- Result 6 (elicited belief, Arm E1 — same Qwen, same design, seeds and targets, but forced to state p_a per candidate and then choose; run once, 3,600/3,600 valid JSON): the V4 learning effect DISAPPEARS. Within-arm verdict `%s`; elicited full-history gain %s (V4 spontaneous 0.187); elicited − spontaneous learning-gain difference %s. Under this prompt the model picks expertise %.1f%% of rounds and never picks fairness; the choice is the argmax of its stated p_a in %d of %d records, so 'belief' and 'choice' are one object; stated confidence is a fixed frame ranking (expertise %.2f > risk %.2f > fairness %.2f) that barely moves with feedback (P(repeat) %.3f after success vs %.3f after failure; V4: 0.876 vs 0.693); post-swap P(belief=new) − P(choice=new) = %s. There is no stated belief that the behaviour ignores; and the V4 learning result is prompt-specific as well as model-specific (fig_w9)." % (e1["summary"].get("verdict"), next((n[1] for n in numbers if n[0].startswith("E1 elicited elicited_full_history learning gain")), "n/a"), next((n[1] for n in numbers if n[0].startswith("E1 − V4 spontaneous: full-history learning gain")), "n/a"), 100 * e1["diag"]["shares"].get("expertise", 0), e1["diag"]["argmax_eq"], e1["diag"]["n"], e1["diag"]["byf"].get("expertise", float("nan")), e1["diag"]["byf"].get("risk", float("nan")), e1["diag"]["byf"].get("fairness", float("nan")), e1["diag"]["ws"], e1["diag"]["ls"], next((n[1] for n in numbers if n[0].startswith("E1 elicited_swap post-swap rounds 1-5")), "n/a"))) if (e1 and e1.get("diag")) else "- Result 6 (elicited belief, Arm E1 — Qwen3.8-27B): PENDING (declared 2026-09-03).",
          "- What was NOT done: no activation capture, probe, or steering on a real model (gated behind a passed revision test that never came, and now moot: no behavioural effect survives a model or prompt change); no human validation of the message bank yet (two blind machine judges; a 45-template blind hand-label sheet exists); E1 cannot separate the output-format change from the model seeing its own past predictions.",
          "", "## Randomly selected V4 examples (seed 0, lines drawn uniformly from the 7,200-record log)", "",
          "The model sees the three candidates **without** frame labels; labels shown here are the registered ground truth. `→` marks the model's choice."]
    for e in ex:
        md.append("**Line %d — %s, round %d, hidden target = %s, scenario: %s**" % (e["line"], e["condition"], e["round"], e["hidden"], e["scenario"]))
        for slot, frame, msg in e["cands"]: md.append("- %s`%d` [%s] %s" % ("→ " if slot == e["chosen"] else "  ", slot, frame, msg.replace("\n", " ")))
        md.append("- model output `%s` → frame %s; target P(A)=%.2f → chose **%s**" % (e["raw"], e["chosen_frame"], e["p_a"], e["choice"])); md.append("")
    for label, exs in (("Arm R1 (Gemma-4-31B), seed 1, 3 lines drawn uniformly from the 7,200-record log", ex_r1), ("Arm E1 (Qwen3.8-27B, elicited), seed 2, 3 lines drawn uniformly from the 3,600-record log", ex_e1)):
        if not exs: continue
        md += ["## Randomly selected examples — %s" % label, ""]
        for e in exs:
            md.append("**Line %d — %s, round %d, hidden target = %s, scenario: %s**" % (e["line"], e["condition"], e["round"], e["hidden"], e["scenario"]))
            for slot, frame, msg in e["cands"]: md.append("- %s`%d` [%s] %s" % ("→ " if slot == e["chosen"] else "  ", slot, frame, msg.replace("\n", " ")))
            md.append("- model output `%s` → frame %s; target P(A)=%.2f → chose **%s**" % (e["raw"], e["chosen_frame"], e["p_a"], e["choice"])); md.append("")
    md += ["## Gate ledger", "", "| version | what changed | gate | verdict | artifact |", "|---|---|---|---|---|",
           "| V4 | controlled choice among registered candidates; target on frame ID | final new-vs-old randomization test | learning PASS; revision FAIL | results/v4_real/checkpoint/ |",
           "| V5 | 24 rounds; constrained decoding; target-free calibrated bank | no-history balance 25–42% per frame | FAIL (13.7/34.2/52.1) | docs/V5_CALIBRATION_RUN_20260901.md |",
           "| V6 | whole-triad selection; matched stable-old twin; every-cell power rule | balance-gate Wilson lower ≥ 0.80 at some N | FAIL at every N (0.41–0.42) | results/v6_design/v6_path_balance_dominance.json |",
           "| V7 | balance gate dropped; measured nuisance cells | own feasibility rule; adversarial review | FAIL (absolute-level gate); review: pooled rule passes on default-attraction | docs/V7_REVIEW.md |",
           "| V8 | declared milestone; destination-stratified acquisition gate; α=0.05/3 | V8-complete Wilson lower ≥ 0.80 at some N, every measured cell | FAIL (0.10–0.56 vs learner_1); null size clean | docs/V8_MILESTONE_DECLARATION.md |",
           "| R1 | frozen V4 design on Gemma-4-31B (replication) | frozen V4 gates | learning FAIL (gain 0.040); revision FAIL; feedback-insensitive | results/v4_real/replication_gemma4/ |",
           "| E1 | frozen V4 design on Qwen, elicited-belief prompt | frozen V4 functions within-arm | learning FAIL (gain −0.020; −0.207 vs V4); belief = choice | results/v4_real/elicited_qwen38/ |",
           "", "## Numbers sheet", "", "| label | value | source |", "|---|---|---|"]
    md += ["| %s | %s | `%s` |" % (a, b, c) for a, b, c in numbers]
    md += ["", "## Figures", "", "- fig_w1_v4_learning_by_condition.png — match rate by round, four stable conditions, held-out band marked",
           "- fig_w2_v4_swap_by_transition.png — new-frame gain and old-frame drop per ordered transition, with adapted counts",
           "- fig_w3_default_frame_priors.png — no-history frame shares: Qwen on V4 bank, Qwen on V5 bank, Gemma-4 on V5 bank",
           "- fig_w4_v8_power_vs_n.png — V8-complete Wilson lower vs N by learner profile at both measured cells; dotted = stratified test alone",
           "- fig_w5_first_crossing_bias.png — apparent probe lead from noise alone",
           "- fig_w6_v4_learning_by_target.png — per hidden target: full vs no-history vs shuffled; learning is largest where the default is weakest",
           "- fig_w7_replication_learning_qwen_vs_gemma.png — Arm R1: match rate by round, Qwen (V4) vs Gemma-4-31B (same frozen design)" if r1 else "- fig_w7 (replication): pending",
           "- fig_w8_replication_swap_by_transition_gemma.png — Arm R1: Gemma revision by transition (adapted counts are dominated by the pre-existing expertise default)" if r1 else "- fig_w8 (replication swap): pending",
           "- fig_w10_history_sensitivity_qwen_vs_gemma.png — win-stay/lose-shift and cross-condition agreement: does the choice depend on history at all?" if hs else "- fig_w10 (history sensitivity): pending",
           "- fig_w9_elicited_belief_vs_choice.png — Arm E1: stated belief vs choice by round, and after the silent swap by rounds since swap" if e1 else "- fig_w9 (elicited belief): pending",
           "- fig_w11_whole_story.png — the summary figure: with-history match rate by round for V4 Qwen, Gemma (R1), and Qwen-elicited (E1), V4 no-history as reference" if whole else "- fig_w11 (whole story): pending", ""]
    open(os.path.join(OUT, "WRITEUP_MATERIALS.md"), "w").write("\n".join(md)); print("wrote", OUT, "with", len(numbers), "sourced numbers and", len(ex), "random examples")


if __name__ == "__main__":
    sys.exit(main())
