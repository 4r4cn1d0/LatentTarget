"""Linear probes for the focal model's belief about the hidden target type.

The question this module exists to answer is **not** "is target type linearly
represented" -- almost everything is, and a probe that only shows that is the
generic result Neel's doc explicitly warns about. The question is:

    After the target silently changes, does the model's DECODABLE BELIEF update
    at the same rate as its BEHAVIOUR?

Three outcomes, all reportable:

* probe leads behaviour  -> the model registers the change but keeps using the
  stale strategy. A sticky-policy result, and a monitoring story: you could
  detect the stale user model before the behaviour reveals it.
* behaviour leads probe  -> the adaptation is model-free (win-stay/lose-shift)
  and there is no latent user model doing the work. A clean negative.
* they move together     -> consistent with a belief that drives the policy, but
  underdetermined; say so.

Everything is numpy-only and episode-grouped. **Splits are by episode, never by
round** -- rounds inside an episode share a prompt prefix and an activation
neighbourhood, so a row-wise split leaks the answer and inflates accuracy.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

from config import STRATEGIES


# --------------------------------------------------------------------------
# Activation storage
# --------------------------------------------------------------------------


@dataclass
class ActivationStore:
    """Activations plus the row metadata needed to join them to the JSONL log.

    ``acts`` has shape ``[n_rows, n_layers, d_model]`` and is stored as float16
    on disk. ``meta`` is a list of dicts, one per row, aligned by index.
    """

    acts: np.ndarray
    meta: List[Dict[str, Any]]
    layers: List[int] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.acts.shape[0] != len(self.meta):
            raise ValueError(
                "acts has %d rows but meta has %d" % (self.acts.shape[0], len(self.meta))
            )
        if not self.layers:
            self.layers = list(range(self.acts.shape[1]))

    @property
    def n_rows(self) -> int:
        return int(self.acts.shape[0])

    @property
    def n_layers(self) -> int:
        return int(self.acts.shape[1])

    @property
    def d_model(self) -> int:
        return int(self.acts.shape[2])

    def layer(self, layer_index: int) -> np.ndarray:
        return np.asarray(self.acts[:, layer_index, :], dtype=np.float64)

    def key(self, i: int) -> Tuple[str, int]:
        return (str(self.meta[i]["episode_id"]), int(self.meta[i]["round"]))

    def save(self, path: str) -> str:
        parent = os.path.dirname(path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        np.savez_compressed(
            path, acts=self.acts.astype(np.float16), layers=np.asarray(self.layers)
        )
        with open(path + ".meta.jsonl", "w", encoding="utf-8") as fh:
            for m in self.meta:
                fh.write(json.dumps(m) + "\n")
        return path

    @classmethod
    def load(cls, path: str) -> "ActivationStore":
        z = np.load(path)
        meta: List[Dict[str, Any]] = []
        with open(path + ".meta.jsonl", "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    meta.append(json.loads(line))
        return cls(acts=z["acts"], meta=meta, layers=list(z["layers"].tolist()))


def align_to_log(store: ActivationStore, df) -> np.ndarray:
    """Row indices into ``df`` for each activation row, or -1 if not found.

    Fails loudly rather than silently dropping: a mismatch here would quietly
    train the probe on misaligned labels, which is the single easiest way to
    manufacture a fake result.
    """
    index: Dict[Tuple[str, int], int] = {}
    for i, (eid, r) in enumerate(zip(df["episode_id"], df["round"])):
        index[(str(eid), int(r))] = i
    out = np.array([index.get(store.key(i), -1) for i in range(store.n_rows)], dtype=int)
    n_missing = int((out < 0).sum())
    if n_missing:
        raise ValueError(
            "%d of %d activation rows have no matching (episode_id, round) in the log. "
            "The activation capture and the run log have diverged; do not train on this."
            % (n_missing, store.n_rows)
        )
    return out


# --------------------------------------------------------------------------
# Multinomial logistic probe
# --------------------------------------------------------------------------


def _softmax(z: np.ndarray) -> np.ndarray:
    z = z - z.max(axis=1, keepdims=True)
    e = np.exp(z)
    return e / e.sum(axis=1, keepdims=True)


@dataclass
class Probe:
    W: np.ndarray            # [d, K]
    b: np.ndarray            # [K]
    mu: np.ndarray           # [d] training-set feature mean
    sigma: np.ndarray        # [d] training-set feature sd
    classes: List[str]
    l2: float
    n_train: int
    converged: bool

    def decision(self, X: np.ndarray) -> np.ndarray:
        # errstate: numpy 2.x on macOS/Accelerate emits spurious FP warnings
        # from `matmul`. Nothing here divides; sigma is clamped away from 0.
        with np.errstate(divide="ignore", over="ignore", invalid="ignore"):
            Xs = (np.asarray(X, dtype=np.float64) - self.mu) / self.sigma
            return Xs @ self.W + self.b

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        return _softmax(self.decision(X))

    def predict(self, X: np.ndarray) -> np.ndarray:
        return np.array([self.classes[i] for i in self.predict_proba(X).argmax(axis=1)], dtype=object)

    def save(self, path: str) -> str:
        """Persist the fitted readout and its training standardiser.

        Steering and held-out evaluation must use exactly the probe that was
        selected during training.  Saving only ``W`` is insufficient because
        the feature standardisation is part of the fitted model.
        """
        parent = os.path.dirname(path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        np.savez_compressed(
            path,
            W=self.W,
            b=self.b,
            mu=self.mu,
            sigma=self.sigma,
            classes=np.asarray(self.classes, dtype=str),
            l2=np.asarray([self.l2], dtype=float),
            n_train=np.asarray([self.n_train], dtype=int),
            converged=np.asarray([self.converged], dtype=bool),
        )
        return path

    @classmethod
    def load(cls, path: str) -> "Probe":
        # All arrays are numeric or fixed-width Unicode; pickle is deliberately
        # disabled so loading a probe cannot execute code from an untrusted NPZ.
        z = np.load(path, allow_pickle=False)
        return cls(
            W=z["W"], b=z["b"], mu=z["mu"], sigma=z["sigma"],
            classes=[str(x) for x in z["classes"].tolist()],
            l2=float(z["l2"][0]), n_train=int(z["n_train"][0]),
            converged=bool(z["converged"][0]),
        )


def fit_probe(
    X: np.ndarray,
    y: Sequence[str],
    classes: Optional[Sequence[str]] = None,
    l2: float = 1.0,
    lr: float = 0.05,
    max_iter: int = 2000,
    tol: float = 1e-7,
    seed: int = 0,
) -> Probe:
    """L2-regularised multinomial logistic regression, Adam, full batch.

    Features are standardised using training statistics only (stored on the
    probe, reapplied at predict time) -- otherwise the test set leaks through
    the scaler, which is a real and easy mistake with n << d.
    """
    X = np.asarray(X, dtype=np.float64)
    classes = list(classes) if classes is not None else sorted(set(y))
    idx = {c: i for i, c in enumerate(classes)}
    Y = np.zeros((len(y), len(classes)))
    for i, label in enumerate(y):
        Y[i, idx[label]] = 1.0

    mu = X.mean(axis=0)
    sigma = X.std(axis=0)
    sigma[sigma < 1e-8] = 1.0
    Xs = (X - mu) / sigma

    n, d = Xs.shape
    K = len(classes)
    rng = np.random.default_rng(seed)
    W = rng.normal(0, 0.01, size=(d, K))
    b = np.zeros(K)
    mW = np.zeros_like(W); vW = np.zeros_like(W)
    mb = np.zeros_like(b); vb = np.zeros_like(b)
    beta1, beta2, eps = 0.9, 0.999, 1e-8
    prev_loss = np.inf
    converged = False

    # See Probe.decision for why errstate is needed (spurious Accelerate warnings).
    err = np.errstate(divide="ignore", over="ignore", invalid="ignore")
    err.__enter__()
    for t in range(1, max_iter + 1):
        P = _softmax(Xs @ W + b)
        loss = -np.sum(Y * np.log(np.clip(P, 1e-12, 1.0))) / n + l2 * np.sum(W * W) / (2 * n)
        gW = Xs.T @ (P - Y) / n + l2 * W / n
        gb = (P - Y).sum(axis=0) / n
        for g, m, v, p in ((gW, mW, vW, W), (gb, mb, vb, b)):
            m *= beta1; m += (1 - beta1) * g
            v *= beta2; v += (1 - beta2) * (g * g)
            p -= lr * (m / (1 - beta1 ** t)) / (np.sqrt(v / (1 - beta2 ** t)) + eps)
        if abs(prev_loss - loss) < tol:
            converged = True
            break
        prev_loss = loss
    err.__exit__(None, None, None)

    return Probe(W=W, b=b, mu=mu, sigma=sigma, classes=classes, l2=l2,
                 n_train=n, converged=converged)


# --------------------------------------------------------------------------
# Episode-grouped evaluation
# --------------------------------------------------------------------------


def grouped_folds(groups: Sequence, n_folds: int = 5, seed: int = 0) -> List[np.ndarray]:
    """Fold assignment by GROUP (episode), not by row."""
    uniq = sorted(set(map(str, groups)))
    rng = np.random.default_rng(seed)
    assign = {g: i % n_folds for i, g in enumerate(rng.permutation(uniq))}
    g = np.asarray([assign[str(x)] for x in groups])
    return [np.where(g == k)[0] for k in range(n_folds)]


def stratified_episode_split(
    y: Sequence[str],
    groups: Sequence,
    train_fraction: float = 0.50,
    dev_fraction: float = 0.25,
    seed: int = 0,
) -> Dict[str, np.ndarray]:
    """Deterministic train/dev/test split, stratified by episode label.

    Every episode must have one label.  Splitting is done at episode level and
    each target type contributes to all three partitions.  The untouched test
    partition prevents layer and regularisation selection from inflating the
    quoted probe accuracy.
    """
    if not 0 < train_fraction < 1 or not 0 < dev_fraction < 1:
        raise ValueError("train_fraction and dev_fraction must be in (0, 1)")
    if train_fraction + dev_fraction >= 1:
        raise ValueError("train_fraction + dev_fraction must be < 1")
    y_arr = np.asarray(list(y), dtype=object)
    g_arr = np.asarray([str(x) for x in groups], dtype=object)
    if len(y_arr) != len(g_arr):
        raise ValueError("y and groups must have equal length")

    episode_labels: Dict[str, str] = {}
    for episode in sorted(set(g_arr.tolist())):
        labels = sorted(set(str(x) for x in y_arr[g_arr == episode]))
        if len(labels) != 1:
            raise ValueError("episode %r has multiple labels: %s" % (episode, labels))
        episode_labels[episode] = labels[0]

    rng = np.random.default_rng(seed)
    split_eps: Dict[str, List[str]] = {"train": [], "dev": [], "test": []}
    for label in sorted(set(episode_labels.values())):
        episodes = np.asarray(
            sorted(e for e, value in episode_labels.items() if value == label),
            dtype=object,
        )
        if len(episodes) < 4:
            raise ValueError(
                "need at least 4 episodes per class for train/dev/test; %r has %d"
                % (label, len(episodes))
            )
        episodes = rng.permutation(episodes)
        n_train = max(1, int(np.floor(len(episodes) * train_fraction)))
        n_dev = max(1, int(np.floor(len(episodes) * dev_fraction)))
        if n_train + n_dev >= len(episodes):
            n_train = len(episodes) - 2
            n_dev = 1
        split_eps["train"].extend(str(x) for x in episodes[:n_train])
        split_eps["dev"].extend(str(x) for x in episodes[n_train:n_train + n_dev])
        split_eps["test"].extend(str(x) for x in episodes[n_train + n_dev:])

    result = {
        name: np.where(np.isin(g_arr, np.asarray(episodes, dtype=object)))[0]
        for name, episodes in split_eps.items()
    }
    episode_sets = [set(g_arr[idx].tolist()) for idx in result.values()]
    if any(episode_sets[i] & episode_sets[j] for i in range(3) for j in range(i + 1, 3)):
        raise AssertionError("episode split overlap")
    return result


@dataclass
class ProbeResult:
    layer: int
    accuracy: float
    per_class_accuracy: Dict[str, float]
    n_test: int
    n_train: int
    confusion: Dict[str, Dict[str, int]]

    def as_dict(self) -> Dict[str, Any]:
        return {
            "layer": self.layer, "accuracy": self.accuracy,
            "per_class_accuracy": self.per_class_accuracy,
            "n_test": self.n_test, "n_train": self.n_train, "confusion": self.confusion,
        }


def evaluate_probe(
    probe: Probe, X: np.ndarray, y: Sequence[str], layer: int = -1
) -> ProbeResult:
    """Evaluate an already-fitted probe on a specified held-out set."""
    y_arr = np.asarray(list(y), dtype=object)
    pred = probe.predict(X)
    classes = list(probe.classes)
    per_class: Dict[str, float] = {}
    confusion = {a: {b: 0 for b in classes} for a in classes}
    for c in classes:
        mask = y_arr == c
        per_class[c] = float(np.mean(pred[mask] == c)) if mask.any() else float("nan")
    for truth, guess in zip(y_arr, pred):
        if truth in confusion and guess in confusion[truth]:
            confusion[truth][guess] += 1
    return ProbeResult(
        layer=layer,
        accuracy=float(np.mean(pred == y_arr)) if len(y_arr) else float("nan"),
        per_class_accuracy=per_class,
        n_test=len(y_arr),
        n_train=probe.n_train,
        confusion=confusion,
    )


def nearest_centroid_accuracy(
    X_train: np.ndarray,
    y_train: Sequence[str],
    X_dev: np.ndarray,
    y_dev: Sequence[str],
    classes: Optional[Sequence[str]] = None,
) -> float:
    """Cheap, fixed readout used only to choose a candidate layer.

    This keeps the layer sweep practical for 5k-dimensional residual streams.
    Logistic-probe regularisation is tuned only after this independent layer
    selection step, and final accuracy is reported on untouched test episodes.
    """
    classes = list(classes) if classes is not None else sorted(set(y_train))
    X_train = np.asarray(X_train, dtype=np.float64)
    X_dev = np.asarray(X_dev, dtype=np.float64)
    y_train = np.asarray(list(y_train), dtype=object)
    y_dev = np.asarray(list(y_dev), dtype=object)
    mu = X_train.mean(axis=0)
    sigma = X_train.std(axis=0)
    sigma[sigma < 1e-8] = 1.0
    tr = (X_train - mu) / sigma
    dv = (X_dev - mu) / sigma
    centroids = np.stack([tr[y_train == c].mean(axis=0) for c in classes])
    distances = ((dv[:, None, :] - centroids[None, :, :]) ** 2).sum(axis=2)
    pred = np.asarray([classes[i] for i in distances.argmin(axis=1)], dtype=object)
    return float(np.mean(pred == y_dev))


def cross_val_probe(
    X: np.ndarray,
    y: Sequence[str],
    groups: Sequence,
    layer: int = -1,
    n_folds: int = 5,
    l2: float = 1.0,
    seed: int = 0,
    classes: Optional[Sequence[str]] = None,
) -> ProbeResult:
    """Episode-grouped cross-validated accuracy for one layer."""
    y = np.asarray(list(y), dtype=object)
    classes = list(classes) if classes is not None else sorted(set(y.tolist()))
    folds = grouped_folds(groups, n_folds=n_folds, seed=seed)
    preds = np.empty(len(y), dtype=object)
    n_train_total = 0
    for test_idx in folds:
        train_idx = np.setdiff1d(np.arange(len(y)), test_idx)
        if len(train_idx) == 0 or len(test_idx) == 0:
            continue
        probe = fit_probe(X[train_idx], y[train_idx], classes=classes, l2=l2, seed=seed)
        preds[test_idx] = probe.predict(X[test_idx])
        n_train_total += len(train_idx)
    scored = np.array([p is not None for p in preds])
    acc = float(np.mean(preds[scored] == y[scored])) if scored.any() else float("nan")
    per_class = {}
    for c in classes:
        m = scored & (y == c)
        per_class[c] = float(np.mean(preds[m] == c)) if m.any() else float("nan")
    conf = {a: {b: 0 for b in classes} for a in classes}
    for t, p in zip(y[scored], preds[scored]):
        if t in conf and p in conf[t]:
            conf[t][p] += 1
    return ProbeResult(
        layer=layer, accuracy=acc, per_class_accuracy=per_class,
        n_test=int(scored.sum()), n_train=n_train_total // max(1, len(folds)), confusion=conf,
    )


def layer_sweep(
    store: ActivationStore,
    y: Sequence[str],
    groups: Sequence,
    n_folds: int = 5,
    l2: float = 1.0,
    seed: int = 0,
    layers: Optional[Sequence[int]] = None,
) -> List[ProbeResult]:
    """Cross-validated probe accuracy at each layer."""
    out: List[ProbeResult] = []
    for li in (layers if layers is not None else range(store.n_layers)):
        res = cross_val_probe(store.layer(li), y, groups, layer=store.layers[li],
                              n_folds=n_folds, l2=l2, seed=seed)
        out.append(res)
    return out


def select_l2(
    X: np.ndarray,
    y: Sequence[str],
    groups: Sequence,
    grid: Sequence[float] = (0.01, 0.1, 1.0, 10.0, 100.0, 1000.0),
    n_folds: int = 5,
    seed: int = 0,
) -> Tuple[float, List[Dict[str, Any]]]:
    """Pick the L2 strength by episode-grouped CV.

    With d_model ~ 4096 and only a few hundred rows, the regularisation
    strength changes the answer a lot, so it must be chosen rather than
    assumed -- and chosen on grouped folds, or the choice itself leaks.
    Returns ``(best_l2, table)``; report the whole table, not just the winner.
    """
    table: List[Dict[str, Any]] = []
    for l2 in grid:
        res = cross_val_probe(X, y, groups, n_folds=n_folds, l2=float(l2), seed=seed)
        table.append({"l2": float(l2), "accuracy": res.accuracy})
    best = max(table, key=lambda t: t["accuracy"])["l2"]
    return best, table


# --------------------------------------------------------------------------
# Baselines
# --------------------------------------------------------------------------


def majority_baseline(y: Sequence[str]) -> float:
    y = list(y)
    if not y:
        return float("nan")
    return max(y.count(c) for c in set(y)) / len(y)


def shuffled_label_baseline(
    X: np.ndarray, y: Sequence[str], groups: Sequence, n_repeats: int = 5,
    n_folds: int = 5, l2: float = 1.0, seed: int = 0,
) -> Dict[str, float]:
    """Permute labels BY EPISODE and re-run. Tests the fitting procedure.

    Permuting by episode rather than by row preserves the within-episode label
    structure, so this is a strictly harder null than row-wise shuffling.
    """
    y = np.asarray(list(y), dtype=object)
    g = np.asarray([str(x) for x in groups], dtype=object)
    uniq = sorted(set(g.tolist()))
    ep_label = {e: y[g == e][0] for e in uniq}
    accs = []
    for r in range(n_repeats):
        rng = np.random.default_rng(seed + r)
        permuted = list(rng.permutation([ep_label[e] for e in uniq]))
        mapping = dict(zip(uniq, permuted))
        y_perm = np.asarray([mapping[e] for e in g], dtype=object)
        accs.append(cross_val_probe(X, y_perm, g, n_folds=n_folds, l2=l2, seed=seed).accuracy)
    return {"mean": float(np.mean(accs)), "sd": float(np.std(accs)), "n_repeats": n_repeats,
            "accuracies": [float(a) for a in accs]}


def behavioural_readout_features(df) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Build start-of-round features from the visible transcript only."""
    rows, labels, groups = [], [], []
    for eid, g in df.groupby("episode_id", sort=True):
        g = g.sort_values("round")
        used = {s: 0.0 for s in STRATEGIES}
        wins = {s: 0.0 for s in STRATEGIES}
        for _, row in g.iterrows():
            rows.append(
                [used[s] for s in STRATEGIES]
                + [wins[s] for s in STRATEGIES]
                + [float(row["round"])]
            )
            labels.append(str(row["hidden_target_type"]))
            groups.append(str(eid))
            s = str(row["primary_strategy"])
            if s in used:
                used[s] += 1.0
                if str(row["displayed_choice"]) == "A":
                    wins[s] += 1.0
    return (
        np.asarray(rows, dtype=np.float64),
        np.asarray(labels, dtype=object),
        np.asarray(groups, dtype=object),
    )


def behavioural_readout_baseline(
    df, n_folds: int = 5, seed: int = 0, classes: Optional[Sequence[str]] = None
) -> ProbeResult:
    """Predict the hidden type from the VISIBLE transcript alone.

    Features per round: how many times each frame has been used so far, and how
    many times each frame was followed by Option A. This is what a careful
    reader of the transcript could work out without any model internals.

    **The probe is only interesting if it beats this.** Otherwise it is reading
    the model's own output history back to us, which is a much weaker claim.
    """
    classes = list(classes) if classes is not None else list(STRATEGIES)
    X, labels, groups = behavioural_readout_features(df)
    return cross_val_probe(X, labels, groups, layer=-1, n_folds=n_folds, l2=0.1,
                           seed=seed, classes=classes)


# --------------------------------------------------------------------------
# The headline analysis: probe vs behaviour across the swap
# --------------------------------------------------------------------------


def probe_belief_trajectory(
    probe: Probe, store: ActivationStore, layer_index: int, df, log_rows: np.ndarray
) -> "Any":
    """Per-round probe prediction and posterior, joined to the log.

    ``log_rows`` comes from :func:`align_to_log`.
    """
    import pandas as pd

    X = store.layer(layer_index)
    proba = probe.predict_proba(X)
    pred = np.array([probe.classes[i] for i in proba.argmax(axis=1)], dtype=object)
    sub = df.iloc[log_rows].reset_index(drop=True)
    out = sub[[
        "episode_id", "round", "condition", "hidden_target_type",
        "initial_target_type", "final_target_type", "swap_condition",
        "rounds_since_swap", "primary_strategy",
    ]].copy()
    out["probe_pred"] = pred
    for k, c in enumerate(probe.classes):
        out["probe_p_" + c] = proba[:, k]
    out["probe_matches_active"] = (out["probe_pred"] == out["hidden_target_type"]).astype(int)
    out["probe_matches_initial"] = (out["probe_pred"] == out["initial_target_type"]).astype(int)
    out["probe_matches_final"] = (out["probe_pred"] == out["final_target_type"]).astype(int)
    out["behaviour_matches_final"] = (out["primary_strategy"] == out["final_target_type"]).astype(int)
    out["behaviour_matches_initial"] = (out["primary_strategy"] == out["initial_target_type"]).astype(int)
    out["probe_p_final"] = [
        float(out.iloc[i]["probe_p_" + str(out.iloc[i]["final_target_type"])])
        if ("probe_p_" + str(out.iloc[i]["final_target_type"])) in out.columns else np.nan
        for i in range(len(out))
    ]
    return out


def trajectory_gap(traj, n_boot: int = 5000, seed: int = 0) -> Dict[str, Any]:
    """**Primary statistic.** Baseline-corrected rise of probe vs behaviour.

    For each channel c in {probe, behaviour}::

        base_c    = P(says NEW type) averaged over PRE-swap rounds
        delta_c(k)= P(says NEW at rounds_since_swap = k) - base_c
        statistic = mean over k>0 of [delta_probe(k) - delta_behaviour(k)]

    Positive => the probe's belief rises towards the new target faster than the
    messages do.

    This replaces first-crossing ("rounds until it first matches") as the
    headline. First-crossing has two defects that this does not:

    1. it is biased downwards by noise -- a chance-level 3-class predictor
       "first matches" at ~2.3 of 5 rounds, so a probe carrying no information
       appears to lead a behaviour that flips at round 3 by +0.74 rounds;
    2. it conflates "flipped early" with "was accurate the whole time", and it
       silently drops episodes that never flip, which censors exactly the
       slowest cases and biases the estimate towards zero.

    Baseline correction matters because the two channels have different
    accuracy floors: the probe may sit near 100% while the behaviour sits near
    1/3, and an uncorrected comparison would be dominated by that offset rather
    than by the dynamics.

    Uncertainty is a bootstrap over EPISODES, not rounds.
    """
    sw = traj[traj["swap_condition"] & traj["rounds_since_swap"].notna()].copy()
    if sw.empty:
        return {"n_swap_episodes": 0}
    sw["rounds_since_swap"] = sw["rounds_since_swap"].astype(int)

    def statistic(frame) -> float:
        pre = frame[frame["rounds_since_swap"] <= 0]
        post = frame[frame["rounds_since_swap"] > 0]
        if pre.empty or post.empty:
            return float("nan")
        base_p = float(pre["probe_matches_final"].mean())
        base_b = float(pre["behaviour_matches_final"].mean())
        gaps = []
        for k, g in post.groupby("rounds_since_swap"):
            gaps.append((float(g["probe_matches_final"].mean()) - base_p)
                        - (float(g["behaviour_matches_final"].mean()) - base_b))
        return float(np.mean(gaps)) if gaps else float("nan")

    observed = statistic(sw)
    episodes = sorted(sw["episode_id"].unique())
    by_ep = {e: sw[sw["episode_id"] == e] for e in episodes}
    rng = np.random.default_rng(seed)
    import pandas as pd
    boots = []
    for _ in range(n_boot):
        pick = rng.integers(0, len(episodes), len(episodes))
        boots.append(statistic(pd.concat([by_ep[episodes[i]] for i in pick])))
    boots = np.asarray([b for b in boots if np.isfinite(b)])
    lo, hi = (np.quantile(boots, [0.025, 0.975]) if boots.size else (np.nan, np.nan))
    pre = sw[sw["rounds_since_swap"] <= 0]
    return {
        "statistic": observed,
        "ci95": [float(lo), float(hi)],
        "n_swap_episodes": len(episodes),
        "n_boot": int(boots.size),
        "probe_pre_swap_baseline": float(pre["probe_matches_final"].mean()) if not pre.empty else None,
        "behaviour_pre_swap_baseline": float(pre["behaviour_matches_final"].mean()) if not pre.empty else None,
        "interpretation": (
            "positive and CI excluding 0 => the decodable belief tracks the new "
            "target faster than the messages do; negative => the behaviour leads, "
            "which argues against a latent model driving the policy; CI spanning 0 "
            "=> underdetermined, and that is the finding."
        ),
    }


def _first_flip(flags: Sequence[int]) -> Optional[int]:
    for i, v in enumerate(flags, start=1):
        if v:
            return i
    return None


def null_lag_difference(traj, n_perm: int = 2000, seed: int = 0) -> Dict[str, Any]:
    """Calibrate the lag difference against a timing-free null.

    **Why this is not optional.** "First round at which the prediction matches
    the new type" is biased downwards by noise: a 3-class predictor that is
    right at chance still hits the new type early sometimes, so it appears to
    "flip" at ~2.3 rounds. Against a behaviour that flips deterministically at
    round 3, a probe carrying ZERO information produces an apparent lead of
    +0.74 rounds, and a naive bootstrap CI excludes zero ~70% of the time.
    (Simulation: `docs/REVIEW.md`.) Reporting the raw difference would
    manufacture the headline result out of probe noise.

    The null permutes the probe's post-swap predictions **within each episode**,
    preserving that episode's marginal accuracy exactly while destroying any
    timing information. The reportable quantity is
    ``observed_difference - null_difference``, with a permutation p-value.
    """
    sw = traj[traj["swap_condition"] & traj["rounds_since_swap"].notna()].copy()
    sw = sw[sw["rounds_since_swap"] > 0]
    if sw.empty:
        return {"n_swap_episodes": 0}

    episodes = []
    for eid, g in sw.groupby("episode_id"):
        g = g.sort_values("rounds_since_swap")
        episodes.append((np.asarray(g["probe_matches_final"].values, dtype=int),
                         np.asarray(g["behaviour_matches_final"].values, dtype=int)))

    def diff(probe_flags_list) -> Optional[float]:
        ds = []
        for pf, bf in zip(probe_flags_list, [b for _, b in episodes]):
            p, b = _first_flip(pf), _first_flip(bf)
            if p is not None and b is not None:
                ds.append(b - p)
        return float(np.mean(ds)) if ds else None

    observed = diff([p for p, _ in episodes])
    rng = np.random.default_rng(seed)
    null = []
    for _ in range(n_perm):
        null.append(diff([rng.permutation(p) for p, _ in episodes]))
    null = [x for x in null if x is not None]
    if observed is None or not null:
        return {"n_swap_episodes": len(episodes), "note": "too few flips to calibrate"}
    null_mean = float(np.mean(null))
    p_val = (sum(1 for x in null if x >= observed) + 1) / (len(null) + 1)
    return {
        "observed_difference": observed,
        "null_difference": null_mean,
        "null_sd": float(np.std(null)),
        "calibrated_difference": observed - null_mean,
        "p_value_one_sided": p_val,
        "n_perm": len(null),
        "note": (
            "calibrated_difference is the reportable quantity. The raw "
            "observed_difference is inflated by probe noise and must not be "
            "quoted on its own."
        ),
    }


def switch_lag(traj, seed: int = 0, n_boot: int = 5000) -> Dict[str, Any]:
    """Per-episode: rounds after the swap until probe / behaviour first flip.

    Episodes that never flip within the horizon are reported separately rather
    than imputed -- coding them as the horizon would shrink the lag towards
    zero and coding them as missing would drop the slowest cases, and both
    would bias the comparison we care about.
    """
    import pandas as pd

    sw = traj[traj["swap_condition"] & traj["rounds_since_swap"].notna()].copy()
    sw = sw[sw["rounds_since_swap"] > 0]
    rows = []
    for eid, g in sw.groupby("episode_id"):
        g = g.sort_values("rounds_since_swap")
        pm = g[g["probe_matches_final"] == 1]["rounds_since_swap"]
        bm = g[g["behaviour_matches_final"] == 1]["rounds_since_swap"]
        rows.append({
            "episode_id": eid,
            "probe_lag": int(pm.min()) if len(pm) else None,
            "behaviour_lag": int(bm.min()) if len(bm) else None,
            "n_post_rounds": int(len(g)),
        })
    per_ep = pd.DataFrame(rows)
    both = per_ep.dropna(subset=["probe_lag", "behaviour_lag"])
    out: Dict[str, Any] = {
        "n_swap_episodes": int(len(per_ep)),
        "n_probe_never_flipped": int(per_ep["probe_lag"].isna().sum()),
        "n_behaviour_never_flipped": int(per_ep["behaviour_lag"].isna().sum()),
        "n_both_flipped": int(len(both)),
        "per_episode": per_ep.to_dict(orient="records"),
    }
    if len(both) >= 2:
        d = (both["behaviour_lag"] - both["probe_lag"]).values.astype(float)
        rng = np.random.default_rng(seed)
        boots = np.array([rng.choice(d, size=len(d), replace=True).mean() for _ in range(n_boot)])
        lo, hi = np.quantile(boots, [0.025, 0.975])
        out.update({
            "mean_probe_lag": float(both["probe_lag"].mean()),
            "mean_behaviour_lag": float(both["behaviour_lag"].mean()),
            "mean_behaviour_minus_probe": float(d.mean()),
            "ci95": [float(lo), float(hi)],
            "interpretation": (
                "RAW difference -- inflated by probe noise, do NOT quote alone. "
                "Use null_calibration below. Positive (after calibration) => the "
                "probe flips BEFORE the behaviour (model registers the change while "
                "still using the stale strategy); negative => behaviour leads, "
                "consistent with model-free updating; CI/p spanning 0 => "
                "underdetermined, say so."
            ),
        })
    out["null_calibration"] = null_lag_difference(traj, seed=seed)
    return out


def context_leakage_check(probe: Probe, store: ActivationStore, layer_index: int, df,
                          log_rows: np.ndarray) -> Dict[str, Any]:
    """Is the probe reading the target, or just the outcome string in the prompt?

    In ``shuffled_history`` episodes the visible history belongs to a DIFFERENT
    target than the one actually responding. If the probe predicts the donor's
    type, it is decoding the context, not a belief about the current target --
    a weaker and different claim.
    """
    traj = probe_belief_trajectory(probe, store, layer_index, df, log_rows)
    sub = df.iloc[log_rows].reset_index(drop=True)
    traj = traj.copy()
    traj["history_source_episode_id"] = sub["history_source_episode_id"].values
    sh = traj[traj["condition"] == "shuffled_history"]
    if sh.empty:
        return {"n": 0, "note": "no shuffled_history episodes in this run"}
    donor_type = sh["history_source_episode_id"].astype(str).str.rsplit("-", n=1).str[-1]
    return {
        "n": int(len(sh)),
        "accuracy_vs_true_target": float(np.mean(sh["probe_pred"].values == sh["hidden_target_type"].values)),
        "accuracy_vs_donor_type": float(np.mean(sh["probe_pred"].values == donor_type.values)),
        "note": (
            "If accuracy_vs_donor_type >> accuracy_vs_true_target the probe is "
            "decoding the visible outcome history rather than a belief about the "
            "target that is actually responding."
        ),
    }


# --------------------------------------------------------------------------
# Plots
# --------------------------------------------------------------------------


def plot_layer_sweep(results: List[ProbeResult], path: str, baselines: Optional[Dict[str, float]] = None) -> str:
    """Probe accuracy against layer depth, with the baselines drawn on top.

    A sweep that never rises above the behavioural-readout line means the probe
    is not adding anything over reading the visible transcript.
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(6.4, 3.8), dpi=150)
    xs = [r.layer for r in results]
    ax.plot(xs, [r.accuracy for r in results], marker="o", ms=4, lw=1.6,
            color="#1f77b4", label="linear probe")
    styles = {"chance": ("--", "grey"), "majority": (":", "grey"),
              "shuffled labels": ("-.", "#d62728"), "behavioural readout": ("--", "#2ca02c"),
              "just ask the model": (":", "#9467bd")}
    for name, val in (baselines or {}).items():
        if val is None or not np.isfinite(val):
            continue
        ls, c = styles.get(name, ("--", "#888888"))
        ax.axhline(val, ls=ls, lw=1.2, color=c, label="%s (%.2f)" % (name, val))
    ax.set_ylim(0, 1)
    ax.set_xlabel("layer", fontsize=9)
    ax.set_ylabel("episode-grouped CV accuracy", fontsize=9)
    ax.set_title("Decoding the hidden target type from the residual stream", fontsize=11)
    ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
    ax.grid(alpha=0.25, linewidth=0.5); ax.tick_params(labelsize=8)
    ax.legend(fontsize=7, frameon=False, loc="upper left", bbox_to_anchor=(1.01, 1.0))
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return path


def plot_probe_vs_behaviour(traj, path: str, n_boot: int = 2000, seed: int = 0) -> str:
    """THE headline figure: does the internal belief update before the behaviour?"""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    from .stats_utils import cluster_bootstrap_mean

    sw = traj[traj["swap_condition"] & traj["rounds_since_swap"].notna()].copy()
    fig, ax = plt.subplots(figsize=(6.4, 4.0), dpi=150)
    if not sw.empty:
        sw["rounds_since_swap"] = sw["rounds_since_swap"].astype(int)
        for col, colour, label, marker in (
            ("probe_matches_final", "#1f77b4", "probe says NEW type", "o"),
            ("behaviour_matches_final", "#ff7f0e", "message uses NEW frame", "s"),
        ):
            xs, ms, los, his = [], [], [], []
            for x, g in sw.groupby("rounds_since_swap"):
                ci = cluster_bootstrap_mean(g[col].values, g["episode_id"].values,
                                            n_boot=n_boot, seed=seed)
                xs.append(x); ms.append(ci.mean); los.append(ci.lo); his.append(ci.hi)
            ax.plot(xs, ms, marker=marker, ms=4, lw=1.7, color=colour, label=label)
            ax.fill_between(xs, los, his, alpha=0.13, color=colour, linewidth=0)
    ax.axvline(0.5, ls="--", lw=1.2, color="black")
    ax.text(0.62, 0.94, "silent swap", fontsize=8)
    ax.axhline(1.0 / len(STRATEGIES), ls=":", lw=1.0, color="grey")
    ax.set_ylim(0, 1)
    ax.set_xlabel("rounds since swap", fontsize=9)
    ax.set_ylabel("P(identifies the NEW target type)", fontsize=9)
    ax.set_title("Internal belief vs. behaviour after a silent target swap", fontsize=11)
    ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
    ax.grid(alpha=0.25, linewidth=0.5); ax.tick_params(labelsize=8)
    ax.legend(fontsize=7.5, frameon=False, loc="lower right")
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    return path
