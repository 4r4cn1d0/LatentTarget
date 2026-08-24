"""Invariants of the persuasion lexicons."""

from __future__ import annotations

import re

import pytest

from src.lexicons import LEXICONS, LexiconMatcher, lexicon_half


def test_terms_are_lowercase_and_nonempty():
    for dim, terms in LEXICONS.items():
        assert terms, dim
        for t in terms:
            assert t == t.lower(), (dim, t)
            assert t.strip() == t and t, (dim, t)


def test_no_duplicate_terms_within_or_across_dimensions():
    seen = {}
    for dim, terms in LEXICONS.items():
        assert len(set(terms)) == len(terms), "duplicate inside %s" % dim
        for t in terms:
            assert t not in seen, "%r appears in both %s and %s" % (t, seen.get(t), dim)
            seen[t] = dim


def test_no_term_whole_word_contains_another():
    """Otherwise a single phrase would be counted twice when we count DISTINCT
    matched terms, silently inflating that dimension's score."""
    all_terms = [t for terms in LEXICONS.values() for t in terms]
    for a in all_terms:
        pat = re.compile(r"\b" + re.escape(a) + r"\b")
        for b in all_terms:
            if a == b:
                continue
            assert not pat.search(b), "term %r whole-word-contains inside %r" % (a, b)


def test_lexicon_halves_are_disjoint_and_exhaustive():
    for dim, terms in LEXICONS.items():
        even = set(lexicon_half(terms, "even"))
        odd = set(lexicon_half(terms, "odd"))
        assert not (even & odd), dim
        assert even | odd == set(terms), dim


def test_matcher_counts_distinct_terms_not_occurrences():
    m = LexiconMatcher("all")
    assert m.hits("risk risk risk risk")["risk"] == 1
    assert m.hits("risk and safety and downside")["risk"] == 3


def test_matcher_is_case_insensitive_and_word_bounded():
    m = LexiconMatcher("all")
    assert m.hits("RISK")["risk"] == 1
    # "brisket" must not match "risk"
    assert m.hits("brisket")["risk"] == 0
    assert m.hits("fairground")["fairness"] == 0


def test_half_argument_is_validated():
    with pytest.raises(ValueError):
        lexicon_half(("a",), "third")
