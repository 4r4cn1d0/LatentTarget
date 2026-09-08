"""One prespecified approximate interval, not a distribution free guarantee.

The independent unit is a whole bundle. Strata have fixed population weights
equal to their allocation fractions. At least six bundles per stratum are
required by this screen. Zero sample variance gives a point interval.
"""
from functools import lru_cache
import math

import numpy as np


@lru_cache(maxsize=64)
def t_critical(df, alpha=.05):
    """Two sided Student critical value by Gauss Legendre integration.

    Restricted to the numerical range validated for this offline screen.
    """
    if type(df) is not int or not 5 <= df <= 10000 or not .001 <= alpha <= .2:
        raise ValueError("requires integer df 5..10000 and alpha .001..0.2")
    nodes, weights = np.polynomial.legendre.leggauss(96)
    constant = math.exp(math.lgamma((df+1)/2)-math.lgamma(df/2)) / math.sqrt(df*math.pi)
    def mass(x):
        t = x*(nodes+1)/2
        return x/2 * np.dot(weights, constant*np.exp(-(df+1)/2*np.log1p(t*t/df)))
    low, high = 0., 16.
    target = .5-alpha/2
    if mass(high) < target:
        raise ArithmeticError("critical value outside validated integration bracket")
    for _ in range(60):
        middle = (low+high)/2
        if mass(middle) < target:
            low = middle
        else:
            high = middle
    return (low+high)/2


def variance_components(values, strata):
    x = np.asarray(values, dtype=float)
    if x.ndim == 1:
        x = x[None, :]
    strata = np.asarray(strata)
    if x.ndim != 2 or not x.shape[1] or strata.shape != (x.shape[1],) or not np.isfinite(x).all():
        raise ValueError("finite study by bundle values and aligned strata required")
    if strata.dtype.kind not in "iu":
        raise ValueError("strata must be integer labels")
    variance = np.zeros(len(x)); bootstrap_variance = np.zeros(len(x))
    sizes = []
    for label in np.unique(strata):
        sample = x[:, strata == label]
        m = sample.shape[1]
        if m < 6:
            raise ValueError("screen requires at least six bundles per stratum")
        sizes.append(m)
        # Translation preserves sample variance and makes a constant sample
        # exactly zero even when its decimal value is not binary representable.
        centred = sample-sample[:, :1]
        contribution = (m/x.shape[1])**2 * centred.var(axis=1, ddof=1)/m
        variance += contribution
        bootstrap_variance += contribution*(m-1)/m
    return {"mean": x.mean(1), "variance": variance,
            "empirical_bootstrap_variance": bootstrap_variance,
            "df": min(sizes)-1, "zero_variance": variance == 0}


def stratified_interval(values, strata, alpha=.05):
    info = variance_components(values, strata)
    half = t_critical(info["df"], alpha)*np.sqrt(info["variance"])
    # No clipping: also supports paired text differences with support [-2, 2].
    return np.stack([info["mean"]-half, info["mean"]+half], axis=1)


def repaired_decision(lower, upper, strata, validity):
    """Original complete gate; only the interval construction is replaced."""
    lower, upper, validity = map(np.asarray, (lower, upper, validity))
    if lower.shape != upper.shape or lower.ndim != 3 or lower.shape[-1] != 6 or not np.isfinite(lower).all() or not np.isfinite(upper).all() or (lower > upper+1e-10).any() or (lower < -1-1e-10).any() or (upper > 1+1e-10).any():
        raise ValueError("invalid contrast bounds")
    if validity.shape != (len(lower), 5) or not np.isfinite(validity).all() or (validity < 0).any() or (validity > 1).any():
        raise ValueError("invalid branch validity")
    lows, highs = [], []
    for j in (0, 1, 3, 4, 5):
        alpha = .025 if j < 2 else .05
        a = stratified_interval(lower[:, :, j], strata, alpha)
        b = a if np.array_equal(lower[:, :, j], upper[:, :, j]) else stratified_interval(upper[:, :, j], strata, alpha)
        lows.append(a); highs.append(b)
    lows, highs = np.stack(lows, axis=1), np.stack(highs, axis=1)
    means = lower.mean(1)
    positive = lows[:, :2, 0] > 1e-12
    primary = positive & (means[:, :2] >= .1-1e-12)
    controls = (lows[:, 2:, 0] >= -.1-1e-12) & (highs[:, 2:, 1] <= .1+1e-12)
    valid = (validity >= .98-1e-12).all(1)
    return {"mean_lower": means, "mean_upper": upper.mean(1),
            "ci_lower_bounds": lows, "ci_upper_bounds": highs,
            "positive_primary": positive, "primary_pass": primary,
            "two_sided_primary_rejection": (lows[:, :2, 0] > 1e-12) | (highs[:, :2, 1] < -1e-12),
            "control_pass": controls, "validity_pass": valid,
            "joint_pass": primary.all(1) & controls.all(1) & valid}
