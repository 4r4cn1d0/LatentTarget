"""Paired analysis for probe-direction steering generations."""

from __future__ import annotations

from typing import Any, Dict, List

import numpy as np
import pandas as pd

from .logging_utils import read_jsonl
from .stats_utils import cluster_bootstrap_mean


def load_steering_dataframe(path: str) -> pd.DataFrame:
    rows = list(read_jsonl(path))
    if not rows:
        raise ValueError("steering log is empty")
    df = pd.DataFrame(rows)
    df["intended_score"] = [
        float(row["strategy_classification"].get(row["steer_target"], 0.0))
        for row in rows
    ]
    df["intended_primary"] = [
        int(row["strategy_classification"].get("primary_strategy") == row["steer_target"])
        for row in rows
    ]
    df["unit"] = [
        "%s|%s|%s|%s" % (
            row["source_episode_id"], row["source_round"],
            row["steer_target"], row["coefficient"],
        )
        for row in rows
    ]
    if df.duplicated(["unit", "intervention"]).any():
        raise ValueError("duplicate steering unit/intervention rows")
    return df


def paired_steering_summary(df: pd.DataFrame, n_boot: int = 5000, seed: int = 0) -> List[Dict[str, Any]]:
    required = {"zero", "target", "opposite", "random"}
    rows: List[Dict[str, Any]] = []
    for coefficient, group in df.groupby("coefficient", sort=True):
        for metric in ("intended_score", "intended_primary"):
            wide = group.pivot(index="unit", columns="intervention", values=metric)
            missing = required - set(wide.columns)
            if missing:
                raise ValueError("coefficient %s lacks controls: %s" % (coefficient, sorted(missing)))
            wide = wide.dropna(subset=sorted(required))
            episode = group.drop_duplicates("unit").set_index("unit")["source_episode_id"]
            for comparator in ("zero", "random", "opposite"):
                diff = wide["target"] - wide[comparator]
                ci = cluster_bootstrap_mean(
                    diff.values, episode.loc[diff.index].values,
                    n_boot=n_boot, seed=seed,
                )
                rows.append({
                    "coefficient": float(coefficient),
                    "metric": metric,
                    "contrast": "target_minus_" + comparator,
                    "mean_difference": ci.mean,
                    "ci_lo": ci.lo,
                    "ci_hi": ci.hi,
                    "n_units": ci.n,
                    "n_source_episodes": ci.n_clusters,
                })
    return rows
