"""Build and test a local matched history diagnostic. Never runs a focal model."""

from __future__ import annotations

import argparse
from collections import Counter
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

from scripts.compare_choice_baselines import save_csv, save_json, sha256
from src.history_diagnostic import (
    FRAMES, INVARIANT_POLICIES, build_bank, decision, policy_probabilities,
    reference_inputs, request_schedule, simulate_design, synthetic_recovery,
)


def save_gzip_jsonl(path: Path, rows) -> None:
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as zipped:
            with io.TextIOWrapper(zipped, encoding="utf-8") as handle:
                for row in rows:
                    handle.write(json.dumps(row, sort_keys=True, allow_nan=False) + "\n")


def read_plan(path: Path) -> dict:
    plan = json.loads(path.read_text())
    if plan["recommend_paid_run"] is not False:
        raise ValueError("this driver cannot authorize paid inference")
    if plan["n_pairs"] != max(plan["n_grid"]) or any(n % 18 for n in plan["n_grid"]):
        raise ValueError("sample grid must match the fixed balanced bank")
    if plan["n_simulations"] < 1000 or plan["n_recovery_simulations"] < 1000:
        raise ValueError("production screen requires at least 1000 simulations")
    if plan["events_per_frame"] != 6 or plan["fixed_suffix_length"] != 3:
        raise ValueError("rendered diagnostic requires 18 history observations and a 3 event suffix")
    return plan


def expected_effects(pairs, predictions) -> list[dict]:
    focuses = np.array([p["focus"] for p in pairs])
    rows = []
    for name, probabilities in predictions.items():
        margins = probabilities[np.arange(len(pairs)), :, focuses]
        gaps = margins[:, 1] - margins[:, 0]
        modal_choices = probabilities.argmax(2)
        modal_gap = (modal_choices[:, 1] == focuses).astype(float) - (modal_choices[:, 0] == focuses).astype(float)
        for frame in ("all", *FRAMES):
            mask = np.ones(len(pairs), dtype=bool) if frame == "all" else focuses == FRAMES.index(frame)
            rows.append({"policy": name, "focus": frame, "n_pairs": int(mask.sum()),
                         "mean_difference": float(gaps[mask].mean()), "sd_difference": float(gaps[mask].std(ddof=1)),
                         "min_difference": float(gaps[mask].min()), "max_difference": float(gaps[mask].max()),
                         "modal_choice_difference": float(modal_gap[mask].mean()),
                         "fraction_modal_choice_changes": float((modal_choices[mask, 0] != modal_choices[mask, 1]).mean())})
    return rows


def make_figures(power: list[dict], verdict: dict, out_dir: Path, plan: dict) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    out_dir.mkdir(exist_ok=True)
    plt.rcParams.update({"font.size": 11, "axes.spines.top": False, "axes.spines.right": False})
    fig, ax = plt.subplots(figsize=(9, 5), constrained_layout=True)
    for fraction, color in zip(plan["effect_fractions"], ["#0072B2", "#D55E00", "#009E73"]):
        rows = [r for r in power if r["role"] == "dynamic_alternative" and r["effect_fraction"] == fraction
                and r["coupling"] == "negative_bound" and r["unusable_fraction"] == .1]
        rows.sort(key=lambda r: r["n_pairs"])
        n = [r["n_pairs"] for r in rows]
        ax.plot(n, [r["joint_rate"] for r in rows], "o-", color=color, label=f"{fraction:.0%} of fitted contrast")
        ax.fill_between(n, [r["joint_ci_lo"] for r in rows], [r["joint_ci_hi"] for r in rows], color=color, alpha=.15)
    ax.axhline(.8, color="0.35", linestyle=":", label="80% sensitivity target")
    ax.set_xscale("log", base=2)
    ax.set_xticks(plan["n_grid"], [str(n) for n in plan["n_grid"]])
    ax.set_ylim(0, 1.03)
    ax.set_xlabel("Independent history pairs, not repeated calls")
    ax.set_ylabel("Probability both exact tests reject")
    ax.set_title("Synthetic sensitivity, not observed LLM performance\n10% unusable pairs; negative within pair dependence bound", fontsize=12)
    ax.legend(fontsize=10, loc="upper left")
    for ext in ("png", "pdf"):
        fig.savefig(out_dir / ("power_sensitivity." + ext), dpi=300, bbox_inches="tight")
    plt.close(fig)

    n = verdict["specificity_evaluation_n"]
    rows = [r for r in power if r["n_pairs"] == n and r["coupling"] == "negative_bound" and r["unusable_fraction"] == .1
            and (r["role"] != "dynamic_alternative" or r["effect_fraction"] == 1)]
    fig, ax = plt.subplots(figsize=(10, 8), constrained_layout=True)
    for i, row in enumerate(rows):
        color = "#0072B2" if row["role"] == "dynamic_alternative" else "#D55E00" if row["role"] == "recency_counterexample" else "#777777"
        ax.errorbar(row["joint_rate"], i, xerr=[[row["joint_rate"] - row["joint_ci_lo"]], [row["joint_ci_hi"] - row["joint_rate"]]],
                    fmt="o", color=color, capsize=3)
    ax.axvline(.05, linestyle=":", color="0.35")
    ax.set_yticks(range(len(rows)), [r["scenario"] for r in rows])
    ax.invert_yaxis()
    ax.set_xlim(-.02, 1.02)
    ax.set_xlabel("Joint rejection rate (Wilson 95% Monte Carlo intervals)")
    ax.set_title(f"Can ordinary recency mimic the diagnostic? N = {n} pairs\nOrange: no target type variable. Blue: dynamic belief. Grey: invariant controls.", fontsize=12)
    for ext in ("png", "pdf"):
        fig.savefig(out_dir / ("recency_counterexamples." + ext), dpi=300, bbox_inches="tight")
    plt.close(fig)


def write_samples(samples: list[dict], predictions: dict, out_dir: Path) -> None:
    lines = ["# Three constructed history pairs", "",
             "These are the first pair for each focus frame in the fixed bank, not selected after outcomes.",
             "No LLM has responded to these prompts. All probabilities below come from mathematical reference policies.", ""]
    for sample in samples:
        pair = sample["pair"]
        i = pair["pair_index"]
        frame = FRAMES[pair["focus"]]
        lines += [f"## Pair {i}: {frame}", "", "Each history has six observations per frame and three successes per frame.", "",
                  "| Policy | Low history: fairness / risk / expertise | High history: fairness / risk / expertise |",
                  "| --- | --- | --- |"]
        for name in ("reward_learning", "belief_static", "belief_dynamic", "decay_q:0.1", "discounted_evidence:0.9"):
            p = predictions[name][i]
            lines.append(f"| {name} | " + " / ".join(f"{x:.4f}" for x in p[0]) + " | " + " / ".join(f"{x:.4f}" for x in p[1]) + " |")
        lines += ["", "### Exact system prompt", "", "```text", sample["prompts"]["low"]["system"], "```"]
        for arm in ("low", "high"):
            lines += ["", f"### Exact user prompt: {arm} history", "", "```text", sample["prompts"][arm]["user"], "```"]
    (out_dir / "SAMPLE_PROMPTS.md").write_text("\n".join(lines) + "\n")


def write_report(power, recovery, effects, verdict, pairs, out_dir, plan):
    selection = verdict["selected_n_for_narrow_test"]
    n = verdict["specificity_evaluation_n"]
    lines = ["# Matched history diagnostic: local feasibility", "", "## Outcome", "",
             f"Sensitivity verdict: **{verdict['sensitivity_status']}**.", "",
             f"Interpretation verdict: **{verdict['interpretation_status']}**.", "",
             "No paid model calls were made. These are mathematical predictions and synthetic studies,",
             "not new LLM results. The original experiments and their stopping rules are unchanged.", "",
             "## What is matched", "",
             f"The fixed bank contains {len(pairs)} unique history pairs. Each pair has two 18 observation",
             "histories with the same six outcomes per frame, three successes per frame, and the same",
             "per frame outcome order. The final three observations are also identical. Only the",
             "interleaving between categories changes. The text rendering keeps the same messages,",
             "scenarios, reward associations and current candidates within the pair.", "",
             "Chosen action reward learning is exactly invariant for any learning rate. Static beliefs,",
             "counts and repetition are invariant too. A dynamic belief model can change its prediction.",
             "Global recency rules can also change, despite never representing a target type.", "",
             "## Prospective sensitivity", "",
             "Two one sided exact paired tests must pass at alpha = 0.025 each: the pooled contrast",
             "and the contrast restricted to fairness and risk focus pairs. The sample unit is the",
             "history pair, not each prompt or a duplicate greedy call. The table uses the 50% contrast",
             "with 10% unusable pairs, taking the weaker lower interval bound across two coupling scenarios.", "",
             "| Pairs | Planned calls including shams | Minimum required power lower | Maximum invariant null upper | Sensitivity and nulls pass |",
             "| --- | ---: | ---: | ---: | --- |"]
    for r in verdict["per_n"]:
        lines.append(f"| {r['n_pairs']} | {8*r['n_pairs']//3} | {r['minimum_required_power_lower']:.3f} | {r['maximum_invariant_null_upper']:.3f} | {r['power_pass'] and r['null_pass']} |")
    lines += ["", f"Smallest qualifying tested sample: {selection if selection is not None else 'none within the fixed ceiling'}.", "",
              "![Power sensitivity under explicit assumptions](figures/power_sensitivity.png)", "",
              f"There are {plan['n_simulations']:,} synthetic studies per scenario and sample size.",
              "The fitted contrast is not assumed to transfer exactly to a greedy LLM. We report nominal,",
              "half and quarter effects, independent sampling and the negative dependence bound, with",
              "zero or 10% random pair loss. These are sensitivity assumptions, not empirical estimates",
              "of future response noise. Informative format errors would require separate handling.", "",
              "## Specificity challenge", "",
              f"The prespecified check uses N = {n}. The following table reports the highest joint",
              "rejection rate across the declared coupling and loss scenarios for each ordinary recency",
              "policy. All scenario rows are retained in power.csv. The main test is about order",
              "invariance, so these are not false positives under that narrow null. They are",
              "counterexamples to interpreting a positive result as evidence uniquely for partner beliefs.", "",
              "| Policy without a target type state | Highest joint rejection | 95% Monte Carlo interval |",
              "| --- | ---: | --- |"]
    names = sorted({r["scenario"] for r in power if r["role"] == "recency_counterexample"})
    for name in names:
        r = max((r for r in power if r["scenario"] == name and r["n_pairs"] == n), key=lambda r: r["joint_rate"])
        lines.append(f"| {name} | {r['joint_rate']:.1%} | [{r['joint_ci_lo']:.1%}, {r['joint_ci_hi']:.1%}] |")
    lines += ["", "![Invariant nulls and ordinary recency counterexamples](figures/recency_counterexamples.png)", "",
              "## Closed set synthetic recovery", "",
              f"At N = {n}, the rows below show identification of the exact generating mathematical policy",
              "by maximum predictive likelihood. All 17 fixed policies were candidates. Ties count as unresolved.",
              "These numbers assume the true rule is in the candidate set. They are not evidence",
              "that an actual LLM uses any one of these algorithms.", "",
              "| Generating policy | Correct identification | Most frequent assigned label |",
              "| --- | ---: | --- |"]
    for name in sorted({r["generating_policy"] for r in recovery}):
        rows = [r for r in recovery if r["generating_policy"] == name and r["n_pairs"] == n]
        correct = next(r["rate"] for r in rows if r["selected_policy"] == name)
        assigned = max(rows, key=lambda r: r["rate"])["selected_policy"]
        lines.append(f"| {name} | {correct:.1%} | {assigned} |")
    lines += ["", "Recovery uses independent categorical draws, no dropout, and one fixed rule per dataset.",
              "It is deliberately separated from the primary paired sign test and its conservative",
              "coupling and loss checks. Good closed set recovery cannot repair a nonspecific primary test.",
              "With balanced counts, static beliefs and history frequency produce identical predictions",
              "under the shared choice settings. Their unresolved ties are structural nonidentifiability,",
              "not a failed implementation. Other near matches also limit recovery.", "",
              "## What is ready and what is not", "",
              "The candidate pool, all selected histories, fixed predictions, allocation, prompt exports,",
              "tests and CPU simulation outputs are ready for inspection. No provider runner or paid",
              "deployment is included. Exact prompts for the first pair of each focus frame are in",
              "[SAMPLE_PROMPTS.md](SAMPLE_PROMPTS.md). Every prompt was constructed, not generated by a focal agent.", "",
              "The intervention changes the distribution of histories and their chronological order.",
              "It measures responses to supplied history, not naturally acquired online partner models.",
              "It cannot establish latent representations, human persuasion, or causal mechanisms inside an LLM.",
              "The independent human semantic validation gate remains unfinished.", "",
              "The declared local screen ends here. Do not extend the sample grid or weaken a requirement",
              "to obtain a pass. Any narrower follow up requires an explicit claim, reviewed design and",
              "new approval before paid calls. Model availability and a current checkpoint would also",
              "need verification then; the reference probabilities here come from historical V4 fits.", "",
              "## Reproduce", "", "```bash",
              ".venv/bin/python scripts/design_history_diagnostic.py \\",
              "  --out-dir results/history_diagnostic_replay", "```", "",
              "The output directory must not already exist. The script uses saved baseline fit summaries,",
              "not raw model logs, credentials, model weights or a GPU. The manifest records inputs, source",
              "and output hashes. CSV tables retain every scenario, not just the cases in these figures.", ""]
    (out_dir / "REPORT.md").write_text("\n".join(lines))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, default=ROOT / "docs/history_diagnostic_20260907.json")
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    plan = read_plan(args.plan)
    fold_path = ROOT / plan["source_fold_audit"]
    baseline_manifest_path = ROOT / plan["source_manifest"]
    baseline_manifest = json.loads(baseline_manifest_path.read_text())
    if sha256(fold_path) != baseline_manifest["outputs_sha256"]["V4/fold_audit.json"]:
        raise ValueError("baseline source hash differs from its manifest")
    priors = reference_inputs(json.loads(fold_path.read_text()), plan)
    args.out_dir.mkdir(parents=True, exist_ok=False)
    sources = [ROOT / name for name in (
        "src/history_diagnostic.py", "scripts/design_history_diagnostic.py", "tests/test_history_diagnostic.py",
        "src/choice_baselines.py", "src/controlled_focal_agent.py", "src/controlled_messages.py", "src/scenarios.py",
        "scripts/compare_choice_baselines.py", "docs/HISTORY_DIAGNOSTIC_PLAN_20260907.md")]
    manifest = {"status": "running", "started_at": datetime.now(timezone.utc).isoformat(),
                "plan": plan, "plan_sha256": sha256(args.plan), "python": platform.python_version(), "numpy": np.__version__,
                "git_commit_at_start": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
                "inputs_sha256": {str(p.relative_to(ROOT)): sha256(p) for p in (fold_path, baseline_manifest_path)},
                "sources_sha256": {str(p.relative_to(ROOT)): sha256(p) for p in sources},
                "reference_priors": priors.tolist(), "new_focal_calls": 0, "paid_experiments": 0}
    save_json(args.out_dir / "manifest.json", manifest)
    try:
        pairs, pools = build_bank(plan, priors, lambda s: print(s, flush=True))
        save_json(args.out_dir / "pairs.json", pairs)
        save_gzip_jsonl(args.out_dir / "candidate_pool.jsonl.gz", pools)
        del pools
        predictions = policy_probabilities(pairs, priors, plan)
        save_json(args.out_dir / "policy_probabilities.json", {k: v.tolist() for k, v in predictions.items()})
        effects = expected_effects(pairs, predictions)
        save_csv(args.out_dir / "expected_effects.csv", effects)
        requests, key, samples = request_schedule(pairs, plan)
        save_gzip_jsonl(args.out_dir / "prepared_requests_NOT_RUN.jsonl.gz", requests)
        save_csv(args.out_dir / "analyst_request_key.csv", key)
        save_json(args.out_dir / "sample_prompt_audit.json", samples)
        write_samples(samples, predictions, args.out_dir)
        request_checks = {
            "all_pairs_matched": all(all(p["matching_checks"].values()) for p in pairs),
            "unique_active_histories": len({json.dumps(p[arm]) for p in pairs for arm in ("low", "high")}) == 2 * len(pairs),
            "opaque_request_schema": all(set(r) == {"request_id", "system", "user"} for r in requests),
            "unique_request_ids": len({r["request_id"] for r in requests}) == len(requests),
            "fixed_request_count": len(requests) == 8 * len(pairs) // 3,
            "positive_ensemble_reference_orientation": all(p["reference_focus_gap"] > 0 for p in pairs),
            "null_invariance": all(np.allclose(predictions[name][:, 0], predictions[name][:, 1], atol=1e-12, rtol=0) for name in INVARIANT_POLICIES),
        }
        save_json(args.out_dir / "construction_checks.json", request_checks)
        if not all(request_checks.values()):
            raise ValueError("construction checks failed: " + str(request_checks))
        print(f"Prepared {len(requests)} prompts; none dispatched. Starting synthetic checks.", flush=True)
        power = simulate_design(pairs, predictions, plan, lambda s: print(s, flush=True))
        save_csv(args.out_dir / "power.csv", power)
        recovery = synthetic_recovery(predictions, plan, lambda s: print(s, flush=True))
        save_csv(args.out_dir / "recovery.csv", recovery)
        verdict = decision(power, plan)
        save_json(args.out_dir / "decision.json", verdict)
        make_figures(power, verdict, args.out_dir / "figures", plan)
        write_report(power, recovery, effects, verdict, pairs, args.out_dir, plan)
        manifest.update(status="completed", completed_at=datetime.now(timezone.utc).isoformat(),
                        n_pairs=len(pairs), n_prepared_requests=len(requests), n_policy_families=len(predictions),
                        n_pairs_positive_under_all_five_priors=sum(min(p["focus_gap_by_prior"]) > 0 for p in pairs),
                        n_power_cells=len(power), n_simulated_power_studies=len(power) * plan["n_simulations"],
                        n_simulated_recovery_studies=len(predictions) * len(plan["n_grid"]) * plan["n_recovery_simulations"])
        manifest["outputs_sha256"] = {str(p.relative_to(args.out_dir)): sha256(p) for p in sorted(args.out_dir.rglob("*")) if p.is_file() and p.name != "manifest.json"}
        save_json(args.out_dir / "manifest.json", manifest)
        print(json.dumps({k: verdict[k] for k in ("sensitivity_status", "interpretation_status", "selected_n_for_narrow_test", "recommend_paid_run")}), flush=True)
        print("Report: " + str(args.out_dir / "REPORT.md"), flush=True)
    except Exception as error:
        manifest.update(status="failed", error=f"{type(error).__name__}: {error}")
        save_json(args.out_dir / "manifest.json", manifest)
        raise


if __name__ == "__main__":
    main()
