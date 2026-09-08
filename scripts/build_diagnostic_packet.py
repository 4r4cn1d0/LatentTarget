"""Build an immutable 60 request GPU pilot from verified offline artifacts."""
import argparse
import gzip
import io
import json
from pathlib import Path
import shutil
import sys
import tarfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.diagnostic_pilot import digest, file_sha, read, write_new, validate_packet, verify_package
from src.grounded_partner import grounded_integrity, grounded_candidates


SOURCES = ("config.py", "src/__init__.py", "src/focal_agent.py", "src/lexicons.py", "src/hf_provider.py",
           "src/diagnostic_pilot.py", "scripts/run_diagnostic_pilot.py", "requirements-pod.txt")


def rows(path):
    with gzip.open(path, "rt") as f:
        return [json.loads(line) for line in f]


def build(source, config_path, destination):
    source, destination = Path(source), Path(destination)
    manifest = read(source / "manifest.json")
    for relative, sha in manifest["outputs"].items():
        p = source / relative
        if not p.resolve().is_relative_to(source.resolve()) or file_sha(p) != sha:
            raise ValueError("offline evidence hash mismatch")
    plan, bank = read(source / "design_snapshot.json"), read(source / "bank_snapshot.json")
    bundles, ledger = rows(source / "evaluation/bundles.jsonl.gz"), rows(source / "evaluation/ledger.jsonl.gz")
    grounded_integrity(plan, bank, bundles, ledger)
    selected = [min((b for b in bundles if b["grounded_family"] == f["id"]), key=lambda b:b["bundle_index"]) for f in bank["evaluation"]]
    by_id = {b["bundle_id"]:b for b in selected}
    requests, analyst = [], []
    for original in ledger:
        if original["bundle_id"] not in by_id or original["spec"]["branch"] == "FORECAST":
            continue
        row = dict(original, execution_index=len(requests), seed=int(digest([202609089, original["request_id"]])[:8], 16))
        requests.append(row)
        b, s = by_id[row["bundle_id"]], row["spec"]
        texts, vectors = grounded_candidates(bank, b, s)
        # Identity rebinding changes which type is associated with a visible ID.
        who = 1-s["recipient"] if s["rebound"] else s["recipient"]
        target_type = b["types"][who]
        probabilities = [.5]*3 if s["branch"] == "RANDOM_RESPONSE" else [.38+.34*v[target_type] for v in vectors]
        analyst.append({"request_id":row["request_id"], "bundle_id":b["bundle_id"], "spec":s,
                        "types":b["types"], "candidate_vectors":vectors, "candidate_texts":texts,
                        "target_type":target_type, "candidate_p_a":probabilities,
                        "probabilities_are_simulator_expectations_not_observed_choices":True})
    packet = {"config":read(config_path), "requests":requests,
              "provenance":{"offline_manifest_sha256":file_sha(source/"manifest.json"),
                            "bank_sha256":file_sha(source/"bank_snapshot.json"),
                            "design_sha256":file_sha(source/"design_snapshot.json"),
                            "selected_bundles":[b["bundle_id"] for b in selected],
                            "selected_families":[b["grounded_family"] for b in selected]}}
    packet_sha = validate_packet(packet)
    destination.mkdir(parents=True, exist_ok=False)
    package = destination / "package"
    package.mkdir()
    for relative in SOURCES:
        target = package / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, target)
    # NumPy is the only nonpod dependency imported by this restricted source set.
    (package/"requirements-local.txt").write_text("numpy==2.4.6\n")
    write_new(package/"packet.json", packet)
    write_new(destination/"analyst_key.json", {"packet_sha256":packet_sha, "bundles":selected, "requests":analyst})
    selected_ids = set(by_id)
    baseline = {}
    for path in sorted((source / "evaluation").glob("*.responses.jsonl.gz")):
        baseline[path.name.split(".")[0]] = [r for r in rows(path) if r["request_id"].split("/")[0] in selected_ids and "/FORECAST/" not in r["request_id"]]
    write_new(destination/"baseline_responses.json", baseline)
    text = ["# Three diagnostic history transcripts", "", "These are simulated, teacher forced histories, not new focal model outputs.",
            "No GPU experiment has run. All 60 exact system/user prompts are in package/packet.json.",
            "The candidate probabilities and annotations in analyst_key.json never enter the provider prompt.",
            "Rebinding exchanges participant IDs on an unchanged history. It is not a target changing over time.", ""]
    for b in selected:
        text += [f"## {b['bundle_id']}: {b['grounded_family']}", "", f"Analyst types: {dict(zip(b['aliases'], b['types']))}. Frame order: fairness, risk, expertise.", ""]
        for name in ("events", "random_events"):
            text += [f"### {name}", ""]
            for i, e in enumerate(b[name], 1):
                text += [f"Record {i}. Participant {e['participant']}", e["decision"], f"Option A: {e['option_a']}. Option B: {e['option_b']}.",
                         f"Message: {e['message']}", f"Choice: {e['choice']}. Analyst frame: {e['analyst_frame']}. P(A): {e['analyst_p_a']}. Sampling draw: {e['analyst_uniform']}.", ""]
        text += ["### Current queries", ""]
        for r in analyst:
            if r["bundle_id"] == b["bundle_id"]:
                text += [f"{r['request_id']}: P(A) for candidates 1, 2, 3 = {r['candidate_p_a']}; vectors = {r['candidate_vectors']}", ""]
    (destination/"THREE_TRANSCRIPTS.md").write_text("\n".join(text))
    (package/"RUN.md").write_text("""# Diagnostic collection only

This package does not create a pod. No credentials are included. Do not store
outputs inside it. Use Python 3.12 on Linux and one A100 80GB for the real run.
The original project virtual environment is not part of this archive.

Verify without model dependencies:
`python scripts/run_diagnostic_pilot.py`

Mock collection after installing requirements-local.txt:
`python scripts/run_diagnostic_pilot.py --mode mock --output ../mock-results`

On an approved pod, install requirements-local.txt and requirements-pod.txt in
a fresh virtual environment. Do not unpin the torch/torchvision/torchaudio trio.
Place model cache and outputs on the new pod's persistent /workspace volume.
Before loading weights, the operator must verify the live price, storage,
absolute two hour pod deadline, external stop watchdog and result retrieval.
Process timeout alone does not stop GPU billing. Stopped volume storage still
costs money. Download the results before disposing of that exact pod volume.

Real collection requires a separate approval file created by the operator
after the user approves the exact packet and diagnostic budget:
`python scripts/run_diagnostic_pilot.py --mode hf --execute --approval ../approval.json --output ../pilot-results`

The runner requires the pinned model revision, runtime versions, single GPU,
BF16, no offload, no activation capture, at most 12,000 prompt tokens, strict
digit choices, and exactly 60 planned requests. A failed or uncertain request
is recorded and stops collection without retry or random fallback. It never
starts a second study. No confirmatory inference is allowed at three bundles.
""")
    write_new(package/"package_manifest.json", {"packet_sha256":packet_sha,
              "files":{str(p.relative_to(package)):file_sha(p) for p in sorted(package.rglob("*")) if p.is_file()}})
    verify_package(package)
    archive = destination / "latenttarget_diagnostic_20260908.tar.gz"
    with archive.open("xb") as raw, gzip.GzipFile(fileobj=raw, mode="wb", mtime=0, filename="") as gz, tarfile.open(fileobj=gz, mode="w") as tar:
        for path in sorted(package.rglob("*")):
            if not path.is_file():
                continue
            data = path.read_bytes()
            info = tarfile.TarInfo("package/"+str(path.relative_to(package)))
            info.size, info.mode, info.mtime = len(data), 0o644, 0
            tar.addfile(info, io.BytesIO(data))
    write_new(destination/"manifest.json", {"status":"PACKAGED_NOT_GPU_VALIDATED", "packet_sha256":packet_sha,
              "source_hashes":{f:file_sha(ROOT/f) for f in SOURCES}, "config_sha256":file_sha(config_path),
              "build_script_sha256":file_sha(__file__), "archive_sha256":file_sha(archive),
              "files":{str(p.relative_to(destination)):file_sha(p) for p in sorted(destination.rglob("*")) if p.is_file()}})
    return {"packet_sha256":packet_sha, "selected_bundles":list(by_id), "requests":60, "archive_bytes":archive.stat().st_size}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source", type=Path, default=ROOT/"results/grounded_partner_readiness_20260908")
    p.add_argument("--config", type=Path, default=ROOT/"docs/diagnostic_pilot_20260908.json")
    p.add_argument("--out-dir", type=Path, required=True)
    a = p.parse_args()
    print(json.dumps(build(a.source, a.config, a.out_dir)))


if __name__ == "__main__":
    main()
