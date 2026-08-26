#!/usr/bin/env python3
"""Blindly reclassify a saved run using the logged-in Codex CLI.

No focal-model calls are made. The judge sees only opaque ids and message text;
all experimental metadata remains outside its prompt. Calls are deterministic,
schema-constrained, cached, and resumable.
"""

from __future__ import annotations

import _bootstrap  # noqa: F401
import argparse
import json
import os
import sys
import tempfile

from src.blind_judge import CodexBlindJudge
from src.logging_utils import read_jsonl, write_manifest


def _default_out(log_path: str) -> str:
    name = os.path.basename(log_path).replace(".jsonl", ".codex-judge.jsonl")
    return os.path.join("data", "processed", name)


def reclassify_with_codex(log_path: str, out_path: str, judge: CodexBlindJudge) -> str:
    records = list(read_jsonl(log_path))
    if not records:
        raise ValueError("no records found in %s" % log_path)
    judged = judge.classify_messages(record["focal_message"] for record in records)

    parent = os.path.dirname(out_path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(prefix=".codex-judge-", suffix=".jsonl", dir=parent or ".")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            for source in records:
                record = dict(source)
                result = dict(judged[record["focal_message"]])
                record["strategy_scores"] = {
                    label: float(result[label])
                    for label in ("fairness", "risk", "expertise", "other")
                }
                record["primary_strategy"] = result["primary_strategy"]
                record["strategy_confidence"] = float(result["confidence"])
                record["classifier_name"] = judge.name
                record["classifier_ok"] = True
                record["classifier_error"] = None
                record["classifier_raw"] = result
                fh.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
        os.replace(tmp_path, out_path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise

    source_manifest_path = log_path[:-6] + ".manifest.json"
    if not os.path.exists(source_manifest_path):
        raise FileNotFoundError("source manifest not found: %s" % source_manifest_path)
    with open(source_manifest_path, "r", encoding="utf-8") as fh:
        manifest = json.load(fh)
    manifest.update(
        {
            "log_path": out_path,
            "n_records": len(records),
            "classifier": judge.describe(),
            "reclassified_from": log_path,
            "source_manifest": source_manifest_path,
            "judge_stats": {
                "unique_messages": len(judged),
                "newly_judged": judge.n_judged,
                "cache_hits": judge.n_cached,
            },
        }
    )
    manifest_path = out_path[:-6] + ".manifest.json"
    write_manifest(manifest_path, manifest)
    print(
        "reclassified %d records / %d unique messages with %s"
        % (len(records), len(judged), judge.name)
    )
    print("newly judged=%d  cache hits=%d" % (judge.n_judged, judge.n_cached))
    print("wrote", out_path)
    print("wrote", manifest_path)
    return out_path


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log", required=True)
    parser.add_argument("--out", default=None)
    parser.add_argument("--model", default="gpt-5.6-luna")
    parser.add_argument("--batch-size", type=int, default=24)
    parser.add_argument("--seed", type=int, default=20260826)
    parser.add_argument("--cache", default="data/processed/codex_judge_cache.jsonl")
    parser.add_argument(
        "--artifact-dir", default="results/qwen38_27b_gonogo/codex_judge/batches"
    )
    parser.add_argument("--codex-executable", default="codex")
    parser.add_argument("--timeout", type=int, default=600)
    args = parser.parse_args(argv)

    out_path = args.out or _default_out(args.log)
    judge = CodexBlindJudge(
        model=args.model,
        cache_path=args.cache,
        artifact_dir=args.artifact_dir,
        batch_size=args.batch_size,
        seed=args.seed,
        executable=args.codex_executable,
        timeout_s=args.timeout,
    )
    reclassify_with_codex(args.log, out_path, judge)
    return 0


if __name__ == "__main__":
    sys.exit(main())
