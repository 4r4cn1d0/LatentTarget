"""Verify the portable packet; collect 60 mock or explicitly approved GPU choices."""
import argparse
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.diagnostic_pilot import read, verify_package, validate_packet, collect


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--packet", type=Path, default=ROOT / "packet.json")
    p.add_argument("--output", type=Path)
    p.add_argument("--mode", choices=("verify", "mock", "hf"), default="verify")
    p.add_argument("--execute", action="store_true")
    p.add_argument("--approval", type=Path)
    a = p.parse_args()
    verify_package(ROOT)
    if a.packet.resolve() != ROOT / "packet.json":
        p.error("only the packaged packet can be executed")
    packet = read(a.packet)
    sha = validate_packet(packet)
    if a.mode == "verify":
        print(json.dumps({"status":"VERIFIED_NO_MODEL_CALLS", "packet_sha256":sha, "planned_requests":60}))
        return
    if not a.output or a.output.resolve().is_relative_to(ROOT):
        p.error("output must be outside the immutable package")
    if a.mode == "hf" and (not a.execute or not a.approval):
        p.error("GPU collection requires --execute and a packet-specific approval file")
    result = collect(packet, a.output, mode=a.mode, approval=read(a.approval) if a.approval else None)
    print(json.dumps(result))


if __name__ == "__main__":
    main()
