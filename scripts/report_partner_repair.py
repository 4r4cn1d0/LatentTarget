"""Generate figures and a complete data backed report from frozen offline outputs."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from scripts.run_partner_offline import sha,save_json
from scripts.verify_partner_repair import verify_manifest
from src.stimulus_audit import SHALLOW,REFERENCES


def interval_text(item):
    a,b = item["mc_ci"]
    return f"{item['rate']:.4f} [{a:.4f}, {b:.4f}]"


def figures(power,coverage,policies,required,out):
    colors = ("#D55E00","#0072B2")
    methods = ("original_bootstrap","minimum_df_t")
    labels = ("Original bootstrap","Candidate Student interval")
    with plt.rc_context({"font.size":10,"axes.spines.top":False,"axes.spines.right":False,
                         "svg.fonttype":"none","savefig.facecolor":"white"}):
        fig,axes = plt.subplots(1,3,figsize=(15,4.8),layout="constrained")
        for method,color,label in zip(methods,colors,labels):
            rows = sorted((r for r in power if r["scenario"] == "uniform_null" and r["method"] == method),key=lambda r:r["n"])
            x = [r["n"] for r in rows]; y = [r["any_two_sided"]["rate"] for r in rows]
            axes[0].plot(x,y,color=color,marker="o",label=label)
            axes[0].fill_between(x,[r["any_two_sided"]["mc_ci"][0] for r in rows],[r["any_two_sided"]["mc_ci"][1] for r in rows],color=color,alpha=.12)
        axes[0].axhline(.05,color=".4",linestyle=":")
        axes[0].set(title="Uniform null: any primary rejection",xlabel="Independent bundles",ylabel="Simulated error probability",ylim=(0,.12),xticks=[36,72,144,288])
        axes[0].legend(fontsize=8)
        for j,(method,color,label) in enumerate(zip(methods,colors,labels)):
            rows = [next(r for r in power if r["scenario"] == name and r["n"] == 288 and r["method"] == method) for name in required]
            x = np.arange(len(rows))+(j-.5)*.2
            y = np.array([r["joint"]["rate"] for r in rows]); ci = np.array([r["joint"]["mc_ci"] for r in rows])
            axes[1].errorbar(x,y,yerr=np.stack([y-ci[:,0],ci[:,1]-y]),fmt="o",color=color,capsize=3,label=label)
        axes[1].axhline(.8,color=".4",linestyle=":")
        axes[1].set(title="Complete continuation, N = 288",ylabel="Synthetic pass probability",ylim=(.7,1.01),
                    xticks=range(4),xticklabels=["Shared","Independent","1% missing","Selective\nmissing"])
        for mean,marker in ((.05,"o"),(.1,"s")):
            for method,color,label in zip(methods,colors,labels):
                rows = sorted((r for r in coverage if r["distribution"] == "bernoulli" and r["true_mean"] == mean and r["method"] == method),key=lambda r:r["n"])
                axes[2].plot([r["n"] for r in rows],[r["coverage"]["rate"] for r in rows],color=color,marker=marker,
                             linestyle="-" if mean == .05 else "--",label=f"{label.split()[0]}, mean {mean:g}")
        axes[2].axhline(.975,color=".4",linestyle=":")
        axes[2].set(title="Sparse Bernoulli coverage",xlabel="Independent bundles",ylabel="Coverage of the known mean",ylim=(.75,1.005),xticks=[36,72,144,288])
        axes[2].legend(fontsize=8)
        fig.suptitle("Offline statistical repair, not LLM evidence\n5,000 datasets per cell; shaded bands and bars are pointwise 95% Monte Carlo intervals",fontsize=12)
        for ext in ("png","svg"):
            fig.savefig(out/f"calibration_comparison.{ext}",dpi=180)
        plt.close(fig)
        fig,ax = plt.subplots(figsize=(11,5.8),layout="constrained")
        for i,policy in enumerate(SHALLOW+REFERENCES):
            old = sorted((r for r in policies if r["policy"] == policy and r["bank"] == "original_confirmation"),key=lambda r:r["seed"])
            new = sorted((r for r in policies if r["policy"] == policy and r["bank"] == "candidate_draft"),key=lambda r:r["seed"])
            for k,(a,b) in enumerate(zip(old,new)):
                y = i+(k-1)*.16
                x0,x1 = [r["decisions"]["minimum_df_t"]["mean_lower"][1] for r in (a,b)]
                ax.plot([x0,x1],[y,y],color=".8",lw=1,zorder=1)
                ax.scatter(x0,y,color=colors[0],marker="o",s=25,label="Original wording" if i==0 and k==0 else None)
                ax.scatter(x1,y,color=colors[1],marker="s",s=25,label="Candidate draft" if i==0 and k==0 else None)
        ax.axvline(0,color=".5",lw=1);ax.axvline(.1,color=".5",linestyle=":")
        ax.set(yticks=range(8),yticklabels=[p.replace("_"," ") for p in SHALLOW+REFERENCES],
               xlabel="Mean composite transfer contrast",xlim=(-.26,1.06),
               title="Paired wording audit, three fixed seeds at N = 288\nEach line joins the same histories; dots are seed results, not confidence intervals")
        ax.invert_yaxis();ax.legend(loc="lower left")
        for ext in ("png","svg"):
            fig.savefig(out/f"wording_audit.{ext}",dpi=180)
        plt.close(fig)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--calibration",type=Path,required=True);p.add_argument("--stimuli",type=Path,required=True)
    p.add_argument("--out-dir",type=Path,required=True)
    args = p.parse_args()
    for folder in (args.calibration,args.stimuli):
        checked = verify_manifest(folder)
        if checked["manifest"]["smoke"]:
            raise ValueError("report requires completed full runs")
    read = lambda folder,name:json.loads((folder/name).read_text())
    power = read(args.calibration,"power_summary.json");coverage = read(args.calibration,"coverage_summary.json")
    decision = read(args.calibration,"verdict.json");config = read(args.calibration,"merged_config.json")
    policies = read(args.stimuli,"policy_summary.json");audit = read(args.stimuli,"verdict.json")
    out = args.out_dir.resolve();out.mkdir(parents=True,exist_ok=False)
    figures(power,coverage,policies,config["required_alternative_cells"],out)
    lines = ["# Bounded repair: complete offline results","",
        f"Candidate statistical screen: **{decision['minimum_df_t']['status']}**.","",
        "**Overall project remains unapproved for deployment or mechanistic claims.** These are synthetic policies and simulated datasets, not new LLM results. Paid calls and GPU deployments: zero.","",
        "## What ran","",
        "One fixed interval candidate was compared with the original bootstrap on 280,000 fresh datasets. A separate 160,000 datasets checked nonzero coverage. Analyzing both methods does not double the number of independent datasets.",
        f"The paired text audit saved {audit['prompt_count']:,} undispatched prompts and {audit['synthetic_responses']:,} synthetic responses, covering eight policies, two wording banks and three fixed seeds. All failures are retained.","",
        "## Statistical decision at the sample ceiling","",
        f"Passing grid values for the candidate: {decision['minimum_df_t']['passing_grid_values']}. This is conditional on the fixed synthetic screen, not universal calibration or a real model power estimate.","",
        "Each primary uses alpha 0.025. Three controls must show equivalence within plus or minus 0.10, both primary lower mean bounds must reach 0.10, and all choice branches must have at least 98% validity. Pointwise 95% Wilson intervals quantify Monte Carlo uncertainty; they are not simultaneous intervals across this table.","",
        "| Scenario | Original complete pass [MC interval] | Candidate complete pass [MC interval] | Candidate any primary rejection [MC interval] |",
        "| --- | --- | --- | --- |"]
    for scenario in config["scenarios"]:
        rs = [next(r for r in power if r["scenario"]==scenario["id"] and r["n"]==288 and r["method"]==m) for m in ("original_bootstrap","minimum_df_t")]
        lines.append(f"| {scenario['id']} | {interval_text(rs[0]['joint'])} | {interval_text(rs[1]['joint'])} | {interval_text(rs[1]['any_two_sided'])} |")
    lines += ["","![Calibration comparison](calibration_comparison.png)","","## Why the variance repair helps, and where it does not","",
        "For equal stratum size m, the conditional empirical bootstrap variance is (m minus one)/m times the sample variance based estimate of mean uncertainty. At N = 36, m = 6 and the factor is 5/6. At N = 288 it is 47/48. The archived summaries compare both estimates against empirical variance across fresh study means. This identifies one source of small sample undercoverage, not necessarily its whole cause.",
        "The candidate uses the minimum stratum degrees of freedom, giving a conservative Student critical factor. It remains an approximation. Sample variance unbiasedness presumes independent, identically distributed observations within strata; fixed allocation heterogeneity can add conservative variation. Neither argument establishes general confidence coverage for arbitrary discrete distributions.",
        "In particular, a sparse sample with no observed successes can have zero estimated variance and a point interval. The following diagnostic outcomes are retained even when the selected null screen clears. Nominal marginal coverage is 0.975.","",
        "| Distribution | True mean | N | Original coverage [MC interval] | Candidate coverage [MC interval] | Zero variance rate | Candidate observed threshold continuation |",
        "| --- | ---: | ---: | --- | --- | ---: | ---: |"]
    for old in [r for r in coverage if r["method"]=="original_bootstrap"]:
        new = next(r for r in coverage if r["method"]=="minimum_df_t" and all(r[k]==old[k] for k in ("distribution","true_mean","n")))
        lines.append(f"| {old['distribution']} | {old['true_mean']} | {old['n']} | {interval_text(old['coverage'])} | {interval_text(new['coverage'])} | {new['zero_variance']['rate']:.4f} | {new['threshold_continuation']['rate']:.4f} |")
    lines += ["","The 0.10 observed mean requirement is not a test that the true effect exceeds 0.10. At a true mean of 0.10, only about half of estimates exceed that threshold even with strong detection against zero. These marginal checks do not include the full control gate.","",
        "## Wording results, every policy and seed","",
        "Each training body has eight whitespace words; each new candidate body has three eight word clauses. This equalizes word lengths, not model token lengths, character patterns or semantic validity. Mathematical references retain privileged registered frames or type access. Their unchanged results across banks are an implementation check, not evidence that an LLM understands both banks.","",
        "| Seed | Policy | Original BIND / TRANSFER | Draft BIND / TRANSFER | Original / draft complete candidate gate |",
        "| --- | --- | --- | --- | --- |"]
    for old in [r for r in policies if r["bank"]=="original_confirmation"]:
        new = next(r for r in policies if r["bank"]=="candidate_draft" and r["seed"]==old["seed"] and r["policy"]==old["policy"])
        a,b = old["decisions"]["minimum_df_t"],new["decisions"]["minimum_df_t"]
        lines.append(f"| {old['seed']} | {old['policy']} | {a['mean_lower'][0]:.4f} / {a['mean_lower'][1]:.4f} | {b['mean_lower'][0]:.4f} / {b['mean_lower'][1]:.4f} | {a['joint_pass']} / {b['joint_pass']} |")
    lines += ["","![Paired wording audit](wording_audit.png)","","## Interpretation and next boundary","",
        "None of the five frozen shallow policies passed the draft's positive complete gate. However, the character trigram policy had consistently negative transfer. An invertible lexical cue remains plausible. We did not add a reversed policy after seeing these outputs, and absence of a positive pass is not absence of lexical information.",
        "The additive simulator also remains compatible with participant specific feature reward learning. This legitimate alternative passes on some seeds without requiring a latent belief about target type. More model calls on this draft would not by themselves distinguish those explanations.",
        "The messages name fairness, caution or competence criteria without establishing why Option A satisfies those criteria. Their semantic validity therefore remains uncertain. The unlabelled export has 54 complete candidate messages and a separate analyst key; no human review was performed.",
        "The next checkpoint should review those messages, freeze a separate evaluation bank, and preregister lexical adversaries that can learn or reverse mappings on development data. A future test should distinguish reward value from target belief if that stronger claim remains the aim. This is a recommendation, not another redesign or a paid run launched by this report.",
        "No finding here demonstrates silent updating, a hidden representation, a causal internal mechanism, general persuasion ability or suitability for a particular research program. Historical failed gates and negative findings remain unchanged.",""]
    (out/"REPORT.md").write_text("\n".join(lines))
    save_json(out/"manifest.json",{"status":"COMPLETE","model_calls":0,"paid_calls":0,
        "inputs":{str(Path(__file__).resolve().relative_to(ROOT)):sha(Path(__file__)),
                  str((args.calibration/"manifest.json").resolve().relative_to(ROOT)):sha(args.calibration/"manifest.json"),
                  str((args.stimuli/"manifest.json").resolve().relative_to(ROOT)):sha(args.stimuli/"manifest.json")},
        "outputs":{str(p.relative_to(out)):sha(p) for p in sorted(out.iterdir()) if p.is_file()}})
    print(str(out/"REPORT.md"))


if __name__ == "__main__":
    main()
