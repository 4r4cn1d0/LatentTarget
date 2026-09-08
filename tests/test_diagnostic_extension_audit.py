import pytest
from scripts.audit_diagnostic_extension import describe


def test_bundle_descriptives_include_all_signs():
    result = describe([-1, 0, 1])
    assert result == dict(n_bundles=3, mean=0, sample_sd=1, median=0,
                          minimum=-1, maximum=1, positive=1, zero=1, negative=1)


def test_no_sample_sd_for_single_bundle():
    with pytest.raises(ValueError, match='two bundles'):
        describe([0])
