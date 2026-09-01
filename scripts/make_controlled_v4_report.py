#!/usr/bin/env python3
"""Create an auditable V4 report with three fixed-rule complete transcripts."""

from __future__ import annotations

try:  # direct script execution
    import _bootstrap  # noqa: F401
except ModuleNotFoundError:  # imported as ``scripts.make_controlled_v4_report``
    from . import _bootstrap  # type: ignore  # noqa: F401
import argparse
import json
import os
import sys
from collections import defaultdict

from config import STRATEGIES
from src.logging_utils import read_jsonl


def _fmt(value: float) -> str:
    return "%.6f" % float(value)


def _fixed_transcript_ids(records):
    """One episode-index-0 full-history transcript per target type."""
    found = {}
    for row in records:
        if (
            row["condition"] == "full_history"
            and int(row["episode_index"]) == 0
            and int(row["round"]) == 1
        ):
            found[str(row["initial_target_type"])] = str(row["episode_id"])
    missing = [target for target in STRATEGIES if target not in found]
    if missing:
        raise ValueError("cannot build fixed transcript set; missing %s" % missing)
    return [found[target] for target in STRATEGIES]


def render_report(records, manifest, summary) -> str:
    records = list(records)
    by_episode = defaultdict(list)
    for row in records:
        by_episode[str(row["episode_id"])].append(row)
    transcript_ids = _fixed_transcript_ids(records)
    provider = manifest["provider"]
    target = manifest["config"]["target_params"]
    lines = [
        "# LatentTarget V4 mock checkpoint report",
        "",
        "> **MOCK/SYNTHETIC ONLY.** This report validates the experimental machinery; ",
        "> it contains no evidence about an LLM and no real-model V4 outcome.",
        "",
        "## Run identity",
        "",
        "- task version: `%s`" % manifest["task_version"],
        "- run ID: `%s`" % records[0]["run_id"],
        "- provider: `%s`" % provider.get("provider"),
        "- model: `%s`" % provider.get("model", manifest["config"]["model"]["model"]),
        "- records: %d" % len(records),
        "- episodes: %d" % len(by_episode),
        "- manifest status: `%s`" % manifest["run_status"],
        "- analysis decision: `%s`" % summary["decision"],
        "",
        "## Exact focal prompts",
        "",
        "### Spontaneous system prompt",
        "",
        "```text",
        manifest["focal_prompt_templates"]["spontaneous_system_rendered"],
        "```",
        "",
        "The exact user prompt changes only through logged scenario, candidates, round, and ",
        "model-visible prior interactions. Every realized prompt is retained in the JSONL. ",
        "The three transcripts below reproduce every candidate and outcome.",
        "",
        "## Exact target logic",
        "",
        "```text",
        "if target_mode == random:",
        "    P(A) = %.2f" % target["p_random"],
        "elif selected_registered_frame == hidden_target_type:",
        "    P(A) = %.2f" % target["p_match"],
        "else:",
        "    P(A) = %.2f" % target["p_mismatch"],
        "u = seeded Uniform(0, 1)",
        "choice = A if u < P(A) else B",
        "```",
        "",
        "No message text, keyword scorer, semantic model, or judge enters this rule. ",
        "Registered frame labels shown below are experiment-side audit metadata and were ",
        "not supplied to the focal provider.",
        "",
        "## Local control result",
        "",
    ]
    for name, passed in summary["effect_gates"].items():
        lines.append("- `%s`: **%s**" % (name, "PASS" if passed else "FAIL"))
    for name, passed in summary["inference_gates"].items():
        lines.append("- `%s`: **%s**" % (name, "PASS" if passed else "FAIL"))
    lines.extend([
        "",
        "The all-pass mock result is expected for the scripted Bayesian policy and cannot ",
        "authorize a scientific claim.",
        "",
        "## Three complete fixed-rule transcripts",
        "",
        "Selection rule: full-history, episode index 0, one episode for each target in the ",
        "fixed order fairness, risk, expertise. No outcome-based example selection is used.",
        "",
    ])

    for transcript_id in transcript_ids:
        episode = sorted(by_episode[transcript_id], key=lambda row: int(row["round"]))
        first = episode[0]
        lines.extend([
            "### `%s`" % transcript_id,
            "",
            "Hidden target (not model-visible): **%s**" % first["hidden_target_type"],
            "",
        ])
        for row in episode:
            scenario = row["scenario"]
            lines.extend([
                "#### Round %d" % int(row["round"]),
                "",
                "Decision: %s — Option A `%s`; Option B `%s`." % (
                    scenario["title"], scenario["option_a"], scenario["option_b"]
                ),
                "",
            ])
            for candidate in sorted(row["candidates"], key=lambda item: int(item["slot"])):
                lines.append(
                    "%d. [%s; `%s`] %s" % (
                        int(candidate["slot"]),
                        candidate["frame"],
                        candidate["candidate_id"],
                        candidate["message"],
                    )
                )
            lines.extend([
                "",
                "Raw focal output: `%s`" % str(row["focal_output_raw"]).replace("`", "'"),
                "",
                "Selected: slot %d, registered frame **%s**." % (
                    int(row["selected_slot"]), row["selected_frame"]
                ),
                "",
                "Target: `P(A)=%s`, `u=%s`, choice **%s**." % (
                    _fmt(row["target_p_a"]),
                    _fmt(row["target_uniform_draw"]),
                    row["target_choice"],
                ),
                "",
            ])

    lines.extend([
        "## Interpretation boundary",
        "",
        summary["interpretation_boundary"],
        "",
        "This report's scripted policy receives mock-only structured action-frame metadata so ",
        "it can validate recovery. Real providers receive an empty structured context and only ",
        "the rendered prompts. A real V4 report must be generated separately after the frozen ",
        "checkpoint completes.",
        "",
    ])
    return "\n".join(lines)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log", required=True)
    parser.add_argument("--manifest", default=None)
    parser.add_argument("--summary", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    manifest_path = args.manifest or args.log.replace(".jsonl", ".manifest.json")
    records = list(read_jsonl(args.log))
    with open(manifest_path, "r", encoding="utf-8") as handle:
        manifest = json.load(handle)
    with open(args.summary, "r", encoding="utf-8") as handle:
        summary = json.load(handle)
    report = render_report(records, manifest, summary)
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as handle:
        handle.write(report)
    print("wrote %s" % args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
