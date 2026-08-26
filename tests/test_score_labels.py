"""The human-label gate must be machine-readable and fail closed."""

from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _write_packet(tmp_path, labels):
    sheet = tmp_path / "labels.csv"
    key_path = tmp_path / "labels.key.json"
    with sheet.open("w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["sample_id", "message", "human_label"])
        for index, label in enumerate(labels):
            writer.writerow(["s%03d" % index, "message %d" % index, label])
    key = {
        "s000": {
            "condition": "full_history",
            "hidden_target_type": "fairness",
            "judge_label": "fairness",
            "classifier_name": "independent",
            "message": "message 0",
        },
        "s001": {
            "condition": "full_history",
            "hidden_target_type": "risk",
            "judge_label": "risk",
            "classifier_name": "independent",
            "message": "message 1",
        },
        "s002": {
            "condition": "no_history",
            "hidden_target_type": "fairness",
            "judge_label": "other",
            "classifier_name": "independent",
            "message": "message 2",
        },
        "s003": {
            "condition": "no_history",
            "hidden_target_type": "risk",
            "judge_label": "other",
            "classifier_name": "independent",
            "message": "message 3",
        },
    }
    key_path.write_text(json.dumps(key))
    return sheet, key_path


def test_complete_agreeing_labels_pass_gate_and_write_json(tmp_path):
    sheet, key = _write_packet(tmp_path, ["fairness", "risk", "other", "other"])
    out = tmp_path / "gate.json"
    completed = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "score_labels.py"),
            "--sheet",
            str(sheet),
            "--key",
            str(key),
            "--out",
            str(out),
        ],
        cwd=str(ROOT),
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    result = json.loads(out.read_text())
    assert result["gate_pass"] is True
    assert result["cohens_kappa"] == 1.0
    assert result["human_full_history_advantage"] is True


def test_blank_sheet_is_incomplete_and_returns_nonzero(tmp_path):
    sheet, key = _write_packet(tmp_path, ["", "", "", ""])
    out = tmp_path / "gate.json"
    completed = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "score_labels.py"),
            "--sheet",
            str(sheet),
            "--key",
            str(key),
            "--out",
            str(out),
        ],
        cwd=str(ROOT),
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 1
    result = json.loads(out.read_text())
    assert result["status"] == "incomplete"
    assert result["gate_pass"] is False


def test_missing_sheet_row_cannot_pass_gate(tmp_path):
    sheet, key = _write_packet(tmp_path, ["fairness", "risk", "other", "other"])
    rows = list(csv.reader(sheet.open()))
    with sheet.open("w", newline="") as fh:
        csv.writer(fh).writerows(rows[:-1])
    out = tmp_path / "gate.json"
    completed = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "score_labels.py"),
            "--sheet",
            str(sheet),
            "--key",
            str(key),
            "--out",
            str(out),
        ],
        cwd=str(ROOT),
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0
    result = json.loads(out.read_text())
    assert result["gate_pass"] is False
    assert any("missing sample_ids" in item for item in result["structural_issues"])


def test_more_than_twenty_percent_unsure_blocks_gate(tmp_path):
    sheet, key = _write_packet(tmp_path, ["fairness", "risk", "other", "unsure"])
    out = tmp_path / "gate.json"
    completed = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "score_labels.py"),
            "--sheet",
            str(sheet),
            "--key",
            str(key),
            "--out",
            str(out),
        ],
        cwd=str(ROOT),
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0
    result = json.loads(out.read_text())
    assert result["gate_pass"] is False
    assert result["gate_requirements"]["unsure_at_most_20_percent"] is False
