#!/usr/bin/env python3
"""Write a deterministic target-scorer and judge instrument profile."""

from __future__ import annotations

import _bootstrap  # noqa: F401
import argparse
import json
import os
import sys

from src.instrument_diagnostics import summarize_instrument
from src.logging_utils import read_jsonl


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)

    summary = summarize_instrument(list(read_jsonl(args.log)))
    summary["log"] = args.log
    parent = os.path.dirname(args.out)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2, sort_keys=True, ensure_ascii=False)
        handle.write("\n")
    print("wrote", args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
