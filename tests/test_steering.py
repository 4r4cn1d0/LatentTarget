import numpy as np
import pytest
import torch

from src.probing import Probe
from src.steering import (
    intervention_directions,
    module_for_hidden_state,
    probe_contrast_direction,
    residual_steering,
)


def fake_probe():
    return Probe(
        W=np.asarray([[2.0, -1.0, -1.0], [0.0, 1.0, -1.0]]),
        b=np.zeros(3), mu=np.zeros(2), sigma=np.asarray([2.0, 1.0]),
        classes=["fairness", "risk", "expertise"], l2=1.0,
        n_train=12, converged=True,
    )


def test_probe_direction_is_unit_and_in_original_coordinates():
    direction = probe_contrast_direction(fake_probe(), "fairness")
    assert np.linalg.norm(direction) == pytest.approx(1.0)
    assert direction[0] > 0


def test_intervention_controls_are_norm_matched():
    directions = intervention_directions(fake_probe(), "risk", seed=9)
    assert np.allclose(directions["opposite"], -directions["target"])
    assert np.linalg.norm(directions["random"]) == pytest.approx(1.0)
    assert np.linalg.norm(directions["target"]) == pytest.approx(1.0)
    assert np.all(directions["zero"] == 0)


class Block(torch.nn.Module):
    def forward(self, x):
        return (x + 1, "cache")


class Wrapped(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.embedding = torch.nn.Embedding(5, 3)
        self.model = torch.nn.Module()
        self.model.layers = torch.nn.ModuleList([Block(), Block()])

    def get_input_embeddings(self):
        return self.embedding


def test_hidden_state_index_maps_embedding_then_blocks():
    model = Wrapped()
    assert module_for_hidden_state(model, 0) is model.embedding
    assert module_for_hidden_state(model, 1) is model.model.layers[0]
    assert module_for_hidden_state(model, 2) is model.model.layers[1]
    with pytest.raises(ValueError, match="model has 2 blocks"):
        module_for_hidden_state(model, 3)


def test_residual_hook_changes_only_last_token_and_is_removed():
    model = Wrapped()
    x = torch.zeros(1, 4, 3)
    baseline = model.model.layers[0](x)[0]
    with residual_steering(model, 1, np.asarray([1.0, 0.0, -1.0]), 2.0):
        changed, cache = model.model.layers[0](x)
    assert cache == "cache"
    assert torch.allclose(changed[:, :-1, :], baseline[:, :-1, :])
    assert torch.allclose(changed[0, -1], torch.tensor([3.0, 1.0, -1.0]))
    assert torch.allclose(model.model.layers[0](x)[0], baseline)
