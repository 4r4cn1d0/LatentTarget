"""Run locally, independently of GPU collection, after explicit deployment approval."""
import argparse
import json
import os
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from src.diagnostic_watchdog import RestClient,watch


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--pod-id",required=True)
    p.add_argument("--deadline-utc",required=True)
    p.add_argument("--log",type=Path,required=True)
    p.add_argument("--execute",action="store_true")
    a=p.parse_args()
    if not a.execute:p.error("this can stop the selected pod; explicit --execute required")
    key=os.environ.get("RUNPOD_API_KEY","")
    client=RestClient(a.pod_id,key)
    with a.log.open("x") as f:
        def emit(event):
            line=json.dumps(event)
            f.write(line+"\n");f.flush();os.fsync(f.fileno())
            print(line,flush=True)
        watch(client,a.pod_id,a.deadline_utc,emit)


if __name__=="__main__":main()
