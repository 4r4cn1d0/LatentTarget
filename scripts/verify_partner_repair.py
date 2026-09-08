"""Read only manifest, archived decision and deterministic prefix verification."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import numpy as np

from scripts.run_partner_offline import sha,verdict
from scripts.verify_partner_offline import inside,load_jsonl
from scripts.repair_partner_calibration import METHODS,calibration_cell,coverage_cell,rate
from src.partner_state import digest


def verify_manifest(directory,replay=None):
    root = Path(directory).resolve()
    manifest = json.loads((root/"manifest.json").read_text())
    if manifest["status"] != "COMPLETE" or manifest["model_calls"] != 0 or manifest["paid_calls"] != 0:
        raise ValueError("not a completed offline artifact")
    actual = {str(p.relative_to(root)) for p in root.rglob("*") if p.is_file() and p != root/"manifest.json"}
    if actual != set(manifest["outputs"]):
        raise ValueError("manifest output set mismatch")
    for name,expected in manifest["outputs"].items():
        if sha(inside(root,name)) != expected:
            raise ValueError(f"artifact hash changed: {name}")
    for name,expected in manifest["inputs"].items():
        if sha(inside(ROOT,name)) != expected:
            raise ValueError(f"input hash changed: {name}")
    if replay is not None:
        other = verify_manifest(replay)
        if other["manifest"]["inputs"] != manifest["inputs"] or other["manifest"]["outputs"] != manifest["outputs"]:
            raise ValueError("scientific replay hashes differ")
    return {"manifest":manifest,"files_verified":len(actual),"inputs_verified":len(manifest["inputs"]),
            "full_scientific_replay_hash_match":replay is not None}


def archived_flags(d,validity):
    lower,upper = np.asarray(d["ci_lower_bounds"]),np.asarray(d["ci_upper_bounds"])
    mean = np.asarray(d["mean_lower"])
    positive = lower[:2,0] > 1e-12
    primary = positive & (mean[:2] >= .1-1e-12)
    controls = (lower[2:,0] >= -.1-1e-12) & (upper[2:,1] <= .1+1e-12)
    valid = bool((np.asarray(validity) >= .98-1e-12).all())
    expected = {"positive_primary":positive.tolist(),"primary_pass":primary.tolist(),
                "control_pass":controls.tolist(),"validity_pass":valid,
                "two_sided_primary_rejection":((lower[:2,0] > 1e-12) | (upper[:2,1] < -1e-12)).tolist(),
                "joint_pass":bool(primary.all() and controls.all() and valid)}
    if any(d[k] != v for k,v in expected.items()):
        raise ValueError("saved decision disagrees with its intervals and validity")
    return {"joint":expected["joint_pass"],"both_primary":bool(primary.all()),
            "both_positive":bool(positive.all()),"any_two_sided":any(expected["two_sided_primary_rejection"]),
            "all_controls":bool(controls.all()),"validity":valid}


def verify_calibration(directory,prefix=100,replay=None):
    root = Path(directory).resolve()
    checked = verify_manifest(root,replay)
    manifest = checked.pop("manifest")
    config = json.loads((root/"merged_config.json").read_text())
    power = json.loads((root/"power_summary.json").read_text())
    coverage = json.loads((root/"coverage_summary.json").read_text())
    scenarios = {s["id"]:s for s in config["scenarios"]}
    replays,raw_count = 0,0
    for summary in power:
        if summary["method"] != METHODS[0]:
            continue
        n,name = summary["n"],summary["scenario"]
        rows = load_jsonl(root/"simulations"/f"{name}_n{n}.jsonl.gz")
        if len(rows) != summary["studies"] or [r["study"] for r in rows] != list(range(len(rows))):
            raise ValueError("study ledger incomplete")
        raw_count += len(rows)
        for method in METHODS:
            saved = next(s for s in power if s["scenario"] == name and s["n"] == n and s["method"] == method)
            f = [archived_flags(r[method],r["validity"]) for r in rows]
            for k in f[0]:
                if saved[k] != rate([r[k] for r in f]):
                    raise ValueError("power summary disagrees with archived decisions")
        # Each prefix is one complete original batch, so RNG call shapes match.
        count = min(prefix,len(rows))
        if count and count != min(config["batch_size"],len(rows)):
            raise ValueError("replay prefix must equal one original batch")
        if count:
            _,regenerated,_ = calibration_cell(config,scenarios[name],n,count)
            if digest(regenerated) != digest(rows[:count]):
                raise ValueError("calibration prefix replay differs")
            replays += count
    coverage_count = 0
    for summary in coverage:
        if summary["method"] != METHODS[0]:
            continue
        n,distribution,mean = summary["n"],summary["distribution"],summary["true_mean"]
        rows = load_jsonl(root/"coverage"/f"{distribution}_mean{mean}_n{n}.jsonl.gz")
        if len(rows) != summary["studies"] or [r["study"] for r in rows] != list(range(len(rows))):
            raise ValueError("coverage ledger incomplete")
        coverage_count += len(rows)
        for method in METHODS:
            saved = next(s for s in coverage if s["distribution"] == distribution and s["true_mean"] == mean and s["n"] == n and s["method"] == method)
            cis = np.array([r[method] for r in rows]); estimates = np.array([r["estimate"] for r in rows])
            flags = {"coverage":(cis[:,0] <= mean+1e-12) & (cis[:,1] >= mean-1e-12),
                     "positive_detection":cis[:,0] > 1e-12,
                     "threshold_continuation":(cis[:,0] > 1e-12) & (estimates >= .1-1e-12),
                     "zero_variance":[r["zero_variance"] for r in rows]}
            if any(saved[k] != rate(v) for k,v in flags.items()):
                raise ValueError("coverage summary differs")
        count = min(prefix,len(rows))
        if count:
            _,regenerated = coverage_cell(config,distribution,mean,n,count)
            if digest(regenerated) != digest(rows[:count]):
                raise ValueError("coverage prefix replay differs")
            replays += count
    saved = json.loads((root/"verdict.json").read_text())
    for method in METHODS:
        if saved[method] != verdict(config,[r for r in power if r["method"] == method],manifest["smoke"]):
            raise ValueError("verdict replay differs")
    return dict(checked,status="VERIFIED_OFFLINE_CALIBRATION",calibration_datasets_checked=raw_count,
                coverage_datasets_checked=coverage_count,first_batch_datasets_regenerated=replays,
                full_simulation_regenerated=False,model_calls=0,paid_calls=0)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory",type=Path)
    parser.add_argument("--calibration",action="store_true")
    parser.add_argument("--replay-dir",type=Path)
    parser.add_argument("--output",type=Path)
    args = parser.parse_args()
    result = verify_calibration(args.directory,replay=args.replay_dir) if args.calibration else verify_manifest(args.directory,args.replay_dir)
    result.pop("manifest",None)
    if args.output is not None:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        with args.output.open("x") as stream:
            json.dump(result,stream,indent=2,allow_nan=False)
            stream.write("\n")
    print(json.dumps(result,indent=2))


if __name__ == "__main__":
    main()
