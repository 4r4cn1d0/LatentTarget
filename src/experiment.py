"""Episode and experiment runners.

Design guarantees implemented here (each has a test):

* **Scenario sequences depend only on ``(master_seed, episode_index)``.**  For a
  given ``episode_index`` all three hidden target types -- and all conditions
  with the same ``n_rounds`` -- see literally the same scenarios in the same
  order.  Scenario content therefore cannot be correlated with target type.
* **The focal agent's prompt never contains the hidden type** (or any word
  about types, profiles or strategies).  See ``focal_agent.SYSTEM_PROMPT``.
* **Every round is seeded deterministically** from
  ``derive_seed(master_seed, condition, episode_index, types..., round)``, so
  re-running an experiment with the same config and a deterministic provider
  reproduces it byte for byte.
* **Nothing is filtered.**  Every round of every episode is written to the log.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np

from config import (
    CONDITIONS,
    STRATEGIES,
    Condition,
    ExperimentConfig,
)
from .focal_agent import (
    DEFAULT_OBJECTIVE,
    BaseProvider,
    FocalAgent,
    HistoryEntry,
    make_provider,
)
from .logging_utils import JsonlWriter, write_manifest
from .scenarios import scenario_sequence
from .seeding import derive_seed
from .strategy_classifier import make_classifier, scorer_lexicon_half_for
from .target_simulator import KeywordPersuasionScorer, make_target

ProgressFn = Callable[[str], None]


# --------------------------------------------------------------------------
# Episode specification
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class EpisodeSpec:
    condition: Condition
    episode_index: int
    initial_target_type: str
    final_target_type: str
    n_rounds: int
    swap_round: Optional[int]
    episode_id: str

    @property
    def swaps(self) -> bool:
        return self.condition.swap and self.final_target_type != self.initial_target_type

    def active_type(self, round_index: int) -> str:
        if self.swaps and self.swap_round is not None and round_index > self.swap_round:
            return self.final_target_type
        return self.initial_target_type


def _swap_partners(initial: str) -> List[str]:
    """Both possible post-swap types, in stable canonical order.

    An earlier design selected one partner from ``episode_index % 2``. Scenario
    sequences are also functions of ``episode_index``, so ordered swap pairs
    were accidentally associated with different scenario sequences. Running
    both partners for every initial type and episode index removes that
    confound and fully counterbalances all six ordered transitions.
    """
    if initial not in STRATEGIES:
        raise ValueError("unknown initial target type %r" % initial)
    return [candidate for candidate in STRATEGIES if candidate != initial]


def build_episode_specs(cfg: ExperimentConfig) -> List[EpisodeSpec]:
    """All episodes to run, in execution order.

    Conditions are visited in the order given by ``cfg.conditions``;
    ``shuffled_history`` requires ``full_history`` to have been run first in the
    same call, because it borrows its donor histories from it.
    """
    specs: List[EpisodeSpec] = []
    for cond_name in cfg.conditions:
        if cond_name not in CONDITIONS:
            raise ValueError(
                "unknown condition %r; known: %s" % (cond_name, sorted(CONDITIONS))
            )
        cond = CONDITIONS[cond_name]
        n_rounds = cond.n_rounds or cfg.n_rounds
        for episode_index in range(cfg.n_episode_seeds):
            for t0 in STRATEGIES:
                partners = _swap_partners(t0) if cond.swap else [t0]
                for t1 in partners:
                    if cond.swap:
                        swap_round: Optional[int] = cfg.swap_round
                        eid = "%s-%03d-%s-to-%s" % (
                            cond.name, episode_index, t0, t1
                        )
                    else:
                        swap_round = None
                        eid = "%s-%03d-%s" % (cond.name, episode_index, t0)
                    specs.append(
                        EpisodeSpec(
                            condition=cond,
                            episode_index=episode_index,
                            initial_target_type=t0,
                            final_target_type=t1,
                            n_rounds=n_rounds,
                            swap_round=swap_round,
                            episode_id=eid,
                        )
                    )
    if "shuffled_history" in cfg.conditions and "full_history" not in cfg.conditions:
        raise ValueError(
            "condition 'shuffled_history' needs donor histories from "
            "'full_history'; add 'full_history' to cfg.conditions (it must also "
            "come first in the list)."
        )
    if "shuffled_history" in cfg.conditions and cfg.conditions.index(
        "shuffled_history"
    ) < cfg.conditions.index("full_history"):
        raise ValueError("'full_history' must come before 'shuffled_history' in cfg.conditions")
    return specs


# --------------------------------------------------------------------------
# Donor registry (for the shuffled-history control)
# --------------------------------------------------------------------------


class DonorRegistry:
    """Histories from completed ``full_history`` episodes, keyed by
    ``(episode_index, target_type)``."""

    def __init__(self) -> None:
        self._store: Dict[Tuple[int, str], Tuple[str, List[HistoryEntry]]] = {}

    def add(self, episode_index: int, target_type: str, episode_id: str, history: List[HistoryEntry]) -> None:
        self._store[(episode_index, target_type)] = (episode_id, list(history))

    def donor_for(self, episode_index: int, true_type: str) -> Tuple[str, List[HistoryEntry]]:
        """Pick a donor with the SAME scenario sequence but a DIFFERENT type."""
        i = STRATEGIES.index(true_type)
        for offset in (1, 2):
            key = (episode_index, STRATEGIES[(i + offset) % len(STRATEGIES)])
            if key in self._store:
                return self._store[key]
        raise KeyError(
            "no donor history available for episode_index=%d, true_type=%s. Run "
            "the 'full_history' condition first." % (episode_index, true_type)
        )


# --------------------------------------------------------------------------
# Episode runner
# --------------------------------------------------------------------------


@dataclass
class EpisodeResult:
    episode_id: str
    records: List[Dict[str, Any]]
    own_history: List[HistoryEntry]


def run_episode(
    spec: EpisodeSpec,
    cfg: ExperimentConfig,
    agent: FocalAgent,
    classifier,
    scorer: KeywordPersuasionScorer,
    run_id: str,
    donors: Optional[DonorRegistry] = None,
    objective: str = DEFAULT_OBJECTIVE,
    progress: Optional[ProgressFn] = None,
) -> EpisodeResult:
    """Run one episode and return its per-round log records."""
    cond = spec.condition
    scenarios = scenario_sequence(spec.episode_index, spec.n_rounds, cfg.seed)
    episode_seed = derive_seed(
        cfg.seed,
        cond.name,
        spec.episode_index,
        spec.initial_target_type,
        spec.final_target_type,
    )

    own_history: List[HistoryEntry] = []
    donor_history: List[HistoryEntry] = []
    donor_episode_id: Optional[str] = None
    if cond.history_mode == "shuffled":
        if donors is None:
            raise ValueError("shuffled history needs a DonorRegistry")
        donor_episode_id, donor_history = donors.donor_for(
            spec.episode_index, spec.initial_target_type
        )

    displayed_history: List[HistoryEntry] = []
    records: List[Dict[str, Any]] = []

    for r in range(1, spec.n_rounds + 1):
        scenario = scenarios[r - 1]
        active_type = spec.active_type(r)
        round_seed = derive_seed(episode_seed, "round", r)
        gen = np.random.default_rng(round_seed)

        # ---- which history does the agent see? ----
        if cond.history_mode == "full":
            visible = list(own_history)
            show_history = True
            history_source = spec.episode_id
        elif cond.history_mode == "none":
            visible = []
            show_history = False
            history_source = None
        elif cond.history_mode == "shuffled":
            visible = list(donor_history[: r - 1])
            show_history = True
            history_source = donor_episode_id
        elif cond.history_mode == "mismatched_feedback":
            visible = list(displayed_history)
            show_history = True
            history_source = spec.episode_id + "|fake_outcomes"
        else:
            raise ValueError("unknown history_mode %r" % cond.history_mode)

        # ---- focal agent ----
        context = {
            "round_index": r,
            "n_rounds": spec.n_rounds,
            "episode_seed": episode_seed,
            "round_seed": round_seed,
            "condition": cond.name,
            "scenario": scenario.as_dict(),
            "visible_history": [e.as_dict() for e in visible],
            # Read ONLY by the `oracle` mock provider. Real providers never
            # touch FocalPrompt.context.
            "hidden_target_type": active_type,
        }
        prompt, raw_message, message = agent.generate_message(
            scenario=scenario,
            history=visible,
            round_index=r,
            n_rounds=spec.n_rounds,
            show_history=show_history,
            objective=objective,
            context=context,
        )

        # Bookkeeping hook for providers that capture activations (open-weight
        # runs). Called AFTER generation, so it cannot influence the output.
        if hasattr(agent.provider, "tag_last"):
            agent.provider.tag_last(
                {"episode_id": spec.episode_id, "round": r, "run_id": run_id}
            )

        # ---- target ----
        target = make_target(
            target_mode=cond.target_mode,
            target_type=active_type,
            params=cfg.target_params,
            scorer=scorer,
        )
        response = target.respond(message, gen)

        # ---- what outcome is the agent shown? ----
        if cond.history_mode == "mismatched_feedback":
            wrong_type = STRATEGIES[
                (STRATEGIES.index(active_type) + 1 + (r % (len(STRATEGIES) - 1)))
                % len(STRATEGIES)
            ]
            fake_target = make_target("typed", wrong_type, cfg.target_params, scorer)
            fake_gen = np.random.default_rng(derive_seed(round_seed, "fake"))
            displayed_choice = fake_target.respond(message, fake_gen).choice
            displayed_feedback_type: Optional[str] = wrong_type
        else:
            displayed_choice = response.choice
            displayed_feedback_type = None

        # ---- classification (blind: message text only) ----
        classification = classifier.classify(message)

        entry = HistoryEntry(
            round=r,
            scenario_id=scenario.id,
            scenario_title=scenario.title,
            message=message,
            choice=displayed_choice,
        )
        own_entry = HistoryEntry(
            round=r,
            scenario_id=scenario.id,
            scenario_title=scenario.title,
            message=message,
            choice=response.choice,
        )
        own_history.append(own_entry)
        displayed_history.append(entry)

        swap_has_occurred = bool(
            spec.swaps and spec.swap_round is not None and r > spec.swap_round
        )
        rounds_since_swap = (
            r - spec.swap_round if (spec.swaps and spec.swap_round is not None) else None
        )

        record: Dict[str, Any] = {
            "experiment_id": cfg.experiment_id,
            "run_id": run_id,
            "condition": cond.name,
            "episode_id": spec.episode_id,
            "episode_index": spec.episode_index,
            "round": r,
            "n_rounds": spec.n_rounds,
            "hidden_target_type": active_type,
            "initial_target_type": spec.initial_target_type,
            "final_target_type": spec.final_target_type,
            "swap_condition": bool(cond.swap),
            "swap_round": spec.swap_round,
            "swap_has_occurred": swap_has_occurred,
            "rounds_since_swap": rounds_since_swap,
            "target_mode": cond.target_mode,
            "history_mode": cond.history_mode,
            "scenario_id": scenario.id,
            "scenario": scenario.as_dict(),
            "focal_system_prompt": prompt.system,
            "focal_user_prompt": prompt.user,
            "focal_message_raw": raw_message,
            "focal_message": message,
            "focal_message_words": len(message.split()),
            "visible_history": [e.as_dict() for e in visible],
            "history_source_episode_id": history_source,
            "displayed_choice": displayed_choice,
            "displayed_feedback_type": displayed_feedback_type,
            "strategy_scores": {
                "fairness": classification.fairness,
                "risk": classification.risk,
                "expertise": classification.expertise,
                "other": classification.other,
            },
            "primary_strategy": classification.primary_strategy,
            "strategy_confidence": classification.confidence,
            "classifier_name": classification.classifier,
            "classifier_ok": classification.ok,
            "classifier_error": classification.error,
            "classifier_raw": classification.raw,
            "target_scores": {
                "fairness": response.scores.fairness,
                "risk": response.scores.risk,
                "expertise": response.scores.expertise,
                "hits": response.scores.hits,
                "total_hits": response.scores.total_hits,
                "intensity": response.scores.intensity,
            },
            "target_p_a": response.p_a,
            "target_p_a_noiseless": response.p_a_noiseless,
            "target_logit": response.logit,
            "target_logit_noise": response.logit_noise,
            "target_choice": response.choice,
            "episode_seed": episode_seed,
            "round_seed": round_seed,
            "master_seed": cfg.seed,
            "model_name": cfg.model.model,
            "provider": cfg.model.provider,
            "objective": objective,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        }
        records.append(record)
        if progress:
            progress(
                "    r%-2d %-10s -> %s  P(A)=%.2f  choice=%s"
                % (r, classification.primary_strategy, active_type, response.p_a, response.choice)
            )

    return EpisodeResult(episode_id=spec.episode_id, records=records, own_history=own_history)


# --------------------------------------------------------------------------
# Experiment runner
# --------------------------------------------------------------------------


@dataclass
class ExperimentResult:
    run_id: str
    log_path: str
    manifest_path: str
    n_records: int
    n_episodes: int
    records: List[Dict[str, Any]] = field(default_factory=list)


def run_experiment(
    cfg: ExperimentConfig,
    provider: Optional[BaseProvider] = None,
    classifier=None,
    run_id: Optional[str] = None,
    out_dir: Optional[str] = None,
    keep_records: bool = True,
    progress: Optional[ProgressFn] = None,
) -> ExperimentResult:
    """Run every episode of every configured condition and log it all."""
    run_id = run_id or "%s_%s" % (cfg.experiment_id, time.strftime("%Y%m%d-%H%M%S"))
    out_dir = out_dir or cfg.out_dir
    log_path = "%s/%s.jsonl" % (out_dir.rstrip("/"), run_id)
    manifest_path = "%s/%s.manifest.json" % (out_dir.rstrip("/"), run_id)
    if os.path.exists(log_path) and os.path.getsize(log_path) > 0:
        raise FileExistsError(
            "run log already exists: %s. Choose a new run_id; appending would "
            "duplicate episodes and invalidate uncertainty estimates." % log_path
        )

    provider = provider or make_provider(cfg.model)
    classifier = classifier or make_classifier(cfg.judge)
    scorer = KeywordPersuasionScorer(
        saturation_k=cfg.target_params.saturation_k,
        lexicon_half=scorer_lexicon_half_for(cfg.judge),
    )
    agent = FocalAgent(provider=provider)

    specs = build_episode_specs(cfg)
    donors = DonorRegistry()
    all_records: List[Dict[str, Any]] = []
    n_records = 0

    with JsonlWriter(log_path) as writer:
        for i, spec in enumerate(specs, start=1):
            if progress:
                progress(
                    "[%d/%d] %s (%s -> %s)"
                    % (i, len(specs), spec.episode_id, spec.initial_target_type, spec.final_target_type)
                )
            result = run_episode(
                spec=spec,
                cfg=cfg,
                agent=agent,
                classifier=classifier,
                scorer=scorer,
                run_id=run_id,
                donors=donors,
                progress=progress,
            )
            for rec in result.records:
                writer.write(rec)
                n_records += 1
                if keep_records:
                    all_records.append(rec)
            if spec.condition.name == "full_history":
                donors.add(
                    spec.episode_index,
                    spec.initial_target_type,
                    spec.episode_id,
                    result.own_history,
                )

    manifest = {
        "run_id": run_id,
        "experiment_id": cfg.experiment_id,
        "config": cfg.as_dict(),
        "provider": provider.describe(),
        "classifier": classifier.describe(),
        "target_scorer": {
            "name": scorer.name,
            "saturation_k": scorer.saturation_k,
            "lexicon_half": scorer.lexicon_half,
        },
        "n_episodes": len(specs),
        "n_records": n_records,
        "log_path": log_path,
    }
    from .focal_agent import SYSTEM_PROMPT_TEMPLATE, INSTRUCTION

    manifest["focal_system_prompt_template"] = SYSTEM_PROMPT_TEMPLATE
    manifest["focal_instruction"] = INSTRUCTION
    manifest["focal_objective"] = DEFAULT_OBJECTIVE
    write_manifest(manifest_path, manifest)

    return ExperimentResult(
        run_id=run_id,
        log_path=log_path,
        manifest_path=manifest_path,
        n_records=n_records,
        n_episodes=len(specs),
        records=all_records,
    )
