#!/usr/bin/env python3
"""Train a linear probe for the hidden target type, and compare its update rate
to the behaviour's after the silent swap.

    python scripts/train_probe.py --log data/raw/<run>.jsonl \
        --acts data/processed/activations.npz

Order of operations is deliberate. The baselines run BEFORE the headline
analysis, because if the probe doesn't beat them there is no headline.
"""

from __future__ import annotations

import _bootstrap  # noqa: F401
import argparse
import json
import os
import sys

import numpy as np

from config import STRATEGIES, TargetParams
from src.analysis import load_dataframe
from src.bayesian_observer import (
    LoggedPersuasionScorer,
    augment_with_bayesian_observer,
    baseline_corrected_trajectory_gap,
)
from src.probing import (
    ActivationStore,
    align_to_log,
    behavioural_readout_features,
    behavioural_readout_baseline,
    context_leakage_check,
    evaluate_probe,
    fit_probe,
    majority_baseline,
    nearest_centroid_accuracy,
    plot_layer_sweep,
    plot_probe_vs_behaviour,
    probe_belief_trajectory,
    shuffled_label_baseline,
    stratified_episode_split,
    switch_lag,
    trajectory_gap,
    ProbeResult,
)


def _load_target_design(log_paths, manifest_path=None):
    paths = [manifest_path] if manifest_path else [
        p[:-6] + ".manifest.json" if p.endswith(".jsonl") else p + ".manifest.json"
        for p in log_paths
    ]
    manifests = []
    for path in paths:
        if not path or not os.path.exists(path):
            raise FileNotFoundError(
                "manifest not found: %s. The Bayesian comparator cannot guess "
                "the target simulator parameters." % path
            )
        with open(path, "r", encoding="utf-8") as fh:
            manifests.append(json.load(fh))
    params = manifests[0]["config"]["target_params"]
    scorer_design = manifests[0].get("target_scorer", {})
    for manifest in manifests[1:]:
        if manifest["config"]["target_params"] != params:
            raise ValueError("logs use different target parameters; train separately")
        if manifest.get("target_scorer", {}) != scorer_design:
            raise ValueError("logs use different target scorers; train separately")
    return TargetParams(**params), scorer_design, paths


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--log", nargs="+", required=True)
    p.add_argument("--acts", required=True)
    p.add_argument("--fig-dir", default="results/figures")
    p.add_argument("--tab-dir", default="results/tables")
    p.add_argument("--n-folds", type=int, default=5)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--layer-step", type=int, default=2, help="sweep every Nth captured layer")
    p.add_argument("--black-box-json", default=None,
                   help="optional {episode_id: {round: guess}} from the ask-the-model baseline")
    p.add_argument("--manifest", default=None,
                   help="manifest path (inferred beside a single log by default)")
    p.add_argument("--bayes-hazard", type=float, default=0.10,
                   help="predeclared target-change hazard for evidence-only comparator")
    p.add_argument("--probe-out", default="data/processed/target_probe.npz")
    args = p.parse_args(argv)

    os.makedirs(args.fig_dir, exist_ok=True)
    os.makedirs(args.tab_dir, exist_ok=True)

    df = load_dataframe(args.log)
    store = ActivationStore.load(args.acts)
    rows = align_to_log(store, df)          # raises loudly on any mismatch
    sub = df.iloc[rows].reset_index(drop=True)
    print("%d activation rows aligned to the log (%d layers, d_model=%d)"
          % (store.n_rows, store.n_layers, store.d_model))

    # Train ONLY on typed, stable, full-history episodes. No-history and random-
    # response rows do not contain target-identifying evidence; including them
    # would teach the probe from labels that the model cannot infer. Swap and
    # all controls stay completely outside fitting.
    stable = np.where(
        (sub["condition"].values == "full_history")
        & (~sub["swap_condition"].values)
        & (sub["target_mode"].values == "typed")
    )[0]
    if len(stable) < 30:
        print("only %d stable rows -- too few to train a probe. Run more episodes."
              % len(stable))
        return 1
    y = sub["hidden_target_type"].values[stable]
    groups = sub["episode_id"].values[stable]
    print("training rows: %d across %d episodes" % (len(stable), len(set(groups))))
    split = stratified_episode_split(y, groups, seed=args.seed)
    for name in ("train", "dev", "test"):
        print("  %-5s: %d rows / %d episodes" % (
            name, len(split[name]), len(set(groups[split[name]]))))
    target_params, scorer_design, manifest_paths = _load_target_design(
        args.log, args.manifest
    )
    logged_scorer = LoggedPersuasionScorer.from_dataframe(df)

    # ---- baselines FIRST ----
    print("\n--- baselines ---")
    chance = 1.0 / len(STRATEGIES)
    maj = majority_baseline(list(y))
    stable_df = sub.iloc[stable].copy()
    beh_cv = behavioural_readout_baseline(stable_df, n_folds=args.n_folds, seed=args.seed)
    beh_X, beh_y, beh_groups = behavioural_readout_features(stable_df)
    train_eps = set(groups[np.r_[split["train"], split["dev"]]])
    test_eps = set(groups[split["test"]])
    beh_train = np.where(np.isin(beh_groups, list(train_eps)))[0]
    beh_test = np.where(np.isin(beh_groups, list(test_eps)))[0]
    beh_probe = fit_probe(
        beh_X[beh_train], beh_y[beh_train], classes=list(STRATEGIES), l2=0.1,
        seed=args.seed,
    )
    beh = evaluate_probe(beh_probe, beh_X[beh_test], beh_y[beh_test])

    bayes_all = augment_with_bayesian_observer(
        df, params=target_params, hazard=args.bayes_hazard, scorer=logged_scorer
    )
    bayes_sub = bayes_all.iloc[rows].reset_index(drop=True)
    stable_test_global = stable[split["test"]]
    bayes_acc = float(bayes_sub.iloc[stable_test_global]["bayes_matches_active"].mean())
    print("chance                 : %.3f" % chance)
    print("majority class         : %.3f" % maj)
    print("behavioural readout    : %.3f held-out (selection CV %.3f)" %
          (beh.accuracy, beh_cv.accuracy))
    print("Bayesian evidence      : %.3f held-out (hazard %.3f)" %
          (bayes_acc, args.bayes_hazard))
    black_box_acc = None
    if args.black_box_json:
        with open(args.black_box_json) as fh:
            guesses = json.load(fh)
        hit, tot = 0, 0
        for i in stable_test_global:
            g = guesses.get(str(sub["episode_id"][i]), {}).get(str(sub["round"][i]))
            if g is not None:
                tot += 1
                hit += int(g == sub["hidden_target_type"][i])
        black_box_acc = hit / tot if tot else None
        print("just ask the model     : %s (n=%d)"
              % ("%.3f" % black_box_acc if black_box_acc is not None else "n/a", tot))

    # ---- model selection on train/dev; untouched test quoted once ----
    print("\n--- layer sweep (nearest-centroid train -> dev only) ---")
    layer_idxs = list(range(0, store.n_layers, args.layer_step))
    store_sub = _subset(store, stable)
    sweep = []
    for li in layer_idxs:
        acc = nearest_centroid_accuracy(
            store_sub.layer(li)[split["train"]], y[split["train"]],
            store_sub.layer(li)[split["dev"]], y[split["dev"]],
            classes=list(STRATEGIES),
        )
        sweep.append(ProbeResult(
            layer=store.layers[li], accuracy=acc,
            per_class_accuracy={}, n_test=len(split["dev"]),
            n_train=len(split["train"]), confusion={},
        ))
    for r in sweep:
        print("  layer %-3d  acc=%.3f" % (r.layer, r.accuracy))
    best = max(sweep, key=lambda r: r.accuracy)
    best_pos = layer_idxs[[r.layer for r in sweep].index(best.layer)]
    print("best layer: %d (dev centroid acc=%.3f)" % (best.layer, best.accuracy))

    l2_table = []
    for candidate in (0.01, 0.1, 1.0, 10.0, 100.0, 1000.0):
        candidate_probe = fit_probe(
            store_sub.layer(best_pos)[split["train"]], y[split["train"]],
            classes=list(STRATEGIES), l2=candidate, seed=args.seed,
        )
        dev = evaluate_probe(
            candidate_probe, store_sub.layer(best_pos)[split["dev"]],
            y[split["dev"]], layer=best.layer,
        )
        l2_table.append({"l2": candidate, "accuracy": dev.accuracy})
    l2 = max(l2_table, key=lambda value: value["accuracy"])["l2"]
    print("selected L2: %g   %s" % (l2, [(t["l2"], round(t["accuracy"], 3)) for t in l2_table]))

    selection_idx = np.r_[split["train"], split["dev"]]
    shuf = shuffled_label_baseline(store_sub.layer(best_pos)[selection_idx], y[selection_idx],
                                   groups[selection_idx],
                                   n_repeats=5, n_folds=args.n_folds, l2=l2, seed=args.seed)
    print("shuffled labels        : %.3f (sd %.3f)" % (shuf["mean"], shuf["sd"]))

    probe = fit_probe(
        store_sub.layer(best_pos)[selection_idx], y[selection_idx],
        classes=list(STRATEGIES), l2=l2, seed=args.seed,
    )
    final_test = evaluate_probe(
        probe, store_sub.layer(best_pos)[split["test"]], y[split["test"]],
        layer=best.layer,
    )
    probe.save(args.probe_out)
    print("probe @ best layer     : %.3f on untouched test" % final_test.accuracy)
    print("saved fitted probe     : %s" % args.probe_out)
    strongest_visible = max(beh.accuracy, bayes_acc)
    if final_test.accuracy <= strongest_visible + 0.05:
        print("  ^ the probe does NOT clearly beat the strongest visible-evidence baseline. Report that "
              "plainly; it is a real (negative) result, not a tuning problem.")

    # ---- headline: probe vs behaviour across the swap ----
    traj = probe_belief_trajectory(probe, store, best_pos, df, rows)
    for column in ("bayes_pred", "bayes_p_final", "bayes_matches_final"):
        traj[column] = bayes_sub[column].values
    lag = switch_lag(traj, seed=args.seed)
    leak = context_leakage_check(probe, store, best_pos, df, rows)

    gap = trajectory_gap(traj, seed=args.seed)
    probe_vs_bayes = baseline_corrected_trajectory_gap(
        traj, evidence_col="probe_p_final", behaviour_col="bayes_p_final",
        seed=args.seed,
    )

    print("\n--- headline: does the belief update before the behaviour? ---")
    if "statistic" in gap:
        print("baseline-corrected trajectory gap : %+.3f  95%% CI [%+.3f, %+.3f]"
              % (gap["statistic"], gap["ci95"][0], gap["ci95"][1]))
        print("  pre-swap baselines: probe %.2f, behaviour %.2f"
              % (gap["probe_pre_swap_baseline"], gap["behaviour_pre_swap_baseline"]))
        lo, hi = gap["ci95"]
        print("  -> %s" % ("probe leads behaviour" if lo > 0 else
                           "behaviour leads probe" if hi < 0 else
                           "CI spans 0: underdetermined, report it as such"))

    print("\n--- secondary (first-crossing; biased by noise, do not quote alone) ---")
    if "mean_behaviour_minus_probe" in lag:
        print("mean probe lag      : %.2f rounds" % lag["mean_probe_lag"])
        print("mean behaviour lag  : %.2f rounds" % lag["mean_behaviour_lag"])
        print("behaviour - probe   : %+.2f  95%% CI [%+.2f, %+.2f]"
              % (lag["mean_behaviour_minus_probe"], lag["ci95"][0], lag["ci95"][1]))
        lo, hi = lag["ci95"]
        print("  -> %s" % ("probe leads behaviour" if lo > 0 else
                           "behaviour leads probe" if hi < 0 else
                           "CI spans 0: underdetermined, say so"))
    else:
        print("not enough swap episodes flipped for a paired comparison "
              "(%d/%d probe, %d/%d behaviour never flipped)"
              % (lag["n_probe_never_flipped"], lag["n_swap_episodes"],
                 lag["n_behaviour_never_flipped"], lag["n_swap_episodes"]))
    print("\ncontext-leakage check (shuffled_history): %s" % json.dumps(leak, indent=2))
    print("\nprobe rise minus Bayesian-evidence rise: %s" % json.dumps(
        probe_vs_bayes, indent=2))

    control_accuracy = {}
    predictions = probe.predict(store.layer(best_pos))
    for condition, condition_rows in sub.groupby("condition"):
        idx = condition_rows.index.to_numpy(dtype=int)
        control_accuracy[str(condition)] = float(np.mean(
            predictions[idx] == condition_rows["hidden_target_type"].values
        ))
    print("\nprobe accuracy by condition (diagnostic only): %s" %
          json.dumps(control_accuracy, indent=2))

    # ---- outputs ----
    figs = {
        "layer_sweep": plot_layer_sweep(
            sweep, os.path.join(args.fig_dir, "fig8_probe_layer_sweep.png"),
            baselines={"chance": chance, "majority": maj,
                       "behavioural readout": beh.accuracy,
                       "Bayesian evidence": bayes_acc,
                       "shuffled labels": shuf["mean"],
                       **({"just ask the model": black_box_acc} if black_box_acc else {})}),
        "probe_vs_behaviour": plot_probe_vs_behaviour(
            traj, os.path.join(args.fig_dir, "fig9_probe_vs_behaviour.png"), seed=args.seed),
    }
    traj.to_csv(os.path.join(args.tab_dir, "probe_trajectory.csv"), index=False)
    summary = {
        "n_activation_rows": store.n_rows, "n_layers": store.n_layers,
        "d_model": store.d_model, "best_layer": best.layer, "selected_l2": l2,
        "manifest_paths": manifest_paths,
        "target_scorer": scorer_design,
        "observer_scorer": logged_scorer.describe(),
        "bayes_hazard": args.bayes_hazard,
        "split_episode_ids": {
            name: sorted(set(str(x) for x in groups[idx])) for name, idx in split.items()
        },
        "l2_table": l2_table,
        "layer_sweep": [r.as_dict() for r in sweep],
        "baselines": {"chance": chance, "majority": maj,
                      "behavioural_readout_heldout": beh.accuracy,
                      "behavioural_readout_selection_cv": beh_cv.accuracy,
                      "bayesian_evidence_heldout": bayes_acc,
                      "shuffled_labels": shuf, "just_ask_the_model": black_box_acc},
        "probe_heldout_test": final_test.as_dict(),
        "probe_accuracy_by_condition": control_accuracy,
        "trajectory_gap": gap, "probe_vs_bayes_gap": probe_vs_bayes,
        "switch_lag": lag, "context_leakage": leak, "figures": figs,
    }
    with open(os.path.join(args.tab_dir, "probe_summary.json"), "w") as fh:
        json.dump(summary, fh, indent=2, default=str)
    print("\nfigures: %s" % ", ".join(figs.values()))
    print("tables : %s" % args.tab_dir)
    return 0


def _subset(store: ActivationStore, idx) -> ActivationStore:
    return ActivationStore(acts=store.acts[idx], meta=[store.meta[i] for i in idx],
                           layers=list(store.layers))


if __name__ == "__main__":
    sys.exit(main())
