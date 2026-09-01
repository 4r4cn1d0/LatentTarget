#!/usr/bin/env python3
"""Audit and visualize the completed V5 target-free calibration gate."""

from __future__ import annotations

import _bootstrap  # noqa: F401
import argparse
import csv
import json
import os
from collections import Counter
from datetime import datetime

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from config import STRATEGIES
from src.logging_utils import read_jsonl
from src.v5_protocol_gate import file_sha256


FRAME_COLORS = {
    "fairness": "#E69F00",
    "risk": "#56B4E9",
    "expertise": "#009E73",
}
SLOT_COLORS = {1: "#0072B2", 2: "#D55E00", 3: "#CC79A7"}


def _load_json(path: str):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def _parse_timestamp(value: str) -> datetime:
    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%S%z")


def _summarize(records):
    records = list(records)
    frame_counts = Counter(str(row["selected_frame"]) for row in records)
    slot_counts = Counter(int(row["selected_slot"]) for row in records)
    n = len(records)
    return {
        "n": n,
        "frame_counts": {frame: frame_counts.get(frame, 0) for frame in STRATEGIES},
        "frame_shares": {
            frame: frame_counts.get(frame, 0) / float(n) for frame in STRATEGIES
        },
        "slot_counts": {str(slot): slot_counts.get(slot, 0) for slot in (1, 2, 3)},
        "slot_shares": {
            str(slot): slot_counts.get(slot, 0) / float(n) for slot in (1, 2, 3)
        },
    }


def _audit_log(records, manifest, expected_mode: str, log_path: str):
    records = list(records)
    checks = {
        "completed": manifest.get("run_status") == "completed",
        "mode": manifest.get("mode") == expected_mode
        and all(row.get("mode") == expected_mode for row in records),
        "target_absent": manifest.get("target_simulator_present") is False,
        "history_absent": manifest.get("history_present") is False,
        "record_count": len(records) == manifest.get("n_records")
        == manifest.get("schedule", {}).get("n_records"),
        "strict_outputs": all(
            row.get("selection_valid") is True
            and row.get("fallback_used") is False
            and str(row.get("focal_output_raw")) in {"1", "2", "3"}
            for row in records
        ),
        "log_hash": file_sha256(log_path) == manifest.get("log_file_sha256"),
        "schedule_audit": manifest.get("schedule_audit", {}).get("pass") is True,
        "frozen_protocol": manifest.get("frozen_protocol", {})
        .get("plan_audit", {})
        .get("pass")
        is True,
    }
    return {"pass": all(checks.values()), "checks": checks}


def _style():
    plt.rcParams.update(
        {
            "font.family": "serif",
            "font.serif": ["Times New Roman", "DejaVu Serif"],
            "font.size": 9,
            "axes.titlesize": 10,
            "axes.titleweight": "bold",
            "axes.labelsize": 9,
            "legend.fontsize": 8,
            "legend.frameon": False,
            "figure.dpi": 150,
            "savefig.dpi": 300,
            "savefig.bbox": "tight",
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": True,
            "grid.alpha": 0.15,
            "grid.linestyle": "-",
        }
    )


def _plot(payload, output_dir: str):
    _style()
    fig, axes = plt.subplots(1, 2, figsize=(6.75, 2.8), constrained_layout=True)

    stage_keys = ("pool_overall", "validation_overall", "validation_development", "validation_heldout")
    stage_labels = ("Pool\noverall", "Selected\noverall", "Selected\ndevelopment", "Selected\nheld-out")
    x = np.arange(len(stage_keys))
    width = 0.23
    for index, frame in enumerate(STRATEGIES):
        values = [payload["summaries"][key]["frame_shares"][frame] for key in stage_keys]
        offset = (index - 1) * width
        bars = axes[0].bar(
            x + offset,
            values,
            width * 0.9,
            label=frame.capitalize(),
            color=FRAME_COLORS[frame],
            edgecolor="white",
            linewidth=0.5,
        )
        for bar, value in zip(bars, values):
            axes[0].text(
                bar.get_x() + bar.get_width() / 2,
                value + 0.012,
                f"{value:.2f}",
                ha="center",
                va="bottom",
                fontsize=6.4,
                rotation=90,
                color="#333333",
            )
    lower = payload["thresholds"]["minimum_frame_share"]
    upper = payload["thresholds"]["maximum_frame_share"]
    axes[0].axhspan(lower, upper, color="#999999", alpha=0.10, zorder=0)
    axes[0].axhline(1.0 / 3.0, color="#333333", linestyle="--", linewidth=0.9)
    axes[0].set_xticks(x)
    axes[0].set_xticklabels(stage_labels)
    axes[0].set_ylim(0, 0.68)
    axes[0].set_ylabel("Choice share")
    axes[0].set_title("Frame-choice balance", pad=34)
    axes[0].legend(
        ncol=3, loc="lower center", bbox_to_anchor=(0.5, 1.01), borderaxespad=0
    )

    slot_stage_keys = ("pool_overall", "validation_overall")
    slot_stage_labels = ("Pool calibration", "Selected-bank validation")
    x2 = np.arange(len(slot_stage_keys))
    width2 = 0.23
    for index, slot in enumerate((1, 2, 3)):
        values = [
            payload["summaries"][key]["slot_shares"][str(slot)]
            for key in slot_stage_keys
        ]
        offset = (index - 1) * width2
        bars = axes[1].bar(
            x2 + offset,
            values,
            width2 * 0.9,
            label=f"Slot {slot}",
            color=SLOT_COLORS[slot],
            edgecolor="white",
            linewidth=0.5,
        )
        for bar, value in zip(bars, values):
            axes[1].text(
                bar.get_x() + bar.get_width() / 2,
                value + 0.012,
                f"{value:.2f}",
                ha="center",
                va="bottom",
                fontsize=7,
                color="#333333",
            )
    axes[1].axhline(1.0 / 3.0, color="#333333", linestyle="--", linewidth=0.9)
    axes[1].set_xticks(x2)
    axes[1].set_xticklabels(slot_stage_labels)
    axes[1].set_ylim(0, 0.55)
    axes[1].set_ylabel("Choice share")
    axes[1].set_title("Residual position preference", pad=34)
    axes[1].legend(
        ncol=3, loc="lower center", bbox_to_anchor=(0.5, 1.01), borderaxespad=0
    )

    fig.suptitle("V5 target-free calibration gate: STOP", fontsize=11, fontweight="bold")
    pdf_path = os.path.join(output_dir, "fig_v5_calibration_gate.pdf")
    png_path = os.path.join(output_dir, "fig_v5_calibration_gate.png")
    fig.savefig(pdf_path)
    fig.savefig(png_path, dpi=300)
    plt.close(fig)
    return pdf_path, png_path


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--pool-log",
        default="data/calibration/qwen38_27b_v5_pool_calibration_20260901.jsonl",
    )
    parser.add_argument(
        "--pool-manifest",
        default="data/calibration/qwen38_27b_v5_pool_calibration_20260901.manifest.json",
    )
    parser.add_argument(
        "--validation-log",
        default="data/calibration/qwen38_27b_v5_selected_bank_validation_20260901.jsonl",
    )
    parser.add_argument(
        "--validation-manifest",
        default="data/calibration/qwen38_27b_v5_selected_bank_validation_20260901.manifest.json",
    )
    parser.add_argument(
        "--selection-report", default="results/v5_design/bank_selection/report.json"
    )
    parser.add_argument(
        "--validation-summary",
        default="results/v5_design/bank_validation/summary.json",
    )
    parser.add_argument(
        "--out-dir", default="results/v5_design/calibration_gate"
    )
    args = parser.parse_args(argv)

    outputs = (
        os.path.join(args.out_dir, "diagnostics.json"),
        os.path.join(args.out_dir, "frame_shares.csv"),
        os.path.join(args.out_dir, "fig_v5_calibration_gate.pdf"),
        os.path.join(args.out_dir, "fig_v5_calibration_gate.png"),
    )
    existing = [path for path in outputs if os.path.exists(path)]
    if existing:
        raise FileExistsError("refusing to overwrite %s" % ", ".join(existing))

    pool_records = list(read_jsonl(args.pool_log))
    validation_records = list(read_jsonl(args.validation_log))
    pool_manifest = _load_json(args.pool_manifest)
    validation_manifest = _load_json(args.validation_manifest)
    selection_report = _load_json(args.selection_report)
    validation_summary = _load_json(args.validation_summary)
    pool_audit = _audit_log(pool_records, pool_manifest, "pool_calibration", args.pool_log)
    validation_audit = _audit_log(
        validation_records,
        validation_manifest,
        "selected_bank_validation",
        args.validation_log,
    )
    if not pool_audit["pass"] or not validation_audit["pass"]:
        raise ValueError("calibration artifact integrity audit failed")
    if validation_summary.get("calibration_run_audit", {}).get("pass") is not True:
        raise ValueError("final validation report does not contain a passed run audit")
    if validation_summary.get("pass") is not False:
        raise ValueError("this diagnostic is only for a completed failed V5 gate")

    pool_overall = _summarize(pool_records)
    validation_overall = _summarize(validation_records)
    validation_development = _summarize(
        row for row in validation_records if row["split"] == "development"
    )
    validation_heldout = _summarize(
        row for row in validation_records if row["split"] == "heldout"
    )
    pool_start = _parse_timestamp(pool_records[0]["timestamp"])
    pool_end = _parse_timestamp(pool_records[-1]["timestamp"])
    validation_start = _parse_timestamp(validation_records[0]["timestamp"])
    validation_end = _parse_timestamp(validation_records[-1]["timestamp"])
    thresholds = validation_summary["thresholds"]
    marginal_gaps = {
        split: float(selection_report["selection_metrics"][split]["objective"]["predicted_frame_gap"])
        for split in ("development", "heldout")
    }
    payload = {
        "status": "STOP_CALIBRATION_INSTRUMENT_FAILED",
        "confirmatory_outcomes_used": False,
        "target_simulator_used": False,
        "history_used": False,
        "focal_model": validation_manifest["provider"],
        "artifact_audits": {"pool": pool_audit, "validation": validation_audit},
        "thresholds": thresholds,
        "summaries": {
            "pool_overall": pool_overall,
            "validation_overall": validation_overall,
            "validation_development": validation_development,
            "validation_heldout": validation_heldout,
        },
        "selector_marginal_rate_diagnostics": {
            "development_best_gap": marginal_gaps["development"],
            "heldout_best_gap": marginal_gaps["heldout"],
            "development_gap_within_frozen_limit": marginal_gaps["development"]
            <= thresholds["maximum_frame_gap"],
            "heldout_gap_within_frozen_limit": marginal_gaps["heldout"]
            <= thresholds["maximum_frame_gap"],
            "caveat": (
                "These are marginal per-candidate selection-rate gaps from the "
                "selector objective, not normalized predictions of joint selected-bank shares."
            ),
        },
        "timing": {
            "pool_first_record": pool_records[0]["timestamp"],
            "pool_last_record": pool_records[-1]["timestamp"],
            "pool_inference_seconds": (pool_end - pool_start).total_seconds(),
            "validation_first_record": validation_records[0]["timestamp"],
            "validation_last_record": validation_records[-1]["timestamp"],
            "validation_inference_seconds": (validation_end - validation_start).total_seconds(),
        },
        "files": {
            "pool_log": {"path": args.pool_log, "sha256": file_sha256(args.pool_log)},
            "pool_manifest": {"path": args.pool_manifest, "sha256": file_sha256(args.pool_manifest)},
            "validation_log": {"path": args.validation_log, "sha256": file_sha256(args.validation_log)},
            "validation_manifest": {"path": args.validation_manifest, "sha256": file_sha256(args.validation_manifest)},
            "selection_report": {"path": args.selection_report, "sha256": file_sha256(args.selection_report)},
            "validation_summary": {"path": args.validation_summary, "sha256": file_sha256(args.validation_summary)},
        },
    }

    os.makedirs(args.out_dir, exist_ok=True)
    with open(outputs[0], "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, allow_nan=False)
    with open(outputs[1], "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["stage", "frame", "count", "share", "minimum", "maximum"])
        for stage in (
            "pool_overall",
            "validation_overall",
            "validation_development",
            "validation_heldout",
        ):
            summary = payload["summaries"][stage]
            for frame in STRATEGIES:
                writer.writerow(
                    [
                        stage,
                        frame,
                        summary["frame_counts"][frame],
                        summary["frame_shares"][frame],
                        thresholds["minimum_frame_share"],
                        thresholds["maximum_frame_share"],
                    ]
                )
    pdf_path, png_path = _plot(payload, args.out_dir)
    print("artifact audits: PASS")
    print("frozen V5 calibration gate: STOP")
    print("wrote %s" % outputs[0])
    print("wrote %s" % outputs[1])
    print("wrote %s" % pdf_path)
    print("wrote %s" % png_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
