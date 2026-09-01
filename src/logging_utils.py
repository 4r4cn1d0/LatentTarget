"""JSONL logging for experiment records, plus run manifests.

One record per (episode, round).  Nothing is aggregated or filtered at write
time: every message, every prompt and every probability is stored so that the
analysis can be re-run, audited, and re-classified without re-querying any
model.  There is no code path anywhere in this project that drops or selects
episodes -- that is a deliberate guard against cherry-picking.
"""

from __future__ import annotations

import json
import os
import platform
import subprocess
import sys
import time
from typing import Any, Callable, Dict, Iterable, Iterator, List, Optional

#: Fields every record must carry.  Checked by ``validate_record`` and by
#: ``tests/test_experiment.py``.
REQUIRED_FIELDS = (
    "experiment_id",
    "run_id",
    "condition",
    "episode_id",
    "episode_index",
    "round",
    "n_rounds",
    "hidden_target_type",          # type ACTIVE this round
    "initial_target_type",
    "final_target_type",
    "swap_condition",              # bool: does this episode ever swap?
    "swap_round",                  # int or None
    "swap_has_occurred",           # bool: has the swap already happened by now?
    "rounds_since_swap",           # int or None
    "target_mode",                 # "typed" | "random"
    "history_mode",
    "scenario_id",
    "scenario",
    "focal_system_prompt",
    "focal_user_prompt",
    "focal_message_raw",
    "focal_message",
    "visible_history",
    "history_source_episode_id",
    "strategy_scores",
    "primary_strategy",
    "strategy_confidence",
    "classifier_name",
    "target_scores",
    "target_p_a",
    "target_p_a_noiseless",
    "target_logit",
    "target_choice",
    "episode_seed",
    "round_seed",
    "master_seed",
    "model_name",
    "provider",
    "timestamp",
)


def validate_record(record: Dict[str, Any]) -> None:
    missing = [f for f in REQUIRED_FIELDS if f not in record]
    if missing:
        raise ValueError("log record is missing required fields: %s" % ", ".join(missing))


class JsonlWriter:
    """Append-only JSONL writer that flushes after every record."""

    def __init__(
        self,
        path: str,
        validate: bool = True,
        validator: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> None:
        self.path = path
        self.validate = validate
        self.validator = validator or validate_record
        parent = os.path.dirname(path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        self._fh = open(path, "a", encoding="utf-8")
        self.n_written = 0

    def write(self, record: Dict[str, Any]) -> None:
        if self.validate:
            self.validator(record)
        self._fh.write(json.dumps(record, ensure_ascii=False, default=_json_default) + "\n")
        self._fh.flush()
        self.n_written += 1

    def close(self) -> None:
        try:
            self._fh.close()
        except Exception:  # pragma: no cover
            pass

    def __enter__(self) -> "JsonlWriter":
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()


def _json_default(obj: Any) -> Any:
    if hasattr(obj, "as_dict"):
        return obj.as_dict()
    if hasattr(obj, "item"):  # numpy scalars
        try:
            return obj.item()
        except Exception:  # pragma: no cover
            pass
    return str(obj)


def read_jsonl(path: str) -> Iterator[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                yield json.loads(line)


def load_records(paths: Iterable[str]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for p in paths:
        out.extend(read_jsonl(p))
    return out


def _git_commit() -> Optional[str]:
    try:
        return (
            subprocess.check_output(
                ["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL
            )
            .decode()
            .strip()
        )
    except Exception:
        return None


def write_manifest(path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Write a run manifest next to the data and return it."""
    manifest = dict(payload)
    manifest.update(
        {
            "written_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "python": sys.version,
            "platform": platform.platform(),
            "git_commit": _git_commit(),
        }
    )
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2, ensure_ascii=False, default=_json_default)
    return manifest
