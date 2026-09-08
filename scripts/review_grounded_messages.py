"""Run the prespecified blind machine review; consumes Codex account usage."""
import argparse
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from src.grounded_review import review_batch
from src.partner_state import digest


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("--items",type=Path,required=True)
    p.add_argument("--out-dir",type=Path,required=True);p.add_argument("--model",choices=["gpt-5.6-sol","gpt-5.6-luna"],required=True)
    a=p.parse_args();items=json.loads(a.items.read_text());rows=[]
    for index,start in enumerate(range(0,len(items),18)):
        rows+=review_batch(items[start:start+18],a.model,a.out_dir,index)
        print(json.dumps({"judge":a.model,"completed_batch":index,"items":len(rows)}),flush=True)
    result={"status":"MACHINE_REVIEW_COMPLETE_NOT_HUMAN_VALIDATION","model":a.model,"input_sha256":digest(items),"results":rows}
    path=a.out_dir/"review.json"
    if path.exists():
        if json.loads(path.read_text())!=result:raise ValueError("existing review differs")
    else:
        with path.open("x") as f:json.dump(result,f,indent=2)


if __name__=="__main__":main()
