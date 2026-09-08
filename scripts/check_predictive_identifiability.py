#!/usr/bin/env python3
"""Write an exclusive offline certificate, without importing any provider."""
import argparse
import json
import sys
from fractions import Fraction
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.predictive_identifiability import design_certificate


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = design_certificate()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    def encode(value):
        if isinstance(value, Fraction):
            return str(value)
        raise TypeError(type(value).__name__)
    with args.output.open("x", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, default=encode)
        handle.write("\n")
    print(json.dumps({"status": report["status"], "model_calls": 0,
                      "grid_pairs": report["grid_pairs"],
                      "predictive_aliases": len(report["all_grid_witnesses"]),
                      "output": str(args.output)}))


if __name__ == "__main__":
    main()
