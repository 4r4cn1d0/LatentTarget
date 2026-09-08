"""Prepare one diagnostic bank and audit fixed lexical controls; no model calls."""
import argparse
from datetime import datetime,timezone
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.run_partner_offline import save_json,save_jsonl,sha
from src.partner_state import digest
from src.grounded_partner import (make_grounded,grounded_ledger,grounded_integrity,fit_signs,
    responses,descriptives,equivalence_audit,texts_for,scenario_text,SHALLOW,REFERENCES)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("--out-dir",type=Path,required=True);a=p.parse_args()
    out=a.out_dir.resolve();out.mkdir(parents=True,exist_ok=False)
    plan=json.loads((ROOT/"docs/partner_state_study_20260907.json").read_text())
    bank=json.loads((ROOT/"docs/grounded_partner_bank_20260908.json").read_text())
    cfg=json.loads((ROOT/"docs/partner_state_offline_20260907.json").read_text())
    paths=[ROOT/"docs/POD_READINESS_PLAN_20260908.md",ROOT/"docs/grounded_partner_bank_20260908.json",
           ROOT/"docs/partner_state_study_20260907.json",ROOT/"docs/partner_state_offline_20260907.json",
           Path(__file__).resolve(),ROOT/"src/grounded_partner.py",ROOT/"src/stimulus_audit.py",
           ROOT/"src/stratified_intervals.py",ROOT/"scripts/run_partner_offline.py",ROOT/"scripts/check_partner_state_design.py",
           *sorted((ROOT/"src").glob("partner_*.py"))]
    hashes={str(f.relative_to(ROOT)):sha(f) for f in paths};save_json(out/"inputs_before.json",hashes)
    save_json(out/"bank_snapshot.json",bank);save_json(out/"design_snapshot.json",plan)
    fitted={};summary=[];review=[];key=[]
    for split,seed in (("development",202609086),("evaluation",202609087)):
        directory=out/split;directory.mkdir()
        bs=make_grounded(plan,bank,36,seed,split);ledger=grounded_ledger(plan,bank,bs,seed)
        save_json(directory/"integrity.json",grounded_integrity(plan,bank,bs,ledger))
        save_jsonl(directory/"bundles.jsonl.gz",bs);save_jsonl(directory/"ledger.jsonl.gz",ledger)
        for policy in SHALLOW+REFERENCES:
            if split=="development" and policy in SHALLOW:
                fitted[policy]=fit_signs(plan,bank,bs,ledger,policy,cfg["policy_parameters"])
                save_json(out/"frozen_development_fit.json",fitted)
            signs=fitted[policy]["signs"] if policy in SHALLOW else None
            raw=responses(plan,bank,bs,ledger,policy,cfg["policy_parameters"],signs)
            result=descriptives(plan,bank,bs,ledger,raw)
            save_jsonl(directory/f"{policy}.responses.jsonl.gz",raw);save_json(directory/f"{policy}.analysis.json",result)
            summary.append(dict(split=split,policy=policy,signs=signs,**result))
            print(json.dumps({"split":split,"policy":policy,"bind_transfer":result["mean_lower"][:2],"signs":signs}),flush=True)
        for family in bank[split]:
            for kind in ("familiar","near","composite"):
                texts,vectors=texts_for(family,kind)
                for text,vector in zip(texts,vectors):
                    item=digest([family["id"],kind,text])[:20]
                    review.append({"item_id":item,"scenario":scenario_text(family),"option_a":family["option_a"],"option_b":family["option_b"],"message":text})
                    key.append({"item_id":item,"split":split,"family":family["id"],"bank":kind,"registered_vector":vector})
    save_json(out/"audit_summary.json",summary);save_json(out/"identifiability.json",equivalence_audit())
    review.sort(key=lambda r:r["item_id"])
    save_json(out/"blind_review_items.json",review);save_json(out/"analyst_key.json",key)
    if any(sha(ROOT/f)!=h for f,h in hashes.items()):raise RuntimeError("source changed during run")
    save_json(out/"manifest.json",{"status":"COMPLETE","utc":datetime.now(timezone.utc).isoformat(),"smoke":False,
        "inputs":hashes,"outputs":{str(f.relative_to(out)):sha(f) for f in sorted(out.rglob("*")) if f.is_file()},
        "model_calls":0,"paid_calls":0,"diagnostic_only":True})


if __name__=="__main__":main()
