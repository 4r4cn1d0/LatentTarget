"""Run the declared, CPU only, exploratory comparison of existing V4 choices."""

from __future__ import annotations

import argparse
from collections import Counter
import csv
from datetime import datetime, timezone
import gzip
import hashlib
import io
import json
from pathlib import Path
import platform
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np

from src.choice_baselines import FRAMES, nested_predictions, prepare_data, score_predictions, summarize
from src.controlled_analysis import audit_controlled_design


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def save_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")


def save_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        raise ValueError("refusing to write empty table: " + str(path))
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def save_predictions(path: Path, data, predictions, fold_ids) -> None:
    fields = list(data.metadata[0]) + ["outer_fold", "family"] + ["p_" + f for f in FRAMES] + ["log_loss", "brier", "accuracy"]
    # Fixed gzip header makes repeated runs byte reproducible.
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as compressed:
            with io.TextIOWrapper(compressed, encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=fields)
                writer.writeheader()
                for family, probabilities in predictions.items():
                    metrics = score_predictions(probabilities, data.y)
                    for i, meta in enumerate(data.metadata):
                        writer.writerow({**meta, "outer_fold": int(fold_ids[i]), "family": family,
                                         **{"p_" + f: float(probabilities[i, j]) for j, f in enumerate(FRAMES)},
                                         **{k: float(v[i]) for k, v in metrics.items()}})


def make_figures(results: dict, out_dir: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    out_dir.mkdir()
    colors = {"V4": "#0072B2", "R1": "#009E73", "E1": "#CC79A7", "P1": "#D55E00"}
    labels = {"V4": "V4: original Qwen", "R1": "R1: Gemma", "E1": "E1: stated probabilities", "P1": "P1: reworded Qwen"}
    plt.rcParams.update({"font.size": 11, "axes.spines.top": False, "axes.spines.right": False})
    fig, ax = plt.subplots(figsize=(9, 4), constrained_layout=True)
    for i, (name, result) in enumerate(results.items()):
        c = next(c for c in result["contrasts"] if c["subset"] == "own_history" and c["metric"] == "log_loss")
        ax.errorbar(c["mean"], i, xerr=[[max(0, c["mean"] - c["ci_lo"])], [max(0, c["ci_hi"] - c["mean"])]],
                    fmt="o", color=colors.get(name, "black"), capsize=4)
    ax.axvline(0, color="0.4", linestyle=":")
    ax.set_yticks(range(len(results)), [labels.get(n, n) for n in results])
    ax.invert_yaxis()
    ax.set_xlabel("Simple minus belief log loss (nats per choice)\nPositive favours the belief model set; negative favours the simple set")
    ax.set_title("Held out choice prediction, own history rounds 2 to 20\nDescriptive 95% bundle intervals, conditional on fitted predictions", fontsize=12)
    for ext in ("png", "pdf"):
        fig.savefig(out_dir / ("primary_comparison." + ext), dpi=300, bbox_inches="tight")
    plt.close(fig)

    n = len(results)
    fig, axes = plt.subplots(n, 1, figsize=(9, 2.4 * n), constrained_layout=True, squeeze=False)
    for ax, (name, result) in zip(axes[:, 0], results.items()):
        losses = {(r["episode_index"], r["family"]): r["log_loss"] for r in result["bundle_losses"]}
        groups = sorted({r["episode_index"] for r in result["bundle_losses"]})
        delta = [losses[g, "simple_selected"] - losses[g, "belief_selected"] for g in groups]
        ax.scatter(groups, delta, color=colors.get(name, "black"), s=28)
        ax.axhline(0, color="0.4", linestyle=":")
        ax.set_title(labels.get(name, name), loc="left", fontsize=12)
        ax.set_ylabel("Loss difference")
        ax.set_xticks(groups)
    axes[-1, 0].set_xlabel("Scenario seed index (all episodes retained)")
    fig.suptitle("Individual seed bundles: simple minus belief log loss", fontsize=14)
    for ext in ("png", "pdf"):
        fig.savefig(out_dir / ("bundle_diagnostics." + ext), dpi=300, bbox_inches="tight")
    plt.close(fig)


def write_report(results: dict, audits: dict, out_dir: Path) -> None:
    lines = ["# Can simpler rules explain these choices?", "", "## Scope", "",
             "Exploratory analysis of existing logs. No new model generations or paid compute.",
             "Every prediction is from a model fitted and selected without that episode's seed bundle.",
             "The comparison predicts choices, not hidden representations or deployment reward.", "",
             "## Main comparison", "",
             "Rounds 2 to 20 with own history, giving stable and swap conditions equal weight.",
             "Lower log loss is better. The difference is simple minus belief, so a positive",
             "difference favours the belief model set. Both sets are selected in inner validation.", "",
             "| Run | Simple log loss | Belief log loss | Difference [descriptive 95% interval] | Simple accuracy | Belief accuracy |",
             "| --- | ---: | ---: | --- | ---: | ---: |"]
    for name, result in results.items():
        rows = {r["family"]: r for r in result["metrics"] if r["subset"] == "own_history"}
        s, b = rows["simple_selected"], rows["belief_selected"]
        c = next(c for c in result["contrasts"] if c["subset"] == "own_history" and c["metric"] == "log_loss")
        lines.append(f"| {name} | {s['log_loss_mean']:.4f} | {b['log_loss_mean']:.4f} | {c['mean']:+.4f} [{c['ci_lo']:+.4f}, {c['ci_hi']:+.4f}] | {s['accuracy_mean']:.1%} | {b['accuracy_mean']:.1%} |")
    lines += ["", "![Comparison of held out predictive loss](figures/primary_comparison.png)", "",
              "Intervals resample whole seed bundles while holding fitted predictions fixed.",
              "They do not include retraining uncertainty. Overlapping training folds can correlate",
              "the predictions. These are descriptive exploratory intervals, not significance tests.", "",
              "## All model families", "",
              "All scores below use the same outer test rows. A family's parameters are chosen",
              "without its outer test rows. The selected set is not picked using this table."]
    for name, result in results.items():
        lines += ["", f"### {name}", "", "| Model | Log loss | Brier score | Accuracy |",
                  "| --- | ---: | ---: | ---: |"]
        for row in result["metrics"]:
            if row["subset"] == "own_history":
                lines.append(f"| {row['family']} | {row['log_loss_mean']:.4f} | {row['brier_mean']:.4f} | {row['accuracy_mean']:.1%} |")
        for label in ("simple_selected", "belief_selected"):
            counts = Counter(f["winners"][label] for f in audits[name])
            lines += ["", f"{label} across outer folds: " + ", ".join(f"{k}: {v}" for k, v in counts.items()) + "."]
        lines += ["", "| Condition | Rows | Invalid responses | Simple loss | Belief loss |",
                  "| --- | ---: | ---: | ---: | ---: |"]
        for diagnostic in result["diagnostics"]:
            subset = "condition:" + diagnostic["condition"]
            rows = {r["family"]: r for r in result["metrics"] if r["subset"] == subset}
            lines.append(f"| {diagnostic['condition']} | {diagnostic['n_rows']} | {diagnostic['n_invalid']} | {rows['simple_selected']['log_loss_mean']:.4f} | {rows['belief_selected']['log_loss_mean']:.4f} |")
        lines += ["", "Counts include round 1. Condition prediction scores use rounds 2 to 20.", "",
                  f"Detailed tables: [{name}/metrics.csv]({name}/metrics.csv), [{name}/contrasts.csv]({name}/contrasts.csv),",
                  f"[{name}/calibration.csv]({name}/calibration.csv), [{name}/fold_audit.json]({name}/fold_audit.json)."]
    lines += ["", "## Checks and limitations", "",
              "- The original design audit and the new history reconstruction checks passed for every included run.",
              "- All candidate families produced finite, positive, normalized probabilities for every row.",
              "- Donors, recipients, conditions and all rounds with the same seed index remained in one fold.",
              "- Invalid responses stay in the primary score. The valid response subset uses the same fitted models and is not an unbiased correction.",
              "- The baselines receive explicit frame annotations. The belief models also receive the true typed target likelihoods. Neither advantage was given to the LLM.",
              "- The E1 comparison omits its past stated probabilities, which the LLM could see.",
              "- The split holds out seed bundles, not unseen templates or a scientifically untouched dataset.",
              "- A predictive advantage cannot establish an internal mechanism. A small difference cannot establish equivalence.",
              "- The finite grids may miss better parameter values or a more suitable model family.",
              "- No result changes the original validity, learning, revision or mechanistic scaling gates.", "",
              "## Diagnostics and reproducibility", "",
              "The metric table includes mean, SD, median, range and IQR outlier counts across",
              "seed bundles. No outliers were removed. Gaussian errors and equal variance are not",
              "assumed. Calibration bins are descriptive and do not pretend that rounds are independent.", "",
              "![Individual seed bundle loss differences](figures/bundle_diagnostics.png)", "",
              "Each run directory also contains predictions.csv.gz with all probabilities and scores,",
              "and summary.json. The top level manifest records input and analysis hashes, versions,",
              "fold settings and output hashes. Raw messages are not copied into these outputs.", "",
              "The raw V4 family JSONL logs are local and are not tracked in Git. A fresh clone",
              "can run the synthetic tests, but reproducing this real data comparison requires those logs.", ""]
    (out_dir / "REPORT.md").write_text("\n".join(lines))


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, default=ROOT / "docs/baseline_comparison_20260907.json")
    parser.add_argument("--runs", nargs="+", choices=["V4", "R1", "E1", "P1"], default=None)
    parser.add_argument("--out-dir", type=Path, required=True, help="New output directory; existing directories are refused")
    args = parser.parse_args(argv)
    plan = json.loads(args.plan.read_text())
    names = args.runs or list(plan["runs"])
    if len(set(names)) != len(names):
        parser.error("duplicate run names")
    # Validate availability before creating outputs; never overwrite a result.
    inputs = []
    for name in names:
        path = ROOT / plan["runs"][name]
        for item in (path, path.with_suffix(".manifest.json")):
            if not item.is_file():
                raise FileNotFoundError("Required local data unavailable: " + str(item))
        inputs.append((name, path))
    args.out_dir.mkdir(parents=True, exist_ok=False)
    provenance = {"status": "running", "started_at": datetime.now(timezone.utc).isoformat(),
                  "analysis": "exploratory; no change to original gates", "plan": plan,
                  "plan_sha256": sha256(args.plan), "python": platform.python_version(),
                  "numpy": np.__version__, "git_commit_at_start": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
                  "source_sha256": {str(p.relative_to(ROOT)): sha256(p) for p in (
                      ROOT / "src/choice_baselines.py", Path(__file__).resolve(),
                      ROOT / "docs/BASELINE_COMPARISON_PLAN_20260907.md",
                      ROOT / "tests/test_choice_baselines.py")}, "inputs": {}}
    save_json(args.out_dir / "manifest.json", provenance)
    results, audits = {}, {}
    try:
        for name, path in inputs:
            print(f"{name}: checking data and histories", flush=True)
            with path.open() as handle:
                records = [json.loads(line) for line in handle if line.strip()]
            manifest = json.loads(path.with_suffix(".manifest.json").read_text())
            audit = audit_controlled_design(records, manifest)
            run_dir = args.out_dir / name
            run_dir.mkdir()
            save_json(run_dir / "design_audit.json", audit)
            if not audit["pass"]:
                raise ValueError(f"{name} design audit failed: {[k for k, v in audit['checks'].items() if not v]}")
            params = manifest["config"]["target_params"]
            if any(params[k] != plan[k] for k in ("p_match", "p_mismatch")):
                raise ValueError("target likelihood differs from declared analysis")
            data = prepare_data(records)
            if len(np.unique(data.groups)) != 20:
                raise ValueError("declared real comparison requires exactly 20 seed bundles")
            provenance["inputs"][name] = {"path": str(path.relative_to(ROOT)), "sha256": sha256(path),
                                         "manifest_sha256": sha256(path.with_suffix(".manifest.json")),
                                         "n_records": len(records), "n_episodes": manifest["n_episodes"],
                                         "model": manifest["provider"], "design_audit_pass": True}
            del records
            predictions, folds, ids = nested_predictions(data, plan, lambda message: print(name + ": " + message, flush=True))
            result = summarize(data, predictions, plan)
            results[name], audits[name] = result, folds
            save_json(run_dir / "summary.json", result)
            save_json(run_dir / "fold_audit.json", folds)
            for key in ("metrics", "contrasts", "bundle_losses", "diagnostics", "calibration"):
                save_csv(run_dir / (key + ".csv"), result[key])
            save_predictions(run_dir / "predictions.csv.gz", data, predictions, ids)
            save_json(args.out_dir / "manifest.json", provenance)
            c = next(c for c in result["contrasts"] if c["subset"] == "own_history" and c["metric"] == "log_loss")
            print(f"{name}: completed; simple minus belief loss {c['mean']:+.6f}", flush=True)
        make_figures(results, args.out_dir / "figures")
        write_report(results, audits, args.out_dir)
        import matplotlib
        provenance.update(status="completed", completed_at=datetime.now(timezone.utc).isoformat(), matplotlib=matplotlib.__version__)
        provenance["outputs_sha256"] = {str(p.relative_to(args.out_dir)): sha256(p) for p in sorted(args.out_dir.rglob("*"))
                                        if p.is_file() and p.name != "manifest.json"}
        save_json(args.out_dir / "manifest.json", provenance)
        print("Completed: " + str(args.out_dir / "REPORT.md"), flush=True)
    except Exception as error:
        provenance.update(status="failed", error=f"{type(error).__name__}: {error}")
        save_json(args.out_dir / "manifest.json", provenance)
        raise


if __name__ == "__main__":
    main()
