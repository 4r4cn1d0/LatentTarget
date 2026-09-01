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
    prompt_example_episode = sorted(
        by_episode[transcript_ids[0]], key=lambda row: int(row["round"])
    )
    if len(prompt_example_episode) < 2:
        raise ValueError("report needs at least two rounds for exact prompt examples")
    first_user_prompt = prompt_example_episode[0]["focal_user_prompt"]
    history_user_prompt = prompt_example_episode[1]["focal_user_prompt"]
    provider = manifest["provider"]
    target = manifest["config"]["target_params"]
    is_mock = str(provider.get("provider", "")).startswith("mock:")
    if is_mock:
        title = "# LatentTarget V4 mock checkpoint report"
        banner = (
            "> **MOCK/SYNTHETIC ONLY.** This report validates the experimental "
            "machinery; it contains no evidence about an LLM and no real-model "
            "V4 outcome."
        )
        gate_heading = "## Local control result"
        gate_note = (
            "The all-pass mock result is expected for the scripted Bayesian policy "
            "and cannot authorize a scientific claim."
        )
    else:
        title = "# LatentTarget V4 real-model behavioral checkpoint"
        banner = (
            "> **REAL-MODEL CONTROLLED-CHOICE CHECKPOINT.** The locked decision is "
            "`%s`. These results concern feedback-conditioned candidate selection; "
            "they do not by themselves establish an explicit latent representation."
            % summary["decision"]
        )
        gate_heading = "## Preregistered checkpoint result"
        gate_note = (
            "The decision above is mechanical: every frozen effect and inference "
            "gate must pass. A failed gate cannot be rescued by a favorable "
            "post-hoc analysis."
        )
    lines = [
        title,
        "",
        banner,
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
        "### Exact round-1 user prompt",
        "",
        (
            "This is the verbatim user prompt from round 1 of the first "
            "fixed-rule transcript."
        ),
        "",
        "```text",
        first_user_prompt,
        "```",
        "",
        "### Exact history-bearing user prompt",
        "",
        (
            "This is the verbatim round-2 user prompt from the same episode and "
            "shows exactly how prior messages and outcomes were rendered."
        ),
        "",
        "```text",
        history_user_prompt,
        "```",
        "",
        (
            "The exact user prompt changes only through logged scenario, candidates, "
            "round, and model-visible prior interactions. Every realized prompt is "
            "retained in the JSONL. The three transcripts below reproduce every "
            "candidate and outcome."
        ),
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
        (
            "No message text, keyword scorer, semantic model, or judge enters this "
            "rule. Registered frame labels shown below are experiment-side audit "
            "metadata and were not supplied to the focal provider."
        ),
        "",
        gate_heading,
        "",
    ]
    for name, passed in summary["effect_gates"].items():
        lines.append("- `%s`: **%s**" % (name, "PASS" if passed else "FAIL"))
    for name, passed in summary["inference_gates"].items():
        lines.append("- `%s`: **%s**" % (name, "PASS" if passed else "FAIL"))
    lines.extend([
        "",
        gate_note,
        "",
        "## Key preregistered metrics",
        "",
        "- valid candidate-number rate: `%s`" % _fmt(summary["valid_selection_rate"]),
        "- full-history early match: `%s`" % _fmt(
            summary["stable_condition_metrics"]["full_history"]["early_match"]["mean"]
        ),
        "- full-history held-out late match: `%s`" % _fmt(
            summary["stable_condition_metrics"]["full_history"]["late_heldout_match"]["mean"]
        ),
        "- full/no-history difference-in-differences: `%s` (`p_one_sided=%s`)" % (
            _fmt(summary["primary_contrasts"]["full_vs_no_difference_in_differences"]["mean"]),
            _fmt(summary["primary_contrasts"]["full_vs_no_difference_in_differences"]["p_value_one_sided"]),
        ),
        "- full minus shuffled held-out match: `%s`" % _fmt(
            summary["primary_contrasts"]["full_over_shuffled_late_heldout"]["mean"]
        ),
        "- swap new-target gain: `%s`" % _fmt(
            summary["swap_metrics"]["new_target_gain"]["mean"]
        ),
        "- swap old-target drop: `%s`" % _fmt(
            summary["swap_metrics"]["old_target_drop"]["mean"]
        ),
        "- swap late new-minus-old: `%s` (`p_one_sided=%s`)" % (
            _fmt(summary["swap_metrics"]["late_new_over_old"]["mean"]),
            _fmt(summary["swap_metrics"]["late_new_over_old"]["p_value_one_sided"]),
        ),
        "",
        "## Three complete fixed-rule transcripts",
        "",
        (
            "Selection rule: full-history, episode index 0, one episode for each "
            "target in the fixed order fairness, risk, expertise. No outcome-based "
            "example selection is used."
        ),
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

    if (
        not is_mock
        and summary["effect_gates"].get("silent_swap_new_over_old")
        and abs(float(summary["swap_metrics"]["late_new_over_old"]["mean"])) <= 1e-12
    ):
        lines.extend([
            "## Numerical audit note",
            "",
            (
                "The run-commit effect gate used a strict floating-point `> 0` "
                "comparison. The stored mean is effectively zero, so round-off "
                "marked that effect-size gate PASS. Treat it substantively as zero; "
                "the preregistered inference gate failed and the overall STOP "
                "decision is unchanged."
            ),
            "",
        ])

    final_provider_note = (
        "This report's scripted policy receives mock-only structured action-frame "
        "metadata so it can validate recovery. Real providers receive an empty "
        "structured context and only the rendered prompts."
        if is_mock
        else (
            "The real provider received an empty structured context and only the "
            "rendered prompts. Registered frame labels in this report are "
            "experiment-side audit metadata reconstructed after each choice."
        )
    )
    lines.extend([
        "## Interpretation boundary",
        "",
        summary["interpretation_boundary"],
        "",
        final_provider_note,
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
