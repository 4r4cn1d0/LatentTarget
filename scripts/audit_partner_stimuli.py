"""One frozen paired wording audit. All outputs are synthetic, all prompts undispatched."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import platform
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import numpy as np

from scripts.run_partner_offline import save_json, save_jsonl, sha
from scripts.repair_partner_calibration import load_config
from src.partner_state import allocation, make_bundle, digest, SCENARIOS
from src.stimulus_audit import (replace_wording, audit_ledger, audit_integrity, assert_wording_only_pair,
    audit_responses, audit_analysis, paired_effects, text_inventory, audit_candidates, body, SHALLOW, REFERENCES)


def validate_draft(draft):
    if draft["frame_order"] != ["fairness","risk","expertise"] or len(draft["training"]) != 3 or [len(x) for x in draft["clauses"]] != [3,3,3]:
        raise ValueError("invalid draft dimensions")
    if any(len(body(t.format(a="Option A")).split()) != 8 for t in draft["training"]):
        raise ValueError("training bodies must each have eight words")
    if any(len(t.split()) != 8 for group in draft["clauses"] for t in group):
        raise ValueError("draft clauses must each have eight words")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config",type=Path,default=ROOT/"docs/partner_repair_20260908.json")
    parser.add_argument("--out-dir",type=Path,required=True)
    parser.add_argument("--smoke",action="store_true")
    args = parser.parse_args()
    config,merged = load_config(args.config)
    audit = config["stimulus_audit"]
    if audit["policies"] != list(SHALLOW+REFERENCES) or audit["post_result_rewording_allowed"] or audit["human_semantic_validation"] or audit["production_heldout_bank"]:
        raise ValueError("audit definition changed")
    plan = json.loads((ROOT/merged["design_path"]).read_text())
    draft = json.loads((ROOT/audit["candidate_path"]).read_text())
    validate_draft(draft)
    out = args.out_dir.resolve(); out.mkdir(parents=True,exist_ok=False)
    started = time.perf_counter()
    inputs = [args.config.resolve(),ROOT/config["parent_config"],ROOT/merged["design_path"],
              ROOT/audit["candidate_path"],ROOT/"docs/PARTNER_REPAIR_PLAN_20260908.md",Path(__file__).resolve(),
              ROOT/"scripts/repair_partner_calibration.py",ROOT/"scripts/run_partner_offline.py",
              ROOT/"scripts/check_partner_state_design.py",ROOT/"src/stimulus_audit.py",
              ROOT/"src/stratified_intervals.py",*sorted((ROOT/"src").glob("partner_*.py"))]
    hashes = {str(p.relative_to(ROOT)):sha(p) for p in inputs}
    save_json(out/"inputs_before_run.json",hashes)
    save_json(out/"repair_snapshot.json",config); save_json(out/"draft_snapshot.json",draft)
    save_json(out/"design_snapshot.json",plan)
    n = 36 if args.smoke else audit["n"]
    seeds = audit["seeds"][:1] if args.smoke else audit["seeds"]
    summaries,comparisons,inventories,review,key = [],[],{},[],[]
    for seed in seeds:
        original = [make_bundle(plan,r,"confirmation",seed) for r in allocation(n,plan["seeds"]["allocation"])]
        all_results = {}
        for bank,wording in (("original_confirmation",None),("candidate_draft",draft)):
            directory = out/f"seed_{seed}"/bank; directory.mkdir(parents=True)
            bundles = replace_wording(original,wording)
            assert_wording_only_pair(original,bundles)
            ledger = audit_ledger(plan,bundles,seed,wording)
            save_json(directory/"integrity.json",audit_integrity(plan,bundles,ledger,wording))
            save_jsonl(directory/"bundles.jsonl.gz",bundles); save_jsonl(directory/"request_ledger.jsonl.gz",ledger)
            if seed == seeds[0]:
                inventories[bank] = {}
                for si,scenario in enumerate(SCENARIOS["confirmation"]):
                    canonical = dict(bundles[0],current=list(scenario),candidate_order=[0,1,2])
                    inventories[bank][str(si)] = text_inventory(plan,canonical,wording)
                    for kind in ("familiar","near","composite"):
                        texts,vectors = audit_candidates(plan,canonical,kind,wording)
                        for text,vector in zip(texts,vectors):
                            item = digest([bank,kind,scenario,text])[:20]
                            review.append({"item_id":item,"scenario":scenario[0],"option_a":scenario[1],
                                           "option_b":scenario[2],"message":text,
                                           "human_label":None,"human_semantic_validity":None})
                            key.append({"item_id":item,"bank":bank,"candidate_kind":kind,"registered_vector":vector})
            all_results[bank] = {}
            for policy in audit["policies"]:
                responses = audit_responses(plan,bundles,ledger,policy,merged["policy_parameters"],wording)
                result = audit_analysis(plan,bundles,ledger,responses,wording)
                all_results[bank][policy] = result
                save_jsonl(directory/f"{policy}.responses.jsonl.gz",responses)
                save_json(directory/f"{policy}.analysis.json",result)
                summaries.append({"seed":seed,"bank":bank,"policy":policy,"n":n,
                                  "response_counts":result["response_counts"],"decisions":result["decisions"]})
                save_json(out/"policy_summary.json",summaries)
                print(json.dumps({"seed":seed,"bank":bank,"policy":policy,
                                  "bind_transfer":result["decisions"]["minimum_df_t"]["mean_lower"][:2],
                                  "repaired_joint":result["decisions"]["minimum_df_t"]["joint_pass"]}),flush=True)
        for policy in audit["policies"]:
            comparisons.append({"seed":seed,"policy":policy,**paired_effects(all_results["original_confirmation"][policy],all_results["candidate_draft"][policy])})
    review.sort(key=lambda r:r["item_id"])
    save_json(out/"text_inventory.json",inventories)
    save_json(out/"human_review_items.json",review); save_json(out/"human_review_analyst_key.json",key)
    save_json(out/"paired_effects.json",comparisons)
    save_json(out/"verdict.json",{"status":"SMOKE_ONLY" if args.smoke else "TEXT_AUDIT_COMPLETE_NOT_DEPLOYMENT_APPROVAL",
              "candidate_shallow_complete_passes":[{"seed":r["seed"],"policy":r["policy"],"method":m}
                for r in summaries if r["bank"] == "candidate_draft" and r["policy"] in SHALLOW
                for m,d in r["decisions"].items() if d["joint_pass"]],
              "prompt_count":len(seeds)*2*n*24,"synthetic_responses":len(seeds)*2*n*24*len(audit["policies"]),
              "human_validation_complete":False,"production_heldout_bank":False,"paid_run_authorized":False,
              "interpretation":"A finite text audit cannot rule out reward learning or establish latent representations."})
    if any(sha(ROOT/p) != h for p,h in hashes.items()):
        raise RuntimeError("inputs changed during audit")
    save_json(out/"manifest.json",{"status":"COMPLETE","smoke":args.smoke,"utc":datetime.now(timezone.utc).isoformat(),
              "seconds":time.perf_counter()-started,"python":platform.python_version(),"numpy":np.__version__,
              "inputs":hashes,"outputs":{str(p.relative_to(out)):sha(p) for p in sorted(out.rglob("*")) if p.is_file()},
              "model_calls":0,"paid_calls":0})


if __name__ == "__main__":
    main()
