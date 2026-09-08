"""Read only verification and optional comparison of completed offline screens."""
import argparse
import gzip
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.run_partner_offline import sha, verdict
from src.partner_state import allocation, make_bundle, build_ledger, integrity, digest
from src.partner_policies import POLICIES
from src.partner_pipeline import mock_responses, analyze


def inside(root, name):
    relative = Path(name)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError("manifest path must be relative and contained")
    path = root / relative
    if not path.resolve().is_relative_to(root.resolve()):
        raise ValueError("manifest path escapes its root")
    return path


def load_jsonl(path):
    with gzip.open(path, "rt") as stream:
        return [json.loads(line) for line in stream]


def verify(directory, replay=None):
    directory = Path(directory).resolve()
    manifest = json.loads((directory/"manifest.json").read_text())
    if manifest["status"] != "COMPLETE" or manifest["model_calls"] != 0 or manifest["paid_calls"] != 0:
        raise ValueError("not a completed offline screen")
    actual = {str(p.relative_to(directory)) for p in directory.rglob("*") if p.is_file() and p != directory/"manifest.json"}
    if actual != set(manifest["outputs"]):
        raise ValueError("output file set differs from manifest")
    for name, expected in manifest["outputs"].items():
        if sha(inside(directory, name)) != expected:
            raise ValueError(f"output changed: {name}")
    for name, expected in manifest["inputs"].items():
        if sha(inside(ROOT, name)) != expected:
            raise ValueError(f"input changed: {name}")
    plan = json.loads((directory/"design_snapshot.json").read_text())
    config = json.loads((directory/"screen_snapshot.json").read_text())
    bundles = load_jsonl(directory/"bundles.jsonl.gz")
    ledger = load_jsonl(directory/"request_ledger.jsonl.gz")
    checks = integrity(plan, bundles, ledger)
    regenerated = [make_bundle(plan,r,"confirmation",config["seed"]) for r in allocation(len(bundles),plan["seeds"]["allocation"])]
    if bundles != regenerated or ledger != build_ledger(plan,regenerated,config["seed"]):
        raise ValueError("allocation or prompt replay differs")
    policies = (*POLICIES,"lexical_retrieval","typed_history_oracle")
    for policy in policies:
        responses = load_jsonl(directory/"mocks"/f"{policy}.responses.jsonl.gz")
        generated = mock_responses(plan,bundles,ledger,policy,config["policy_parameters"])
        if responses != generated:
            raise ValueError(f"mock response replay differs: {policy}")
        saved = json.loads((directory/"mocks"/f"{policy}.analysis.json").read_text())
        if digest(saved) != digest(analyze(plan,bundles,ledger,responses)):
            raise ValueError(f"analysis replay differs: {policy}")
    rows = json.loads((directory/"power_summary.json").read_text())
    saved_verdict = json.loads((directory/"verdict.json").read_text())
    if verdict(config,rows,manifest["smoke"]) != saved_verdict:
        raise ValueError("verdict replay differs")
    full_replay = False
    if replay is not None:
        replay = Path(replay).resolve()
        other = json.loads((replay/"manifest.json").read_text())
        if other["status"] != "COMPLETE" or manifest["inputs"] != other["inputs"] or manifest["outputs"] != other["outputs"]:
            raise ValueError("replay manifests differ beyond timestamp/runtime")
        for name, expected in other["outputs"].items():
            if sha(inside(replay,name)) != expected:
                raise ValueError(f"replay output changed: {name}")
        full_replay = True
    return {"status": "VERIFIED_OFFLINE_ARTIFACTS", "directory": str(directory),
            "files_hashed": len(manifest["outputs"]), "inputs_hashed": len(manifest["inputs"]),
            "bundle_count": checks["bundles"], "undispatched_requests": checks["planned_requests"],
            "mock_policies_regenerated_and_reanalyzed": len(policies),
            "full_simulation_replay_hashes_match": full_replay,
            "replay_directory": str(replay) if full_replay else None,
            "screen_verdict": saved_verdict["status"], "model_calls": 0, "paid_calls": 0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--replay-dir", type=Path)
    args = parser.parse_args()
    print(json.dumps(verify(args.directory,args.replay_dir),indent=2))


if __name__ == "__main__":
    main()
