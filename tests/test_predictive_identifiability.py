from fractions import Fraction as F

import pytest

from src.predictive_identifiability import (
    alias_pairs, bernoulli_update, design_certificate, response_vector,
    simplex_grid, transition_belief,
)


def test_witness_is_exact_and_changes_optimal_action():
    report = design_certificate()
    witness = report["recoverable_witness"]
    assert witness["left"] == (F(3, 4), F(1, 4), 0)
    assert witness["right"] == (F(1, 4), F(3, 4), 0)
    assert witness["current"] == (F(3, 5), F(2, 5), F(1, 2))
    assert witness["future_left"] == (F(11, 20), F(9, 20), F(1, 2))
    assert witness["future_right"] == (F(9, 20), F(11, 20), F(1, 2))
    assert report["model_calls"] == 0
    assert report["original_predictive_aliases"] == 0
    assert report["identity_transition_predictive_aliases"] == 0
    assert report["grid_pairs"] == 105


def test_all_witnesses_obey_contract():
    report = design_certificate()
    emissions = report["proposed_emissions"]
    transitions = report["proposed_transitions"]
    assert report["all_grid_witnesses"]
    for item in report["all_grid_witnesses"]:
        assert response_vector(item["left"], emissions) == response_vector(item["right"], emissions)
        assert item["future_left"] != item["future_right"]
        assert response_vector(transition_belief(item["left"], transitions), emissions) == item["future_left"]


def test_grid_complete_unique():
    grid = simplex_grid(10)
    assert len(set(grid)) == 66
    assert all(sum(b) == 1 and min(b) >= 0 for b in grid)


@pytest.mark.parametrize("value", [0, -1, True, 2.5])
def test_bad_grid(value):
    with pytest.raises(ValueError):
        simplex_grid(value)


@pytest.mark.parametrize("belief,emissions", [
    ((.2, .2), ((.5,), (.5,))),
    ((1, 0), ((.5,),)),
    ((1, 0), ((.5,), (.2, .4))),
    ((1, 0), ((1.1,), (.2,))),
    ((1, 0), ((), ())),
])
def test_bad_emissions(belief, emissions):
    with pytest.raises(ValueError):
        response_vector(belief, emissions)


def test_invalid_transition_and_impossible_observation():
    with pytest.raises(ValueError):
        transition_belief((1, 0), ((.2, .2), (0, 1)))
    with pytest.raises(ValueError):
        transition_belief((1, 0), ((1, 0, 0), (0, 1, 0)))
    with pytest.raises(ValueError):
        bernoulli_update((1, 0), (0, 1), True)
    with pytest.raises(ValueError):
        bernoulli_update((1, 0), (1,), True)
    with pytest.raises(ValueError):
        bernoulli_update((1, 0), (1, 0), "A")


def test_no_mutation_and_emission_rows_are_not_distributions():
    belief = [F(1, 2), F(1, 2)]
    emissions = [[.5, .5, .5], [.5, .5, .5]]
    assert response_vector(belief, emissions) == (F(1, 2),)*3
    assert belief == [F(1, 2), F(1, 2)]
    assert emissions == [[.5, .5, .5], [.5, .5, .5]]
    assert alias_pairs((belief, belief), emissions, ((1, 0), (0, 1))) == []
