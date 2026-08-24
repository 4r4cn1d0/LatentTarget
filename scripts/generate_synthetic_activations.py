#!/usr/bin/env python3
"""Generate labelled synthetic activations to validate the probe pipeline.

This is an oracle engineering fixture, never scientific evidence. One middle
layer receives a strong target-class direction; every episode also receives a
nuisance vector so episode-grouped splitting remains necessary.
"""

from __future__ import annotations

import _bootstrap  # noqa: F401
import argparse
import sys

import numpy as np

from config import STRATEGIES
from src.analysis import load_dataframe
from src.logging_utils import write_manifest
from src.probing import ActivationStore


def generate(log_path: str, out_path: str, d_model: int = 64,
             n_layers: int = 5, seed: int = 0) -> ActivationStore:
    if d_model < len(STRATEGIES) or n_layers < 3:
        raise ValueError("need d_model >= 3 and n_layers >= 3")
    df = load_dataframe(log_path)
    rng = np.random.default_rng(seed)
    raw_dirs = rng.normal(size=(len(STRATEGIES), d_model))
    directions = np.linalg.qr(raw_dirs.T)[0].T
    strengths = np.linspace(0.25, 1.0, n_layers)
    signal_layer = n_layers // 2
    strengths[signal_layer] = 5.0
    episode_nuisance = {
        str(episode): rng.normal(0, 0.4, size=d_model)
        for episode in df["episode_id"].unique()
    }
    acts = []
    meta = []
    for _, row in df.iterrows():
        cls = STRATEGIES.index(str(row["hidden_target_type"]))
        base = episode_nuisance[str(row["episode_id"])]
        layers = []
        for strength in strengths:
            layers.append(
                base + strength * directions[cls] + rng.normal(0, 0.5, size=d_model)
            )
        acts.append(np.stack(layers))
        meta.append({
            "episode_id": str(row["episode_id"]),
            "round": int(row["round"]),
            "run_id": str(row["run_id"]),
            "synthetic_oracle_activation": True,
        })
    store = ActivationStore(np.asarray(acts, dtype=np.float16), meta)
    store.save(out_path)
    write_manifest(out_path + ".manifest.json", {
        "kind": "synthetic_oracle_activations",
        "source_log": log_path,
        "shape": list(store.acts.shape),
        "signal_layer_index": signal_layer,
        "d_model": d_model,
        "n_layers": n_layers,
        "seed": seed,
        "warning": "Pipeline fixture only; not a real model result.",
    })
    return store


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log", required=True)
    parser.add_argument("--out", default="data/processed/synthetic_activations.npz")
    parser.add_argument("--d-model", type=int, default=64)
    parser.add_argument("--layers", type=int, default=5)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args(argv)
    store = generate(args.log, args.out, args.d_model, args.layers, args.seed)
    print("wrote synthetic-only activations %s with shape %s" %
          (args.out, tuple(store.acts.shape)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
