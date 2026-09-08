"""Verify the frozen packet, or collect its requests exactly once."""
import argparse
from pathlib import Path
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.diagnostic_pilot import read, verify_package
from src.presentation_diagnostic import validate
from src.presentation_collection import collect

if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--execute', action='store_true')
    p.add_argument('--mode', choices=('mock', 'hf'), default='mock')
    p.add_argument('--approval', type=Path)
    p.add_argument('--output', type=Path)
    a = p.parse_args()
    manifest = verify_package(ROOT)
    packet, pilot = read(ROOT / 'presentation_packet.json'), read(ROOT / 'packet.json')
    sha = validate(packet, pilot)
    if manifest['packet_sha256'] != sha:
        raise ValueError('package packet identity differs')
    print(dict(status='VERIFIED', packet_sha256=sha), flush=True)
    if a.execute:
        if a.output is None or a.output.resolve().is_relative_to(ROOT):
            raise ValueError('external output directory required')
        result = collect(packet, pilot, a.output, a.mode, read(a.approval) if a.approval else None)
        print({k: v for k, v in result.items() if k != 'response_hashes'})
