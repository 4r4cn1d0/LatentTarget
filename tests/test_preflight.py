import numpy as np

from src.preflight import validate_capture
from src.probing import ActivationStore


def store(shape=(1, 4, 8), layers=None):
    return ActivationStore(
        acts=np.zeros(shape, dtype=np.float16),
        meta=[{"episode_id": "e", "round": 1}] * shape[0],
        layers=layers or list(range(shape[1])),
    )


def test_valid_capture_passes():
    report = validate_capture(store(), n_text_blocks=3)
    assert report["ok"]
    assert report["activation_shape"] == [1, 4, 8]


def test_wrong_layer_count_fails():
    report = validate_capture(store(), n_text_blocks=4)
    assert not report["ok"]
    assert "expected embedding" in report["issues"][0]


def test_nonfinite_capture_fails():
    bad = store()
    bad.acts[0, 0, 0] = np.nan
    report = validate_capture(bad, n_text_blocks=3)
    assert not report["ok"]
    assert any("NaN" in issue for issue in report["issues"])
