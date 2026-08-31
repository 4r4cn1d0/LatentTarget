"""Metrics, statistical tests, diagnostics and plots.

Everything is computed from the raw JSONL log, so the analysis can be re-run
without touching a model.  Nothing here selects or drops episodes.

The alternative explanations this module is built to rule out (or fail to rule
out) are, in order of how likely they are to be the real story:

1. **Self-consistency, not target modelling.**  An agent that picks one of the
   three rewarded frames at round 1 and repeats it forever produces a *flat*
   match curve at 1/3.  Because ``other`` is also a valid label, 1/3 is only a
   reference line, not a universal chance rate.  If round-1 choices happened to
   be skewed towards one type the aggregate can still look like learning.
   ``recovery_after_wrong_start`` and ``strategy_persistence``
   address this: the diagnostic question is whether episodes that *started
   wrong* recover.
2. **Instrument circularity.**  If the classifier and the target scorer share a
   lexicon, "match" is partly true by construction.
   ``classifier_target_agreement`` quantifies the overlap.
3. **Prompt artefacts.**  If specialisation also appears under
   ``random_target`` (where nothing is learnable) the effect is an artefact of
   the prompt or of the classifier, not of adaptation.
4. **Scenario pull.**  If certain scenarios drag the agent towards one frame,
   round-wise effects can appear from the scenario order alone.
   ``strategy_by_scenario`` and the by-construction scenario balance check
   address this.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from config import ALL_LABELS, CHANCE_MATCH_RATE, STRATEGIES  # noqa: E402
from .logging_utils import read_jsonl  # noqa: E402
from .stats_utils import (  # noqa: E402
    MeanCI,
    cluster_bootstrap_mean,
    design_matrix,
    dummies,
    logistic_regression,
    permutation_slope_test,
    permutation_type_test,
)

CONDITION_COLOURS = {
    "full_history": "#1f77b4",
    "no_history": "#ff7f0e",
    "shuffled_history": "#2ca02c",
    "mismatched_feedback": "#8c564b",
    "random_target": "#d62728",
    "swap": "#9467bd",
}


# --------------------------------------------------------------------------
# Loading
# --------------------------------------------------------------------------


def load_dataframe(paths) -> pd.DataFrame:
    """Load one or more JSONL logs into a tidy DataFrame with derived columns."""
    if isinstance(paths, str):
        paths = [paths]
    rows: List[Dict[str, Any]] = []
    for p in paths:
        rows.extend(read_jsonl(p))
    if not rows:
        raise ValueError("no records found in %s" % (paths,))
    df = pd.DataFrame(rows)

    for label in ALL_LABELS:
        df["cls_" + label] = df["strategy_scores"].apply(lambda d, k=label: float(d.get(k, np.nan)))
    for label in STRATEGIES:
        df["tgt_" + label] = df["target_scores"].apply(lambda d, k=label: float(d.get(k, np.nan)))
    df["tgt_total_hits"] = df["target_scores"].apply(lambda d: int(d.get("total_hits", 0)))

    df["match"] = (df["primary_strategy"] == df["hidden_target_type"]).astype(int)
    df["match_initial"] = (df["primary_strategy"] == df["initial_target_type"]).astype(int)
    df["match_final"] = (df["primary_strategy"] == df["final_target_type"]).astype(int)
    df["chose_a"] = (df["target_choice"] == "A").astype(int)
    df["msg_words"] = df["focal_message"].apply(lambda s: len(str(s).split()))

    df = df.sort_values(["condition", "episode_id", "round"]).reset_index(drop=True)
    grp = df.groupby("episode_id", sort=False)
    df["prev_strategy"] = grp["primary_strategy"].shift(1)
    df["prev_choice"] = grp["displayed_choice"].shift(1)
    df["switched"] = np.where(
        df["prev_strategy"].isna(), np.nan, (df["primary_strategy"] != df["prev_strategy"]).astype(float)
    )

    first = df[df["round"] == 1][["episode_id", "match"]].rename(columns={"match": "match_round1"})
    df = df.merge(first, on="episode_id", how="left")
    return df


# --------------------------------------------------------------------------
# Core metrics
# --------------------------------------------------------------------------


def _grouped_ci(
    df: pd.DataFrame,
    group_cols: Sequence[str],
    value_col: str,
    cluster_col: str = "episode_id",
    n_boot: int = 2000,
    seed: int = 0,
) -> pd.DataFrame:
    rows: List[Dict[str, Any]] = []
    group_cols = list(group_cols)
    for keys, g in df.groupby(group_cols, dropna=False, sort=True):
        if not isinstance(keys, tuple):
            keys = (keys,)
        sub = g.dropna(subset=[value_col])
        ci = cluster_bootstrap_mean(
            sub[value_col].values, sub[cluster_col].values, n_boot=n_boot, seed=seed
        )
        row: Dict[str, Any] = dict(zip(group_cols, keys))
        row.update(ci.as_dict())
        rows.append(row)
    return pd.DataFrame(rows)


def match_rate_by_round(df: pd.DataFrame, n_boot: int = 2000, seed: int = 0) -> pd.DataFrame:
    """Primary outcome: P(primary strategy == active hidden type) by round."""
    return _grouped_ci(df, ["condition", "round"], "match", n_boot=n_boot, seed=seed)


def success_rate_by_round(df: pd.DataFrame, n_boot: int = 2000, seed: int = 0) -> pd.DataFrame:
    return _grouped_ci(df, ["condition", "round"], "chose_a", n_boot=n_boot, seed=seed)


def overall_rates(df: pd.DataFrame, n_boot: int = 2000, seed: int = 0) -> pd.DataFrame:
    m = _grouped_ci(df, ["condition"], "match", n_boot=n_boot, seed=seed).rename(
        columns={"mean": "match_rate", "ci_lo": "match_lo", "ci_hi": "match_hi"}
    )
    s = _grouped_ci(df, ["condition"], "chose_a", n_boot=n_boot, seed=seed).rename(
        columns={"mean": "success_rate", "ci_lo": "success_lo", "ci_hi": "success_hi"}
    )
    return m.merge(s[["condition", "success_rate", "success_lo", "success_hi"]], on="condition")


def strategy_distribution(df: pd.DataFrame) -> pd.DataFrame:
    """Row-normalised distribution of chosen strategy, per condition and type."""
    tab = (
        df.groupby(["condition", "hidden_target_type", "primary_strategy"])
        .size()
        .rename("n")
        .reset_index()
    )
    totals = tab.groupby(["condition", "hidden_target_type"])["n"].transform("sum")
    tab["fraction"] = tab["n"] / totals
    return tab


def adaptation_after_swap(
    df: pd.DataFrame, n_boot: int = 2000, seed: int = 0
) -> pd.DataFrame:
    """Match-to-new-type and match-to-old-type against rounds since the swap."""
    sw = df[df["swap_condition"] & df["rounds_since_swap"].notna()].copy()
    if sw.empty:
        return pd.DataFrame(
            columns=["rounds_since_swap", "match_new", "new_lo", "new_hi", "match_old", "old_lo", "old_hi", "n"]
        )
    sw["rounds_since_swap"] = sw["rounds_since_swap"].astype(int)
    new = _grouped_ci(sw, ["rounds_since_swap"], "match_final", n_boot=n_boot, seed=seed).rename(
        columns={"mean": "match_new", "ci_lo": "new_lo", "ci_hi": "new_hi"}
    )
    old = _grouped_ci(sw, ["rounds_since_swap"], "match_initial", n_boot=n_boot, seed=seed).rename(
        columns={"mean": "match_old", "ci_lo": "old_lo", "ci_hi": "old_hi"}
    )
    out = new.merge(
        old[["rounds_since_swap", "match_old", "old_lo", "old_hi"]], on="rounds_since_swap"
    )
    return out.sort_values("rounds_since_swap").reset_index(drop=True)


def rounds_to_adapt(df: pd.DataFrame) -> pd.DataFrame:
    """Per swapped episode: the first post-swap round whose strategy matches the
    new type, and whether the old strategy persisted.

    ``rounds_to_adapt`` is NaN when the episode never adapts within the horizon;
    those episodes are reported separately rather than being dropped or coded as
    the maximum, because either choice would bias the mean.
    """
    sw = df[df["swap_condition"]].copy()
    rows: List[Dict[str, Any]] = []
    for eid, g in sw.groupby("episode_id"):
        g = g.sort_values("round")
        post = g[g["rounds_since_swap"] > 0]
        if post.empty:
            continue
        matched = post[post["match_final"] == 1]
        first = int(matched["rounds_since_swap"].min()) if not matched.empty else None
        pre = g[g["rounds_since_swap"] <= 0]
        rows.append(
            {
                "episode_id": eid,
                "initial_target_type": g["initial_target_type"].iloc[0],
                "final_target_type": g["final_target_type"].iloc[0],
                "pre_swap_match_rate": float(pre["match_initial"].mean()) if not pre.empty else np.nan,
                "post_swap_match_new_rate": float(post["match_final"].mean()),
                "post_swap_match_old_rate": float(post["match_initial"].mean()),
                "rounds_to_adapt": first if first is not None else np.nan,
                "adapted": bool(first is not None),
                "n_post_rounds": int(len(post)),
            }
        )
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------
# Alternative-explanation diagnostics
# --------------------------------------------------------------------------


def strategy_persistence(df: pd.DataFrame) -> pd.DataFrame:
    """P(strategy repeats the previous round's strategy), per condition.

    A high number with a flat match curve is the signature of self-consistency
    rather than target modelling.
    """
    sub = df.dropna(subset=["switched"])
    out = (
        sub.groupby("condition")["switched"]
        .agg(["mean", "count"])
        .rename(columns={"mean": "switch_rate", "count": "n"})
        .reset_index()
    )
    out["repeat_rate"] = 1.0 - out["switch_rate"]
    return out


def feedback_contingency(df: pd.DataFrame) -> pd.DataFrame:
    """Win-stay / lose-shift: P(switch strategy | previous displayed outcome).

    This is the most direct behavioural signature of feedback-driven updating
    available without looking inside the model.  It is computed against the
    *displayed* outcome, i.e. what the agent actually saw.
    """
    sub = df.dropna(subset=["switched", "prev_choice"])
    out = (
        sub.groupby(["condition", "prev_choice"])["switched"]
        .agg(["mean", "count"])
        .rename(columns={"mean": "switch_rate", "count": "n"})
        .reset_index()
    )
    piv = out.pivot(index="condition", columns="prev_choice", values="switch_rate")
    piv = piv.rename(columns={"A": "switch_after_A", "B": "switch_after_B"}).reset_index()
    counts = out.pivot(index="condition", columns="prev_choice", values="n")
    counts = counts.rename(columns={"A": "n_after_A", "B": "n_after_B"}).reset_index()
    merged = piv.merge(counts, on="condition")
    if "switch_after_B" in merged and "switch_after_A" in merged:
        merged["lose_shift_minus_win_shift"] = merged["switch_after_B"] - merged["switch_after_A"]
    return merged


def recovery_after_wrong_start(
    df: pd.DataFrame, n_boot: int = 2000, seed: int = 0
) -> pd.DataFrame:
    """Match rate by round, restricted to episodes whose round-1 frame was wrong.

    If the rise in the overall curve is just self-consistency (a lucky round-1
    frame repeated), this curve stays flat near zero.  If the agent is actually
    using feedback, this curve rises.
    """
    sub = df[(df["match_round1"] == 0) & (~df["swap_condition"])]
    if sub.empty:
        return pd.DataFrame(columns=["condition", "round", "mean", "ci_lo", "ci_hi", "n", "n_clusters"])
    return _grouped_ci(sub, ["condition", "round"], "match", n_boot=n_boot, seed=seed)


def classifier_target_agreement(df: pd.DataFrame) -> Dict[str, Any]:
    """How much does the measurement instrument overlap the reward function?

    If the classifier's argmax always equals the target scorer's argmax, then
    "strategy match" is partly true by construction and the effect size cannot
    be interpreted independently of the lexicon.
    """
    tgt_cols = ["tgt_" + s for s in STRATEGIES]
    cls_cols = ["cls_" + s for s in STRATEGIES]
    sub = df.dropna(subset=tgt_cols + cls_cols).copy()
    if sub.empty:
        return {"n": 0}
    # Semantic scorers deliberately report zero keyword hits, so total_hits is
    # not a valid signal-presence test outside keyword_v1. The rewarded score
    # mass is the common, version-independent contract.
    has_signal = sub[tgt_cols].sum(axis=1) > 1e-12
    tgt_arg = sub.loc[has_signal, tgt_cols].values.argmax(axis=1)
    cls_arg = sub.loc[has_signal, cls_cols].values.argmax(axis=1)
    agreement = float(np.mean(tgt_arg == cls_arg)) if len(tgt_arg) else float("nan")
    corrs = {}
    for s in STRATEGIES:
        a = sub["tgt_" + s].values
        b = sub["cls_" + s].values
        if np.std(a) > 0 and np.std(b) > 0:
            corrs[s] = float(np.corrcoef(a, b)[0, 1])
        else:
            corrs[s] = float("nan")
    return {
        "n": int(len(sub)),
        "n_with_target_signal": int(has_signal.sum()),
        "target_signal_definition": "sum(fairness, risk, expertise) > 1e-12",
        "argmax_agreement": agreement,
        "pearson_r": corrs,
        "classifier_names": sorted(df["classifier_name"].unique().tolist()),
        "note": (
            "argmax_agreement near 1.0 means the classifier and the target "
            "scorer are effectively the same instrument; interpret match rates "
            "with care and prefer an LLM judge or a disjoint lexicon."
        ),
    }


def scenario_balance(df: pd.DataFrame) -> Dict[str, Any]:
    """Check scenario content is not correlated with hidden target type.

    By construction the scenario sequence depends only on ``episode_index``, so
    within a condition every hidden type should see exactly the same scenario
    counts.  Any deviation is a bug in the design, not a statistical question.
    """
    out: Dict[str, Any] = {}
    for cond, g in df.groupby("condition"):
        tab = pd.crosstab(g["scenario_id"], g["initial_target_type"])
        if tab.shape[1] < 2:
            out[cond] = {"identical_across_types": True, "max_abs_deviation": 0}
            continue
        dev = int((tab.max(axis=1) - tab.min(axis=1)).max())
        out[cond] = {
            "identical_across_types": dev == 0,
            "max_abs_deviation": dev,
            "table": tab.to_dict(),
        }
    return out


def strategy_by_scenario(df: pd.DataFrame) -> pd.DataFrame:
    """Diagnostic for scenario pull: does a scenario drag the agent to a frame?"""
    tab = df.groupby(["scenario_id", "primary_strategy"]).size().rename("n").reset_index()
    tab["fraction"] = tab["n"] / tab.groupby("scenario_id")["n"].transform("sum")
    return tab


def message_length_check(df: pd.DataFrame) -> pd.DataFrame:
    """Message length by round and hidden type -- a possible classifier confound."""
    return (
        df.groupby(["condition", "round"])["msg_words"]
        .agg(["mean", "std", "count"])
        .reset_index()
        .rename(columns={"mean": "mean_words", "std": "sd_words", "count": "n"})
    )


# --------------------------------------------------------------------------
# Regressions and permutation tests
# --------------------------------------------------------------------------


def fit_primary_history_interaction(df: pd.DataFrame) -> Optional[Dict[str, Any]]:
    """Preregistered primary contrast: does valid history steepen adaptation?

    Fits only ``full_history`` and ``no_history`` stable-target episodes::

        match ~ round_c + full_history + round_c:full_history

    The interaction is the primary estimand. Positive means strategy matching
    rises faster when target-specific feedback history is available. Standard
    errors are clustered by episode.
    """
    sub = df[
        (~df["swap_condition"])
        & (df["condition"].isin(["full_history", "no_history"]))
    ].copy()
    if sub.empty or sub["condition"].nunique() < 2:
        return None
    denom = max(1.0, float(sub["round"].max() - 1))
    round_c = (sub["round"].astype(float).values - 1.0) / denom
    full = (sub["condition"].values == "full_history").astype(float)
    X, names = design_matrix({
        "round_0_to_1": round_c,
        "full_history": full,
        "round:full_history": round_c * full,
    }, intercept=True)
    fit = logistic_regression(
        X, sub["match"].values.astype(float), names,
        clusters=sub["episode_id"].values,
    )
    return {
        "fit": fit,
        "n": int(len(sub)),
        "n_episodes": int(sub["episode_id"].nunique()),
        "primary_term": "round:full_history",
    }


def fit_match_regression(df: pd.DataFrame) -> Optional[Dict[str, Any]]:
    """``match ~ round + condition`` with episode-clustered standard errors.

    Restricted to the non-swap conditions.  ``full_history`` is the reference
    level, and ``round`` is centred at 1 so the intercept is the round-1 rate.
    """
    sub = df[~df["swap_condition"]].copy()
    if sub.empty or sub["condition"].nunique() == 0:
        return None
    levels = ["full_history"] + sorted(c for c in sub["condition"].unique() if c != "full_history")
    levels = [c for c in levels if c in set(sub["condition"])]
    cols: Dict[str, Any] = {"round_c": (sub["round"] - 1).astype(float).values}
    cols.update(dummies(sub["condition"].values, levels, "cond"))
    for lev, arr in list(cols.items()):
        if lev.startswith("cond["):
            cols["round_c:" + lev] = arr * cols["round_c"]
    X, names = design_matrix(cols, intercept=True)
    fit = logistic_regression(X, sub["match"].values.astype(float), names, clusters=sub["episode_id"].values)
    return {"levels": levels, "fit": fit, "n": int(len(sub))}


def fit_swap_regression(df: pd.DataFrame) -> Optional[Dict[str, Any]]:
    """``match_new ~ rounds_since_swap`` on post-swap rounds only."""
    sub = df[(df["swap_condition"]) & (df["rounds_since_swap"].notna())].copy()
    sub = sub[sub["rounds_since_swap"] > 0]
    if sub.empty:
        return None
    cols = {"rounds_since_swap": sub["rounds_since_swap"].astype(float).values}
    X, names = design_matrix(cols, intercept=True)
    fit = logistic_regression(
        X, sub["match_final"].values.astype(float), names, clusters=sub["episode_id"].values
    )
    return {"fit": fit, "n": int(len(sub))}


def per_condition_tests(df: pd.DataFrame, seed: int = 0) -> pd.DataFrame:
    """Permutation tests, per condition.

    * ``slope`` -- does match rate trend upward across rounds? (round labels
      permuted within episode)
    * ``type``  -- is the chosen strategy aligned with *this* target's type?
      (episode -> hidden type assignment permuted, strategies untouched)
    """
    rows: List[Dict[str, Any]] = []
    for cond, g in df.groupby("condition"):
        slope = permutation_slope_test(
            g["round"].values, g["match"].values, g["episode_id"].values, n_perm=2000, seed=seed
        )
        stable = g[~g["swap_condition"]]
        if not stable.empty:
            type_map = (
                stable.groupby("episode_id")["hidden_target_type"].first().to_dict()
            )
            tt = permutation_type_test(
                stable["primary_strategy"].values,
                type_map,
                stable["episode_id"].values,
                n_perm=2000,
                seed=seed,
            )
        else:
            tt = {"observed_match_rate": float("nan"), "p_value_one_sided": float("nan")}
        rows.append(
            {
                "condition": cond,
                "slope": slope["observed_slope"],
                "slope_p": slope["p_value_one_sided"],
                "match_rate": tt["observed_match_rate"],
                "type_alignment_p": tt["p_value_one_sided"],
                "n_rows": int(len(g)),
                "n_episodes": int(g["episode_id"].nunique()),
            }
        )
    return pd.DataFrame(rows).sort_values("condition").reset_index(drop=True)


# --------------------------------------------------------------------------
# Plots
# --------------------------------------------------------------------------


def _style(ax, title: str, xlabel: str, ylabel: str) -> None:
    ax.set_title(title, fontsize=11)
    ax.set_xlabel(xlabel, fontsize=9)
    ax.set_ylabel(ylabel, fontsize=9)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.tick_params(labelsize=8)
    ax.grid(alpha=0.25, linewidth=0.5)


MARKERS = {
    "full_history": ("o", "-"),
    "no_history": ("s", "--"),
    "shuffled_history": ("^", "--"),
    "mismatched_feedback": ("v", "--"),
    "random_target": ("D", ":"),
    "swap": ("P", "-."),
}


def plot_rate_by_round(
    table: pd.DataFrame,
    path: str,
    title: str,
    ylabel: str,
    chance: Optional[float] = None,
    exclude: Sequence[str] = (),
) -> str:
    """Mean +/- episode-clustered bootstrap CI, one line per condition.

    ``exclude`` drops conditions whose "active hidden type" is not constant
    within an episode (i.e. ``swap``), which would otherwise make the y-axis
    mean two different things at different x values.  The swap condition has its
    own figure.
    """
    table = table[~table["condition"].isin(set(exclude))]
    fig, ax = plt.subplots(figsize=(6.8, 4.0), dpi=150)
    for cond, g in table.groupby("condition"):
        g = g.sort_values("round")
        colour = CONDITION_COLOURS.get(cond, None)
        marker, ls = MARKERS.get(cond, ("o", "-"))
        ax.plot(
            g["round"], g["mean"], marker=marker, ls=ls, ms=4.5, lw=1.6,
            label="%s (n=%d ep)" % (cond, int(g["n_clusters"].max())), color=colour,
        )
        ax.fill_between(g["round"], g["ci_lo"], g["ci_hi"], alpha=0.10, color=colour, linewidth=0)
    if chance is not None:
        ax.axhline(chance, ls="--", lw=1.0, color="grey")
        ax.text(
            float(table["round"].min()), chance + 0.02,
            "1/3 reference (if no 'other')",
            va="bottom", ha="left", fontsize=7, color="grey",
        )
    ax.set_ylim(0, 1)
    ax.set_xticks(sorted(table["round"].unique()))
    _style(ax, title, "interaction round", ylabel)
    ax.legend(fontsize=7, frameon=False, loc="upper left", bbox_to_anchor=(1.01, 1.0))
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return path


def plot_strategy_distribution(dist: pd.DataFrame, path: str, conditions: Sequence[str]) -> str:
    conditions = [c for c in conditions if c in set(dist["condition"])]
    if not conditions:
        conditions = sorted(dist["condition"].unique())
    n = len(conditions)
    fig, axes = plt.subplots(1, n, figsize=(3.1 * n, 3.2), dpi=150, squeeze=False)
    for j, cond in enumerate(conditions):
        ax = axes[0][j]
        sub = dist[dist["condition"] == cond]
        mat = np.zeros((len(STRATEGIES), len(ALL_LABELS)))
        for i, t in enumerate(STRATEGIES):
            for k, s in enumerate(ALL_LABELS):
                sel = sub[(sub["hidden_target_type"] == t) & (sub["primary_strategy"] == s)]
                mat[i, k] = float(sel["fraction"].iloc[0]) if len(sel) else 0.0
        im = ax.imshow(mat, vmin=0, vmax=1, cmap="Blues")
        ax.set_xticks(range(len(ALL_LABELS)))
        ax.set_xticklabels(ALL_LABELS, rotation=45, ha="right", fontsize=7)
        ax.set_yticks(range(len(STRATEGIES)))
        ax.set_yticklabels(STRATEGIES if j == 0 else [""] * len(STRATEGIES), fontsize=7)
        for i in range(mat.shape[0]):
            for k in range(mat.shape[1]):
                ax.text(
                    k,
                    i,
                    "%.2f" % mat[i, k],
                    ha="center",
                    va="center",
                    fontsize=6.5,
                    color="white" if mat[i, k] > 0.55 else "black",
                )
        ax.set_title(cond, fontsize=9)
        if j == 0:
            ax.set_ylabel("hidden target type", fontsize=8)
        ax.set_xlabel("chosen strategy", fontsize=8)
    fig.colorbar(im, ax=axes[0].tolist(), fraction=0.02, pad=0.02)
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return path


def plot_adaptation(table: pd.DataFrame, path: str, swap_round: int) -> str:
    fig, ax = plt.subplots(figsize=(6.0, 4.0), dpi=150)
    if not table.empty:
        ax.plot(
            table["rounds_since_swap"], table["match_new"], marker="o", ms=4, lw=1.6,
            color="#2ca02c", label="matches NEW type",
        )
        ax.fill_between(
            table["rounds_since_swap"], table["new_lo"], table["new_hi"], alpha=0.15,
            color="#2ca02c", linewidth=0,
        )
        ax.plot(
            table["rounds_since_swap"], table["match_old"], marker="s", ms=4, lw=1.6,
            color="#d62728", label="matches OLD type",
        )
        ax.fill_between(
            table["rounds_since_swap"], table["old_lo"], table["old_hi"], alpha=0.15,
            color="#d62728", linewidth=0,
        )
    else:
        ax.text(
            0.5, 0.5, "No swap episodes in this run",
            transform=ax.transAxes, ha="center", va="center", fontsize=10,
            color="grey",
        )
    ax.axvline(0.5, ls="--", lw=1.2, color="black")
    ax.text(0.6, 0.95, "swap", fontsize=8, color="black")
    ax.axhline(CHANCE_MATCH_RATE, ls=":", lw=1.0, color="grey")
    ax.set_ylim(0, 1)
    _style(ax, "Adaptation after a silent target swap", "rounds since swap", "P(strategy matches)")
    if not table.empty:
        ax.legend(fontsize=7, frameon=False)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    return path


def plot_condition_comparison(overall: pd.DataFrame, path: str) -> str:
    fig, ax = plt.subplots(figsize=(6.0, 3.6), dpi=150)
    o = overall.sort_values("match_rate", ascending=False)
    x = np.arange(len(o))
    colours = [CONDITION_COLOURS.get(c, "#777777") for c in o["condition"]]
    ax.bar(x, o["match_rate"], color=colours, width=0.6)
    ax.errorbar(
        x,
        o["match_rate"],
        yerr=[o["match_rate"] - o["match_lo"], o["match_hi"] - o["match_rate"]],
        fmt="none",
        ecolor="black",
        elinewidth=1,
        capsize=3,
    )
    ax.axhline(CHANCE_MATCH_RATE, ls="--", lw=1.0, color="grey")
    ax.set_xticks(x)
    ax.set_xticklabels(o["condition"], rotation=20, ha="right", fontsize=7.5)
    ax.set_ylim(0, 1)
    _style(ax, "Overall strategy-match rate by condition", "", "P(strategy matches hidden type)")
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    return path


def plot_feedback_contingency(table: pd.DataFrame, path: str) -> str:
    fig, ax = plt.subplots(figsize=(6.0, 3.6), dpi=150)
    if not table.empty and {"switch_after_A", "switch_after_B"} <= set(table.columns):
        x = np.arange(len(table))
        ax.bar(x - 0.18, table["switch_after_A"], width=0.36, label="after Option A (win)", color="#1f77b4")
        ax.bar(x + 0.18, table["switch_after_B"], width=0.36, label="after Option B (loss)", color="#d62728")
        ax.set_xticks(x)
        ax.set_xticklabels(table["condition"], rotation=20, ha="right", fontsize=7.5)
        ax.legend(fontsize=7, frameon=False)
    ax.set_ylim(0, 1)
    _style(ax, "Win-stay / lose-shift: P(change strategy next round)", "", "P(switch strategy)")
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    return path


def plot_recovery(table: pd.DataFrame, path: str) -> str:
    fig, ax = plt.subplots(figsize=(6.0, 3.8), dpi=150)
    for cond, g in table.groupby("condition"):
        g = g.sort_values("round")
        ax.plot(
            g["round"], g["mean"], marker="o", ms=4, lw=1.6, label=cond,
            color=CONDITION_COLOURS.get(cond),
        )
        ax.fill_between(
            g["round"], g["ci_lo"], g["ci_hi"], alpha=0.15,
            color=CONDITION_COLOURS.get(cond), linewidth=0,
        )
    ax.set_ylim(0, 1)
    _style(
        ax,
        "Recovery: episodes whose round-1 strategy was WRONG",
        "interaction round",
        "P(strategy matches hidden type)",
    )
    ax.legend(fontsize=7, frameon=False)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    return path


# --------------------------------------------------------------------------
# Top-level driver
# --------------------------------------------------------------------------


def run_full_analysis(
    log_paths,
    fig_dir: str = "results/figures",
    tab_dir: str = "results/tables",
    n_boot: int = 2000,
    seed: int = 0,
    prefix: str = "",
) -> Dict[str, Any]:
    """Compute every metric, write every table and figure, return a summary."""
    os.makedirs(fig_dir, exist_ok=True)
    os.makedirs(tab_dir, exist_ok=True)
    df = load_dataframe(log_paths)

    def tpath(name: str) -> str:
        return os.path.join(tab_dir, prefix + name)

    def fpath(name: str) -> str:
        return os.path.join(fig_dir, prefix + name)

    match_tbl = match_rate_by_round(df, n_boot=n_boot, seed=seed)
    success_tbl = success_rate_by_round(df, n_boot=n_boot, seed=seed)
    overall = overall_rates(df, n_boot=n_boot, seed=seed)
    dist = strategy_distribution(df)
    adapt = adaptation_after_swap(df, n_boot=n_boot, seed=seed)
    adapt_eps = rounds_to_adapt(df)
    persistence = strategy_persistence(df)
    contingency = feedback_contingency(df)
    recovery = recovery_after_wrong_start(df, n_boot=n_boot, seed=seed)
    lengths = message_length_check(df)
    by_scenario = strategy_by_scenario(df)
    tests = per_condition_tests(df, seed=seed)

    for name, tbl in [
        ("match_rate_by_round.csv", match_tbl),
        ("success_rate_by_round.csv", success_tbl),
        ("overall_rates.csv", overall),
        ("strategy_distribution.csv", dist),
        ("adaptation_after_swap.csv", adapt),
        ("rounds_to_adapt_by_episode.csv", adapt_eps),
        ("strategy_persistence.csv", persistence),
        ("feedback_contingency.csv", contingency),
        ("recovery_after_wrong_start.csv", recovery),
        ("message_length_by_round.csv", lengths),
        ("strategy_by_scenario.csv", by_scenario),
        ("permutation_tests.csv", tests),
    ]:
        tbl.to_csv(tpath(name), index=False)

    figures = {
        "match_rate_by_round": plot_rate_by_round(
            match_tbl,
            fpath("fig1_match_rate_by_round.png"),
            "Strategy-match rate by round (stable-target conditions)",
            "P(strategy matches hidden type)",
            chance=CHANCE_MATCH_RATE,
            exclude=("swap",),
        ),
        "success_rate_by_round": plot_rate_by_round(
            success_tbl,
            fpath("fig2_success_rate_by_round.png"),
            "Target success rate by interaction round",
            "P(target chooses Option A)",
        ),
        "strategy_distribution": plot_strategy_distribution(
            dist,
            fpath("fig3_strategy_distribution.png"),
            ["full_history", "no_history", "shuffled_history", "random_target"],
        ),
        "adaptation_after_swap": plot_adaptation(
            adapt, fpath("fig4_adaptation_after_swap.png"), swap_round=0
        ),
        "condition_comparison": plot_condition_comparison(
            overall, fpath("fig5_condition_comparison.png")
        ),
        "feedback_contingency": plot_feedback_contingency(
            contingency, fpath("fig6_feedback_contingency.png")
        ),
        "recovery_after_wrong_start": plot_recovery(
            recovery, fpath("fig7_recovery_after_wrong_start.png")
        ),
    }

    primary_reg = fit_primary_history_interaction(df)
    reg = fit_match_regression(df)
    swap_reg = fit_swap_regression(df)

    summary: Dict[str, Any] = {
        "n_records": int(len(df)),
        "n_episodes": int(df["episode_id"].nunique()),
        "conditions": sorted(df["condition"].unique().tolist()),
        "models": sorted(df["model_name"].unique().tolist()),
        "providers": sorted(df["provider"].unique().tolist()),
        "classifiers": sorted(df["classifier_name"].unique().tolist()),
        "overall_rates": overall.to_dict(orient="records"),
        "permutation_tests": tests.to_dict(orient="records"),
        "strategy_persistence": persistence.to_dict(orient="records"),
        "feedback_contingency": contingency.to_dict(orient="records"),
        "adaptation_summary": {
            "n_swap_episodes": int(len(adapt_eps)),
            "n_adapted": int(adapt_eps["adapted"].sum()) if len(adapt_eps) else 0,
            "median_rounds_to_adapt": (
                float(adapt_eps["rounds_to_adapt"].median()) if len(adapt_eps) else None
            ),
            "pre_swap_match_old": (
                float(adapt_eps["pre_swap_match_rate"].mean()) if len(adapt_eps) else None
            ),
            "post_swap_match_new": (
                float(adapt_eps["post_swap_match_new_rate"].mean()) if len(adapt_eps) else None
            ),
            "post_swap_match_old": (
                float(adapt_eps["post_swap_match_old_rate"].mean()) if len(adapt_eps) else None
            ),
        },
        "diagnostics": {
            "classifier_target_agreement": classifier_target_agreement(df),
            "scenario_balance": scenario_balance(df),
            "unparsed_classifications": int((df["primary_strategy"] == "unparsed").sum()),
            "mean_message_words": float(df["msg_words"].mean()),
            "max_message_words": int(df["msg_words"].max()),
            "over_80_words_fraction": float((df["msg_words"] > 80).mean()),
        },
        "figures": figures,
        "tables_dir": tab_dir,
    }
    if primary_reg is not None:
        summary["primary_history_interaction"] = {
            "n": primary_reg["n"],
            "n_episodes": primary_reg["n_episodes"],
            "primary_term": primary_reg["primary_term"],
            "rows": primary_reg["fit"].to_rows(),
            "summary": primary_reg["fit"].summary(),
        }
    if reg is not None:
        summary["match_regression"] = {
            "n": reg["n"],
            "levels": reg["levels"],
            "rows": reg["fit"].to_rows(),
            "summary": reg["fit"].summary(),
        }
    if swap_reg is not None:
        summary["swap_regression"] = {
            "n": swap_reg["n"],
            "rows": swap_reg["fit"].to_rows(),
            "summary": swap_reg["fit"].summary(),
        }

    with open(tpath("summary.json"), "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2, default=str)
    return summary


def format_summary(summary: Dict[str, Any]) -> str:
    """Human-readable console summary."""
    lines: List[str] = []
    lines.append(
        "records=%d  episodes=%d  conditions=%s"
        % (summary["n_records"], summary["n_episodes"], ", ".join(summary["conditions"]))
    )
    lines.append("models=%s  classifiers=%s" % (summary["models"], summary["classifiers"]))
    lines.append("")
    lines.append("%-20s %14s %14s %8s %8s" % ("condition", "match rate", "success rate", "slope", "slope p"))
    tests = {t["condition"]: t for t in summary["permutation_tests"]}
    for row in summary["overall_rates"]:
        t = tests.get(row["condition"], {})
        lines.append(
            "%-20s %6.3f [%.2f,%.2f] %6.3f [%.2f,%.2f] %8.4f %8.4f"
            % (
                row["condition"],
                row["match_rate"],
                row["match_lo"],
                row["match_hi"],
                row["success_rate"],
                row["success_lo"],
                row["success_hi"],
                t.get("slope", float("nan")),
                t.get("slope_p", float("nan")),
            )
        )
    lines.append("")
    ad = summary["adaptation_summary"]
    if ad["n_swap_episodes"]:
        lines.append(
            "swap: %d episodes, %d adapted, median rounds-to-adapt=%s"
            % (ad["n_swap_episodes"], ad["n_adapted"], ad["median_rounds_to_adapt"])
        )
        lines.append(
            "      pre-swap match(old)=%.3f  post-swap match(new)=%.3f  post-swap match(old)=%.3f"
            % (ad["pre_swap_match_old"], ad["post_swap_match_new"], ad["post_swap_match_old"])
        )
    diag = summary["diagnostics"]
    agree = diag["classifier_target_agreement"]
    lines.append("")
    lines.append(
        "diagnostics: classifier/target argmax agreement=%s, unparsed=%d, mean words=%.1f"
        % (agree.get("argmax_agreement"), diag["unparsed_classifications"], diag["mean_message_words"])
    )
    bad = [c for c, v in diag["scenario_balance"].items() if not v.get("identical_across_types", True)]
    lines.append(
        "scenario balance: %s"
        % ("identical across target types in every condition" if not bad else "UNBALANCED in " + ", ".join(bad))
    )
    if "match_regression" in summary:
        lines.append("")
        lines.append(summary["match_regression"]["summary"])
    if "primary_history_interaction" in summary:
        lines.append("")
        lines.append("PREREGISTERED PRIMARY:\n" + summary["primary_history_interaction"]["summary"])
    if "swap_regression" in summary:
        lines.append("")
        lines.append("post-swap: " + summary["swap_regression"]["summary"])
    return "\n".join(lines)
