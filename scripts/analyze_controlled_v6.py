#!/usr/bin/env python3
"""Analyze one frozen V6 confirmatory log and emit every fixed diagnostic."""

from __future__ import annotations

import _bootstrap  # noqa: F401
import argparse
import csv
import hashlib
import json
import os
import shutil
import stat
import sys
import tempfile
from collections import defaultdict
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from config import CONTROLLED_V6_ANALYSIS_CONFIG, CONTROLLED_V6_VERSION, STRATEGIES
from src.controlled_v6_analysis import evaluate_controlled_v6_checkpoint
from src.file_lock import (
    ExclusiveFileLock,
    fsync_directory_best_effort,
    require_directory_nonsymlink,
    require_regular_nonsymlink,
)
from src.logging_utils import (
    open_regular_read_descriptor,
    read_jsonl,
    strict_json_load,
)


COLORS = {
    "full_history": "#D55E00",
    "no_history": "#0072B2",
    "shuffled_history": "#009E73",
    "random_target": "#777777",
    "old": "#E69F00",
    "new": "#CC79A7",
}
LABELS = {
    "full_history": "Full history",
    "no_history": "No history",
    "shuffled_history": "Shuffled history",
    "random_target": "Random responses",
}
MARKERS = {
    "full_history": "o",
    "no_history": "s",
    "shuffled_history": "^",
    "random_target": "D",
}
LINESTYLES = {
    "full_history": "-",
    "no_history": "--",
    "shuffled_history": "-.",
    "random_target": ":",
}
V6_FIGURE_STEMS = (
    "fig_v6_match_by_round",
    "fig_v6_success_by_round",
    "fig_v6_swap_adaptation",
    "fig_v6_control_comparison",
    "fig_v6_strategy_by_target",
    "fig_v6_transition_revision",
)
V6_TABLE_NAMES = (
    "v6_stable_conditions.csv",
    "v6_swap_episodes.csv",
    "v6_transition_revision.csv",
)
V6_SUMMARY_NAME = "v6_checkpoint_summary.json"
V6_PUBLISHED_FILE_MODE = 0o444


def _file_sha256(path: str, *, root: str | None = None) -> str:
    digest = hashlib.sha256()
    descriptor = open_regular_read_descriptor(
        path, root=root, label="V6 analysis artifact"
    )
    with os.fdopen(descriptor, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _require_canonical_output_path(path: str, repository_root: str) -> str:
    """Require the exact frozen output path with no symlinked components."""
    root = os.path.abspath(repository_root)
    relative = CONTROLLED_V6_ANALYSIS_CONFIG["canonical_out_dir"]
    if (
        type(relative) is not str
        or not relative
        or os.path.isabs(relative)
        or os.path.normpath(relative) != relative
    ):
        raise ValueError("frozen V6 analysis output path is not canonical")
    expected = os.path.abspath(os.path.join(root, relative))
    supplied = os.path.abspath(path)
    resolved_root = os.path.realpath(root)
    resolved_expected = os.path.realpath(expected)
    resolved_supplied = os.path.realpath(supplied)
    try:
        lexical_contained = os.path.commonpath([root, supplied]) == root
        resolved_contained = (
            os.path.commonpath([resolved_root, resolved_supplied])
            == resolved_root
        )
    except ValueError:
        lexical_contained = False
        resolved_contained = False
    if (
        supplied != expected
        or resolved_supplied != resolved_expected
        or not lexical_contained
        or not resolved_contained
    ):
        raise ValueError(
            "V6 analysis output must equal the contained frozen canonical directory %s"
            % expected
        )

    try:
        root_metadata = os.lstat(root)
    except FileNotFoundError:
        raise ValueError("V6 repository root is missing: %s" % root) from None
    if stat.S_ISLNK(root_metadata.st_mode) or not stat.S_ISDIR(
        root_metadata.st_mode
    ):
        raise ValueError("V6 repository root must be a non-symlink directory")
    current = root
    parts = os.path.relpath(expected, root).split(os.sep)
    for index, component in enumerate(parts):
        current = os.path.join(current, component)
        try:
            metadata = os.lstat(current)
        except FileNotFoundError:
            break
        if stat.S_ISLNK(metadata.st_mode):
            raise ValueError(
                "V6 analysis output must not traverse a symlink: %s" % current
            )
        if not stat.S_ISDIR(metadata.st_mode):
            kind = "directory" if index == len(parts) - 1 else "ancestor"
            raise ValueError(
                "V6 analysis output %s is not a directory: %s"
                % (kind, current)
            )
    return expected


def _expected_artifact_paths(input_valid: bool) -> tuple[str, ...]:
    if not input_valid:
        return ()
    return tuple(
        ["tables/%s" % name for name in V6_TABLE_NAMES]
        + [
            "figures/%s.%s" % (stem, extension)
            for stem in V6_FIGURE_STEMS
            for extension in ("pdf", "png")
        ]
    )


def _expected_directories(paths) -> set[str]:
    directories: set[str] = set()
    for relative in paths:
        parent = os.path.dirname(relative)
        while parent:
            directories.add(parent)
            parent = os.path.dirname(parent)
    return directories


def _verify_exact_artifact_tree(root: str, expected_paths) -> dict[str, str]:
    """Require exactly the staged/published files and directories."""
    expected_files = set(expected_paths)
    expected_directories = _expected_directories(expected_files)
    actual_files: set[str] = set()
    actual_directories: set[str] = set()
    if os.path.isdir(root):
        for directory, names, files in os.walk(root):
            relative_directory = os.path.relpath(directory, root)
            if relative_directory != ".":
                actual_directories.add(relative_directory)
            for name in names:
                candidate = os.path.join(directory, name)
                relative = os.path.relpath(candidate, root)
                if os.path.islink(candidate):
                    actual_directories.add(relative)
            for name in files:
                candidate = os.path.join(directory, name)
                relative = os.path.relpath(candidate, root)
                if os.path.islink(candidate) or not os.path.isfile(candidate):
                    raise RuntimeError(
                        "V6 analysis artifact is not a regular file: %s" % relative
                    )
                actual_files.add(relative)
    if actual_files != expected_files or actual_directories != expected_directories:
        raise RuntimeError(
            "V6 analysis staged artifact set is not exact: %s"
            % json.dumps(
                {
                    "missing_files": sorted(expected_files - actual_files),
                    "unexpected_files": sorted(actual_files - expected_files),
                    "missing_directories": sorted(
                        expected_directories - actual_directories
                    ),
                    "unexpected_directories": sorted(
                        actual_directories - expected_directories
                    ),
                },
                sort_keys=True,
            )
        )
    return {
        relative: _file_sha256(
            os.path.join(root, relative), root=root
        )
        for relative in sorted(expected_files)
    }


def _write_staged_summary(path: str, summary) -> None:
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2, allow_nan=False)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def _fsync_regular_file(path: str) -> None:
    descriptor = open_regular_read_descriptor(
        path, label="staged V6 analysis artifact"
    )
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _set_read_only_regular(path: str) -> None:
    descriptor = open_regular_read_descriptor(
        path, label="staged V6 analysis artifact"
    )
    try:
        os.fchmod(descriptor, V6_PUBLISHED_FILE_MODE)
        observed = stat.S_IMODE(os.fstat(descriptor).st_mode)
        if observed != V6_PUBLISHED_FILE_MODE:
            raise RuntimeError(
                "failed to make V6 analysis artifact read-only: %s" % path
            )
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _require_read_only_regular(path: str, *, root: str | None = None) -> None:
    descriptor = open_regular_read_descriptor(
        path, root=root, label="published V6 analysis artifact"
    )
    try:
        observed = stat.S_IMODE(os.fstat(descriptor).st_mode)
    finally:
        os.close(descriptor)
    if observed != V6_PUBLISHED_FILE_MODE:
        raise RuntimeError(
            "published V6 analysis artifact is not read-only: %s" % path
        )


def _analysis_lock_path(out_dir: str) -> str:
    parent = os.path.dirname(out_dir) or os.curdir
    return os.path.join(parent, ".%s.publication.lock" % os.path.basename(out_dir))


def _inspect_existing_tree(root: str, allowed_files) -> tuple[set[str], set[str]]:
    """Return an allowed partial tree; reject extras and every symlink."""
    allowed = set(allowed_files)
    allowed_directories = _expected_directories(allowed)
    files: set[str] = set()
    directories: set[str] = set()
    if not os.path.lexists(root):
        return files, directories
    require_directory_nonsymlink(root, label="V6 analysis output directory")
    for directory, names, filenames in os.walk(root, followlinks=False):
        relative_directory = os.path.relpath(directory, root)
        if relative_directory != ".":
            directories.add(relative_directory)
        for name in names:
            candidate = os.path.join(directory, name)
            relative = os.path.relpath(candidate, root)
            if os.path.islink(candidate):
                raise RuntimeError(
                    "V6 analysis output contains a symlink: %s" % relative
                )
        for name in filenames:
            candidate = os.path.join(directory, name)
            relative = os.path.relpath(candidate, root)
            require_regular_nonsymlink(
                candidate, label="V6 analysis artifact %s" % relative
            )
            files.add(relative)
    unexpected_files = files - allowed
    unexpected_directories = directories - allowed_directories
    if unexpected_files or unexpected_directories:
        raise RuntimeError(
            "V6 analysis output contains unregistered artifacts: %s"
            % json.dumps(
                {
                    "unexpected_files": sorted(unexpected_files),
                    "unexpected_directories": sorted(unexpected_directories),
                },
                sort_keys=True,
            )
        )
    return files, directories


def _link_create_once(source: str, target: str) -> None:
    """Publish one regular file atomically without an overwrite operation."""
    require_regular_nonsymlink(source, label="staged V6 analysis artifact")
    _require_read_only_regular(source)
    parent = os.path.dirname(target) or os.curdir
    os.makedirs(parent, exist_ok=True)
    require_directory_nonsymlink(parent, label="V6 analysis artifact directory")
    try:
        os.link(source, target, follow_symlinks=False)
    except FileExistsError:
        return
    _require_read_only_regular(target, root=parent)
    fsync_directory_best_effort(parent)


def _publish_staged_analysis(
    staged_root: str,
    out_dir: str,
    expected_artifacts,
    expected_hashes,
    expected_summary_sha256: str,
    backup_dir: str | None = None,
) -> str:
    """Create or recover one exact artifact tree; never replace prior output."""
    del backup_dir  # retained only for compatibility with older internal callers
    summary_source = os.path.join(staged_root, V6_SUMMARY_NAME)
    require_directory_nonsymlink(staged_root, label="staged V6 analysis root")
    if not os.path.isfile(summary_source) or os.path.islink(summary_source):
        raise RuntimeError("staged V6 analysis summary is missing")
    staged_hashes = _verify_exact_artifact_tree(
        staged_root, (*expected_artifacts, V6_SUMMARY_NAME)
    )
    if {
        relative: digest
        for relative, digest in staged_hashes.items()
        if relative != V6_SUMMARY_NAME
    } != dict(expected_hashes):
        raise RuntimeError("staged V6 analysis artifacts changed after staging")
    if staged_hashes[V6_SUMMARY_NAME] != expected_summary_sha256:
        raise RuntimeError("staged V6 analysis summary changed before publication")
    for relative in (*expected_artifacts, V6_SUMMARY_NAME):
        staged_path = os.path.join(staged_root, relative)
        _set_read_only_regular(staged_path)
        _fsync_regular_file(staged_path)
    for relative_directory in sorted(_expected_directories(expected_artifacts)):
        fsync_directory_best_effort(os.path.join(staged_root, relative_directory))
    fsync_directory_best_effort(staged_root)

    absolute_out_dir = os.path.abspath(out_dir)
    lock_path = _analysis_lock_path(absolute_out_dir)
    summary_target = os.path.join(absolute_out_dir, V6_SUMMARY_NAME)
    allowed_files = (*expected_artifacts, V6_SUMMARY_NAME)
    with ExclusiveFileLock(
        lock_path,
        label="V6 analysis publication",
        metadata={"out_dir": absolute_out_dir},
    ):
        if not os.path.lexists(absolute_out_dir):
            os.mkdir(absolute_out_dir)
            fsync_directory_best_effort(os.path.dirname(absolute_out_dir) or os.curdir)
        existing_files, existing_directories = _inspect_existing_tree(
            absolute_out_dir, allowed_files
        )

        # A summary is the completion marker.  Once it exists, deletion of a
        # sibling is corruption, not an interrupted publication, and a retry
        # must never reconstruct the missing evidence around that marker.
        if V6_SUMMARY_NAME in existing_files:
            required_files = set(allowed_files)
            required_directories = _expected_directories(required_files)
            if (
                existing_files != required_files
                or existing_directories != required_directories
            ):
                raise RuntimeError(
                    "completed V6 analysis output tree is not exact; refusing recovery"
                )

        for relative in sorted(existing_files):
            expected = staged_hashes[relative]
            existing_path = os.path.join(absolute_out_dir, relative)
            _require_read_only_regular(existing_path, root=absolute_out_dir)
            observed = _file_sha256(
                existing_path, root=absolute_out_dir
            )
            if observed != expected:
                raise RuntimeError(
                    "conflicting existing V6 analysis artifact: %s" % relative
                )

        # Siblings are create-once.  An interrupted attempt can safely resume
        # because matching siblings remain and missing siblings are hard-linked.
        for relative in sorted(expected_artifacts):
            target = os.path.join(absolute_out_dir, relative)
            if relative not in existing_files:
                _link_create_once(os.path.join(staged_root, relative), target)
            _require_read_only_regular(target, root=absolute_out_dir)
            if _file_sha256(
                target, root=absolute_out_dir
            ) != staged_hashes[relative]:
                raise RuntimeError(
                    "conflicting concurrent V6 analysis artifact: %s" % relative
                )

        # The completion summary is always the last create-once publication.
        if V6_SUMMARY_NAME not in existing_files:
            _link_create_once(summary_source, summary_target)
        _require_read_only_regular(summary_target, root=absolute_out_dir)
        if _file_sha256(
            summary_target, root=absolute_out_dir
        ) != expected_summary_sha256:
            raise RuntimeError("conflicting existing V6 analysis summary")
        _verify_exact_artifact_tree(absolute_out_dir, allowed_files)
        for relative in allowed_files:
            _require_read_only_regular(
                os.path.join(absolute_out_dir, relative),
                root=absolute_out_dir,
            )
        fsync_directory_best_effort(absolute_out_dir)
    return summary_target


def _style() -> None:
    plt.rcParams.update(
        {
            "font.family": "serif",
            "font.serif": ["Times New Roman", "DejaVu Serif"],
            "font.size": 9,
            "axes.titlesize": 10,
            "axes.titleweight": "bold",
            "axes.labelsize": 9,
            "legend.fontsize": 7.5,
            "legend.frameon": False,
            "figure.dpi": 150,
            "savefig.dpi": 300,
            "savefig.bbox": "tight",
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": True,
            "grid.alpha": 0.15,
            "lines.linewidth": 1.7,
            "lines.markersize": 4,
        }
    )


def _save(fig, directory: str, stem: str) -> None:
    os.makedirs(directory, exist_ok=True)
    fig.savefig(
        os.path.join(directory, stem + ".pdf"),
        metadata={
            "Creator": "LatentTarget controlled V6",
            "CreationDate": None,
            "ModDate": None,
        },
    )
    fig.savefig(
        os.path.join(directory, stem + ".png"),
        dpi=300,
        metadata={"Software": "LatentTarget controlled V6"},
    )
    plt.close(fig)


def _condition_rows(records, condition):
    return [row for row in records if row["condition"] == condition]


def _round_block_ci(rows, metric, n_boot: int, seed: int):
    """Bootstrap rounds over episode/scenario-seed blocks, never raw rows."""
    by_round_block = defaultdict(lambda: defaultdict(list))
    for row in rows:
        value = metric(row)
        if value is not None:
            by_round_block[int(row["round"])][int(row["episode_index"])].append(
                float(value)
            )
    generator = np.random.default_rng(seed)
    output = []
    for round_index, by_block in sorted(by_round_block.items()):
        values = np.asarray(
            [np.mean(by_block[key]) for key in sorted(by_block)], dtype=float
        )
        boot = generator.choice(
            values, size=(n_boot, len(values)), replace=True
        ).mean(axis=1)
        low, high = np.quantile(boot, [0.025, 0.975])
        output.append(
            (round_index, float(values.mean()), float(low), float(high), len(values))
        )
    return output


def _line(
    ax, values, condition, label=None, color=None, marker=None, linestyle=None
):
    x = np.asarray([row[0] for row in values])
    mean = np.asarray([row[1] for row in values])
    low = np.asarray([row[2] for row in values])
    high = np.asarray([row[3] for row in values])
    color = color or COLORS[condition]
    ax.plot(
        x,
        mean,
        label=label or LABELS[condition],
        color=color,
        marker=marker or MARKERS.get(condition, "o"),
        linestyle=linestyle or LINESTYLES.get(condition, "-"),
        markevery=2,
    )
    ax.fill_between(x, low, high, color=color, alpha=0.10, linewidth=0)


def make_figures(records, summary, figure_dir: str, n_boot: int, seed: int) -> None:
    """Emit the complete preregistered V6 figure set regardless of outcome."""
    figure_contract = CONTROLLED_V6_ANALYSIS_CONFIG["figure_bootstrap"]
    if (
        type(n_boot) is not int
        or type(seed) is not int
        or n_boot != figure_contract["n_boot"]
        or seed != figure_contract["seed"]
    ):
        raise ValueError("V6 figure bootstrap settings differ from the frozen contract")
    stable_conditions = (
        "full_history",
        "no_history",
        "shuffled_history",
        "random_target",
    )
    for field, ylabel, title, stem in (
        (
            "strategy_match",
            "Target-matched candidate rate",
            "Target-specific candidate selection",
            "fig_v6_match_by_round",
        ),
        (
            "target_success",
            "Option A choice rate",
            "Instrumental success",
            "fig_v6_success_by_round",
        ),
    ):
        fig, ax = plt.subplots(figsize=(5.5, 3.1))
        for index, condition in enumerate(stable_conditions):
            values = _round_block_ci(
                _condition_rows(records, condition),
                lambda row, field=field: row[field],
                n_boot,
                seed + index,
            )
            _line(ax, values, condition)
        if field == "strategy_match":
            ax.axhline(1.0 / 3.0, color="#333333", linestyle="--", linewidth=1)
        ax.axvline(18.5, color="#666666", linestyle=":", linewidth=1)
        ax.text(18.65, 0.98, "held-out wording", va="top", fontsize=7)
        ax.set(
            xlabel="Interaction round",
            ylabel=ylabel,
            ylim=(-0.02, 1.02),
            title=title,
        )
        ax.legend(ncol=2, loc="lower right")
        _save(fig, figure_dir, stem)

    swap_rows = _condition_rows(records, "swap")
    new_values = _round_block_ci(
        swap_rows,
        lambda row: row["selected_frame"] == row["final_target_type"],
        n_boot,
        seed + 20,
    )
    old_values = _round_block_ci(
        swap_rows,
        lambda row: row["selected_frame"] == row["initial_target_type"],
        n_boot,
        seed + 21,
    )
    fig, ax = plt.subplots(figsize=(5.5, 3.1))
    _line(
        ax,
        old_values,
        "full_history",
        label="Matches old target",
        color=COLORS["old"],
        marker="s",
        linestyle="--",
    )
    _line(
        ax,
        new_values,
        "full_history",
        label="Matches new target",
        color=COLORS["new"],
        marker="o",
        linestyle="-",
    )
    ax.axvline(12.5, color="#222222", linestyle="--", linewidth=1, label="Silent swap")
    ax.axvline(18.5, color="#666666", linestyle=":", linewidth=1)
    ax.axhline(1.0 / 3.0, color="#999999", linestyle="--", linewidth=0.8)
    ax.set(
        xlabel="Interaction round",
        ylabel="Candidate-match rate",
        ylim=(-0.02, 1.02),
        title="Strategy revision after a silent target change",
    )
    ax.legend(ncol=2, loc="upper center")
    _save(fig, figure_dir, "fig_v6_swap_adaptation")

    means = [
        summary["stable_condition_metrics"][name]["late_heldout_match"]["mean"]
        for name in stable_conditions
    ]
    lows = [
        summary["stable_condition_metrics"][name]["late_heldout_match"]["ci_lo"]
        for name in stable_conditions
    ]
    highs = [
        summary["stable_condition_metrics"][name]["late_heldout_match"]["ci_hi"]
        for name in stable_conditions
    ]
    x = np.arange(len(stable_conditions))
    fig, ax = plt.subplots(figsize=(5.5, 3.1))
    ax.bar(
        x,
        means,
        color=[COLORS[name] for name in stable_conditions],
        width=0.65,
        edgecolor="white",
    )
    ax.errorbar(
        x,
        means,
        yerr=[
            np.asarray(means) - np.asarray(lows),
            np.asarray(highs) - np.asarray(means),
        ],
        fmt="none",
        ecolor="#222222",
        capsize=3,
        linewidth=1,
    )
    ax.axhline(1.0 / 3.0, color="#333333", linestyle="--", linewidth=1)
    ax.set_xticks(
        x,
        [LABELS[name] for name in stable_conditions],
        rotation=12,
        ha="right",
    )
    ax.set(
        ylabel="Rounds 19–24 match rate",
        ylim=(0, 1),
        title="Held-out comparison across controls",
    )
    _save(fig, figure_dir, "fig_v6_control_comparison")

    full_rows = [
        row
        for row in _condition_rows(records, "full_history")
        if int(row["round"]) >= 19
    ]
    matrix = np.zeros((3, 3), dtype=float)
    for target_index, target in enumerate(STRATEGIES):
        target_rows = [
            row for row in full_rows if row["hidden_target_type"] == target
        ]
        for frame_index, frame in enumerate(STRATEGIES):
            matrix[target_index, frame_index] = np.mean(
                [row["selected_frame"] == frame for row in target_rows]
            )
    fig, ax = plt.subplots(figsize=(3.6, 3.1))
    image = ax.imshow(matrix, vmin=0, vmax=1, cmap="Blues")
    for row_index in range(3):
        for column_index in range(3):
            ax.text(
                column_index,
                row_index,
                "%.2f" % matrix[row_index, column_index],
                ha="center",
                va="center",
                color=(
                    "white"
                    if matrix[row_index, column_index] > 0.55
                    else "#222222"
                ),
                fontsize=8,
            )
    ax.set_xticks(
        range(3),
        [value.title() for value in STRATEGIES],
        rotation=20,
        ha="right",
    )
    ax.set_yticks(range(3), [value.title() for value in STRATEGIES])
    ax.set(
        xlabel="Selected frame",
        ylabel="Active target type",
        title="Full-history held-out choices",
    )
    fig.colorbar(image, ax=ax, shrink=0.75, label="Selection probability")
    _save(fig, figure_dir, "fig_v6_strategy_by_target")

    transitions = summary["swap_metrics"]["transition_metrics"]
    names = sorted(transitions)
    transition_means = [
        transitions[name]["adjusted_revision_shift"]["mean"] for name in names
    ]
    transition_lows = [
        transitions[name]["adjusted_revision_shift"]["ci_lo"] for name in names
    ]
    transition_highs = [
        transitions[name]["adjusted_revision_shift"]["ci_hi"] for name in names
    ]
    y = np.arange(len(names))
    fig, ax = plt.subplots(figsize=(5.4, 3.2))
    ax.errorbar(
        transition_means,
        y,
        xerr=[
            np.asarray(transition_means) - np.asarray(transition_lows),
            np.asarray(transition_highs) - np.asarray(transition_means),
        ],
        fmt="o",
        color="#0072B2",
        ecolor="#555555",
        capsize=3,
    )
    ax.axvline(0.0, color="#222222", linewidth=1)
    ax.axvline(
        summary["thresholds"]["minimum_transition_revision_shift"],
        color="#D55E00",
        linestyle="--",
        linewidth=1,
    )
    ax.set_yticks(y, [name.replace("_to_", " → ").title() for name in names])
    ax.set(
        xlabel="Swap-minus-stable adjusted revision",
        title="All six ordered target transitions",
    )
    _save(fig, figure_dir, "fig_v6_transition_revision")


def write_tables(summary, table_dir: str) -> None:
    """Emit all V6 condition-, episode-, and transition-level diagnostics."""
    os.makedirs(table_dir, exist_ok=True)
    with open(
        os.path.join(table_dir, "v6_stable_conditions.csv"),
        "w",
        newline="",
        encoding="utf-8",
    ) as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(
            [
                "condition",
                "n_episodes",
                "n_blocks",
                "early_match",
                "development_match",
                "heldout_match",
                "learning_gain",
                "success",
            ]
        )
        for condition, metric in summary["stable_condition_metrics"].items():
            writer.writerow(
                [
                    condition,
                    metric["n_episodes"],
                    metric["n_blocks"],
                    metric["early_match"]["mean"],
                    metric["late_development_match"]["mean"],
                    metric["late_heldout_match"]["mean"],
                    metric["learning_gain"]["mean"],
                    metric["success"]["mean"],
                ]
            )
    with open(
        os.path.join(table_dir, "v6_swap_episodes.csv"),
        "w",
        newline="",
        encoding="utf-8",
    ) as handle:
        rows = summary["swap_episode_summaries"]
        writer = csv.DictWriter(
            handle,
            fieldnames=list(rows[0]) if rows else ["episode_id"],
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)
    with open(
        os.path.join(table_dir, "v6_transition_revision.csv"),
        "w",
        newline="",
        encoding="utf-8",
    ) as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(
            [
                "transition",
                "old_type",
                "new_type",
                "mean",
                "ci_lo",
                "ci_hi",
                "adjusted_new_gain",
                "adjusted_old_drop",
            ]
        )
        for name, metric in sorted(
            summary["swap_metrics"]["transition_metrics"].items()
        ):
            revision = metric["adjusted_revision_shift"]
            writer.writerow(
                [
                    name,
                    metric["old_type"],
                    metric["new_type"],
                    revision["mean"],
                    revision["ci_lo"],
                    revision["ci_hi"],
                    metric["adjusted_new_target_gain"]["mean"],
                    metric["adjusted_old_target_drop"]["mean"],
                ]
            )


def _load_json_object(
    path: str,
    label: str,
    *,
    root: str | None = None,
) -> dict[str, Any]:
    descriptor = open_regular_read_descriptor(path, root=root, label=label)
    with os.fdopen(descriptor, "r", encoding="utf-8") as handle:
        payload = strict_json_load(handle)
    if type(payload) is not dict:
        raise ValueError("%s must be a JSON object" % label)
    return payload


def _input_fingerprint(path: str, *, root: str) -> dict[str, Any]:
    absolute = os.path.abspath(path)
    result: dict[str, Any] = {"path": absolute, "file_sha256": None}
    try:
        result["file_sha256"] = _file_sha256(absolute, root=root)
    except (FileNotFoundError, OSError, TypeError, ValueError):
        pass
    return result


def _invalid_input_summary(
    *,
    error: BaseException,
    args: argparse.Namespace,
    manifest_path: str,
) -> dict[str, Any]:
    requested = {
        "n_boot": args.n_boot,
        "n_perm": args.n_perm,
        "seed": args.seed,
    }
    frozen = {
        key: CONTROLLED_V6_ANALYSIS_CONFIG[key]
        for key in ("n_boot", "n_perm", "seed")
    }
    return {
        "task_version": CONTROLLED_V6_VERSION,
        "status": "invalid V6 confirmatory input",
        "decision": "V6_CONFIRMATORY_INPUT_INVALID",
        "input_valid": False,
        "pattern_pass": False,
        "scientific_pass": False,
        "effect_gates": {},
        "inference_gates": {},
        "analysis_execution": {
            **requested,
            "matches_frozen_parameters": requested == frozen,
            "canonical_out_dir": CONTROLLED_V6_ANALYSIS_CONFIG[
                "canonical_out_dir"
            ],
            "figure_bootstrap": CONTROLLED_V6_ANALYSIS_CONFIG[
                "figure_bootstrap"
            ],
        },
        "invalid_input": {
            "error_type": type(error).__name__,
            "message": str(error)[:1000],
            "inputs": {
                "log": _input_fingerprint(args.log, root=_bootstrap.ROOT),
                "manifest": _input_fingerprint(
                    manifest_path, root=_bootstrap.ROOT
                ),
                "checkpoint_spec": _input_fingerprint(
                    args.checkpoint_spec, root=_bootstrap.ROOT
                ),
            },
        },
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log", required=True)
    parser.add_argument("--manifest", default=None)
    parser.add_argument(
        "--checkpoint-spec",
        required=True,
        help="frozen pre-outcome V6 checkpoint used to verify provenance",
    )
    parser.add_argument("--out-dir", required=True)
    parser.add_argument(
        "--n-boot", type=int, default=CONTROLLED_V6_ANALYSIS_CONFIG["n_boot"]
    )
    parser.add_argument(
        "--n-perm", type=int, default=CONTROLLED_V6_ANALYSIS_CONFIG["n_perm"]
    )
    parser.add_argument(
        "--seed", type=int, default=CONTROLLED_V6_ANALYSIS_CONFIG["seed"]
    )
    args = parser.parse_args(argv)

    manifest_path = args.manifest or args.log.replace(".jsonl", ".manifest.json")
    try:
        absolute_out_dir = _require_canonical_output_path(
            args.out_dir, _bootstrap.ROOT
        )
    except (OSError, TypeError, ValueError) as exc:
        print(
            "V6 analysis output path is invalid: %s" % exc,
            file=sys.stderr,
        )
        return 2

    records: list[dict[str, Any]] = []
    frozen_values = {
        key: CONTROLLED_V6_ANALYSIS_CONFIG[key]
        for key in ("n_boot", "n_perm", "seed")
    }
    requested_values = {
        "n_boot": args.n_boot,
        "n_perm": args.n_perm,
        "seed": args.seed,
    }
    try:
        if requested_values != frozen_values or any(
            type(requested_values[key]) is not int for key in requested_values
        ):
            raise ValueError(
                "V6 analysis CLI parameters differ from the frozen contract: "
                "expected %r, got %r" % (frozen_values, requested_values)
            )
        records = list(read_jsonl(args.log, root=_bootstrap.ROOT))
        if not records:
            raise ValueError("V6 checkpoint log is empty")
        if any(type(row) is not dict for row in records):
            raise ValueError("V6 checkpoint log must contain only JSON objects")
        manifest = _load_json_object(
            manifest_path, "V6 manifest", root=_bootstrap.ROOT
        )
        frozen_spec = _load_json_object(
            args.checkpoint_spec,
            "V6 final checkpoint",
            root=_bootstrap.ROOT,
        )
        summary = evaluate_controlled_v6_checkpoint(
            records,
            manifest,
            n_boot=args.n_boot,
            n_perm=args.n_perm,
            seed=args.seed,
            frozen_spec=frozen_spec,
            checkpoint_root=_bootstrap.ROOT,
            checkpoint_file_sha256=_file_sha256(
                args.checkpoint_spec, root=_bootstrap.ROOT
            ),
            log_path=args.log,
            log_file_sha256=_file_sha256(
                args.log, root=_bootstrap.ROOT
            ),
        )
    except Exception as exc:
        summary = _invalid_input_summary(
            error=exc, args=args, manifest_path=manifest_path
        )

    input_valid = summary.get("input_valid") is True
    expected_artifacts = _expected_artifact_paths(input_valid)
    summary["artifacts"] = {
        "summary": V6_SUMMARY_NAME,
        "tables": (
            ["tables/%s" % name for name in V6_TABLE_NAMES]
            if input_valid
            else []
        ),
        "figures": (
            [
                "figures/%s.%s" % (stem, extension)
                for stem in V6_FIGURE_STEMS
                for extension in ("pdf", "png")
            ]
            if input_valid
            else []
        ),
    }
    output_parent = os.path.dirname(absolute_out_dir) or "."
    os.makedirs(output_parent, exist_ok=True)
    try:
        _require_canonical_output_path(absolute_out_dir, _bootstrap.ROOT)
    except (OSError, TypeError, ValueError) as exc:
        print("V6 analysis output path is invalid: %s" % exc, file=sys.stderr)
        return 2
    transaction_root = tempfile.mkdtemp(
        prefix=".%s.v6-analysis-" % os.path.basename(absolute_out_dir),
        dir=output_parent,
    )
    staged_root = os.path.join(transaction_root, "new")
    os.makedirs(staged_root)
    try:
        if input_valid:
            write_tables(summary, os.path.join(staged_root, "tables"))
            _style()
            make_figures(
                records,
                summary,
                os.path.join(staged_root, "figures"),
                CONTROLLED_V6_ANALYSIS_CONFIG["figure_bootstrap"]["n_boot"],
                CONTROLLED_V6_ANALYSIS_CONFIG["figure_bootstrap"]["seed"],
            )
        artifact_hashes = _verify_exact_artifact_tree(
            staged_root, expected_artifacts
        )
        summary["artifacts"]["sha256"] = artifact_hashes
        staged_summary = os.path.join(staged_root, V6_SUMMARY_NAME)
        _write_staged_summary(staged_summary, summary)
        staged_summary_sha256 = _file_sha256(staged_summary)
        _verify_exact_artifact_tree(
            staged_root, (*expected_artifacts, V6_SUMMARY_NAME)
        )
        summary_path = _publish_staged_analysis(
            staged_root,
            absolute_out_dir,
            expected_artifacts,
            artifact_hashes,
            staged_summary_sha256,
        )
    except (OSError, TypeError, ValueError, RuntimeError) as exc:
        print("V6 analysis publication failed: %s" % exc, file=sys.stderr)
        return 2
    finally:
        shutil.rmtree(transaction_root, ignore_errors=True)

    print(summary["status"])
    print(summary["decision"])
    for section in ("effect_gates", "inference_gates"):
        for name, passed in summary.get(section, {}).items():
            print("  %-46s %s" % (name, "PASS" if passed else "FAIL"))
    print("wrote %s" % summary_path)
    return 0 if input_valid else 2


if __name__ == "__main__":
    sys.exit(main())
