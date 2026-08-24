"""Small, dependency-light statistics helpers.

Everything here is numpy-only on purpose: no ``statsmodels``, no ``scipy``, so
the project runs anywhere.  The methods are deliberately plain --- bootstrap
confidence intervals, permutation tests, and a logistic regression with
cluster-robust standard errors.  Nothing fancier is justified by the design.

**Clustering matters.**  Rounds within an episode are not independent (the
agent's round-5 message depends on its round-4 message).  Every interval and
test here therefore resamples or permutes at the *episode* level, never at the
row level.  Row-level bootstrapping would produce intervals roughly
``sqrt(n_rounds)`` times too narrow.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np


# --------------------------------------------------------------------------
# Confidence intervals
# --------------------------------------------------------------------------


def wilson_ci(successes: int, n: int, z: float = 1.96) -> Tuple[float, float]:
    """Wilson score interval for a proportion (ignores clustering)."""
    if n == 0:
        return (float("nan"), float("nan"))
    p = successes / n
    denom = 1.0 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = (z / denom) * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (max(0.0, centre - half), min(1.0, centre + half))


@dataclass(frozen=True)
class MeanCI:
    mean: float
    lo: float
    hi: float
    n: int
    n_clusters: int

    def as_dict(self) -> Dict[str, float]:
        return {
            "mean": self.mean,
            "ci_lo": self.lo,
            "ci_hi": self.hi,
            "n": self.n,
            "n_clusters": self.n_clusters,
        }


def cluster_bootstrap_mean(
    values: Sequence[float],
    clusters: Sequence,
    n_boot: int = 2000,
    alpha: float = 0.05,
    seed: int = 0,
) -> MeanCI:
    """Percentile bootstrap CI for a mean, resampling whole clusters.

    ``clusters`` is a parallel sequence of cluster labels (episode ids).
    """
    v = np.asarray(values, dtype=float)
    if v.size == 0:
        return MeanCI(float("nan"), float("nan"), float("nan"), 0, 0)
    labels = np.asarray(clusters)
    uniq, inverse = np.unique(labels, return_inverse=True)
    by_cluster: List[np.ndarray] = [v[inverse == i] for i in range(len(uniq))]
    rng = np.random.default_rng(seed)
    means = np.empty(n_boot, dtype=float)
    n_clusters = len(uniq)
    for b in range(n_boot):
        idx = rng.integers(0, n_clusters, size=n_clusters)
        sample = np.concatenate([by_cluster[i] for i in idx])
        means[b] = sample.mean()
    lo, hi = np.quantile(means, [alpha / 2.0, 1.0 - alpha / 2.0])
    return MeanCI(float(v.mean()), float(lo), float(hi), int(v.size), n_clusters)


# --------------------------------------------------------------------------
# Permutation tests
# --------------------------------------------------------------------------


def _ols_slope(x: np.ndarray, y: np.ndarray) -> float:
    xm = x - x.mean()
    denom = float((xm * xm).sum())
    if denom == 0.0:
        return float("nan")
    return float((xm * (y - y.mean())).sum() / denom)


def permutation_slope_test(
    rounds: Sequence[float],
    outcomes: Sequence[float],
    clusters: Sequence,
    n_perm: int = 5000,
    seed: int = 0,
) -> Dict[str, float]:
    """Test H0: outcome does not trend with round.

    The null is built by permuting the round labels *within each episode*.  That
    destroys any round-order relationship while preserving each episode's set of
    outcomes and its overall rate, so it cannot be passed by between-episode
    differences alone.  One-sided (alternative: positive slope).
    """
    x = np.asarray(rounds, dtype=float)
    y = np.asarray(outcomes, dtype=float)
    labels = np.asarray(clusters)
    observed = _ols_slope(x, y)
    uniq = np.unique(labels)
    index_by_cluster = [np.where(labels == u)[0] for u in uniq]
    rng = np.random.default_rng(seed)
    count = 0
    null = np.empty(n_perm, dtype=float)
    for b in range(n_perm):
        xp = x.copy()
        for idx in index_by_cluster:
            xp[idx] = rng.permutation(x[idx])
        s = _ols_slope(xp, y)
        null[b] = s
        if s >= observed:
            count += 1
    return {
        "observed_slope": observed,
        "p_value_one_sided": (count + 1) / (n_perm + 1),
        "null_mean": float(np.nanmean(null)),
        "null_sd": float(np.nanstd(null)),
        "n_perm": n_perm,
    }


def permutation_type_test(
    primary_strategy: Sequence[str],
    hidden_type_by_episode: Dict,
    episode_of_row: Sequence,
    n_perm: int = 5000,
    seed: int = 0,
) -> Dict[str, float]:
    """Test H0: the agent's chosen strategy is independent of the hidden type.

    The statistic is the overall match rate.  The null shuffles the *episode ->
    hidden type* assignment, which preserves the agent's strategy sequences
    exactly and only breaks their alignment with the targets.  This is the test
    that distinguishes "the agent picks a strategy and sticks to it" (match rate
    unchanged under shuffling) from "the agent picks the right strategy for this
    target".
    """
    strategies = np.asarray(primary_strategy, dtype=object)
    episodes = np.asarray(episode_of_row, dtype=object)
    ep_ids = list(hidden_type_by_episode.keys())
    types = [hidden_type_by_episode[e] for e in ep_ids]

    def match_rate(type_map: Dict) -> float:
        truth = np.asarray([type_map[e] for e in episodes], dtype=object)
        return float(np.mean(strategies == truth))

    observed = match_rate(hidden_type_by_episode)
    rng = np.random.default_rng(seed)
    count = 0
    for _ in range(n_perm):
        permuted = list(rng.permutation(types))
        type_map = dict(zip(ep_ids, permuted))
        if match_rate(type_map) >= observed:
            count += 1
    return {
        "observed_match_rate": observed,
        "p_value_one_sided": (count + 1) / (n_perm + 1),
        "n_perm": n_perm,
    }


# --------------------------------------------------------------------------
# Logistic regression with cluster-robust SEs
# --------------------------------------------------------------------------


def _norm_sf(z: float) -> float:
    return 0.5 * math.erfc(z / math.sqrt(2.0))


@dataclass
class LogitFit:
    names: List[str]
    coef: np.ndarray
    se: np.ndarray
    z: np.ndarray
    p: np.ndarray
    n: int
    n_clusters: int
    converged: bool
    log_likelihood: float

    def to_rows(self) -> List[Dict[str, object]]:
        return [
            {
                "term": self.names[i],
                "coef": float(self.coef[i]),
                "se": float(self.se[i]),
                "z": float(self.z[i]),
                "p": float(self.p[i]),
                "odds_ratio": float(math.exp(self.coef[i])),
            }
            for i in range(len(self.names))
        ]

    def summary(self) -> str:
        lines = [
            "logistic regression  n=%d  clusters=%d  logLik=%.2f  converged=%s"
            % (self.n, self.n_clusters, self.log_likelihood, self.converged),
            "%-28s %9s %9s %8s %9s" % ("term", "coef", "se", "z", "p"),
        ]
        for row in self.to_rows():
            lines.append(
                "%-28s %9.4f %9.4f %8.2f %9.4g"
                % (row["term"], row["coef"], row["se"], row["z"], row["p"])
            )
        return "\n".join(lines)


def logistic_regression(
    X: np.ndarray,
    y: np.ndarray,
    names: Sequence[str],
    clusters: Optional[Sequence] = None,
    max_iter: int = 100,
    tol: float = 1e-9,
    ridge: float = 1e-8,
) -> LogitFit:
    """IRLS logistic regression with optional cluster-robust (sandwich) SEs.

    ``X`` must already include an intercept column if one is wanted.
    """
    # numpy 2.x on macOS/Accelerate raises spurious FP warnings from `matmul`
    # ("divide by zero encountered in matmul"), which are noise here: the
    # arithmetic below cannot divide, and `w` is clipped away from 0.
    with np.errstate(divide="ignore", over="ignore", invalid="ignore"):
        return _logistic_regression_impl(X, y, names, clusters, max_iter, tol, ridge)


def _logistic_regression_impl(X, y, names, clusters, max_iter, tol, ridge) -> LogitFit:
    X = np.asarray(X, dtype=float)
    y = np.asarray(y, dtype=float)
    n, k = X.shape
    beta = np.zeros(k)
    converged = False
    for _ in range(max_iter):
        eta = X @ beta
        mu = 1.0 / (1.0 + np.exp(-np.clip(eta, -35, 35)))
        w = np.clip(mu * (1.0 - mu), 1e-10, None)
        z = eta + (y - mu) / w
        XtW = X.T * w
        A = XtW @ X + ridge * np.eye(k)
        try:
            new_beta = np.linalg.solve(A, XtW @ z)
        except np.linalg.LinAlgError:  # pragma: no cover
            new_beta = np.linalg.lstsq(A, XtW @ z, rcond=None)[0]
        if np.max(np.abs(new_beta - beta)) < tol:
            beta = new_beta
            converged = True
            break
        beta = new_beta

    eta = X @ beta
    mu = 1.0 / (1.0 + np.exp(-np.clip(eta, -35, 35)))
    w = np.clip(mu * (1.0 - mu), 1e-10, None)
    bread = np.linalg.pinv((X.T * w) @ X + ridge * np.eye(k))
    resid = (y - mu)[:, None] * X
    if clusters is None:
        meat = resid.T @ resid
    else:
        labels = np.asarray(clusters)
        meat = np.zeros((k, k))
        for u in np.unique(labels):
            s = resid[labels == u].sum(axis=0)[:, None]
            meat += s @ s.T
    V = bread @ meat @ bread
    se = np.sqrt(np.clip(np.diag(V), 0.0, None))
    with np.errstate(divide="ignore", invalid="ignore"):
        zstat = np.where(se > 0, beta / se, np.nan)
    p = np.array([2.0 * _norm_sf(abs(t)) if np.isfinite(t) else float("nan") for t in zstat])
    eps = 1e-12
    ll = float(np.sum(y * np.log(np.clip(mu, eps, 1)) + (1 - y) * np.log(np.clip(1 - mu, eps, 1))))
    n_clusters = int(len(np.unique(np.asarray(clusters)))) if clusters is not None else n
    return LogitFit(
        names=list(names),
        coef=beta,
        se=se,
        z=zstat,
        p=p,
        n=n,
        n_clusters=n_clusters,
        converged=converged,
        log_likelihood=ll,
    )


def design_matrix(
    columns: Dict[str, Sequence[float]], intercept: bool = True
) -> Tuple[np.ndarray, List[str]]:
    """Assemble a design matrix from a dict of named columns."""
    names: List[str] = []
    cols: List[np.ndarray] = []
    n = len(next(iter(columns.values()))) if columns else 0
    if intercept:
        names.append("intercept")
        cols.append(np.ones(n))
    for name, values in columns.items():
        names.append(name)
        cols.append(np.asarray(values, dtype=float))
    return np.column_stack(cols) if cols else np.zeros((0, 0)), names


def dummies(values: Sequence[str], levels: Iterable[str], prefix: str) -> Dict[str, np.ndarray]:
    """One-hot columns for all but the first level (treatment coding)."""
    levels = list(levels)
    out: Dict[str, np.ndarray] = {}
    arr = np.asarray(values, dtype=object)
    for lev in levels[1:]:
        out["%s[%s]" % (prefix, lev)] = (arr == lev).astype(float)
    return out
