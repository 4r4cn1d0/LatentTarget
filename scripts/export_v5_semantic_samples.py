#!/usr/bin/env python3
"""Export blind V5 candidate text and a separate intended-label key."""

from __future__ import annotations

import _bootstrap  # noqa: F401
import argparse
import json
import os
import sys

from src.controlled_v5_messages import V5MessageBank
from src.v5_calibration import build_blind_semantic_samples


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bank", required=True)
    parser.add_argument("--samples-out", required=True)
    parser.add_argument("--key-out", required=True)
    parser.add_argument("--seed", type=int, default=20261001)
    args = parser.parse_args(argv)
    bank = V5MessageBank.load(args.bank)
    visible, key = build_blind_semantic_samples(bank, seed=args.seed)
    for path in (args.samples_out, args.key_out):
        parent = os.path.dirname(path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        if os.path.exists(path):
            raise FileExistsError("refusing to overwrite %s" % path)
    with open(args.samples_out, "w", encoding="utf-8") as handle:
        for row in visible:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    with open(args.key_out, "w", encoding="utf-8") as handle:
        json.dump(
            {
                "pool_sha256": bank.sha256(),
                "scientific_status": "hidden intended-label key; never judge-visible",
                "samples": key,
            },
            handle,
            indent=2,
        )
    print("wrote %d blind samples to %s" % (len(visible), args.samples_out))
    print("wrote hidden key to %s" % args.key_out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
