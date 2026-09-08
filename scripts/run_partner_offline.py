"""Run the partner study offline. No credentials, model weights, or network calls."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
import platform
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np

from src.partner_state import allocation, make_bundle, build_ledger, integrity, WORDING, digest
from src.partner_policies import POLICIES, simulate_choices
from src.partner_pipeline import mock_responses, analyze
from src.partner_statistics import bounds_from_choices, validity_from_choices, decision_batch, wilson


def save_json(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")


def save_jsonl(path, rows):
    # Stable compression, no timestamp or path in header.
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as stream:
            for row in rows:
                stream.write((json.dumps(row, sort_keys=True, allow_nan=False) + "\n").encode())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def one_cell(config, scenario, n, studies):
    # Cell streams do not depend on ordering of scenarios in the JSON file.
    seed = int(digest([config["seed"], scenario["id"], n]), 16)
    rng = np.random.default_rng(seed)
    counts = {"joint": 0, "both_primary": 0, "both_positive": 0, "any_two_sided": 0,
              "all_controls": 0, "validity": 0}
    each = np.zeros(5, dtype=int)
    total_means = np.zeros(6)
    sum_squares = np.zeros(6)
    validity_sum = np.zeros(5)
    all_rows = []
    for start in range(0, studies, config["batch_size"]):
        batch = min(config["batch_size"], studies-start)
        choices, types, vectors, strata = simulate_choices(batch, n, rng, scenario, config["policy_parameters"])
        lower, upper = bounds_from_choices(types, vectors, choices)
        validity = validity_from_choices(choices)
        decision = decision_batch(lower, upper, strata, validity)
        flags = {"joint": decision["joint_pass"], "both_primary": decision["primary_pass"].all(1),
                 "both_positive": decision["positive_primary"].all(1),
                 "any_two_sided": decision["two_sided_primary_rejection"].any(1),
                 "all_controls": decision["control_pass"].all(1), "validity": decision["validity_pass"]}
        for key in counts:
            counts[key] += int(flags[key].sum())
        each += np.concatenate([decision["primary_pass"], decision["control_pass"]], axis=1).sum(0)
        total_means += decision["mean_lower"].sum(0)
        sum_squares += (decision["mean_lower"]**2).sum(0)
        validity_sum += validity.sum(0)
        # Store every study decision and bounds, not only successful examples.
        for i in range(batch):
            all_rows.append({"study": start+i, "mean_lower": decision["mean_lower"][i].tolist(),
                             "mean_upper": decision["mean_upper"][i].tolist(),
                             "ci_lower": decision["ci_lower_bounds"][i].tolist(),
                             "ci_upper": decision["ci_upper_bounds"][i].tolist(),
                             "validity": validity[i].tolist(),
                             **{key: bool(value[i]) for key, value in flags.items()}})
    summary = {"scenario": scenario["id"], "role": scenario["role"], "n": n, "studies": studies,
               "mean_contrast_lower": (total_means/studies).tolist(),
               "sd_study_mean_lower": np.sqrt(np.maximum(0, (sum_squares-total_means**2/studies)/max(1,studies-1))).tolist(),
               "branch_validity_mean": (validity_sum/studies).tolist(),
               "individual_gate_rates": (each/studies).tolist()}
    for key, hits in counts.items():
        lo, hi = wilson(hits, studies)
        summary[key] = {"count": hits, "rate": hits/studies, "mc_ci": [lo, hi]}
    return summary, all_rows


def verdict(config, rows, smoke):
    passing = []
    for n in config["n_grid"]:
        cells = {r["scenario"]: r for r in rows if r["n"] == n}
        if len(cells) != len(config["scenarios"]):
            continue
        sensitivity = all(cells[s]["joint"]["mc_ci"][0] >= config["required_joint_lower"] for s in config["required_alternative_cells"])
        calibration = all(cells[s["id"]]["joint"]["mc_ci"][1] <= config["required_null_upper"]
                          and cells[s["id"]]["any_two_sided"]["mc_ci"][1] <= config["required_null_upper"]
                          for s in config["scenarios"] if s["role"] == "null")
        if sensitivity and calibration:
            passing.append(n)
    return {"status": "SMOKE_ONLY" if smoke else "OFFLINE_SENSITIVITY_PASS" if passing else "OFFLINE_SCREEN_NO_GO",
            "passing_grid_values": [] if smoke else passing,
            "conditional_candidate_n": None if smoke or not passing else min(passing),
            "paid_run_authorized": False, "model_selected": False,
            "human_validation_complete": False, "mechanistic_work_authorized": False,
            "interpretation": "Participant specific reward learning can pass. No latent representation claim."}


def figures(rows, out):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    with plt.rc_context({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False}):
        fig, axes = plt.subplots(1, 2, figsize=(12, 4.8), constrained_layout=True)
        names = ("belief_full", "belief_half_shared", "belief_half_independent", "belief_half_mcar_1pct", "belief_half_selective_1pct", "feature_reward")
        colors = ("#0072B2", "#009E73", "#E69F00", "#D55E00", "#CC79A7", "#555555")
        for name, color in zip(names, colors):
            selected = sorted((r for r in rows if r["scenario"] == name), key=lambda r:r["n"])
            for ax, key in zip(axes, ("both_primary", "joint")):
                x = [r["n"] for r in selected]
                y = [r[key]["rate"] for r in selected]
                ax.plot(x, y, marker="o", color=color, label=name.replace("_", " "))
                ax.fill_between(x, [r[key]["mc_ci"][0] for r in selected], [r[key]["mc_ci"][1] for r in selected], color=color, alpha=.12)
        for ax, title in zip(axes, ("Primary tests only", "Complete decision including controls and validity")):
            ax.axhline(.8, color="0.3", linestyle=":")
            ax.set(xlabel="Independent history bundles", ylabel="Synthetic pass probability", ylim=(-.02,1.02), title=title)
            ax.set_xticks(sorted({r["n"] for r in rows}))
        axes[0].legend(fontsize=8)
        fig.suptitle("Prospective simulation, not LLM performance\nBands: 95% Wilson Monte Carlo intervals")
        fig.savefig(out/"power_screen.png", dpi=180)
        plt.close(fig)


def report(rows, benchmarks, decision, checks, out, smoke):
    lines = ["# Partner study offline screen", "", f"Status: **{decision['status']}**.", "",
             "These are mathematical mock policies and synthetic studies, not LLM results. No paid calls ran.",
             "The original design snapshot and historical scientific gates are unchanged.", "",
             "## What ran", "", f"Prepared {checks['bundles']} confirmation bundles and {checks['planned_requests']} requests, all undispatched.",
             f"Evaluated {len(benchmarks)} mock policies on that fixed bank.",
             f"Ran {sum(r['studies'] for r in rows):,} fresh simulated studies across {len(rows)} declared cells.", "",
             "## Complete decision versus primary tests", "",
             "A primary pass alone is insufficient. The complete decision also requires three control equivalence intervals and 98% validity in every choice branch.",
             "Monte Carlo intervals describe uncertainty in simulated pass rates, not uncertainty about real LLM performance.", "",
             "| Scenario | N | Both primary | All controls | Validity | Complete pass [95% MC interval] |",
             "| --- | ---: | ---: | ---: | ---: | --- |"]
    for r in rows:
        low, high = r["joint"]["mc_ci"]
        lines.append(f"| {r['scenario']} | {r['n']} | {r['both_primary']['rate']:.3f} | {r['all_controls']['rate']:.3f} | {r['validity']['rate']:.3f} | {r['joint']['rate']:.3f} [{low:.3f}, {high:.3f}] |")
    lines += ["", "![Synthetic sensitivity](power_screen.png)", "", "## Mock policies on the saved bank", "",
              "One fixed bank per policy. These results test the pipeline and alternative explanations; they are not power estimates.", "",
              "| Policy | BIND mean | TRANSFER mean | NEAR mean | Complete mock pass |",
              "| --- | ---: | ---: | ---: | --- |"]
    for name, result in benchmarks.items():
        mean = result["decision"]["mean_lower"]
        lines.append(f"| {name} | {mean[0]:.3f} | {mean[1]:.3f} | {mean[2]:.3f} | {result['decision']['joint_pass']} |")
    lines += ["", "## Decision and limitations", "",
              f"Conditional sample candidate: {decision['conditional_candidate_n']}. This is not permission to deploy.",
              "The required sensitivity scenarios and sample ceiling were written before this screen. No failed scenario was removed.",
              "The finite convolution computes the marginal empirical bootstrap distribution, not exact population coverage. Null rejection rates are separately recorded in power_summary.json.",
              "The mathematical policies have frame annotations and known likelihoods where declared. They do not model a real LLM's language understanding.",
              "Development and confirmation use disjoint aliases, scenario families and exact wording. Semantic family independence and human validity remain unverified.",
              "The additive composite rule remains an assumption. No new model has been selected; no activation experiment is authorized.",
              "Shared versus independent mixture routing and selective invalidity are explicit stress assumptions, not estimates from old LLM results.",
              "The selective scenario uses 3% invalidity for a fairness dominant choice and zero otherwise. Its overall missing fraction need not equal the nominal 1% label; actual branch validity is reported.",
              "All planned requests, mock responses, per-study decisions, plans and hashes are archived. Full event arrays for Monte Carlo studies are deterministically regenerated from the saved config and cell seeds.", ""]
    if smoke:
        lines += ["This is a smoke run only and cannot select a sample size.", ""]
    (out/"REPORT.md").write_text("\n".join(lines))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=ROOT/"docs/partner_state_offline_20260907.json")
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args()
    config = json.loads(args.config.read_text())
    design_path = ROOT/config["design_path"]
    if sha(design_path) != config["design_sha256"]:
        raise ValueError("original design hash mismatch")
    plan = json.loads(design_path.read_text())
    if any(plan["authorization"][k] for k in ("model_calls_allowed", "paid_calls_allowed", "mechanistic_runs_allowed")):
        raise ValueError("offline driver refuses dispatch authorization")
    if not args.smoke and config["studies_per_cell"] < 5000:
        raise ValueError("production screen requires 5000 studies per cell")
    out = args.out_dir.resolve()
    out.mkdir(parents=True, exist_ok=False)
    started = time.perf_counter()
    inputs = [args.config.resolve(), design_path, Path(__file__).resolve(),
              ROOT/"scripts/check_partner_state_design.py", *(ROOT/"src").glob("partner_*.py")]
    input_hashes = {str(p.relative_to(ROOT)): sha(p) for p in inputs}
    save_json(out/"design_snapshot.json", plan); save_json(out/"screen_snapshot.json", config)
    n_grid = [36] if args.smoke else config["n_grid"]
    studies = 100 if args.smoke else config["studies_per_cell"]
    bundles = [make_bundle(plan, r, "confirmation", config["seed"]) for r in allocation(max(n_grid), plan["seeds"]["allocation"])]
    ledger = build_ledger(plan, bundles, config["seed"])
    checks = integrity(plan, bundles, ledger)
    save_jsonl(out/"bundles.jsonl.gz", bundles); save_jsonl(out/"request_ledger.jsonl.gz", ledger)
    save_json(out/"integrity.json", checks)
    benchmarks = {}
    (out/"mocks").mkdir()
    for policy in (*POLICIES, "lexical_retrieval", "typed_history_oracle"):
        responses = mock_responses(plan, bundles, ledger, policy, config["policy_parameters"])
        benchmarks[policy] = analyze(plan, bundles, ledger, responses)
        save_jsonl(out/"mocks"/f"{policy}.responses.jsonl.gz", responses)
        save_json(out/"mocks"/f"{policy}.analysis.json", benchmarks[policy])
    # Unlabelled items for future independent human review, with a separate key.
    items, key = [], []
    for split, (training, clauses) in WORDING.items():
        for frame in range(3):
            for text in (training[frame].format(a="Option A"), *clauses[frame]):
                identifier = digest([split, text])[:16]
                items.append({"item_id": identifier, "text": text})
                key.append({"item_id": identifier, "registered_frame": frame, "split": split})
    items.sort(key=lambda x:x["item_id"])
    save_json(out/"human_review_items.json", items); save_json(out/"human_review_analyst_key.json", key)
    rows = []
    (out/"simulations").mkdir()
    for scenario in config["scenarios"]:
        for n in n_grid:
            summary, decisions = one_cell(config, scenario, n, studies)
            rows.append(summary)
            save_jsonl(out/"simulations"/f"{scenario['id']}_n{n}.jsonl.gz", decisions)
            save_json(out/"power_summary.json", rows)
            print(json.dumps({"completed_cell": scenario["id"], "n": n, "studies": studies,
                              "joint_rate": summary["joint"]["rate"]}), flush=True)
    decision = verdict(config, rows, args.smoke)
    save_json(out/"verdict.json", decision)
    figures(rows, out)
    report(rows, benchmarks, decision, checks, out, args.smoke)
    if any(sha(ROOT/p) != h for p,h in input_hashes.items()):
        raise RuntimeError("source changed during run; results require review")
    save_json(out/"manifest.json", {"status": "COMPLETE", "utc": datetime.now(timezone.utc).isoformat(),
              "seconds": time.perf_counter()-started, "python": platform.python_version(), "numpy": np.__version__,
              "smoke": args.smoke, "inputs": input_hashes, "outputs": {str(p.relative_to(out)):sha(p) for p in sorted(out.rglob("*")) if p.is_file()},
              "model_calls": 0, "paid_calls": 0})
    print(json.dumps(decision), flush=True)


if __name__ == "__main__":
    main()
