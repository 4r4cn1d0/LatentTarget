"""Residual-stream interventions derived from a fitted linear probe.

These utilities are architecture-light: a captured hidden-state index of zero
means the embedding output; index ``k > 0`` means the output of transformer
block ``k - 1``.  The GPU preflight verifies this mapping before any full run.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Dict, Iterator, Sequence

import numpy as np

from .probing import Probe


def probe_contrast_direction(probe: Probe, target_class: str) -> np.ndarray:
    """Unit vector that raises one class logit relative to the other classes.

    The probe operates on standardised features, so dividing by ``sigma`` maps
    its weights back into the original residual-stream coordinates.
    """
    if target_class not in probe.classes:
        raise ValueError("unknown probe class %r" % target_class)
    target = probe.classes.index(target_class)
    others = [i for i in range(len(probe.classes)) if i != target]
    contrast = probe.W[:, target] - probe.W[:, others].mean(axis=1)
    direction = contrast / probe.sigma
    norm = float(np.linalg.norm(direction))
    if not np.isfinite(norm) or norm <= 0:
        raise ValueError("probe contrast has zero or non-finite norm")
    return direction / norm


def intervention_directions(
    probe: Probe, target_class: str, seed: int = 0
) -> Dict[str, np.ndarray]:
    """Target, opposite, norm-matched random, and zero controls."""
    target = probe_contrast_direction(probe, target_class)
    rng = np.random.default_rng(seed)
    random = rng.normal(size=target.shape)
    random /= np.linalg.norm(random)
    return {
        "target": target,
        "opposite": -target,
        "random": random,
        "zero": np.zeros_like(target),
    }


def find_text_layers(model):
    """Locate a transformer's ordered text blocks across common HF wrappers."""
    candidate_paths: Sequence[Sequence[str]] = (
        ("language_model", "layers"),
        ("language_model", "model", "layers"),
        ("model", "language_model", "layers"),
        ("model", "language_model", "model", "layers"),
        ("model", "layers"),
        ("transformer", "h"),
    )
    for path in candidate_paths:
        value = model
        for component in path:
            if not hasattr(value, component):
                break
            value = getattr(value, component)
        else:
            if hasattr(value, "__len__") and len(value) > 0:
                return value
    raise ValueError(
        "could not locate text transformer blocks; inspect the loaded model and "
        "extend find_text_layers before steering"
    )


def module_for_hidden_state(model, hidden_state_index: int):
    """Map the index returned by ``output_hidden_states`` to its producer."""
    if hidden_state_index < 0:
        raise ValueError("hidden_state_index must be non-negative")
    if hidden_state_index == 0:
        module = model.get_input_embeddings()
        if module is None:
            raise ValueError("model exposes no input embedding module")
        return module
    layers = find_text_layers(model)
    block_index = hidden_state_index - 1
    if block_index >= len(layers):
        raise ValueError(
            "hidden-state index %d implies block %d, but model has %d blocks"
            % (hidden_state_index, block_index, len(layers))
        )
    return layers[block_index]


def _add_to_last_token(output, direction, coefficient):
    """Forward-hook transform supporting tensor and tuple block outputs."""
    import torch

    first = output[0] if isinstance(output, tuple) else output
    if not torch.is_tensor(first) or first.ndim != 3:
        raise TypeError("expected [batch, sequence, d_model] tensor from hooked module")
    if first.shape[-1] != len(direction):
        raise ValueError(
            "direction has %d dimensions but residual has %d"
            % (len(direction), first.shape[-1])
        )
    delta = torch.as_tensor(direction, device=first.device, dtype=first.dtype)
    changed = first.clone()
    changed[:, -1, :] = changed[:, -1, :] + float(coefficient) * delta
    if isinstance(output, tuple):
        return (changed,) + output[1:]
    return changed


@contextmanager
def residual_steering(
    model, hidden_state_index: int, direction: np.ndarray, coefficient: float
) -> Iterator[None]:
    """Temporarily add a direction to the final token at every forward step."""
    module = module_for_hidden_state(model, hidden_state_index)

    def hook(_module, _inputs, output):
        return _add_to_last_token(output, direction, coefficient)

    handle = module.register_forward_hook(hook)
    try:
        yield
    finally:
        handle.remove()
