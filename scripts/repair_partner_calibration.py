"""Fresh paired offline calibration. No provider, credentials or GPU code."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import platform
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np

from scripts.run_partner_offline import save_json, save_jsonl, sha, verdict
from src.partner_state import digest
from src.partner_policies import simulate_choices
from src.partner_statistics import bounds_from_choices, validity_from_choices, decision_batch, percentile_interval, wilson
from src.stratified_intervals import repaired_decision, stratified_interval, variance_components

METHODS = ("original_bootstrap", "minimum_df_t")


def load_config(path):
    config = json.loads(Path(path).read_text())
    parent_path = ROOT/config["parent_config"]
    if sha(parent_path) != config["parent_sha256"]:
        raise ValueError("parent config changed")
    parent = json.loads(parent_path.read_text())
    if sha(ROOT/parent["design_path"]) != parent["design_sha256"]:
        raise ValueError("original design changed")
    expected = {"method": "stratified_unbiased_variance_minimum_df_t", "method_candidates": 1,
                "primary_alpha": .025, "control_alpha": .05, "mean_threshold": .1,
                "control_margin": .1, "branch_validity": .98,
                "paid_run_authorized": False, "mechanistic_run_authorized": False}
    if any(config.get(k) != v for k, v in expected.items()):
        raise ValueError("unsupported method, gate or authorization change")
    merged = dict(parent, **config)
    merged["scenarios"] = parent["scenarios"]+config["extra_scenarios"]
    return config, merged


def rate(bits):
    hits = int(np.sum(bits)); n = len(bits)
    return {"count": hits, "rate": hits/n, "mc_ci": list(wilson(hits, n))}


def flags(d):
    return {"joint": d["joint_pass"], "both_primary": d["primary_pass"].all(1),
            "both_positive": d["positive_primary"].all(1),
            "any_two_sided": d["two_sided_primary_rejection"].any(1),
            "all_controls": d["control_pass"].all(1), "validity": d["validity_pass"]}


def scalar_row(d, i):
    return {k: v[i].tolist() for k, v in d.items()}


def calibration_cell(config, scenario, n, studies):
    seed = int(digest([config["seed"], scenario["id"], n]), 16)
    rng = np.random.default_rng(seed)
    decisions = {m: [] for m in METHODS}
    means, estimated, empirical_bootstrap, validity_all, rows = [], [], [], [], []
    for start in range(0, studies, config["batch_size"]):
        batch = min(config["batch_size"], studies-start)
        choices, types, vectors, strata = simulate_choices(batch, n, rng, scenario, config["policy_parameters"])
        lo, hi = bounds_from_choices(types, vectors, choices)
        valid = validity_from_choices(choices)
        pair = (decision_batch(lo, hi, strata, valid), repaired_decision(lo, hi, strata, valid))
        info = [variance_components(lo[:, :, j], strata) for j in range(6)]
        means.append(lo.mean(1)); validity_all.append(valid)
        estimated.append(np.stack([x["variance"] for x in info], axis=1))
        empirical_bootstrap.append(np.stack([x["empirical_bootstrap_variance"] for x in info], axis=1))
        for method, decision in zip(METHODS, pair):
            decisions[method].append(decision)
        for i in range(batch):
            rows.append({"study": start+i, "validity": valid[i].tolist(),
                         **{m: scalar_row(d, i) for m, d in zip(METHODS, pair)}})
    means = np.concatenate(means)
    summaries = []
    combined = {m: {k: np.concatenate([d[k] for d in ds]) for k in ds[0]} for m, ds in decisions.items()}
    for method, d in combined.items():
        summaries.append({"method": method, "scenario": scenario["id"], "role": scenario["role"],
                          "n": n, "studies": studies, "cell_seed": str(seed),
                          "mean_contrast_lower": means.mean(0).tolist(),
                          "empirical_variance_of_study_means": means.var(0, ddof=1).tolist(),
                          "average_unbiased_variance": np.concatenate(estimated).mean(0).tolist(),
                          "average_empirical_bootstrap_variance": np.concatenate(empirical_bootstrap).mean(0).tolist(),
                          "branch_validity_mean": np.concatenate(validity_all).mean(0).tolist(),
                          "individual_gate_rates": np.concatenate([d["primary_pass"], d["control_pass"]], axis=1).mean(0).tolist(),
                          **{k: rate(v) for k, v in flags(d).items()}})
    old, new = [combined[m]["joint_pass"] for m in METHODS]
    paired = {"scenario": scenario["id"], "n": n, "studies": studies,
              "new_only_pass": int((new & ~old).sum()), "old_only_pass": int((old & ~new).sum()),
              "both_pass": int((old & new).sum()), "neither_pass": int((~old & ~new).sum()),
              "paired_rate_difference": float(new.mean()-old.mean())}
    return summaries, rows, paired


def coverage_cell(config, distribution, mean, n, studies):
    seed = int(digest([config["coverage_diagnostics"]["seed"], distribution, mean, n]), 16)
    rng = np.random.default_rng(seed)
    strata = np.repeat(np.arange(6), n//6)
    rows, values, variances, zeros = [], [], [], []
    intervals = {m: [] for m in METHODS}
    for start in range(0, studies, config["batch_size"]):
        batch = min(config["batch_size"], studies-start)
        if distribution not in ("bernoulli", "signed_bernoulli"):
            raise ValueError("unknown coverage distribution")
        p = mean if distribution == "bernoulli" else (1+mean)/2
        x = (rng.random((batch, n)) < p).astype(float)
        if distribution == "signed_bernoulli":
            x = 2*x-1
        info = variance_components(x, strata)
        values.extend(info["mean"]); variances.extend(info["variance"]); zeros.extend(info["zero_variance"])
        pair = (percentile_interval(x, strata, .025), stratified_interval(x, strata, .025))
        for m, ci in zip(METHODS, pair):
            intervals[m].append(ci)
        for i in range(batch):
            rows.append({"study": start+i, "estimate": float(info["mean"][i]),
                         "zero_variance": bool(info["zero_variance"][i]),
                         "unbiased_variance": float(info["variance"][i]),
                         **{m: ci[i].tolist() for m, ci in zip(METHODS, pair)}})
    values = np.asarray(values)
    summaries = []
    for m, cis in intervals.items():
        ci = np.concatenate(cis)
        summaries.append({"method": m, "distribution": distribution, "true_mean": mean,
                          "n": n, "studies": studies, "cell_seed": str(seed), "nominal_coverage": .975,
                          "empirical_mean": float(values.mean()), "sd_study_mean": float(values.std(ddof=1)),
                          "average_unbiased_variance": float(np.mean(variances)),
                          "coverage": rate((ci[:, 0] <= mean+1e-12) & (ci[:, 1] >= mean-1e-12)),
                          "zero_variance": rate(zeros), "positive_detection": rate(ci[:, 0] > 1e-12),
                          "threshold_continuation": rate((ci[:, 0] > 1e-12) & (values >= .1-1e-12))})
    return summaries, rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT/"docs/partner_repair_20260908.json")
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args()
    original, config = load_config(args.config)
    out = args.out_dir.resolve()
    out.mkdir(parents=True, exist_ok=False)
    started = time.perf_counter()
    paths = [args.config.resolve(), ROOT/config["parent_config"], ROOT/config["design_path"],
             ROOT/"docs/PARTNER_REPAIR_PLAN_20260908.md", Path(__file__).resolve(),
             ROOT/"scripts/run_partner_offline.py", ROOT/"scripts/check_partner_state_design.py",
             ROOT/"src/stratified_intervals.py", *sorted((ROOT/"src").glob("partner_*.py"))]
    inputs = {str(p.relative_to(ROOT)): sha(p) for p in paths}
    save_json(out/"repair_snapshot.json", original); save_json(out/"merged_config.json", config)
    save_json(out/"inputs_before_run.json", inputs)
    grid = [36] if args.smoke else config["n_grid"]
    studies = 100 if args.smoke else config["studies_per_cell"]
    if studies < 5000 and not args.smoke:
        raise ValueError("full screen requires at least 5000 studies")
    (out/"simulations").mkdir(); (out/"coverage").mkdir()
    power, paired, coverage = [], [], []
    for scenario in config["scenarios"]:
        for n in grid:
            summaries, rows, comparison = calibration_cell(config, scenario, n, studies)
            power.extend(summaries); paired.append(comparison)
            save_jsonl(out/"simulations"/f"{scenario['id']}_n{n}.jsonl.gz", rows)
            save_json(out/"power_summary.json", power); save_json(out/"paired_decisions.json", paired)
            print(json.dumps({"cell": scenario["id"], "n": n,
                              "old_new_joint": [r["joint"]["rate"] for r in summaries]}), flush=True)
    for distribution in config["coverage_diagnostics"]["distributions"]:
        for mean in config["coverage_diagnostics"]["means"]:
            for n in grid:
                count = 100 if args.smoke else config["coverage_diagnostics"]["studies_per_cell"]
                summaries, rows = coverage_cell(config, distribution, mean, n, count)
                coverage.extend(summaries)
                save_jsonl(out/"coverage"/f"{distribution}_mean{mean}_n{n}.jsonl.gz", rows)
                save_json(out/"coverage_summary.json", coverage)
                print(json.dumps({"coverage": distribution, "mean": mean, "n": n,
                                  "old_new_coverage": [r["coverage"]["rate"] for r in summaries]}), flush=True)
    result = {m: verdict(config, [r for r in power if r["method"] == m], args.smoke) for m in METHODS}
    result["coverage_is_not_distribution_free"] = True
    save_json(out/"verdict.json", result)
    if any(sha(ROOT/p) != h for p, h in inputs.items()):
        raise RuntimeError("inputs changed during run")
    save_json(out/"manifest.json", {"status": "COMPLETE", "utc": datetime.now(timezone.utc).isoformat(),
              "seconds": time.perf_counter()-started, "smoke": args.smoke,
              "python": platform.python_version(), "numpy": np.__version__, "inputs": inputs,
              "outputs": {str(p.relative_to(out)): sha(p) for p in sorted(out.rglob("*")) if p.is_file()},
              "model_calls": 0, "paid_calls": 0})
    print(json.dumps(result), flush=True)


if __name__ == "__main__":
    main()
