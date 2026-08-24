"""End-to-end experiment runner: schema, conditions, leakage and reproducibility."""

from __future__ import annotations

import dataclasses
import re

import pytest

from config import CONDITIONS, ExperimentConfig, JudgeConfig, ModelConfig, STRATEGIES
from src.experiment import (
    DonorRegistry,
    _swap_partners,
    build_episode_specs,
    run_experiment,
)
from src.lexicons import LEXICONS
from src.logging_utils import REQUIRED_FIELDS, read_jsonl, validate_record
from src.scenarios import scenario_sequence


def cfg_for(tmp_path, conditions, variant="win_stay_lose_shift", n_seeds=2, exp_id="test"):
    return ExperimentConfig(
        experiment_id=exp_id,
        n_rounds=4,
        swap_round=2,
        n_episode_seeds=n_seeds,
        conditions=list(conditions),
        model=ModelConfig(provider="mock:" + variant, model="mock"),
        judge=JudgeConfig(kind="keyword"),
        out_dir=str(tmp_path),
    )


# --------------------------------------------------------------------------
# Episode specs
# --------------------------------------------------------------------------


def test_one_episode_per_target_type_per_episode_index(tmp_path):
    cfg = cfg_for(tmp_path, ["full_history"], n_seeds=3)
    specs = build_episode_specs(cfg)
    assert len(specs) == 3 * len(STRATEGIES)
    for idx in range(3):
        types = sorted(s.initial_target_type for s in specs if s.episode_index == idx)
        assert types == sorted(STRATEGIES)


def test_scenario_sequences_are_identical_across_target_types(tmp_path):
    cfg = cfg_for(tmp_path, ["full_history"], n_seeds=3)
    specs = build_episode_specs(cfg)
    for idx in range(3):
        seqs = {
            s.initial_target_type: [
                sc.id for sc in scenario_sequence(s.episode_index, s.n_rounds, cfg.seed)
            ]
            for s in specs
            if s.episode_index == idx
        }
        assert len(set(map(tuple, seqs.values()))) == 1, seqs


def test_swap_partners_are_fully_counterbalanced_within_every_scenario_sequence(tmp_path):
    for t in STRATEGIES:
        partners = set(_swap_partners(t))
        assert t not in partners
        assert partners == {s for s in STRATEGIES if s != t}

    cfg = cfg_for(tmp_path, ["swap"], n_seeds=3)
    specs = build_episode_specs(cfg)
    assert len(specs) == 3 * len(STRATEGIES) * (len(STRATEGIES) - 1)
    for idx in range(3):
        pairs = {
            (s.initial_target_type, s.final_target_type)
            for s in specs if s.episode_index == idx
        }
        assert len(pairs) == 6


def test_shuffled_history_requires_full_history(tmp_path):
    with pytest.raises(ValueError, match="full_history"):
        build_episode_specs(cfg_for(tmp_path, ["shuffled_history"]))
    with pytest.raises(ValueError, match="must come before"):
        build_episode_specs(cfg_for(tmp_path, ["shuffled_history", "full_history"]))


def test_unknown_condition_is_rejected(tmp_path):
    with pytest.raises(ValueError, match="unknown condition"):
        build_episode_specs(cfg_for(tmp_path, ["telepathy"]))


# --------------------------------------------------------------------------
# Record schema
# --------------------------------------------------------------------------


def test_every_record_has_every_required_field(tmp_path):
    cfg = cfg_for(tmp_path, ["full_history", "no_history", "shuffled_history", "random_target", "swap"])
    res = run_experiment(cfg, run_id="schema")
    assert res.n_records > 0
    for rec in read_jsonl(res.log_path):
        validate_record(rec)
    assert set(REQUIRED_FIELDS) <= set(res.records[0])


def test_validate_record_rejects_incomplete_records():
    with pytest.raises(ValueError, match="missing required fields"):
        validate_record({"experiment_id": "x"})


def test_manifest_records_prompts_and_config(tmp_path):
    import json

    cfg = cfg_for(tmp_path, ["full_history"])
    res = run_experiment(cfg, run_id="manifest")
    with open(res.manifest_path) as fh:
        man = json.load(fh)
    assert "focal_system_prompt_template" in man
    assert man["config"]["target_params"]["w_match"] == cfg.target_params.w_match
    assert man["classifier"]["kind"] == "keyword"
    assert man["target_scorer"]["lexicon_half"] == "all"


# --------------------------------------------------------------------------
# Leakage
# --------------------------------------------------------------------------


def test_hidden_type_never_appears_in_a_prompt(tmp_path):
    cfg = cfg_for(tmp_path, ["full_history", "swap"])
    res = run_experiment(cfg, run_id="leak")
    for rec in res.records:
        assert rec["hidden_target_type"] not in rec["focal_system_prompt"].lower()
        # The user prompt may quote the agent's OWN earlier messages, which can
        # contain persuasion vocabulary; what must never appear is the type name
        # in the scaffolding.  Check the part of the prompt we generate.
        scaffold = rec["focal_user_prompt"].split("--- Previous interactions ---")[0]
        current = rec["focal_user_prompt"].split("--- Current interaction")[-1]
        for part in (scaffold, current):
            for t in STRATEGIES:
                assert not re.search(r"\b%s\b" % t, part, re.IGNORECASE), part


def test_current_round_block_contains_no_lexicon_terms(tmp_path):
    cfg = cfg_for(tmp_path, ["full_history"])
    res = run_experiment(cfg, run_id="lex")
    for rec in res.records:
        current = rec["focal_user_prompt"].split("--- Current interaction")[-1]
        for dim, terms in LEXICONS.items():
            for t in terms:
                assert not re.search(r"\b%s\b" % re.escape(t), current, re.IGNORECASE), (
                    dim, t, current,
                )


def test_target_never_sees_the_scenario(tmp_path):
    """The target's probability must be a pure function of the message."""
    from src.target_simulator import TypedTarget

    t = TypedTarget("risk")
    msg = "This is safer, it avoids failure, protects us, and reduces risk."
    assert t.p_a_noiseless(msg) == t.p_a_noiseless(msg)
    import inspect

    assert list(inspect.signature(t.p_a_noiseless).parameters) == ["message"]


# --------------------------------------------------------------------------
# Conditions behave as specified
# --------------------------------------------------------------------------


def test_no_history_condition_shows_no_history(tmp_path):
    cfg = cfg_for(tmp_path, ["no_history"])
    res = run_experiment(cfg, run_id="nohist")
    for rec in res.records:
        assert "Previous interactions" not in rec["focal_user_prompt"]
        assert rec["visible_history"] == []


def test_full_history_grows_by_one_each_round(tmp_path):
    cfg = cfg_for(tmp_path, ["full_history"])
    res = run_experiment(cfg, run_id="fullhist")
    for rec in res.records:
        assert len(rec["visible_history"]) == rec["round"] - 1
        if rec["round"] > 1:
            assert "Previous interactions" in rec["focal_user_prompt"]


def test_shuffled_history_comes_from_a_different_target_type(tmp_path):
    cfg = cfg_for(tmp_path, ["full_history", "shuffled_history"])
    res = run_experiment(cfg, run_id="shuffled")
    shuffled = [r for r in res.records if r["condition"] == "shuffled_history"]
    assert shuffled
    for rec in shuffled:
        donor = rec["history_source_episode_id"]
        assert donor is not None and donor.startswith("full_history-")
        donor_type = donor.rsplit("-", 1)[-1]
        assert donor_type != rec["hidden_target_type"]
        assert len(rec["visible_history"]) == rec["round"] - 1


def test_shuffled_history_uses_the_same_scenario_sequence(tmp_path):
    """Donor and recipient must share scenarios, so only the outcomes differ."""
    cfg = cfg_for(tmp_path, ["full_history", "shuffled_history"])
    res = run_experiment(cfg, run_id="shuffled2")
    by_ep = {}
    for r in res.records:
        by_ep.setdefault(r["episode_id"], []).append(r)
    for eid, recs in by_ep.items():
        if not eid.startswith("shuffled_history"):
            continue
        donor = recs[0]["history_source_episode_id"]
        donor_scen = [x["scenario_id"] for x in sorted(by_ep[donor], key=lambda r: r["round"])]
        own_scen = [x["scenario_id"] for x in sorted(recs, key=lambda r: r["round"])]
        assert donor_scen == own_scen


def test_random_target_probability_is_constant(tmp_path):
    cfg = cfg_for(tmp_path, ["random_target"])
    res = run_experiment(cfg, run_id="randt")
    assert {r["target_p_a"] for r in res.records} == {cfg.target_params.random_p_a}
    assert {r["target_mode"] for r in res.records} == {"random"}


def test_swap_changes_the_active_type_silently(tmp_path):
    cfg = cfg_for(tmp_path, ["swap"])
    res = run_experiment(cfg, run_id="swap")
    assert res.records
    for rec in res.records:
        expected = (
            rec["initial_target_type"] if rec["round"] <= cfg.swap_round else rec["final_target_type"]
        )
        assert rec["hidden_target_type"] == expected
        assert rec["swap_has_occurred"] == (rec["round"] > cfg.swap_round)
        assert rec["rounds_since_swap"] == rec["round"] - cfg.swap_round
        assert rec["initial_target_type"] != rec["final_target_type"]
        # Nothing in the prompt announces the change.
        assert "change" not in rec["focal_system_prompt"].lower()


def test_swap_uses_the_condition_specific_round_count(tmp_path):
    cfg = cfg_for(tmp_path, ["swap"])
    res = run_experiment(cfg, run_id="swaprounds")
    assert {r["n_rounds"] for r in res.records} == {CONDITIONS["swap"].n_rounds}


def test_mismatched_feedback_displays_a_different_outcome_sometimes(tmp_path):
    cfg = cfg_for(tmp_path, ["mismatched_feedback"], n_seeds=4)
    res = run_experiment(cfg, run_id="mismatch")
    assert any(r["displayed_choice"] != r["target_choice"] for r in res.records)
    for rec in res.records:
        if rec["round"] > 1:
            assert rec["displayed_feedback_type"] != rec["hidden_target_type"]


# --------------------------------------------------------------------------
# Reproducibility
# --------------------------------------------------------------------------

_VOLATILE = {"timestamp", "run_id"}


def test_two_runs_with_the_same_config_are_identical(tmp_path):
    cfg = cfg_for(tmp_path, ["full_history", "no_history", "shuffled_history", "random_target", "swap"])
    a = run_experiment(cfg, run_id="repro_a")
    b = run_experiment(cfg, run_id="repro_b")
    assert len(a.records) == len(b.records)
    for ra, rb in zip(a.records, b.records):
        da = {k: v for k, v in ra.items() if k not in _VOLATILE}
        db = {k: v for k, v in rb.items() if k not in _VOLATILE}
        assert da == db


def test_changing_the_master_seed_changes_the_data(tmp_path):
    base = cfg_for(tmp_path, ["full_history"])
    other = dataclasses.replace(base, seed=base.seed + 1)
    a = run_experiment(base, run_id="seed_a")
    b = run_experiment(other, run_id="seed_b")
    assert [r["target_choice"] for r in a.records] != [r["target_choice"] for r in b.records]


def test_existing_run_id_is_refused_instead_of_appending_duplicates(tmp_path):
    cfg = cfg_for(tmp_path, ["full_history"], n_seeds=1)
    run_experiment(cfg, run_id="same")
    with pytest.raises(FileExistsError, match="duplicate episodes"):
        run_experiment(cfg, run_id="same")


def test_donor_registry_raises_a_useful_error_when_empty():
    reg = DonorRegistry()
    with pytest.raises(KeyError, match="full_history"):
        reg.donor_for(0, "risk")


# --------------------------------------------------------------------------
# Sanity: the pipeline can detect adaptation when it is present
# --------------------------------------------------------------------------


def test_oracle_mock_reaches_a_perfect_match_rate(tmp_path):
    cfg = cfg_for(tmp_path, ["full_history"], variant="oracle", n_seeds=3)
    res = run_experiment(cfg, run_id="oracle")
    matches = [r["primary_strategy"] == r["hidden_target_type"] for r in res.records]
    assert all(matches)


def test_random_mock_stays_near_chance(tmp_path):
    cfg = cfg_for(tmp_path, ["full_history"], variant="random", n_seeds=8)
    res = run_experiment(cfg, run_id="randmock")
    rate = sum(r["primary_strategy"] == r["hidden_target_type"] for r in res.records) / len(
        res.records
    )
    assert 0.05 < rate < 0.45


def test_win_stay_lose_shift_improves_with_history_but_not_without(tmp_path):
    """The measurement pipeline must show a rise when adaptation is real, and no
    rise when the agent cannot see any feedback."""
    cfg = ExperimentConfig(
        experiment_id="wsls",
        n_rounds=8,
        n_episode_seeds=16,
        conditions=["full_history", "no_history"],
        model=ModelConfig(provider="mock:win_stay_lose_shift", model="mock"),
        judge=JudgeConfig(kind="keyword"),
        out_dir=str(tmp_path),
    )
    res = run_experiment(cfg, run_id="wsls")

    def rate(cond, rnd):
        rows = [r for r in res.records if r["condition"] == cond and r["round"] == rnd]
        return sum(r["primary_strategy"] == r["hidden_target_type"] for r in rows) / len(rows)

    assert rate("full_history", 8) > rate("full_history", 1) + 0.15
    assert abs(rate("no_history", 8) - rate("no_history", 1)) < 0.15
