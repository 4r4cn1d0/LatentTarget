#!/usr/bin/env python3
"""Register a model's measured no-history prior into the V8 protocol.

Reads a target-free measurement log (V5 selected-bank-validation format),
verifies every selection was valid with no fallback and that the log's model
matches the registered model key, computes the three frame shares for the
overall / development / held-out sections with the same evaluator V5 used,
registers the largest overall share as the model's DEFAULT FRAME, and appends
two measured nuisance cells. One command; no numbers typed by hand.

    python scripts/register_v8_prior.py --model-key gemma4_31b \\
        --log data/calibration/v8-gemma4-prior.jsonl --dry-run
"""

from __future__ import annotations

import _bootstrap  # noqa: F401
import argparse
import json
import os
import sys
from typing import Any, Dict, List

from src.controlled_v5_messages import V5MessageBank
from src.v5_calibration import evaluate_v5_bank_validation
from src.v5_protocol_gate import file_sha256

FRAMES = ("fairness", "risk", "expertise")


def register(spec: Dict[str, Any], records: List[Dict[str, Any]], bank: V5MessageBank,
             model_key: str, log_path: str, manifest_path: str) -> Dict[str, Any]:
    model = spec["models"][model_key]
    if not records:
        raise ValueError("empty measurement log")
    bad = [r for r in records if r.get("selection_valid") is not True or r.get("fallback_used")]
    if bad:
        raise ValueError("%d records are invalid or used a fallback; refusing to register" % len(bad))
    modes = {r.get("mode") for r in records}
    if modes != {"selected_bank_validation"}:
        raise ValueError("expected only selected_bank_validation records, saw %s" % sorted(modes))
    names = {r.get("model_name") for r in records}
    if names != {model["id"]}:
        raise ValueError("log model %s does not match registered %s = %s" % (sorted(names), model_key, model["id"]))
    n_expected = spec["prior_measurement_schedule"]["n_records"]
    if len(records) != n_expected:
        raise ValueError("expected %d records, got %d" % (n_expected, len(records)))

    ev = evaluate_v5_bank_validation(records, bank)
    sections = {}
    for name, sec in ev["sections"].items():
        counts = {f: int(sec["counts"].get(f, 0)) for f in FRAMES}
        n = sum(counts.values())
        sections[name] = {"n": n, "counts": counts, "shares": {f: counts[f] / n for f in FRAMES}}
    overall = sections["overall"]
    default = max(FRAMES, key=lambda f: overall["shares"][f])

    model.update({
        "prior_measured": True,
        "measured_no_history_shares": overall["shares"],
        "measured_sections": sections,
        "registered_default_frame": default,
        "measurement_source": {
            "log_path": os.path.relpath(log_path, _bootstrap.ROOT),
            "log_file_sha256": file_sha256(log_path),
            "manifest_path": os.path.relpath(manifest_path, _bootstrap.ROOT) if manifest_path else None,
            "manifest_file_sha256": file_sha256(manifest_path) if manifest_path else None,
            "n_records": len(records),
            "evaluator": "src.v5_calibration.evaluate_v5_bank_validation",
        },
    })
    cells = [c for c in spec.get("nuisance_cells_measured", []) if not c["cell_id"].startswith(model_key + "_")]
    for section in ("overall", "heldout"):
        cells.append({
            "cell_id": "%s_v5bank_%s" % (model_key, section), "kind": "measured",
            "frame_shares": sections[section]["shares"],
            "provenance": "%s target-free no-history %s section, n=%d, log sha %s" % (
                model["id"], section, sections[section]["n"], file_sha256(log_path)[:16]),
        })
    spec["nuisance_cells_measured"] = cells
    return {"model_key": model_key, "default_frame": default, "sections": sections}


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--protocol", default=os.path.join(_bootstrap.ROOT, "docs", "v8_protocol.json"))
    p.add_argument("--model-key", required=True)
    p.add_argument("--log", required=True)
    p.add_argument("--manifest", default=None, help="default: <log>.manifest.json")
    p.add_argument("--dry-run", action="store_true")
    a = p.parse_args(argv)
    manifest = a.manifest or (a.log[:-6] + ".manifest.json" if a.log.endswith(".jsonl") else None)
    spec = json.load(open(a.protocol, encoding="utf-8"))
    bank = V5MessageBank.load(os.path.join(_bootstrap.ROOT, spec["selected_bank"]["path"]))
    records = [json.loads(l) for l in open(a.log, encoding="utf-8") if l.strip()]
    out = register(spec, records, bank, a.model_key, os.path.abspath(a.log),
                   os.path.abspath(manifest) if manifest and os.path.exists(manifest) else None)
    for name, sec in out["sections"].items():
        print("  %-12s n=%3d  %s" % (name, sec["n"], "  ".join("%s=%.3f" % (f, sec["shares"][f]) for f in FRAMES)))
    print("  registered default frame for %s: %s" % (a.model_key, out["default_frame"]))
    if a.dry_run:
        print("DRY RUN: protocol not written"); return 0
    json.dump(spec, open(a.protocol, "w", encoding="utf-8"), indent=2)
    print("wrote %s" % a.protocol)
    return 0


if __name__ == "__main__":
    sys.exit(main())
