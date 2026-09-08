"""Reconcile both single-pass blind reviews and preserve every disagreement."""
import argparse
import json
from pathlib import Path
import statistics
import sys

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from src.diagnostic_pilot import read,write_new,file_sha,digest
from src.grounded_review import validate,RUBRIC


def report(source,reviews,out):
    source,reviews,out=map(Path,(source,reviews,out))
    items=read(source/"blind_review_items.json");keys=read(source/"analyst_key.json")
    key={r["item_id"]:r for r in keys};visible={r["item_id"]:r for r in items}
    if len(key)!=54 or set(key)!=set(visible):raise ValueError("incomplete review inventory")
    models={};joined={};files=[source/"blind_review_items.json",source/"analyst_key.json",Path(__file__),ROOT/"src/grounded_review.py"]
    frames=("fairness","risk","expertise")
    for suffix,model in (("sol","gpt-5.6-sol"),("luna","gpt-5.6-luna")):
        directory=reviews/suffix;summary=read(directory/"review.json");collected=[]
        if summary["model"]!=model or summary["input_sha256"]!=digest(items):raise ValueError("judge identity or input mismatch")
        for i in range(3):
            batch=items[i*18:(i+1)*18];claim=read(directory/f"batch_{i:02d}.claim.json");meta=read(directory/f"batch_{i:02d}.meta.json")
            raw=(directory/f"batch_{i:02d}.output.json").read_text()
            prompt=RUBRIC+"\nItems:\n"+json.dumps(batch,ensure_ascii=False,allow_nan=False)
            identity={"requested_model":model,"input_sha256":digest(batch),"prompt_sha256":digest(prompt),"index":i}
            if claim!=identity or any(meta.get(k)!=v for k,v in identity.items()) or meta["status"]!="COMPLETE" or meta["reported_model"]!=model or meta["output_sha256"]!=digest(raw):
                raise ValueError("raw judgment identity/hash mismatch")
            if read(directory/f"batch_{i:02d}.input.json")["prompt"]!=prompt:raise ValueError("judge prompt changed")
            collected.extend(validate(json.loads(raw),[r["item_id"] for r in batch]))
        if collected!=summary["results"]:raise ValueError("combined review differs from raw outputs")
        files.extend(sorted(p for p in directory.iterdir() if p.is_file()))
        disagreements=[]
        for r in collected:
            k=key[r["item_id"]];expected=frames[max(range(3),key=lambda i:k["registered_vector"][i])]
            if r["primary_frame"]!=expected:
                disagreements.append({"registered_primary":expected,**k,**r,"message":visible[r["item_id"]]["message"]})
        models[model]={"items":54,"batches":3,"registered_primary_agreement":54-len(disagreements),
                       "score_summaries":{k:{"mean":statistics.mean(r[k] for r in collected),"minimum":min(r[k] for r in collected)} for k in ("factual_support","choice_relevance","clarity")},
                       "disagreements":disagreements}
        joined[model]={r["item_id"]:r for r in collected}
    agreement=sum(joined["gpt-5.6-sol"][i]["primary_frame"]==joined["gpt-5.6-luna"][i]["primary_frame"] for i in key)
    result={"status":"MACHINE_REVIEW_COMPLETE_NOT_HUMAN_VALIDATION","machine_invocations":6,"message_assessments":108,
            "unique_messages":54,"interjudge_primary_agreement":agreement,"judges":models,
            "human_labels":0,"gate_threshold_preregistered":False,"confirmation_gate_pass":None,
            "focal_model_calls":0,"runpod_calls":0,"account_usage_consumed":True}
    out.mkdir(parents=True,exist_ok=False);write_new(out/"summary.json",result)
    lines=["# Grounded message machine review","","Six completed calls, 108 assessments of 54 distinct messages. No human validation.",
           "Both reviewers were blind to the target, outcomes, split, registered vectors and policy scores. They share a model family.",
           "No acceptance threshold was declared, so this report does not manufacture a pass/fail gate after observing scores.","",
           "| Judge | Primary agreement with registered dominant frame | Mean factual support | Minimum factual support |",
           "| --- | ---: | ---: | ---: |"]
    for model,res in models.items():
        score=res["score_summaries"]["factual_support"]
        lines.append(f"| {model} | {res['registered_primary_agreement']}/54 | {score['mean']:.4f} | {score['minimum']:.2f} |")
    lines += ["",f"The judges agree with each other on {agreement}/54 primary labels. These scores are subjective assessments, not measured probabilities of factual truth.",
              "Clause count is not the same as psychological strength. A mixed message can have two risk clauses but a stronger authority appeal.",""]
    for model,res in models.items():
        for r in res["disagreements"]:
            lines += [f"## {model}: {r['item_id']}","",f"Family {r['family']}; bank {r['bank']}; split {r['split']}.",
                      f"Registered primary: {r['registered_primary']}. Judge primary: {r['primary_frame']}.",r["message"],r["reason"],""]
    (out/"MACHINE_REVIEW.md").write_text("\n".join(lines))
    write_new(out/"manifest.json",{"inputs":{str(p.resolve()):file_sha(p) for p in files},
              "outputs":{p.name:file_sha(p) for p in out.iterdir() if p.is_file()}})
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source",type=Path,default=ROOT/"results/grounded_partner_readiness_20260908")
    p.add_argument("--reviews",type=Path,default=ROOT/"results/grounded_partner_machine_review_20260908")
    p.add_argument("--out-dir",type=Path,required=True)
    a=p.parse_args();r=report(a.source,a.reviews,a.out_dir)
    print({"status":r["status"],"assessments":108,"agreement":r["interjudge_primary_agreement"]})


if __name__=="__main__":main()
