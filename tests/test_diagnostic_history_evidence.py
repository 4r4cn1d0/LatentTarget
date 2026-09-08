import pytest
from scripts.audit_diagnostic_history_evidence import history_evidence


def test_outcome_counting_and_posterior():
    events = []
    for who in ('X', 'Y'):
        for frame in range(3):
            for _ in range(4):
                events.append({'participant': who, 'analyst_frame': frame,
                               'choice': 'A' if frame == (0 if who == 'X' else 2) else 'B'})
    result = history_evidence({'aliases': ['X', 'Y'], 'types': [0, 2], 'events': events})
    assert result[0]['a_counts'] == [4, 0, 0]
    assert result[0]['b_counts'] == [0, 4, 4]
    assert result[1]['a_counts'] == [0, 0, 4]
    assert result[1]['b_counts'] == [4, 4, 0]
    assert [r['highest_posterior_types'] for r in result] == [[0], [2]]
    for r in result:
        assert sum(r['posterior_uniform_prior']) == pytest.approx(1)
