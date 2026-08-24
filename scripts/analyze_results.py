#!/usr/bin/env python3
"""Analyse one or more experiment logs: tables, figures, tests, console summary.

    python scripts/analyze_results.py --log data/raw/main_20250819-101500.jsonl

Optionally re-classify every stored message with a different classifier without
re-running any episodes (the raw messages are all in the log)::

    python scripts/analyze_results.py --log ... --reclassify llm \\
        --judge-provider openai --judge-model gpt-4o-mini
"""

from __future__ import annotations

import _bootstrap  # noqa: F401
import argparse
import json
import os
import sys

from config import JudgeConfig
from src.analysis import format_summary, run_full_analysis
from src.logging_utils import read_jsonl, write_manifest
from src.strategy_classifier import make_classifier


def reclassify(in_path: str, out_path: str, judge_cfg: JudgeConfig) -> str:
    """Re-label every message in a log with a different classifier.

    Writes a new log; the original is never modified.
    """
    classifier = make_classifier(judge_cfg)
    parent = os.path.dirname(out_path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    n = 0
    with open(out_path, "w", encoding="utf-8") as fh:
        for rec in read_jsonl(in_path):
            c = classifier.classify(rec["focal_message"])
            rec = dict(rec)
            rec["strategy_scores"] = {
                "fairness": c.fairness, "risk": c.risk, "expertise": c.expertise, "other": c.other,
            }
            rec["primary_strategy"] = c.primary_strategy
            rec["strategy_confidence"] = c.confidence
            rec["classifier_name"] = c.classifier
            rec["classifier_ok"] = c.ok
            rec["classifier_error"] = c.error
            rec["classifier_raw"] = c.raw
            fh.write(json.dumps(rec, ensure_ascii=False, default=str) + "\n")
            n += 1
    source_manifest_path = (
        in_path[:-6] + ".manifest.json" if in_path.endswith(".jsonl")
        else in_path + ".manifest.json"
    )
    out_manifest_path = (
        out_path[:-6] + ".manifest.json" if out_path.endswith(".jsonl")
        else out_path + ".manifest.json"
    )
    if os.path.exists(source_manifest_path):
        with open(source_manifest_path, "r", encoding="utf-8") as source_fh:
            manifest = json.load(source_fh)
        manifest.update({
            "log_path": out_path,
            "n_records": n,
            "classifier": classifier.describe(),
            "reclassified_from": in_path,
            "source_manifest": source_manifest_path,
        })
        write_manifest(out_manifest_path, manifest)
    else:
        print(
            "WARNING: source manifest missing (%s); no reclassified manifest "
            "was written. Bayesian/probe analyses will require --manifest."
            % source_manifest_path
        )
    print("re-classified %d records with %s -> %s" % (n, classifier.describe()["classifier"], out_path))
    return out_path


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--log", nargs="+", required=True)
    p.add_argument("--fig-dir", default="results/figures")
    p.add_argument("--tab-dir", default="results/tables")
    p.add_argument("--prefix", default="", help="prefix for every output filename")
    p.add_argument("--n-boot", type=int, default=2000)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--reclassify", default=None, choices=["keyword", "llm"])
    p.add_argument("--judge-provider", default="mock:judge")
    p.add_argument("--judge-model", default="mock")
    p.add_argument("--judge-cache", default="data/processed/judge_cache.jsonl")
    p.add_argument("--disjoint-lexicon", action="store_true")
    args = p.parse_args(argv)

    logs = list(args.log)
    if args.reclassify:
        cfg = JudgeConfig(
            kind=args.reclassify,
            provider=args.judge_provider,
            model=args.judge_model,
            cache_path=args.judge_cache,
            disjoint_lexicon=args.disjoint_lexicon,
        )
        logs = [
            reclassify(
                lp,
                os.path.join("data/processed", os.path.basename(lp).replace(".jsonl", ".reclassified.jsonl")),
                cfg,
            )
            for lp in logs
        ]

    summary = run_full_analysis(
        logs, args.fig_dir, args.tab_dir, n_boot=args.n_boot, seed=args.seed, prefix=args.prefix
    )
    print(format_summary(summary))
    print("\nfigures: %s" % args.fig_dir)
    print("tables : %s" % args.tab_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
