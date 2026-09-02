"""Prospective matched-bundle randomization for controlled-choice V6.

The allocation is a deterministic function of the frozen randomization seed,
family code, and episode-seed index.  It is nevertheless a genuine
prospective random assignment because the seed and algorithm are frozen before
any focal-model outcome is generated.  A single coin is used for each whole
episode-seed bundle, so the three stable targets and six ordered swap
transitions are never treated as independent randomized units.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List, Mapping

import numpy as np

from config import (
    CONTROLLED_V6_RANDOMIZATION_RNG,
    CONTROLLED_V6_RANDOMIZATION_SEED,
)


V6_HISTORY_FAMILY = "history_access"
V6_SWAP_FAMILY = "target_regime"
V6_RANDOMIZATION_FAMILY_CODES: Mapping[str, int] = {
    V6_HISTORY_FAMILY: 0,
    V6_SWAP_FAMILY: 1,
}
V6_RUN_ORDER_FAMILY_CODE = 2


def _canonical_sha256(payload: Any) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def v6_allocation_bit(
    family: str,
    episode_index: int,
    *,
    seed: int = CONTROLLED_V6_RANDOMIZATION_SEED,
) -> int:
    """Return the prospectively frozen treated slot (0 or 1)."""
    if family not in V6_RANDOMIZATION_FAMILY_CODES:
        raise ValueError("unknown V6 randomization family %r" % family)
    if type(episode_index) is not int or episode_index < 0:
        raise ValueError("episode_index must be a non-negative integer")
    if type(seed) is not int or seed < 0:
        raise ValueError("randomization seed must be a non-negative integer")
    sequence = np.random.SeedSequence(
        [seed, V6_RANDOMIZATION_FAMILY_CODES[family], episode_index]
    )
    generator = np.random.Generator(np.random.PCG64DXSM(sequence))
    return int(generator.integers(0, 2))


def v6_allocation_schedule(
    n_episode_seeds: int,
    *,
    seed: int = CONTROLLED_V6_RANDOMIZATION_SEED,
) -> Dict[str, Any]:
    """Return the complete allocation table and its canonical identity."""
    if type(n_episode_seeds) is not int or n_episode_seeds < 1:
        raise ValueError("n_episode_seeds must be a positive integer")
    rows: List[Dict[str, int]] = []
    for episode_index in range(n_episode_seeds):
        rows.append(
            {
                "episode_index": episode_index,
                "history_treated_slot": v6_allocation_bit(
                    V6_HISTORY_FAMILY, episode_index, seed=seed
                ),
                "swap_treated_slot": v6_allocation_bit(
                    V6_SWAP_FAMILY, episode_index, seed=seed
                ),
            }
        )
    payload: Dict[str, Any] = {
        "schema_version": "controlled-v6-randomization-1.0",
        "rng": CONTROLLED_V6_RANDOMIZATION_RNG,
        "seed": seed,
        "unit": "episode-seed bundle",
        "families": {
            V6_HISTORY_FAMILY: {
                "code": V6_RANDOMIZATION_FAMILY_CODES[V6_HISTORY_FAMILY],
                "treated_regime": "full_history",
                "control_regime": "no_history",
                "trajectories_per_slot": 3,
            },
            V6_SWAP_FAMILY: {
                "code": V6_RANDOMIZATION_FAMILY_CODES[V6_SWAP_FAMILY],
                "treated_regime": "swap",
                "control_regime": "swap_control",
                "trajectories_per_slot": 6,
            },
        },
        "rows": rows,
    }
    payload["schedule_sha256"] = _canonical_sha256(payload)
    return payload


def audit_v6_allocation_schedule(payload: Mapping[str, Any]) -> Dict[str, Any]:
    """Replay one serialized schedule exactly and fail closed on additions."""
    expected_keys = {
        "schema_version",
        "rng",
        "seed",
        "unit",
        "families",
        "rows",
        "schedule_sha256",
    }
    rows = payload.get("rows")
    seed = payload.get("seed")
    shape_ok = (
        set(payload) == expected_keys
        and type(seed) is int
        and type(rows) is list
        and bool(rows)
        and all(
            type(row) is dict
            and set(row)
            == {"episode_index", "history_treated_slot", "swap_treated_slot"}
            for row in rows
        )
    )
    expected: Dict[str, Any] = {}
    if shape_ok:
        try:
            expected = v6_allocation_schedule(len(rows), seed=seed)
        except (TypeError, ValueError):
            shape_ok = False
    checks = {
        "exact_schema": shape_ok,
        "rng_exact": payload.get("rng") == CONTROLLED_V6_RANDOMIZATION_RNG,
        "seed_exact": seed == CONTROLLED_V6_RANDOMIZATION_SEED,
        "table_exact": bool(shape_ok) and dict(payload) == expected,
    }
    return {
        "pass": all(checks.values()),
        "checks": checks,
        "expected": expected if shape_ok else {},
    }


def v6_regime_assignment(
    condition: str,
    episode_index: int,
    *,
    seed: int = CONTROLLED_V6_RANDOMIZATION_SEED,
) -> Dict[str, Any]:
    """Map a V6 condition to its frozen family and physical pair slot."""
    if condition in {"full_history", "no_history"}:
        family = V6_HISTORY_FAMILY
        treated = condition == "full_history"
    elif condition in {"swap", "swap_control"}:
        family = V6_SWAP_FAMILY
        treated = condition == "swap"
    else:
        return {
            "pair_family": None,
            "pair_id": None,
            "pair_slot": None,
            "allocation_bit": None,
            "assigned_regime": condition,
        }
    bit = v6_allocation_bit(family, episode_index, seed=seed)
    slot = bit if treated else 1 - bit
    return {
        "pair_family": family,
        "pair_id": "%s-%03d" % (family, episode_index),
        "pair_slot": slot,
        "allocation_bit": bit,
        "assigned_regime": condition,
    }
