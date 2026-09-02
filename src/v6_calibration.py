"""Target-free whole-triad calibration and final V6 bank selection."""

from __future__ import annotations

import hashlib
import itertools
import json
import os
import re
import stat
import tempfile
import time
from collections import Counter, defaultdict
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

import numpy as np

from config import (
    CONTROLLED_V6_CALIBRATION_THRESHOLDS,
    CONTROLLED_V6_VERSION,
    STRATEGIES,
)
from .controlled_focal_agent import build_controlled_prompt, parse_controlled_choice
from .controlled_messages import MessageCandidate, candidate_for_slot
from .controlled_v6_messages import V6TriadBank, audit_v6_bank_payload
from .focal_agent import BaseProvider, ProviderError
from .file_lock import (
    ExclusiveFileLock,
    require_contained_path,
    require_directory_nonsymlink,
    require_regular_nonsymlink,
)
from .logging_utils import write_manifest
from .scenarios import (
    V6_CALIBRATION_SCENARIOS,
    V6_VALIDATION_SCENARIOS,
)
from .seeding import derive_seed


V6_CALIBRATION_VERSION = "v6-triad-calibration-1.0"
V6_POOL_MODE = "pool_screening"
V6_VALIDATION_MODE = "selected_bank_validation"
V6_CALIBRATION_FOLDS: Tuple[Tuple[str, str], ...] = tuple(
    (
        V6_CALIBRATION_SCENARIOS[index].id,
        V6_CALIBRATION_SCENARIOS[index + 1].id,
    )
    for index in range(0, len(V6_CALIBRATION_SCENARIOS), 2)
)
V6_VALIDATION_FOLDS: Tuple[Tuple[str, str], ...] = tuple(
    (
        V6_VALIDATION_SCENARIOS[index].id,
        V6_VALIDATION_SCENARIOS[index + 1].id,
    )
    for index in range(0, len(V6_VALIDATION_SCENARIOS), 2)
)
_V6_IMMUTABLE_SCHEDULE_FIELDS: Tuple[str, ...] = (
    "calibration_version",
    "pool_sha256",
    "split",
    "triad_id",
    "triad_index",
    "scenario_index",
    "permutation_index",
    "frame_order",
    "episode_index",
    "round",
    "n_rounds",
    "heldout_start_round",
    "scenario",
    "candidates",
    "generation_seed",
)
_V6_SAMPLE_ARTIFACT_VERSION = "v6-calibration-sample-1.0"
_V6_SAMPLE_ARTIFACT_PATTERN = re.compile(r"^(\d{8})\.json$")
_V6_INFLIGHT_CLAIM_VERSION = "v6-calibration-inflight-1.0"


def canonical_sha256(payload: Any) -> str:
    canonical = json.dumps(
        payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def file_sha256(path: str) -> str:
    digest = hashlib.sha256()
    require_regular_nonsymlink(path, label="SHA-256 input")
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags)
    if not stat.S_ISREG(os.fstat(descriptor).st_mode):
        os.close(descriptor)
        raise ValueError("SHA-256 input is not a regular file: %s" % path)
    with os.fdopen(descriptor, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def bank_content_sha256(payload: Mapping[str, Any]) -> str:
    return canonical_sha256(payload.get("splits", {}))


def _json_exact(left: Any, right: Any) -> bool:
    try:
        return json.dumps(
            left,
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        ) == json.dumps(
            right,
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError):
        return False


def _fsync_directory(path: str) -> None:
    """Best-effort directory sync after an atomic publication."""
    parent = os.path.dirname(os.path.abspath(path)) or os.curdir
    descriptor: Optional[int] = None
    try:
        descriptor = os.open(parent, os.O_RDONLY)
        os.fsync(descriptor)
    except OSError:
        # Some filesystems do not permit fsync on directories. The data file
        # itself is still fsynced before publication.
        pass
    finally:
        if descriptor is not None:
            os.close(descriptor)


def _path_exists(path: str) -> bool:
    """Existence check that does not hide a broken symlink."""
    return os.path.lexists(path)


def _require_safe_parent(path: str, label: str) -> str:
    parent = os.path.dirname(os.path.abspath(path)) or os.curdir
    require_directory_nonsymlink(parent, label=label + " parent")
    return parent


def _open_regular_read(path: str, label: str, *, binary: bool = False):
    """Open one already-validated artifact without following a final symlink."""
    require_regular_nonsymlink(path, label=label)
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags)
    if not stat.S_ISREG(os.fstat(descriptor).st_mode):
        os.close(descriptor)
        raise ValueError("%s is not a regular file" % label)
    if binary:
        return os.fdopen(descriptor, "rb")
    return os.fdopen(descriptor, "r", encoding="utf-8")


def _ensure_nonsymlink_directory(path: str, label: str) -> None:
    """Create a directory if absent, then reject links and special files."""
    if _path_exists(path):
        require_directory_nonsymlink(path, label=label)
        return
    parent = os.path.dirname(os.path.abspath(path)) or os.curdir
    require_directory_nonsymlink(parent, label=label + " parent")
    os.mkdir(path)
    require_directory_nonsymlink(path, label=label)
    _fsync_directory(os.path.join(path, ".directory-entry"))


def _atomic_write_json(path: str, payload: Mapping[str, Any]) -> None:
    """Durably replace one JSON artifact without exposing a partial file."""
    parent = os.path.dirname(path)
    if parent:
        _ensure_nonsymlink_directory(parent, "JSON artifact directory")
    require_regular_nonsymlink(
        path, label="JSON artifact", allow_missing=True
    )
    descriptor, temporary = tempfile.mkstemp(
        prefix=".%s.tmp." % os.path.basename(path), dir=parent or os.curdir
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(
                payload,
                handle,
                indent=2,
                ensure_ascii=False,
                allow_nan=False,
            )
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        require_regular_nonsymlink(
            path, label="JSON artifact", allow_missing=True
        )
        os.replace(temporary, path)
        _fsync_directory(path)
    finally:
        if _path_exists(temporary):
            os.unlink(temporary)


def _atomic_create_json(path: str, payload: Mapping[str, Any]) -> None:
    """Publish an immutable JSON artifact, refusing a non-identical reuse."""
    if _path_exists(path):
        with _open_regular_read(path, "immutable JSON artifact") as handle:
            existing = json.load(handle)
        if not _json_exact(existing, payload):
            raise ValueError("existing V6 sample artifact differs from frozen sample")
        return
    parent = os.path.dirname(path)
    if parent:
        _ensure_nonsymlink_directory(parent, "immutable JSON artifact directory")
    descriptor, temporary = tempfile.mkstemp(
        prefix=".%s.tmp." % os.path.basename(path), dir=parent or os.curdir
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(
                payload,
                handle,
                indent=2,
                ensure_ascii=False,
                allow_nan=False,
            )
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temporary, path)
        except FileExistsError:
            with _open_regular_read(path, "immutable JSON artifact") as handle:
                existing = json.load(handle)
            if not _json_exact(existing, payload):
                raise ValueError(
                    "concurrent V6 sample artifact differs from frozen sample"
                )
        _fsync_directory(path)
    finally:
        if _path_exists(temporary):
            os.unlink(temporary)


def _atomic_write_manifest(path: str, payload: Mapping[str, Any]) -> Dict[str, Any]:
    """Use the project manifest enricher, then atomically publish its result."""
    parent = os.path.dirname(path)
    if parent:
        _ensure_nonsymlink_directory(parent, "V6 manifest directory")
    require_regular_nonsymlink(
        path, label="V6 calibration manifest", allow_missing=True
    )
    descriptor, temporary = tempfile.mkstemp(
        prefix=".%s.tmp." % os.path.basename(path), dir=parent or os.curdir
    )
    os.close(descriptor)
    try:
        written = write_manifest(temporary, dict(payload))
        with _open_regular_read(temporary, "temporary V6 manifest", binary=True) as handle:
            os.fsync(handle.fileno())
        require_regular_nonsymlink(
            path, label="V6 calibration manifest", allow_missing=True
        )
        os.replace(temporary, path)
        _fsync_directory(path)
        return written
    finally:
        if _path_exists(temporary):
            os.unlink(temporary)


def _atomic_write_jsonl(path: str, records: Sequence[Mapping[str, Any]]) -> None:
    parent = os.path.dirname(path)
    if parent:
        _ensure_nonsymlink_directory(parent, "V6 raw-log directory")
    require_regular_nonsymlink(path, label="V6 raw log", allow_missing=True)
    descriptor, temporary = tempfile.mkstemp(
        prefix=".%s.tmp." % os.path.basename(path), dir=parent or os.curdir
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            for record in records:
                handle.write(
                    json.dumps(
                        record,
                        ensure_ascii=False,
                        separators=(",", ":"),
                        allow_nan=False,
                    )
                    + "\n"
                )
            handle.flush()
            os.fsync(handle.fileno())
        require_regular_nonsymlink(path, label="V6 raw log", allow_missing=True)
        os.replace(temporary, path)
        _fsync_directory(path)
    finally:
        if _path_exists(temporary):
            os.unlink(temporary)


def _append_jsonl_durable(path: str, record: Mapping[str, Any]) -> None:
    encoded = (
        json.dumps(
            record,
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")
    _require_safe_parent(path, "V6 raw log")
    require_regular_nonsymlink(path, label="V6 raw log", allow_missing=True)
    flags = os.O_WRONLY | os.O_APPEND | os.O_CREAT
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags, 0o600)
    try:
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            raise ValueError("V6 raw log is not a regular file")
        offset = 0
        while offset < len(encoded):
            offset += os.write(descriptor, encoded[offset:])
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _sample_sha256(record: Mapping[str, Any]) -> str:
    unhashed = {key: value for key, value in record.items() if key != "sample_sha256"}
    return canonical_sha256(unhashed)


def _sample_coordinate(row: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        "split": row["split"],
        "triad_id": row["triad_id"],
        "scenario_index": row["scenario_index"],
        "permutation_index": row["permutation_index"],
        "generation_seed": row["generation_seed"],
    }


def _sample_artifact(index: int, record: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        "artifact_version": _V6_SAMPLE_ARTIFACT_VERSION,
        "schedule_index": index,
        "coordinate": _sample_coordinate(record),
        "sample_sha256": record["sample_sha256"],
        "record": dict(record),
    }


def _inflight_claim(
    *,
    schedule_index: int,
    schedule_row: Mapping[str, Any],
    run_id: str,
    mode: str,
    provider_description: Mapping[str, Any],
) -> Dict[str, Any]:
    """Build the immutable pre-generation claim for one exact paid call."""
    payload: Dict[str, Any] = {
        "claim_version": _V6_INFLIGHT_CLAIM_VERSION,
        "run_id": run_id,
        "mode": mode,
        "schedule_index": schedule_index,
        "coordinate": _sample_coordinate(schedule_row),
        "schedule_row_sha256": canonical_sha256(schedule_row),
        "provider_sha256": canonical_sha256(provider_description),
    }
    payload["claim_sha256"] = canonical_sha256(payload)
    return payload


def _create_inflight_claim(path: str, payload: Mapping[str, Any]) -> None:
    """Durably claim a coordinate before generation; never reuse a claim."""
    if _path_exists(path):
        require_regular_nonsymlink(path, label="V6 in-flight claim")
        raise RuntimeError("V6 in-flight claim already exists")
    _atomic_create_json(path, payload)
    sealed = _load_json_mapping(path, "V6 in-flight claim")
    if not _json_exact(sealed, payload):
        raise RuntimeError("V6 in-flight claim was not durably sealed")


def _clear_inflight_claim_after_sample(
    *,
    claim_path: str,
    expected_claim: Mapping[str, Any],
    sample_path: str,
    expected_sample: Mapping[str, Any],
) -> None:
    """Clear a claim only after its exact response sample is durable."""
    claim = _load_json_mapping(claim_path, "V6 in-flight claim")
    if not _json_exact(claim, expected_claim):
        raise ValueError("V6 in-flight claim differs from the frozen coordinate")
    sample = _load_json_mapping(sample_path, "V6 claimed response sample")
    if not _json_exact(sample, expected_sample):
        raise ValueError("V6 in-flight claim has no exact durable response sample")
    require_regular_nonsymlink(claim_path, label="V6 in-flight claim")
    os.unlink(claim_path)
    _fsync_directory(claim_path)


def _triads(bank: V6TriadBank, split: Optional[str] = None):
    if split is None:
        for split_name in ("development", "heldout"):
            yield from bank.payload["splits"][split_name]
    else:
        yield from bank.payload["splits"][split]


def _candidate_rows_for_triad(
    triad: Mapping[str, Any], scenario: Any, permutation: Sequence[str], split: str
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for slot, frame in enumerate(permutation, start=1):
        entry = triad["candidates"][frame]
        text = " ".join(str(entry["template"]).format(a=scenario.option_a).split())
        rows.append(
            {
                "slot": slot,
                "triad_id": str(triad["triad_id"]),
                "pool_candidate_id": str(entry["candidate_id"]),
                "candidate_id": "%s-%s" % (entry["candidate_id"], scenario.id),
                "message": text,
                "frame": frame,
                "split": split,
            }
        )
    return rows


def _counterfactual_round_index(
    split: str, triad_index: int, scenario_index: int
) -> int:
    """Keep visible round metadata fixed across a block's six permutations."""
    if split == "development":
        return (scenario_index + triad_index) % 18 + 1
    if split == "heldout":
        return 19 + (scenario_index + triad_index) % 6
    raise ValueError("unknown V6 split %r" % split)


def build_v6_pool_schedule(
    bank: V6TriadBank, seed: int = 20262001
) -> List[Dict[str, Any]]:
    """Evaluate every triad on all scenarios and all six slot permutations."""
    permutations = list(itertools.permutations(STRATEGIES))
    rows: List[Dict[str, Any]] = []
    pool_hash = bank.sha256()
    global_index = 0
    for split in ("development", "heldout"):
        triads = list(_triads(bank, split))
        for triad_index, triad in enumerate(triads):
            for scenario_index, scenario in enumerate(V6_CALIBRATION_SCENARIOS):
                # Rotate which lexical permutation receives each permutation index
                # without changing the complete six-permutation set.
                offset = derive_seed(
                    "v6_pool_permutation_offset",
                    seed,
                    split,
                    triad["triad_id"],
                    scenario.id,
                ) % len(permutations)
                ordered = permutations[offset:] + permutations[:offset]
                for local_index, permutation in enumerate(ordered):
                    round_index = _counterfactual_round_index(
                        split, triad_index, scenario_index
                    )
                    rows.append(
                        {
                            "calibration_version": V6_CALIBRATION_VERSION,
                            "pool_sha256": pool_hash,
                            "split": split,
                            "triad_id": str(triad["triad_id"]),
                            "triad_index": triad_index,
                            "scenario_index": scenario_index,
                            "permutation_index": local_index,
                            "frame_order": list(permutation),
                            "episode_index": global_index // 24,
                            "round": round_index,
                            "n_rounds": 24,
                            "heldout_start_round": 19,
                            "scenario": scenario.as_dict(),
                            "candidates": _candidate_rows_for_triad(
                                triad, scenario, permutation, split
                            ),
                            "generation_seed": derive_seed(
                                V6_CALIBRATION_VERSION,
                                seed,
                                split,
                                triad["triad_id"],
                                scenario.id,
                                local_index,
                            ),
                        }
                    )
                    global_index += 1
    audit = audit_v6_pool_schedule(rows, bank)
    if not audit["pass"]:
        failed = sorted(name for name, passed in audit["checks"].items() if not passed)
        raise RuntimeError("generated V6 pool schedule failed: %s" % ", ".join(failed))
    return rows


def audit_v6_pool_schedule(
    rows: Sequence[Mapping[str, Any]], bank: V6TriadBank
) -> Dict[str, Any]:
    rows = list(rows)
    expected_triads = {
        str(triad["triad_id"]): split
        for split in ("development", "heldout")
        for triad in _triads(bank, split)
    }
    triad_counts: Counter = Counter()
    scenario_counts: Dict[str, Counter] = defaultdict(Counter)
    frame_slots: Dict[str, Counter] = defaultdict(Counter)
    permutations: Dict[str, set] = defaultdict(set)
    round_metadata: Dict[Tuple[str, str], set] = defaultdict(set)
    rounds_by_split: Dict[str, set] = defaultdict(set)
    complete = True
    for row in rows:
        triad_id = str(row.get("triad_id", ""))
        triad_counts[triad_id] += 1
        scenario_id = str(row.get("scenario", {}).get("id", ""))
        scenario_counts[triad_id][scenario_id] += 1
        candidates = row.get("candidates", [])
        complete &= (
            len(candidates) == 3
            and {str(candidate.get("frame")) for candidate in candidates}
            == set(STRATEGIES)
            and {int(candidate.get("slot", -1)) for candidate in candidates}
            == {1, 2, 3}
            and all(str(candidate.get("triad_id")) == triad_id for candidate in candidates)
        )
        order = tuple(
            str(candidate["frame"])
            for candidate in sorted(candidates, key=lambda item: int(item["slot"]))
        )
        permutations[triad_id].add(order)
        for candidate in candidates:
            frame_slots[triad_id][
                (str(candidate["frame"]), int(candidate["slot"]))
            ] += 1
        split = str(row.get("split", ""))
        round_index = int(row.get("round", -1))
        round_metadata[(triad_id, scenario_id)].add(
            (
                round_index,
                int(row.get("n_rounds", -1)),
                int(row.get("heldout_start_round", -1)),
            )
        )
        rounds_by_split[split].add(round_index)
        complete &= split == expected_triads.get(triad_id)
        complete &= (
            1 <= round_index <= 18
            if split == "development"
            else 19 <= round_index <= 24
        )
        complete &= int(row.get("n_rounds", -1)) == 24
        complete &= int(row.get("heldout_start_round", -1)) == 19
    expected_count = len(expected_triads) * len(V6_CALIBRATION_SCENARIOS) * 6
    checks = {
        "nonempty": bool(rows),
        "record_count": len(rows) == expected_count,
        "exact_triad_membership": set(triad_counts) == set(expected_triads),
        "complete_candidate_sets": complete,
        "triad_exposure": all(
            value == len(V6_CALIBRATION_SCENARIOS) * 6
            for value in triad_counts.values()
        ),
        "all_scenarios_per_triad": all(
            set(counts) == {scenario.id for scenario in V6_CALIBRATION_SCENARIOS}
            and set(counts.values()) == {6}
            for counts in scenario_counts.values()
        ),
        "all_six_permutations": all(len(values) == 6 for values in permutations.values()),
        "counterfactual_round_metadata": len(round_metadata)
        == len(expected_triads) * len(V6_CALIBRATION_SCENARIOS)
        and all(len(values) == 1 for values in round_metadata.values()),
        "round_partitions": rounds_by_split["development"] == set(range(1, 19))
        and rounds_by_split["heldout"] == set(range(19, 25)),
        "frame_slot_balance": all(
            set(counts) == {(frame, slot) for frame in STRATEGIES for slot in (1, 2, 3)}
            and set(counts.values()) == {len(V6_CALIBRATION_SCENARIOS) * 2}
            for counts in frame_slots.values()
        ),
        "pool_hash": all(row.get("pool_sha256") == bank.sha256() for row in rows),
    }
    return {
        "pass": all(checks.values()),
        "checks": checks,
        "n_rows": len(rows),
        "triad_exposures": dict(triad_counts),
        "frame_slot_counts": {
            triad_id: {"%s@%d" % key: value for key, value in counts.items()}
            for triad_id, counts in frame_slots.items()
        },
    }


def _base_candidate_id(candidate_id: str, scenario_id: str) -> str:
    suffix = "-" + scenario_id
    if not candidate_id.endswith(suffix):
        raise ValueError("candidate id does not end with scenario id")
    return candidate_id[: -len(suffix)]


def _triad_lookup(bank: V6TriadBank) -> Dict[str, Tuple[str, str]]:
    lookup: Dict[str, Tuple[str, str]] = {}
    for split in ("development", "heldout"):
        for triad in _triads(bank, split):
            for entry in triad["candidates"].values():
                lookup[str(entry["candidate_id"])] = (str(triad["triad_id"]), split)
    return lookup


def build_v6_validation_schedule(
    bank: V6TriadBank,
    seed: int = 20262002,
) -> List[Dict[str, Any]]:
    """Challenge the locked bank on disjoint scenarios and all permutations."""
    permutations = list(itertools.permutations(STRATEGIES))
    rows: List[Dict[str, Any]] = []
    global_index = 0
    for split in ("development", "heldout"):
        for triad_index, triad in enumerate(_triads(bank, split)):
            for scenario_index, scenario in enumerate(V6_VALIDATION_SCENARIOS):
                offset = derive_seed(
                    "v6_validation_permutation_offset",
                    seed,
                    split,
                    triad["triad_id"],
                    scenario.id,
                ) % len(permutations)
                ordered = permutations[offset:] + permutations[:offset]
                for local_index, permutation in enumerate(ordered):
                    round_index = _counterfactual_round_index(
                        split, triad_index, scenario_index
                    )
                    rows.append(
                        {
                            "calibration_version": V6_CALIBRATION_VERSION,
                            "pool_sha256": bank.sha256(),
                            "split": split,
                            "triad_id": str(triad["triad_id"]),
                            "triad_index": triad_index,
                            "scenario_index": scenario_index,
                            "permutation_index": local_index,
                            "frame_order": list(permutation),
                            "episode_index": global_index // 24,
                            "round": round_index,
                            "n_rounds": 24,
                            "heldout_start_round": 19,
                            "scenario": scenario.as_dict(),
                            "candidates": _candidate_rows_for_triad(
                                triad, scenario, permutation, split
                            ),
                            "generation_seed": derive_seed(
                                V6_CALIBRATION_VERSION,
                                "independent_validation",
                                seed,
                                split,
                                triad["triad_id"],
                                scenario.id,
                                local_index,
                            ),
                        }
                    )
                    global_index += 1
    audit = audit_v6_validation_schedule(rows, bank)
    if not audit["pass"]:
        failed = sorted(name for name, passed in audit["checks"].items() if not passed)
        raise RuntimeError("generated V6 validation schedule failed: %s" % ", ".join(failed))
    return rows


def audit_v6_validation_schedule(
    rows: Sequence[Mapping[str, Any]], bank: V6TriadBank
) -> Dict[str, Any]:
    rows = list(rows)
    triad_counts: Dict[str, Counter] = defaultdict(Counter)
    scenario_counts: Dict[str, Counter] = defaultdict(Counter)
    frame_slots: Dict[str, Counter] = defaultdict(Counter)
    permutations: Dict[str, set] = defaultdict(set)
    round_metadata: Dict[Tuple[str, str], set] = defaultdict(set)
    rounds_by_split: Dict[str, set] = defaultdict(set)
    complete = True
    for row in rows:
        split = str(row["split"])
        triad_id = str(row["triad_id"])
        triad_counts[split][triad_id] += 1
        scenario_id = str(row["scenario"]["id"])
        scenario_counts[triad_id][scenario_id] += 1
        candidates = row.get("candidates", [])
        complete &= len(candidates) == 3
        complete &= {candidate["frame"] for candidate in candidates} == set(STRATEGIES)
        complete &= {int(candidate["slot"]) for candidate in candidates} == {1, 2, 3}
        complete &= all(candidate["triad_id"] == row["triad_id"] for candidate in candidates)
        order = tuple(
            str(candidate["frame"])
            for candidate in sorted(candidates, key=lambda item: int(item["slot"]))
        )
        permutations[triad_id].add(order)
        for candidate in candidates:
            frame_slots[triad_id][
                (str(candidate["frame"]), int(candidate["slot"]))
            ] += 1
        round_index = int(row.get("round", -1))
        round_metadata[(triad_id, scenario_id)].add(
            (
                round_index,
                int(row.get("n_rounds", -1)),
                int(row.get("heldout_start_round", -1)),
            )
        )
        rounds_by_split[split].add(round_index)
        complete &= (
            1 <= round_index <= 18
            if split == "development"
            else 19 <= round_index <= 24
        )
        complete &= int(row.get("n_rounds", -1)) == 24
        complete &= int(row.get("heldout_start_round", -1)) == 19
    expected_ids = {
        split: {str(triad["triad_id"]) for triad in _triads(bank, split)}
        for split in ("development", "heldout")
    }
    expected_total = sum(len(values) for values in expected_ids.values()) * len(
        V6_VALIDATION_SCENARIOS
    ) * 6
    checks = {
        "nonempty": bool(rows),
        "record_count": len(rows) == expected_total,
        "complete_candidate_sets": complete,
        "pool_hash": all(row.get("pool_sha256") == bank.sha256() for row in rows),
        "split_membership": all(set(triad_counts[split]) == expected_ids[split] for split in expected_ids),
        "triad_exposure": all(
            value == len(V6_VALIDATION_SCENARIOS) * 6
            for counts in triad_counts.values()
            for value in counts.values()
        ),
        "disjoint_validation_scenarios": all(
            set(counts) == {scenario.id for scenario in V6_VALIDATION_SCENARIOS}
            and set(counts.values()) == {6}
            for counts in scenario_counts.values()
        ),
        "all_six_permutations": all(len(values) == 6 for values in permutations.values()),
        "counterfactual_round_metadata": len(round_metadata)
        == sum(len(values) for values in expected_ids.values())
        * len(V6_VALIDATION_SCENARIOS)
        and all(len(values) == 1 for values in round_metadata.values()),
        "round_partitions": rounds_by_split["development"] == set(range(1, 19))
        and rounds_by_split["heldout"] == set(range(19, 25)),
        "frame_slot_balance": all(
            set(counts) == {(frame, slot) for frame in STRATEGIES for slot in (1, 2, 3)}
            and set(counts.values()) == {len(V6_VALIDATION_SCENARIOS) * 2}
            for counts in frame_slots.values()
        ),
    }
    return {
        "pass": all(checks.values()),
        "checks": checks,
        "n_rows": len(rows),
        "triad_counts": {split: dict(counts) for split, counts in triad_counts.items()},
        "frame_slot_counts": {
            triad_id: {"%s@%d" % key: value for key, value in counts.items()}
            for triad_id, counts in frame_slots.items()
        },
    }


def _message_candidates(row: Mapping[str, Any]) -> List[MessageCandidate]:
    return [
        MessageCandidate(
            slot=int(candidate["slot"]),
            candidate_id=str(candidate["candidate_id"]),
            message=str(candidate["message"]),
            frame=str(candidate["frame"]),
            split=str(candidate["split"]),
            template_index=-1,
        )
        for candidate in row["candidates"]
    ]


def _scenario_proxy(scenario: Mapping[str, Any]):
    class ScenarioProxy:
        id = scenario["id"]
        title = scenario["title"]
        context = scenario["context"]
        option_a = scenario["option_a"]
        option_b = scenario["option_b"]

        @classmethod
        def render(cls):
            return (
                "Decision: %s\n%s\nOption A: %s\nOption B: %s"
                % (cls.title, cls.context, cls.option_a, cls.option_b)
            )

    return ScenarioProxy


def _v6_schedule(
    bank: V6TriadBank, seed: int, mode: str
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    if mode == V6_POOL_MODE:
        schedule = build_v6_pool_schedule(bank, seed=seed)
        audit = audit_v6_pool_schedule(schedule, bank)
    elif mode == V6_VALIDATION_MODE:
        schedule = build_v6_validation_schedule(bank, seed=seed)
        audit = audit_v6_validation_schedule(schedule, bank)
    else:
        raise ValueError("unknown V6 calibration mode %r" % mode)
    if not audit["pass"]:
        raise ValueError("V6 calibration schedule audit failed")
    return schedule, audit


def _v6_run_paths(out_dir: str, run_id: str) -> Dict[str, str]:
    root = os.path.abspath(out_dir)
    return {
        "log": os.path.join(root, run_id + ".jsonl"),
        "manifest": os.path.join(root, run_id + ".manifest.json"),
        "samples": os.path.join(root, run_id + ".samples"),
        "claim": os.path.join(root, run_id + ".inflight.json"),
        "lock": os.path.join(root, run_id + ".lock"),
    }


def _validate_v6_output_layout(
    out_dir: str,
    paths: Mapping[str, str],
    *,
    create_out_dir: bool,
) -> str:
    """Reject path traversal, links, and special files in the canonical run tree."""
    root = os.path.abspath(out_dir)
    if os.path.realpath(root) != root:
        raise ValueError(
            "V6 canonical output directory must not traverse a symlink"
        )
    if _path_exists(root):
        require_directory_nonsymlink(root, label="V6 canonical output directory")
    elif create_out_dir:
        parent = os.path.dirname(root) or os.curdir
        require_directory_nonsymlink(
            parent, label="V6 canonical output directory parent"
        )
        os.mkdir(root)
        require_directory_nonsymlink(root, label="V6 canonical output directory")
        _fsync_directory(os.path.join(root, ".directory-entry"))

    root_real = os.path.realpath(root)
    for name, path in paths.items():
        absolute = require_contained_path(path, root, label="V6 %s path" % name)
        parent = os.path.dirname(absolute) or os.curdir
        if _path_exists(parent):
            require_directory_nonsymlink(parent, label="V6 %s parent" % name)
            parent_real = os.path.realpath(parent)
            try:
                contained = os.path.commonpath([root_real, parent_real]) == root_real
            except ValueError:
                contained = False
            if not contained:
                raise ValueError("V6 %s parent leaves the canonical output" % name)

    for name in ("log", "manifest", "claim", "lock"):
        require_regular_nonsymlink(
            paths[name], label="V6 %s artifact" % name, allow_missing=True
        )
    require_directory_nonsymlink(
        paths["samples"], label="V6 sample artifact directory", allow_missing=True
    )
    if _path_exists(paths["samples"]):
        for entry in os.listdir(paths["samples"]):
            sample_path = os.path.join(paths["samples"], entry)
            require_contained_path(
                sample_path, root, label="V6 sample artifact"
            )
            require_regular_nonsymlink(
                sample_path, label="V6 sample artifact"
            )
    return root


def _v6_manifest_base(
    *,
    bank: V6TriadBank,
    provider_description: Mapping[str, Any],
    run_id: str,
    out_dir: str,
    seed: int,
    mode: str,
    schedule: Sequence[Mapping[str, Any]],
    schedule_audit: Mapping[str, Any],
    provenance: Optional[Mapping[str, Any]],
) -> Dict[str, Any]:
    paths = _v6_run_paths(out_dir, run_id)
    manifest: Dict[str, Any] = {
        "calibration_version": V6_CALIBRATION_VERSION,
        "task_version": CONTROLLED_V6_VERSION,
        "mode": mode,
        "run_id": run_id,
        "run_status": "running",
        "target_simulator_present": False,
        "history_present": False,
        "pool_sha256": bank.sha256(),
        "bank_content_sha256": bank_content_sha256(bank.payload),
        "bank_source": bank.source_path,
        "provider": json.loads(json.dumps(provider_description)),
        "schedule": {
            "seed": seed,
            "n_records": len(schedule),
            "n_episode_blocks": None,
            "n_rounds": 24,
            "heldout_start_round": 19,
        },
        "schedule_audit": json.loads(json.dumps(schedule_audit)),
        "sample_artifacts": {
            "version": _V6_SAMPLE_ARTIFACT_VERSION,
            "directory": os.path.abspath(paths["samples"]),
            "filename_pattern": "{schedule_index:08d}.json",
            "write_order": (
                "inflight_claim_then_generation_then_sample_artifact_then_"
                "claim_clear_then_jsonl_then_manifest"
            ),
        },
        "inflight_claim": {
            "version": _V6_INFLIGHT_CLAIM_VERSION,
            "path": os.path.abspath(paths["claim"]),
            "restart_policy": (
                "clear_only_for_exact_durable_sample; otherwise stop_ambiguous"
            ),
        },
        "n_records_committed": 0,
        "last_committed_sample_sha256": None,
    }
    if provenance is not None:
        manifest["frozen_protocol"] = json.loads(json.dumps(provenance))
    return manifest


def _load_json_mapping(path: str, label: str) -> Dict[str, Any]:
    try:
        with _open_regular_read(path, label, binary=True) as handle:
            raw = handle.read()
        payload = _strict_external_json_loads(raw.decode("utf-8"))
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
        raise ValueError("could not read %s: %s" % (label, exc)) from exc
    if not isinstance(payload, dict):
        raise ValueError("%s must contain one JSON object" % label)
    return payload


def _strict_external_json_loads(text: str) -> Any:
    def object_from_pairs(pairs: Sequence[Tuple[str, Any]]) -> Dict[str, Any]:
        result: Dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate JSON key %r" % key)
            result[key] = value
        return result

    def reject_constant(token: str) -> None:
        raise ValueError("non-finite JSON constant %s" % token)

    return json.loads(
        text,
        object_pairs_hook=object_from_pairs,
        parse_constant=reject_constant,
    )


def _load_sample_artifacts(
    sample_dir: str,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    if not _path_exists(sample_dir):
        return [], []
    require_directory_nonsymlink(
        sample_dir, label="V6 sample artifact directory"
    )
    indexed: List[Tuple[int, str]] = []
    for name in os.listdir(sample_dir):
        path = os.path.join(sample_dir, name)
        require_regular_nonsymlink(path, label="V6 sample artifact")
        # A process can die while writing an unpublished temporary. It is not
        # evidence of a completed generation and is intentionally ignored.
        if name.startswith(".") and ".tmp." in name:
            continue
        match = _V6_SAMPLE_ARTIFACT_PATTERN.fullmatch(name)
        if match is None:
            raise ValueError("unexpected file in V6 sample artifact directory: %s" % name)
        indexed.append((int(match.group(1)), path))
    indexed.sort()
    if [index for index, _path in indexed] != list(range(len(indexed))):
        raise ValueError("V6 sample artifacts contain a gap or duplicate coordinate")
    artifacts: List[Dict[str, Any]] = []
    records: List[Dict[str, Any]] = []
    for index, path in indexed:
        artifact = _load_json_mapping(path, "V6 sample artifact %d" % index)
        record = artifact.get("record")
        if not isinstance(record, dict):
            raise ValueError("V6 sample artifact %d has no record" % index)
        try:
            expected = _sample_artifact(index, record)
        except KeyError as exc:
            raise ValueError(
                "V6 sample artifact %d lacks a coordinate field" % index
            ) from exc
        if not _json_exact(artifact, expected):
            raise ValueError("V6 sample artifact %d failed its exact hash envelope" % index)
        if record.get("sample_sha256") != _sample_sha256(record):
            raise ValueError("V6 sample artifact %d has a forged sample hash" % index)
        artifacts.append(artifact)
        records.append(record)
    return artifacts, records


def _load_jsonl_for_resume(
    path: str,
) -> Tuple[List[Dict[str, Any]], bool, bool, bool]:
    """Return rows, repair flag, existence, and malformed-tail flag."""
    if not _path_exists(path):
        return [], False, False, False
    try:
        with _open_regular_read(path, "V6 raw log", binary=True) as handle:
            raw = handle.read()
    except OSError as exc:
        raise ValueError("could not read V6 raw JSONL: %s" % exc) from exc
    records: List[Dict[str, Any]] = []
    repair_needed = bool(raw) and not raw.endswith(b"\n")
    trailing_malformed = False
    lines = raw.splitlines(keepends=True)
    for index, line in enumerate(lines):
        complete = line.endswith(b"\n")
        body = line.rstrip(b"\r\n")
        if not body:
            raise ValueError("V6 raw JSONL contains a blank row")
        try:
            decoded = _strict_external_json_loads(body.decode("utf-8"))
        except (UnicodeError, ValueError, json.JSONDecodeError) as exc:
            if index == len(lines) - 1 and not complete:
                repair_needed = True
                trailing_malformed = True
                break
            raise ValueError("V6 raw JSONL row %d is malformed" % index) from exc
        if not isinstance(decoded, dict):
            raise ValueError("V6 raw JSONL row %d is not an object" % index)
        records.append(decoded)
    return records, repair_needed, True, trailing_malformed


def _audit_v6_prefix(
    *,
    records: Sequence[Mapping[str, Any]],
    schedule: Sequence[Mapping[str, Any]],
    manifest: Mapping[str, Any],
    expected_manifest: Mapping[str, Any],
    provider_description: Mapping[str, Any],
    run_id: str,
    mode: str,
) -> Dict[str, Any]:
    if len(records) > len(schedule):
        raise ValueError("V6 raw log is longer than the frozen schedule")
    manifest_fields = (
        "calibration_version",
        "task_version",
        "mode",
        "run_id",
        "target_simulator_present",
        "history_present",
        "pool_sha256",
        "bank_content_sha256",
        "bank_source",
        "provider",
        "schedule",
        "schedule_audit",
        "sample_artifacts",
        "inflight_claim",
        "frozen_protocol",
    )
    mismatched_manifest = [
        field
        for field in manifest_fields
        if (field in manifest or field in expected_manifest)
        and not _json_exact(manifest.get(field), expected_manifest.get(field))
    ]
    if mismatched_manifest:
        raise ValueError(
            "V6 running manifest has foreign configuration: %s"
            % ", ".join(mismatched_manifest)
        )
    status = manifest.get("run_status")
    if status not in {"running", "completed"}:
        raise ValueError("V6 manifest has invalid run status")
    committed = manifest.get("n_records_committed")
    if type(committed) is not int or committed < 0 or committed > len(records):
        raise ValueError("V6 manifest committed count is ahead of durable samples")
    expected_last = records[committed - 1].get("sample_sha256") if committed else None
    if manifest.get("last_committed_sample_sha256") != expected_last:
        raise ValueError("V6 manifest last committed sample hash is inconsistent")

    for index, (record, expected) in enumerate(zip(records, schedule)):
        immutable = {field: record.get(field) for field in _V6_IMMUTABLE_SCHEDULE_FIELDS}
        expected_immutable = {
            field: expected[field] for field in _V6_IMMUTABLE_SCHEDULE_FIELDS
        }
        if not _json_exact(immutable, expected_immutable):
            raise ValueError("V6 raw record %d substitutes a frozen coordinate" % index)
        prompt = build_controlled_prompt(
            scenario=_scenario_proxy(expected["scenario"]),
            candidates=_message_candidates(expected),
            history=[],
            round_index=int(expected["round"]),
            n_rounds=24,
            show_history=False,
            focal_mode="spontaneous",
            context={},
        )
        raw = record.get("focal_output_raw")
        if type(raw) is not str:
            raise ValueError("V6 raw record %d has no exact model artifact" % index)
        parsed = parse_controlled_choice(raw, "spontaneous", int(expected["generation_seed"]))
        candidates = _message_candidates(expected)
        if not parsed.selection_valid:
            raise ValueError("V6 raw record %d has an invalid constrained output" % index)
        selected = candidate_for_slot(candidates, parsed.selected_slot)
        source = next(
            candidate
            for candidate in expected["candidates"]
            if int(candidate["slot"]) == parsed.selected_slot
        )
        required = {
            "run_id": run_id,
            "mode": mode,
            "focal_system_prompt": prompt.system,
            "focal_user_prompt": prompt.user,
            "selection_valid": True,
            "fallback_used": False,
            "selected_slot": parsed.selected_slot,
            "selected_frame": selected.frame,
            "selected_candidate_id": selected.candidate_id,
            "selected_pool_candidate_id": source["pool_candidate_id"],
            "provider": provider_description.get("provider"),
            "model_name": provider_description.get("model") or "unknown",
            "provider_metadata": provider_description,
        }
        mismatched = [
            field
            for field, value in required.items()
            if not _json_exact(record.get(field), value)
        ]
        if mismatched:
            raise ValueError(
                "V6 raw record %d has substituted generation metadata: %s"
                % (index, ", ".join(mismatched))
            )
        if type(record.get("timestamp")) is not str or not record["timestamp"]:
            raise ValueError("V6 raw record %d has no timestamp" % index)
        if record.get("sample_sha256") != _sample_sha256(record):
            raise ValueError("V6 raw record %d has a forged sample hash" % index)
    return {
        "pass": True,
        "n_completed": len(records),
        "n_remaining": len(schedule) - len(records),
        "next_schedule_index": len(records),
        "run_status": status,
    }


def preflight_v6_target_free_calibration(
    *,
    bank: V6TriadBank,
    provider_description: Mapping[str, Any],
    run_id: str,
    out_dir: str,
    seed: int,
    mode: str,
    n_episode_blocks: Optional[int] = None,
    provenance: Optional[Mapping[str, Any]] = None,
    _lock_held: bool = False,
) -> Dict[str, Any]:
    """Audit a new, interrupted, or completed run without invoking a provider."""
    if n_episode_blocks is not None:
        raise ValueError(
            "V6 uses a complete triad-by-scenario-by-permutation schedule; "
            "episode-block overrides are not defined"
        )
    schedule, schedule_audit = _v6_schedule(bank, seed, mode)
    paths = _v6_run_paths(out_dir, run_id)
    _validate_v6_output_layout(out_dir, paths, create_out_dir=False)
    expected_manifest = _v6_manifest_base(
        bank=bank,
        provider_description=provider_description,
        run_id=run_id,
        out_dir=out_dir,
        seed=seed,
        mode=mode,
        schedule=schedule,
        schedule_audit=schedule_audit,
        provenance=provenance,
    )
    manifest_exists = _path_exists(paths["manifest"])
    log_exists = _path_exists(paths["log"])
    claim_exists = _path_exists(paths["claim"])
    sample_entries = (
        os.listdir(paths["samples"])
        if _path_exists(paths["samples"])
        else []
    )
    visible_sample_entries = [
        name for name in sample_entries if not (name.startswith(".") and ".tmp." in name)
    ]
    if not manifest_exists:
        if log_exists or claim_exists or visible_sample_entries:
            raise ValueError("V6 outputs exist without their canonical running manifest")
        return {
            "state": "new",
            "schedule": schedule,
            "schedule_audit": schedule_audit,
            "expected_manifest": expected_manifest,
            "manifest": None,
            "records": [],
            "paths": paths,
            "prefix_audit": {"pass": True, "n_completed": 0, "n_remaining": len(schedule)},
        }

    manifest = _load_json_mapping(paths["manifest"], "V6 calibration manifest")
    artifacts, artifact_records = _load_sample_artifacts(paths["samples"])
    (
        log_records,
        log_needs_repair,
        _present,
        trailing_malformed,
    ) = _load_jsonl_for_resume(paths["log"])
    if log_records != artifact_records[: len(log_records)]:
        raise ValueError("V6 raw JSONL differs from immutable sample artifacts")
    if len(log_records) > len(artifact_records):
        raise ValueError("V6 raw JSONL contains an unsealed paid sample")
    if trailing_malformed and len(artifact_records) <= len(log_records):
        raise ValueError("V6 raw JSONL has an unexplained malformed trailing row")
    if len(log_records) < len(artifact_records):
        log_needs_repair = True
    prefix = _audit_v6_prefix(
        records=artifact_records,
        schedule=schedule,
        manifest=manifest,
        expected_manifest=expected_manifest,
        provider_description=provider_description,
        run_id=run_id,
        mode=mode,
    )
    claim_recovery_pending = False
    if claim_exists:
        claim = _load_json_mapping(paths["claim"], "V6 in-flight claim")
        claim_index = claim.get("schedule_index")
        if type(claim_index) is not int or not (0 <= claim_index < len(schedule)):
            raise ValueError("V6 in-flight claim has an invalid schedule index")
        expected_claim = _inflight_claim(
            schedule_index=claim_index,
            schedule_row=schedule[claim_index],
            run_id=run_id,
            mode=mode,
            provider_description=provider_description,
        )
        if not _json_exact(claim, expected_claim):
            raise ValueError("V6 in-flight claim differs from the frozen coordinate")
        if len(artifact_records) == claim_index + 1:
            expected_sample = _sample_artifact(
                claim_index, artifact_records[claim_index]
            )
            if not _json_exact(artifacts[claim_index], expected_sample):
                raise ValueError(
                    "V6 in-flight claim has no exact durable response sample"
                )
            if _lock_held:
                _clear_inflight_claim_after_sample(
                    claim_path=paths["claim"],
                    expected_claim=expected_claim,
                    sample_path=os.path.join(
                        paths["samples"], "%08d.json" % claim_index
                    ),
                    expected_sample=expected_sample,
                )
            else:
                claim_recovery_pending = True
        elif len(artifact_records) <= claim_index:
            raise ValueError(
                "ambiguous V6 in-flight claim has no durable response sample; "
                "refusing to repeat the paid call"
            )
        else:
            raise ValueError(
                "V6 in-flight claim is inconsistent with the durable sample prefix"
            )
    if (log_needs_repair or not log_exists) and _lock_held:
        _atomic_write_jsonl(paths["log"], artifact_records)
    if manifest.get("run_status") == "completed":
        if len(artifact_records) != len(schedule):
            raise ValueError("completed V6 manifest has an incomplete sample schedule")
        if manifest.get("n_records_committed") != len(schedule):
            raise ValueError("completed V6 manifest has an incomplete commit count")
        if manifest.get("n_records") != len(schedule):
            raise ValueError("completed V6 manifest record count is inconsistent")
        if manifest.get("valid_selection_rate") != 1.0:
            raise ValueError("completed V6 manifest has invalid selection summary")
        if manifest.get("log_path") != os.path.abspath(paths["log"]):
            raise ValueError("completed V6 manifest points at a foreign raw log")
        if manifest.get("log_file_sha256") != file_sha256(paths["log"]):
            raise ValueError("completed V6 manifest raw log hash is inconsistent")
        full_audit = audit_v6_calibration_run(artifact_records, manifest, bank, mode)
        if not full_audit["pass"]:
            failed = sorted(name for name, passed in full_audit["checks"].items() if not passed)
            raise ValueError("completed V6 calibration audit failed: %s" % ", ".join(failed))
        state = "completed"
    else:
        state = "resume" if artifact_records else "new_claimed"
    return {
        "state": state,
        "schedule": schedule,
        "schedule_audit": schedule_audit,
        "expected_manifest": expected_manifest,
        "manifest": manifest,
        "records": artifact_records,
        "paths": paths,
        "prefix_audit": prefix,
        "claim_recovery_pending": claim_recovery_pending,
    }


def _run_v6_target_free_calibration_locked(
    bank: V6TriadBank,
    provider: BaseProvider,
    run_id: str,
    out_dir: str,
    seed: int,
    mode: str,
    n_episode_blocks: Optional[int] = None,
    provenance: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    if n_episode_blocks is not None:
        raise ValueError(
            "V6 uses a complete triad-by-scenario-by-permutation schedule; "
            "episode-block overrides are not defined"
        )
    provider_description = provider.describe()
    preflight = preflight_v6_target_free_calibration(
        bank=bank,
        provider_description=provider_description,
        run_id=run_id,
        out_dir=out_dir,
        seed=seed,
        mode=mode,
        n_episode_blocks=n_episode_blocks,
        provenance=provenance,
        _lock_held=True,
    )
    schedule = preflight["schedule"]
    paths = preflight["paths"]
    records: List[Dict[str, Any]] = list(preflight["records"])
    if preflight["state"] == "completed":
        return {
            "records": records,
            "manifest": preflight["manifest"],
            "log_path": paths["log"],
            "manifest_path": paths["manifest"],
            "run_state": "completed_existing",
        }

    if preflight["manifest"] is None:
        manifest = _atomic_write_manifest(paths["manifest"], preflight["expected_manifest"])
        _ensure_nonsymlink_directory(
            paths["samples"], "V6 sample artifact directory"
        )
        if not _path_exists(paths["log"]):
            _atomic_write_jsonl(paths["log"], [])
    else:
        manifest = dict(preflight["manifest"])
        if manifest.get("n_records_committed") != len(records):
            manifest["n_records_committed"] = len(records)
            manifest["last_committed_sample_sha256"] = (
                records[-1]["sample_sha256"] if records else None
            )
            manifest = _atomic_write_manifest(paths["manifest"], manifest)

    for schedule_index in range(len(records), len(schedule)):
        schedule_row = schedule[schedule_index]
        candidates = _message_candidates(schedule_row)
        prompt = build_controlled_prompt(
            scenario=_scenario_proxy(schedule_row["scenario"]),
            candidates=candidates,
            history=[],
            round_index=int(schedule_row["round"]),
            n_rounds=24,
            show_history=False,
            focal_mode="spontaneous",
            context={},
        )
        set_next_seed = getattr(provider, "set_next_seed", None)
        if callable(set_next_seed):
            set_next_seed(int(schedule_row["generation_seed"]))
        claim = _inflight_claim(
            schedule_index=schedule_index,
            schedule_row=schedule_row,
            run_id=run_id,
            mode=mode,
            provider_description=provider_description,
        )
        _create_inflight_claim(paths["claim"], claim)
        raw = provider.generate(prompt)
        parsed = parse_controlled_choice(
            raw, "spontaneous", int(schedule_row["generation_seed"])
        )
        if not parsed.selection_valid:
            raise ProviderError(
                "V6 calibration requires an exact constrained choice; got %r" % raw
            )
        selected = candidate_for_slot(candidates, parsed.selected_slot)
        source = next(
            candidate
            for candidate in schedule_row["candidates"]
            if int(candidate["slot"]) == parsed.selected_slot
        )
        record: Dict[str, Any] = {
            **schedule_row,
            "run_id": run_id,
            "mode": mode,
            "focal_system_prompt": prompt.system,
            "focal_user_prompt": prompt.user,
            "focal_output_raw": raw,
            "selection_valid": True,
            "fallback_used": False,
            "selected_slot": parsed.selected_slot,
            "selected_frame": selected.frame,
            "selected_candidate_id": selected.candidate_id,
            "selected_pool_candidate_id": source["pool_candidate_id"],
            "provider": provider_description.get("provider", provider.name),
            "model_name": provider_description.get("model") or "unknown",
            "provider_metadata": json.loads(json.dumps(provider_description)),
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        }
        record["sample_sha256"] = _sample_sha256(record)
        sample_path = os.path.join(paths["samples"], "%08d.json" % schedule_index)
        sample_artifact = _sample_artifact(schedule_index, record)
        _atomic_create_json(sample_path, sample_artifact)
        _clear_inflight_claim_after_sample(
            claim_path=paths["claim"],
            expected_claim=claim,
            sample_path=sample_path,
            expected_sample=sample_artifact,
        )
        _append_jsonl_durable(paths["log"], record)
        records.append(record)
        manifest["n_records_committed"] = len(records)
        manifest["last_committed_sample_sha256"] = record["sample_sha256"]
        manifest = _atomic_write_manifest(paths["manifest"], manifest)

    manifest["run_status"] = "completed"
    manifest["n_records"] = len(records)
    manifest["valid_selection_rate"] = 1.0
    manifest["log_path"] = os.path.abspath(paths["log"])
    manifest["log_file_sha256"] = file_sha256(paths["log"])
    manifest = _atomic_write_manifest(paths["manifest"], manifest)
    return {
        "records": records,
        "manifest": manifest,
        "log_path": paths["log"],
        "manifest_path": paths["manifest"],
        "run_state": "completed_resumed" if preflight["state"] == "resume" else "completed_new",
    }


def run_v6_target_free_calibration(
    bank: V6TriadBank,
    provider: BaseProvider,
    run_id: str,
    out_dir: str,
    seed: int,
    mode: str,
    n_episode_blocks: Optional[int] = None,
    provenance: Optional[Mapping[str, Any]] = None,
    _lock_held: bool = False,
) -> Dict[str, Any]:
    """Run or resume one official calibration under a process-safe lock."""
    if n_episode_blocks is not None:
        raise ValueError(
            "V6 uses a complete triad-by-scenario-by-permutation schedule; "
            "episode-block overrides are not defined"
        )
    paths = _v6_run_paths(out_dir, run_id)
    canonical_out_dir = _validate_v6_output_layout(
        out_dir, paths, create_out_dir=True
    )
    if _lock_held:
        _validate_v6_output_layout(
            canonical_out_dir, paths, create_out_dir=False
        )
        return _run_v6_target_free_calibration_locked(
            bank=bank,
            provider=provider,
            run_id=run_id,
            out_dir=canonical_out_dir,
            seed=seed,
            mode=mode,
            n_episode_blocks=n_episode_blocks,
            provenance=provenance,
        )
    with ExclusiveFileLock(
        paths["lock"],
        label="V6 calibration run",
        metadata={"run_id": run_id, "mode": mode},
    ):
        _validate_v6_output_layout(
            canonical_out_dir, paths, create_out_dir=False
        )
        return _run_v6_target_free_calibration_locked(
            bank=bank,
            provider=provider,
            run_id=run_id,
            out_dir=canonical_out_dir,
            seed=seed,
            mode=mode,
            n_episode_blocks=n_episode_blocks,
            provenance=provenance,
        )


def audit_v6_calibration_run(
    records: Sequence[Mapping[str, Any]],
    manifest: Mapping[str, Any],
    bank: V6TriadBank,
    expected_mode: str,
) -> Dict[str, Any]:
    """Verify that logged choices came from the exact frozen V6 schedule."""
    records = list(records)
    manifest_is_mapping = isinstance(manifest, Mapping)
    manifest = manifest if manifest_is_mapping else {}
    schedule_spec = manifest.get("schedule", {})
    schedule_spec = schedule_spec if isinstance(schedule_spec, Mapping) else {}
    schedule_seed = schedule_spec.get("seed")
    seed_is_exact_integer = type(schedule_seed) is int

    regenerated_schedule: List[Dict[str, Any]] = []
    regeneration_error: Optional[str] = None
    if not seed_is_exact_integer:
        regeneration_error = "manifest schedule seed must be an integer"
    else:
        try:
            if expected_mode == V6_POOL_MODE:
                regenerated_schedule = build_v6_pool_schedule(
                    bank, seed=schedule_seed
                )
            elif expected_mode == V6_VALIDATION_MODE:
                regenerated_schedule = build_v6_validation_schedule(
                    bank, seed=schedule_seed
                )
            else:
                regeneration_error = "unknown V6 calibration mode %r" % expected_mode
        except Exception as exc:
            regeneration_error = str(exc)
            regenerated_schedule = []

    try:
        if expected_mode == V6_POOL_MODE:
            schedule_audit = audit_v6_pool_schedule(records, bank)
        elif expected_mode == V6_VALIDATION_MODE:
            schedule_audit = audit_v6_validation_schedule(records, bank)
        else:
            raise ValueError("unknown V6 calibration mode %r" % expected_mode)
    except Exception as exc:
        schedule_audit = {
            "pass": False,
            "checks": {"well_formed": False},
            "n_rows": len(records),
            "error": str(exc),
        }

    def _json_exact(left: Any, right: Any) -> bool:
        try:
            return json.dumps(
                left,
                sort_keys=True,
                ensure_ascii=False,
                separators=(",", ":"),
                allow_nan=False,
            ) == json.dumps(
                right,
                sort_keys=True,
                ensure_ascii=False,
                separators=(",", ":"),
                allow_nan=False,
            )
        except (TypeError, ValueError):
            return False

    def _matches_schedule_row(
        record: Mapping[str, Any], expected: Mapping[str, Any]
    ) -> bool:
        if (
            set(expected) != set(_V6_IMMUTABLE_SCHEDULE_FIELDS)
            or not isinstance(record, Mapping)
            or any(field not in record for field in _V6_IMMUTABLE_SCHEDULE_FIELDS)
        ):
            return False
        observed = {
            field: record[field] for field in _V6_IMMUTABLE_SCHEDULE_FIELDS
        }
        immutable_expected = {
            field: expected[field] for field in _V6_IMMUTABLE_SCHEDULE_FIELDS
        }
        return _json_exact(observed, immutable_expected)

    schedule_mismatch_indices = [
        index
        for index, (record, expected) in enumerate(
            zip(records, regenerated_schedule)
        )
        if not _matches_schedule_row(record, expected)
    ]
    if len(records) != len(regenerated_schedule):
        schedule_mismatch_indices.extend(
            range(
                min(len(records), len(regenerated_schedule)),
                max(len(records), len(regenerated_schedule)),
            )
        )
    exact_schedule = (
        regeneration_error is None and not schedule_mismatch_indices
    )
    immutable_schedule_field_checks = {
        field: len(records) == len(regenerated_schedule)
        and all(
            isinstance(record, Mapping)
            and field in record
            and field in expected
            and _json_exact(record[field], expected[field])
            for record, expected in zip(records, regenerated_schedule)
        )
        for field in _V6_IMMUTABLE_SCHEDULE_FIELDS
    }
    immutable_schedule_fields = (
        regeneration_error is None
        and bool(regenerated_schedule)
        and all(immutable_schedule_field_checks.values())
    )
    row_identity_fields = (
        "split",
        "triad_id",
        "scenario_index",
        "permutation_index",
    )
    schedule_row_order = (
        regeneration_error is None
        and len(records) == len(regenerated_schedule)
        and all(
            isinstance(record, Mapping)
            and all(
                field in record
                and _json_exact(record[field], expected[field])
                for field in row_identity_fields
            )
            for record, expected in zip(records, regenerated_schedule)
        )
    )

    def _selection_reconciled(
        record: Mapping[str, Any], expected: Mapping[str, Any]
    ) -> bool:
        if not isinstance(record, Mapping):
            return False
        raw_output = record.get("focal_output_raw")
        selected_slot = record.get("selected_slot")
        if (
            type(raw_output) is not str
            or raw_output not in {"1", "2", "3"}
            or type(selected_slot) is not int
        ):
            return False
        parsed = parse_controlled_choice(
            raw_output, "spontaneous", int(expected["generation_seed"])
        )
        if (
            parsed.selection_valid is not True
            or parsed.fallback_used is not False
            or selected_slot != parsed.selected_slot
        ):
            return False
        selected_candidates = [
            candidate
            for candidate in expected.get("candidates", [])
            if candidate.get("slot") == selected_slot
        ]
        if len(selected_candidates) != 1:
            return False
        selected = selected_candidates[0]
        return (
            record.get("selected_frame") == selected.get("frame")
            and record.get("selected_candidate_id") == selected.get("candidate_id")
            and record.get("selected_pool_candidate_id")
            == selected.get("pool_candidate_id")
        )

    selection_mismatch_indices = [
        index
        for index, (record, expected) in enumerate(
            zip(records, regenerated_schedule)
        )
        if not _selection_reconciled(record, expected)
    ]
    if len(records) != len(regenerated_schedule):
        selection_mismatch_indices.extend(
            range(
                min(len(records), len(regenerated_schedule)),
                max(len(records), len(regenerated_schedule)),
            )
        )

    def _prompt_reconciled(
        record: Mapping[str, Any], expected: Mapping[str, Any]
    ) -> bool:
        if not isinstance(record, Mapping):
            return False
        prompt = build_controlled_prompt(
            scenario=_scenario_proxy(expected["scenario"]),
            candidates=_message_candidates(expected),
            history=[],
            round_index=int(expected["round"]),
            n_rounds=24,
            show_history=False,
            focal_mode="spontaneous",
            context={},
        )
        return (
            record.get("focal_system_prompt") == prompt.system
            and record.get("focal_user_prompt") == prompt.user
        )

    prompt_mismatch_indices = [
        index
        for index, (record, expected) in enumerate(
            zip(records, regenerated_schedule)
        )
        if not _prompt_reconciled(record, expected)
    ]
    if len(records) != len(regenerated_schedule):
        prompt_mismatch_indices.extend(
            range(
                min(len(records), len(regenerated_schedule)),
                max(len(records), len(regenerated_schedule)),
            )
        )

    expected_manifest_schedule = {
        "seed": schedule_seed,
        "n_records": len(regenerated_schedule),
        "n_episode_blocks": None,
        "n_rounds": 24,
        "heldout_start_round": 19,
    }
    manifest_schedule_exact = regeneration_error is None and all(
        field in schedule_spec
        and _json_exact(schedule_spec[field], expected_value)
        for field, expected_value in expected_manifest_schedule.items()
    )

    frozen = manifest.get("frozen_protocol", {})
    frozen = frozen if isinstance(frozen, Mapping) else {}
    plan_audit = frozen.get("plan_audit", {})
    plan_audit = plan_audit if isinstance(plan_audit, Mapping) else {}
    provider = manifest.get("provider", {})
    provider = provider if isinstance(provider, Mapping) else {}
    record_mappings = all(isinstance(row, Mapping) for row in records)
    run_ids = (
        {str(row.get("run_id")) for row in records}
        if record_mappings
        else set()
    )
    checks = {
        "manifest_mapping": manifest_is_mapping,
        "nonempty": bool(records),
        "completed": manifest.get("run_status") == "completed",
        "task_version": manifest.get("task_version") == CONTROLLED_V6_VERSION,
        "calibration_version": manifest.get("calibration_version") == V6_CALIBRATION_VERSION,
        "mode": record_mappings
        and manifest.get("mode") == expected_mode
        and all(row.get("mode") == expected_mode for row in records),
        "target_absent": manifest.get("target_simulator_present") is False,
        "history_absent": manifest.get("history_present") is False,
        "bank_hash": record_mappings
        and manifest.get("pool_sha256") == bank.sha256()
        and manifest.get("bank_content_sha256")
        == bank_content_sha256(bank.payload)
        and all(row.get("pool_sha256") == bank.sha256() for row in records),
        "record_count": regeneration_error is None
        and manifest.get("n_records")
        == len(records)
        == schedule_spec.get("n_records")
        == len(regenerated_schedule),
        "manifest_schedule": manifest_schedule_exact,
        "schedule_row_order": schedule_row_order,
        "immutable_schedule_fields": immutable_schedule_fields,
        "exact_schedule": exact_schedule,
        "strict_outputs": record_mappings
        and all(
            row.get("selection_valid") is True
            and row.get("fallback_used") is False
            and type(row.get("focal_output_raw")) is str
            and row.get("focal_output_raw") in {"1", "2", "3"}
            for row in records
        ),
        "selection_reconciliation": regeneration_error is None
        and not selection_mismatch_indices,
        "prompt_reconciliation": regeneration_error is None
        and not prompt_mismatch_indices,
        "provider_constrained": provider.get("constrained_choices")
        == ["1", "2", "3"],
        "schedule_audit": schedule_audit["pass"],
        "frozen_protocol_audit": plan_audit.get("pass") is True,
        "run_id_consistent": len(run_ids) == 1
        and next(iter(run_ids), None) == str(manifest.get("run_id")),
    }
    return {
        "pass": all(checks.values()),
        "checks": checks,
        "schedule_audit": schedule_audit,
        "schedule_mismatch_indices": schedule_mismatch_indices,
        "immutable_schedule_field_checks": immutable_schedule_field_checks,
        "selection_mismatch_indices": selection_mismatch_indices,
        "prompt_mismatch_indices": prompt_mismatch_indices,
        "schedule_regeneration_error": regeneration_error,
        "n_records": len(records),
        "expected_mode": expected_mode,
    }


def _eligible_triads(
    bank: V6TriadBank,
    semantic_validation: Mapping[str, Any],
    quality_validation: Mapping[str, Any],
) -> set:
    for name, result in (
        ("semantic", semantic_validation),
        ("quality", quality_validation),
    ):
        if result.get("pass") is not True:
            raise ValueError("V6 %s validation did not pass" % name)
        if result.get("pool_sha256") != bank.sha256():
            raise ValueError("V6 %s validation pool hash mismatch" % name)
    semantic = {str(value) for value in semantic_validation.get("eligible_triad_ids", [])}
    quality = {str(value) for value in quality_validation.get("eligible_triad_ids", [])}
    eligible = semantic & quality
    if not eligible:
        raise ValueError("V6 validation contains no jointly eligible triads")
    return eligible


def _frame_summary(rows: Iterable[Mapping[str, Any]]) -> Dict[str, Any]:
    rows = list(rows)
    counts = Counter(str(row["selected_frame"]) for row in rows)
    shares = {
        frame: counts.get(frame, 0) / float(len(rows)) if rows else float("nan")
        for frame in STRATEGIES
    }
    return {
        "n": len(rows),
        "counts": dict(counts),
        "shares": shares,
        "gap": max(shares.values()) - min(shares.values()) if rows else float("nan"),
    }


def _passes(summary: Mapping[str, Any], thresholds: Mapping[str, float], cv: bool) -> bool:
    prefix = "cross_validation_" if cv else ""
    low = float(thresholds[prefix + "minimum_frame_share"])
    high = float(thresholds[prefix + "maximum_frame_share"])
    gap = float(thresholds[prefix + "maximum_frame_gap"])
    return bool(summary["n"]) and all(
        low <= float(value) <= high for value in summary["shares"].values()
    ) and float(summary["gap"]) <= gap


def _best_subset(
    rows: Sequence[Mapping[str, Any]],
    ids: Sequence[str],
    n_select: int,
    thresholds: Mapping[str, float],
    cv_thresholds: bool,
) -> Tuple[Tuple[str, ...], Dict[str, Any]]:
    best_objective = None
    best_choice: Optional[Tuple[str, ...]] = None
    best_summary: Optional[Dict[str, Any]] = None
    for chosen in itertools.combinations(sorted(ids), n_select):
        chosen_set = set(chosen)
        summary = _frame_summary(
            row for row in rows if str(row["triad_id"]) in chosen_set
        )
        passed = _passes(summary, thresholds, cv=cv_thresholds)
        distances = [
            abs(float(value) - 1.0 / 3.0)
            for value in summary["shares"].values()
        ]
        objective = (
            0 if passed else 1,
            float(summary["gap"]),
            max(distances),
            sum(distances),
            chosen,
        )
        if best_objective is None or objective < best_objective:
            best_objective = objective
            best_choice = chosen
            best_summary = {**summary, "pass": passed}
    assert best_choice is not None and best_summary is not None
    return best_choice, {
        "selected_triad_ids": list(best_choice),
        "summary": best_summary,
        "objective": {
            "fail_indicator": int(best_objective[0]),
            "frame_gap": float(best_objective[1]),
            "maximum_distance_from_one_third": float(best_objective[2]),
            "sum_distance_from_one_third": float(best_objective[3]),
            "lexical_tie_break": list(best_choice),
        },
    }


def _select_split(
    records: Sequence[Mapping[str, Any]],
    eligible_ids: set,
    split: str,
    n_select: int,
    thresholds: Mapping[str, float],
) -> Tuple[Optional[Tuple[str, ...]], Dict[str, Any]]:
    rows = [row for row in records if str(row["split"]) == split]
    by_triad: Dict[str, List[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        by_triad[str(row["triad_id"])].append(row)
    ids = sorted(set(by_triad) & eligible_ids)
    if len(ids) < n_select:
        raise ValueError("not enough jointly eligible V6 triads in %s" % split)
    expected_exposures = int(thresholds["minimum_triad_exposures"])
    if any(len(by_triad[triad_id]) < expected_exposures for triad_id in ids):
        raise ValueError("insufficient V6 triad calibration exposure in %s" % split)

    # Genuine cross-validation: each fold selects from the twelve training
    # scenarios, then evaluates that selected subset only on the untouched pair.
    folds: Dict[str, Dict[str, Any]] = {}
    for fold_index, heldout_pair in enumerate(V6_CALIBRATION_FOLDS):
        heldout = set(heldout_pair)
        train_rows = [
            row for row in rows if str(row["scenario"]["id"]) not in heldout
        ]
        test_rows = [
            row for row in rows if str(row["scenario"]["id"]) in heldout
        ]
        fold_choice, training = _best_subset(
            train_rows, ids, n_select, thresholds, cv_thresholds=False
        )
        fold_set = set(fold_choice)
        test_summary = _frame_summary(
            row for row in test_rows if str(row["triad_id"]) in fold_set
        )
        test_summary["pass"] = _passes(test_summary, thresholds, cv=True)
        fold_key = "fold_%02d" % fold_index
        folds[fold_key] = {
            "heldout_scenario_ids": list(heldout_pair),
            "training_scenario_ids": sorted(
                {str(row["scenario"]["id"]) for row in train_rows}
            ),
            "selected_on_training": training,
            "heldout_evaluation": test_summary,
            "no_heldout_rows_in_selection": not any(
                str(row["scenario"]["id"]) in heldout for row in train_rows
            ),
            "pass": bool(test_summary["pass"]),
        }
    cv_pass = all(fold["pass"] for fold in folds.values())
    final_choice, final_selection = _best_subset(
        rows, ids, n_select, thresholds, cv_thresholds=False
    )
    support_pass = bool(final_selection["summary"]["pass"] and cv_pass)
    payload = {
        "selected_triad_ids": list(final_choice),
        "aggregate": final_selection["summary"],
        "selection_objective": final_selection["objective"],
        "cross_validation": folds,
        "cross_validation_pass": cv_pass,
        "worst_heldout_pair_gap": max(
            float(fold["heldout_evaluation"]["gap"]) for fold in folds.values()
        ),
        "support_pass": support_pass,
    }
    return (final_choice if support_pass else None, payload)


def select_v6_bank(
    bank: V6TriadBank,
    calibration_records: Sequence[Mapping[str, Any]],
    semantic_validation: Mapping[str, Any],
    quality_validation: Mapping[str, Any],
    thresholds: Optional[Mapping[str, float]] = None,
) -> Tuple[Optional[Dict[str, Any]], Dict[str, Any]]:
    thresholds = dict(thresholds or CONTROLLED_V6_CALIBRATION_THRESHOLDS)
    eligible = _eligible_triads(bank, semantic_validation, quality_validation)
    selections: Dict[str, Optional[Tuple[str, ...]]] = {}
    metrics: Dict[str, Any] = {}
    for split, count_key in (
        ("development", "development_triads_selected"),
        ("heldout", "heldout_triads_selected"),
    ):
        selection, metric = _select_split(
            calibration_records,
            eligible,
            split,
            int(thresholds[count_key]),
            thresholds,
        )
        selections[split] = selection
        metrics[split] = metric
    semantic_hash = canonical_sha256(semantic_validation)
    quality_hash = canonical_sha256(quality_validation)
    support_pass = all(value is not None for value in selections.values())
    report: Dict[str, Any] = {
        "status": (
            "selected bank requires one separate target-free validation"
            if support_pass
            else "STOP: V6 calibration support gate failed"
        ),
        "support_pass": support_pass,
        "source_pool_sha256": bank.sha256(),
        "source_pool_content_sha256": bank_content_sha256(bank.payload),
        "semantic_validation_sha256": semantic_hash,
        "quality_validation_sha256": quality_hash,
        "jointly_eligible_triad_ids": sorted(eligible),
        "selection_metrics": metrics,
        "thresholds": thresholds,
    }
    if not support_pass:
        return None, report
    selected_splits: Dict[str, List[Dict[str, Any]]] = {}
    for split in ("development", "heldout"):
        wanted = set(selections[split] or ())
        selected_splits[split] = [
            json.loads(json.dumps(triad))
            for triad in _triads(bank, split)
            if str(triad["triad_id"]) in wanted
        ]
    output: Dict[str, Any] = {
        "pool_id": "%s-selected" % bank.payload["pool_id"],
        "status": "selected_bank_pending_no_history_validation",
        "candidate_text_authored_before_v6_focal_calibration": True,
        "source_pool_sha256": bank.sha256(),
        "source_pool_content_sha256": bank_content_sha256(bank.payload),
        "semantic_validation_sha256": semantic_hash,
        "quality_validation_sha256": quality_hash,
        "selection_method": (
            "whole-triad exhaustive subset search with seven two-scenario "
            "cross-validation folds and final selection on all calibration scenarios"
        ),
        "selection_thresholds": thresholds,
        "splits": selected_splits,
    }
    audit = audit_v6_bank_payload(output)
    if not audit["pass"]:
        raise RuntimeError("selected V6 bank failed structural audit")
    report["selected_bank_sha256"] = canonical_sha256(output)
    report["selected_bank_content_sha256"] = bank_content_sha256(output)
    return output, report


def evaluate_v6_bank_validation(
    records: Sequence[Mapping[str, Any]],
    bank: V6TriadBank,
    thresholds: Optional[Mapping[str, float]] = None,
) -> Dict[str, Any]:
    thresholds = dict(thresholds or CONTROLLED_V6_CALIBRATION_THRESHOLDS)
    records = list(records)
    if not records:
        raise ValueError("selected-bank validation records are empty")
    if any(row.get("pool_sha256") != bank.sha256() for row in records):
        raise ValueError("selected-bank validation hash mismatch")
    if any(not row.get("selection_valid") or row.get("fallback_used") for row in records):
        raise ValueError("selected-bank validation contains invalid or fallback choices")
    section_rows = {
        "overall": records,
        "development": [row for row in records if row["split"] == "development"],
        "heldout": [row for row in records if row["split"] == "heldout"],
    }
    sections: Dict[str, Dict[str, Any]] = {}
    for name, part in section_rows.items():
        summary = _frame_summary(part)
        summary["pass"] = _passes(summary, thresholds, cv=False)
        sections[name] = summary

    folds: Dict[str, Dict[str, Any]] = {}
    for fold_index, scenario_pair in enumerate(V6_VALIDATION_FOLDS):
        pair = set(scenario_pair)
        fold_sections: Dict[str, Any] = {}
        for name, part in section_rows.items():
            summary = _frame_summary(
                row for row in part if str(row["scenario"]["id"]) in pair
            )
            summary["pass"] = _passes(summary, thresholds, cv=True)
            fold_sections[name] = summary
        folds["fold_%02d" % fold_index] = {
            "scenario_ids": list(scenario_pair),
            "sections": fold_sections,
            "pass": all(summary["pass"] for summary in fold_sections.values()),
        }

    scenario_ids = sorted({str(row["scenario"]["id"]) for row in records})
    n_boot = int(thresholds["bootstrap_resamples"])
    confidence = float(thresholds["bootstrap_confidence"])
    bootstrap_seed = int(thresholds["bootstrap_seed"])
    generator = np.random.default_rng(
        derive_seed("v6_validation_bootstrap", bootstrap_seed, bank.sha256())
    )
    bootstrap: Dict[str, Any] = {}
    alpha = 1.0 - confidence
    for name, part in section_rows.items():
        by_scenario: Dict[str, List[Mapping[str, Any]]] = defaultdict(list)
        for row in part:
            by_scenario[str(row["scenario"]["id"])].append(row)
        share_draws = {frame: np.empty(n_boot, dtype=float) for frame in STRATEGIES}
        gap_draws = np.empty(n_boot, dtype=float)
        for index in range(n_boot):
            sampled = generator.choice(scenario_ids, size=len(scenario_ids), replace=True)
            summary = _frame_summary(
                row for scenario_id in sampled for row in by_scenario[str(scenario_id)]
            )
            for frame in STRATEGIES:
                share_draws[frame][index] = float(summary["shares"][frame])
            gap_draws[index] = float(summary["gap"])
        intervals = {
            frame: {
                "lo": float(np.quantile(values, alpha / 2.0)),
                "hi": float(np.quantile(values, 1.0 - alpha / 2.0)),
            }
            for frame, values in share_draws.items()
        }
        gap_quantile = float(np.quantile(gap_draws, confidence))
        passed = all(
            interval["lo"] >= float(thresholds["minimum_frame_share"])
            and interval["hi"] <= float(thresholds["maximum_frame_share"])
            for interval in intervals.values()
        ) and gap_quantile <= float(thresholds["maximum_frame_gap"])
        bootstrap[name] = {
            "n_resamples": n_boot,
            "confidence": confidence,
            "bootstrap_seed": bootstrap_seed,
            "cluster": "scenario_id",
            "frame_share_intervals": intervals,
            "gap_confidence_quantile": gap_quantile,
            "pass": bool(passed),
        }

    block_counts: Dict[Tuple[str, str], Counter] = defaultdict(Counter)
    for row in records:
        block_counts[(str(row["scenario"]["id"]), str(row["triad_id"]))][
            str(row["selected_frame"])
        ] += 1
    nontrivial_blocks = sum(
        max(counts.values(), default=0) >= 3 for counts in block_counts.values()
    )
    nontrivial_fraction = nontrivial_blocks / float(len(block_counts))
    anti_triviality = {
        "definition": "a scenario-by-triad block selects one frame in at least three of six slot permutations",
        "n_blocks": len(block_counts),
        "n_nontrivial_blocks": nontrivial_blocks,
        "fraction": nontrivial_fraction,
        "minimum_fraction": float(thresholds["minimum_nontrivial_block_fraction"]),
        "pass": nontrivial_fraction
        >= float(thresholds["minimum_nontrivial_block_fraction"]),
    }
    overall_pass = (
        all(section["pass"] for section in sections.values())
        and all(fold["pass"] for fold in folds.values())
        and all(section["pass"] for section in bootstrap.values())
        and anti_triviality["pass"]
    )
    return {
        "pass": bool(overall_pass),
        "status": "selected-bank target-free independent validation",
        "bank_sha256": bank.sha256(),
        "bank_content_sha256": bank_content_sha256(bank.payload),
        "thresholds": thresholds,
        "sections": sections,
        "validation_scenario_pair_folds": folds,
        "scenario_cluster_bootstrap": bootstrap,
        "anti_triviality": anti_triviality,
    }


def finalize_validated_v6_bank(
    pending_payload: Mapping[str, Any], validation: Mapping[str, Any]
) -> Dict[str, Any]:
    pending = json.loads(json.dumps(pending_payload))
    pending_hash = canonical_sha256(pending)
    if validation.get("pass") is not True:
        raise ValueError("cannot finalize a V6 bank whose validation failed")
    if validation.get("bank_sha256") != pending_hash:
        raise ValueError("V6 validation does not refer to this pending bank")
    if validation.get("bank_content_sha256") != bank_content_sha256(pending):
        raise ValueError("V6 validation candidate content hash mismatch")
    pending["status"] = "selected_bank_validated"
    pending["no_history_validation"] = {
        "pending_bank_sha256": pending_hash,
        "validation_sha256": canonical_sha256(validation),
        "sections": validation["sections"],
        "thresholds": validation["thresholds"],
    }
    audit = audit_v6_bank_payload(pending)
    if not audit["pass"]:
        raise RuntimeError("finalized V6 bank failed structural audit")
    return pending
