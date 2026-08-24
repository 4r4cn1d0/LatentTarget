"""Deterministic seed derivation.

Python's builtin ``hash()`` is salted per process (``PYTHONHASHSEED``), so it
must never be used to derive experiment seeds.  Everything here is SHA-256
based and therefore stable across processes, machines and Python versions.
"""

from __future__ import annotations

import hashlib
from typing import Any

import numpy as np

_MASK_63 = (1 << 63) - 1


def derive_seed(*parts: Any) -> int:
    """Return a stable non-negative 63-bit seed from arbitrary parts.

    >>> derive_seed(1, "full_history", "fairness") == derive_seed(1, "full_history", "fairness")
    True
    """
    joined = "\x1f".join(repr(p) for p in parts)
    digest = hashlib.sha256(joined.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big") & _MASK_63


def rng(*parts: Any) -> np.random.Generator:
    """A ``numpy`` Generator seeded deterministically from ``parts``."""
    return np.random.default_rng(derive_seed(*parts))
