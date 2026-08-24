"""Validation helpers for the one-generation open-weight preflight."""

from __future__ import annotations

from typing import Any, Dict

import numpy as np


def validate_capture(store, n_text_blocks: int, expected_rows: int = 1) -> Dict[str, Any]:
    """Fail loudly when captured hidden states cannot support the probe design."""
    issues = []
    if store.n_rows != expected_rows:
        issues.append("captured %d rows, expected %d" % (store.n_rows, expected_rows))
    if store.n_layers != n_text_blocks + 1:
        issues.append(
            "captured %d hidden states, expected embedding + %d blocks = %d"
            % (store.n_layers, n_text_blocks, n_text_blocks + 1)
        )
    if store.acts.ndim != 3 or store.d_model < 1:
        issues.append("activation array is not [rows, layers, d_model]")
    if not np.isfinite(np.asarray(store.acts, dtype=np.float32)).all():
        issues.append("activations contain NaN or infinity")
    if store.layers != list(range(store.n_layers)):
        issues.append("preflight must use layer_stride=1 and capture every hidden state")
    return {
        "ok": not issues,
        "issues": issues,
        "activation_shape": list(store.acts.shape),
        "n_text_blocks": int(n_text_blocks),
        "d_model": store.d_model,
        "captured_hidden_state_indices": list(store.layers),
    }
