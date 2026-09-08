"""Bundle level analysis. No normality assumption and no dropped missing cells.

The exact distribution here is the EMPIRICAL bootstrap distribution, not exact
population coverage. It is calibrated prospectively by the offline screen.
"""
from __future__ import annotations

import numpy as np

METRICS = ("BIND", "TRANSFER", "NEAR", "NO_HISTORY_familiar", "NO_HISTORY_composite", "RANDOM_RESPONSE")
CELL_COUNTS = (4, 4, 4, 2, 2, 4)


def bootstrap_distribution(values, strata):
    """Batch of exact marginal distributions for stratified resampled means.

    If Z=4*contrast+4 is an integer 0..8, the sum distribution is the product
    over strata of each empirical probability polynomial raised to stratum N.
    FFT length exceeds its degree, preventing circular convolution aliasing.
    """
    x = np.asarray(values, dtype=float)
    if x.ndim == 1:
        x = x[None, :]
    strata = np.asarray(strata)
    if x.ndim != 2 or not x.shape[1] or strata.shape != (x.shape[1],) or not np.isfinite(x).all():
        raise ValueError("finite study by bundle values and aligned strata required")
    z = np.rint(x * 4 + 4).astype(int)
    if not np.allclose(z, x * 4 + 4, atol=1e-10, rtol=0) or z.min() < 0 or z.max() > 8:
        raise ValueError("contrast must lie on the declared quarter lattice")
    n = x.shape[1]
    length = 1 << (8 * n).bit_length()
    transform = np.ones((x.shape[0], length // 2 + 1), dtype=complex)
    for s in np.unique(strata):
        subset = z[:, strata == s]
        empirical = np.stack([(subset == k).mean(axis=1) for k in range(9)], axis=1)
        transform *= np.fft.rfft(empirical, n=length, axis=1) ** subset.shape[1]
    mass = np.fft.irfft(transform, n=length, axis=1)[:, :8 * n + 1]
    if mass.min() < -1e-9 or not np.isfinite(mass).all():
        raise ArithmeticError("bootstrap convolution failed numerically")
    mass = np.maximum(mass, 0)
    mass /= mass.sum(axis=1, keepdims=True)
    support = (np.arange(8 * n + 1) - 4 * n) / (4 * n)
    return support, mass


def percentile_interval(values, strata, alpha=.05):
    if not 0 < alpha < 1:
        raise ValueError("invalid alpha")
    support, mass = bootstrap_distribution(values, strata)
    cdf = mass.cumsum(axis=1)
    # Numerical tolerance only for equality at a discrete CDF boundary.
    low = (cdf >= alpha / 2 - 1e-12).argmax(axis=1)
    high = (cdf >= 1 - alpha / 2 - 1e-12).argmax(axis=1)
    return np.stack([support[low], support[high]], axis=1)


def bounds_from_choices(types, vectors, choices):
    """Batched choices (study,bundle,metric,4), -1 means missing.

    vectors is (bundle,metric,candidate,frame); no history metrics use two cells.
    The randomized response metric deliberately uses pseudo type geometry.
    """
    choices = np.asarray(choices)
    types, vectors = np.asarray(types), np.asarray(vectors)
    if choices.ndim != 4 or choices.shape[2:] != (6, 4) or choices.dtype.kind not in "iu" or choices.min() < -1 or choices.max() > 2:
        raise ValueError("invalid choice tensor")
    n = choices.shape[1]
    if types.shape != (n, 2) or vectors.shape != (n, 6, 3, 3) or not np.isfinite(vectors).all():
        raise ValueError("invalid geometry shape")
    if types.dtype.kind not in "iu" or types.min() < 0 or types.max() > 2 or (types[:, 0] == types[:, 1]).any():
        raise ValueError("invalid distinct types")
    if (vectors < 0).any() or not np.allclose(vectors.sum(-1), 1):
        raise ValueError("invalid vectors")
    delta = np.take_along_axis(vectors, types[:, None, None, 0, None], axis=-1)[..., 0]
    delta -= np.take_along_axis(vectors, types[:, None, None, 1, None], axis=-1)[..., 0]
    span = np.ptp(delta, axis=-1)
    if (span < .5 - 1e-10).any():
        raise ValueError("insufficient contrast span")
    # The common 0.34 likelihood scale cancels from the normalized contrast.
    lo = np.zeros(choices.shape[:3]); hi = np.zeros_like(lo)
    for j, count in enumerate(CELL_COUNTS):
        signs = (1, -1, -1, 1) if count == 4 else (1, -1)
        for cell, sign in enumerate(signs):
            coefficients = sign * delta[:, j] / (span[:, j, None] * (2 if count == 4 else 1))
            c = choices[:, :, j, cell]
            actual = np.take_along_axis(np.broadcast_to(coefficients, (*c.shape, 3)), np.maximum(c, 0)[..., None], axis=-1)[..., 0]
            lo[:, :, j] += np.where(c < 0, coefficients.min(axis=1), actual)
            hi[:, :, j] += np.where(c < 0, coefficients.max(axis=1), actual)
    return lo, hi


def validity_from_choices(choices):
    valid = choices >= 0
    # Five original choice branches; NO_HISTORY pools its two candidate sets.
    return np.stack([valid[:, :, 0].mean((1, 2)), valid[:, :, 2].mean((1, 2)),
                     valid[:, :, 1].mean((1, 2)), valid[:, :, 3:5, :2].mean((1, 2, 3)),
                     valid[:, :, 5].mean((1, 2))], axis=1)


def decision_batch(lower, upper, strata, validity):
    lower, upper = np.asarray(lower), np.asarray(upper)
    validity = np.asarray(validity)
    if lower.shape != upper.shape or lower.ndim != 3 or lower.shape[-1] != 6 or not np.isfinite(lower).all() or not np.isfinite(upper).all() or (lower > upper + 1e-10).any():
        raise ValueError("invalid contrast bounds")
    if np.asarray(validity).shape != (len(lower), 5) or not np.isfinite(validity).all() or (validity < 0).any() or (validity > 1).any():
        raise ValueError("invalid branch validity")
    selected = (0, 1, 3, 4, 5)
    cis_low, cis_high = [], []
    for j in selected:
        alpha = .025 if j < 2 else .05
        a = percentile_interval(lower[:, :, j], strata, alpha)
        b = a if np.array_equal(lower[:, :, j], upper[:, :, j]) else percentile_interval(upper[:, :, j], strata, alpha)
        cis_low.append(a); cis_high.append(b)
    cis_low = np.stack(cis_low, axis=1)
    cis_high = np.stack(cis_high, axis=1)
    means = lower.mean(axis=1)
    positive = cis_low[:, :2, 0] > 1e-12
    primary = positive & (means[:, :2] >= .10 - 1e-12)
    controls = (cis_low[:, 2:, 0] >= -.10 - 1e-12) & (cis_high[:, 2:, 1] <= .10 + 1e-12)
    valid = (validity >= .98 - 1e-12).all(axis=1)
    return {"mean_lower": means, "mean_upper": upper.mean(axis=1),
            "ci_lower_bounds": cis_low, "ci_upper_bounds": cis_high,
            "positive_primary": positive, "primary_pass": primary,
            "two_sided_primary_rejection": (cis_low[:, :2, 0] > 1e-12) | (cis_high[:, :2, 1] < -1e-12),
            "control_pass": controls, "validity_pass": valid,
            "joint_pass": primary.all(axis=1) & controls.all(axis=1) & valid}


def wilson(k, n, z=1.959963984540054):
    if not 0 <= k <= n or n <= 0:
        raise ValueError("invalid count")
    p = k / n
    centre = (p + z*z/(2*n)) / (1+z*z/n)
    half = z * np.sqrt(p*(1-p)/n + z*z/(4*n*n)) / (1+z*z/n)
    return float(max(0, centre-half)), float(min(1, centre+half))
