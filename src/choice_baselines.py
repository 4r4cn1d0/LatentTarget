"""Exploratory, grouped prediction of existing controlled message choices.

This module never calls a model provider. Predictors accept only explicit
histories, not the analysis metadata that contains hidden target identities.
See docs/BASELINE_COMPARISON_PLAN_20260907.md for the declared comparison.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from typing import Any, Mapping, Sequence

import numpy as np


FRAMES = ("fairness", "risk", "expertise")
OWN_CONDITIONS = ("full_history", "swap", "elicited_full_history", "elicited_swap")


@dataclass(frozen=True)
class ChoiceData:
    """Keep predictive histories separate from response and audit metadata."""

    histories: tuple[tuple[tuple[int, int], ...], ...]
    y: np.ndarray
    groups: np.ndarray
    rounds: np.ndarray
    conditions: np.ndarray
    valid: np.ndarray
    metadata: tuple[dict, ...]

    @property
    def fitting_mask(self) -> np.ndarray:
        return np.isin(self.conditions, OWN_CONDITIONS) & (self.rounds >= 2)


def prepare_data(records: Sequence[Mapping[str, Any]]) -> ChoiceData:
    """Fail closed on incomplete logs or inconsistent visible histories.

    Registered annotations map visible message text to a frame. Current and
    future rewards do not enter a row's predictive history. Source rows are
    used solely to verify that recorded visible feedback is authentic.
    """
    if not records:
        raise ValueError("empty log")
    rows = sorted(records, key=lambda r: (str(r["episode_id"]), int(r["round"])))
    by_episode: dict[str, list] = {}
    text_frame: dict[str, int] = {}
    for row in rows:
        by_episode.setdefault(row["episode_id"], []).append(row)
        candidates = row["candidates"]
        if sorted(c["frame"] for c in candidates) != sorted(FRAMES):
            raise ValueError("expected one candidate per frame")
        if sorted(c["slot"] for c in candidates) != [1, 2, 3]:
            raise ValueError("invalid candidate slots")
        for candidate in candidates:
            text, frame = candidate["message"], FRAMES.index(candidate["frame"])
            if text in text_frame and text_frame[text] != frame:
                raise ValueError("ambiguous message to frame mapping")
            text_frame[text] = frame
        selected = [c for c in candidates if c["slot"] == row["selected_slot"]]
        if (selected[0]["frame"] != row["selected_frame"]
                or selected[0]["message"] != row["selected_message"]):
            raise ValueError("selected candidate mapping disagrees")
        if row["target_choice"] not in ("A", "B"):
            raise ValueError("invalid target choice")
        if type(row["selection_valid"]) is not bool or type(row["fallback_used"]) is not bool:
            raise ValueError("missing or invalid response validity flag")
        if row["selection_valid"] == row["fallback_used"]:
            raise ValueError("fallback must be the inverse of selection validity")
    for episode in by_episode.values():
        first = episode[0]
        if [r["round"] for r in episode] != list(range(1, first["n_rounds"] + 1)):
            raise ValueError("duplicate or incomplete episode")
        for field in ("episode_index", "condition", "n_rounds", "history_mode"):
            if any(r[field] != first[field] for r in episode):
                raise ValueError("inconsistent episode metadata: " + field)
    histories, metadata = [], []
    for row in rows:
        history = row["visible_history"]
        source = row["history_source_episode_id"]
        mode = row["history_mode"]
        if mode == "none":
            if history or source is not None:
                raise ValueError("no history condition exposes history")
        else:
            if source not in by_episode:
                raise ValueError("missing history donor")
            donor = by_episode[source]
            if donor[0]["episode_index"] != row["episode_index"]:
                raise ValueError("cross seed donor would leak between folds")
            if mode == "full" and source != row["episode_id"]:
                raise ValueError("own history source disagrees")
            if mode not in ("full", "shuffled"):
                raise ValueError("unsupported history mode: " + mode)
            if len(history) != row["round"] - 1:
                raise ValueError("incomplete visible history")
            for index, entry in enumerate(history):
                original = donor[index]
                if (entry["round"] != index + 1
                        or entry["selected_message"] != original["selected_message"]
                        or entry["choice"] != original["target_choice"]
                        or entry["scenario_title"] != original["scenario"]["title"]):
                    raise ValueError("visible history does not match earlier source rows")
        histories.append(tuple((text_frame[e["selected_message"]], int(e["choice"] == "A"))
                               for e in history))
        metadata.append({k: row[k] for k in (
            "episode_id", "episode_index", "round", "condition", "selected_frame",
            "selection_valid", "fallback_used", "hidden_target_type",
            "initial_target_type", "final_target_type", "swap_has_occurred",
        )})
    return ChoiceData(
        histories=tuple(histories),
        y=np.array([FRAMES.index(r["selected_frame"]) for r in rows]),
        groups=np.array([r["episode_index"] for r in rows]),
        rounds=np.array([r["round"] for r in rows]),
        conditions=np.array([r["condition"] for r in rows]),
        valid=np.array([r["selection_valid"] for r in rows]),
        metadata=tuple(metadata),
    )


def group_folds(groups: Sequence[int], n_folds: int, seed: int) -> list[np.ndarray]:
    unique = np.unique(groups)
    if n_folds < 2 or len(unique) < n_folds:
        raise ValueError("not enough independent groups for the requested folds")
    return list(np.array_split(np.random.default_rng(seed).permutation(unique), n_folds))


def balanced_weights(data: ChoiceData, mask: np.ndarray) -> np.ndarray:
    """Equal condition weight; complete seed bundles have equal episode counts."""
    if not np.any(mask):
        raise ValueError("empty fitting/evaluation subset")
    conditions = data.conditions[mask]
    names, counts = np.unique(conditions, return_counts=True)
    return np.array([1 / (len(names) * counts[np.flatnonzero(names == name)[0]])
                     for name in conditions])


def training_prior(data: ChoiceData, mask: np.ndarray) -> np.ndarray:
    weights = balanced_weights(data, mask)
    # Scale to the number of selected rows before adding one pseudo observation.
    counts = np.bincount(data.y[mask], weights=weights * mask.sum(), minlength=3)
    return (counts + 1) / (counts.sum() + 3)


class HistoryFeatures:
    """Deterministic history summaries. No labels or hidden metadata accepted."""

    def __init__(self, histories: Sequence[Sequence[tuple[int, int]]], p_match=.72, p_mismatch=.38):
        if not 0 < p_mismatch < p_match < 1:
            raise ValueError("require strictly interior ordered likelihoods")
        self.n = len(histories)
        self.p_match, self.p_mismatch = p_match, p_mismatch
        self.length = np.array([len(h) for h in histories])
        self.actions = np.full((self.n, max(self.length, default=0)), -1, dtype=int)
        self.rewards = np.zeros_like(self.actions, dtype=float)
        for i, history in enumerate(histories):
            for t, (action, reward) in enumerate(history):
                if action not in (0, 1, 2) or reward not in (0, 1):
                    raise ValueError("invalid visible action or reward")
                self.actions[i, t], self.rewards[i, t] = action, reward
        self.last = np.zeros((self.n, 3))
        self.win_stay = np.zeros((self.n, 3))
        self.win_stay[:, 2] = 1
        self.frequency = np.ones((self.n, 3))
        for i, history in enumerate(histories):
            if history:
                self.last[i, history[-1][0]] = 1
                if history[-1][1]:
                    self.win_stay[i] = self.last[i]
            for action, _ in history:
                self.frequency[i, action] += 1
        self.frequency /= self.frequency.sum(1, keepdims=True)
        self.cache: dict[tuple[str, float], np.ndarray] = {}

    def reward_values(self, alpha: float) -> np.ndarray:
        if not 0 <= alpha <= 1:
            raise ValueError("alpha must be a probability")
        key = ("reward", alpha)
        if key not in self.cache:
            q = np.full((self.n, 3), .5)
            for t in range(self.actions.shape[1]):
                ix = np.flatnonzero(self.length > t)
                actions = self.actions[ix, t]
                q[ix, actions] += alpha * (self.rewards[ix, t] - q[ix, actions])
            self.cache[key] = q
        return self.cache[key]

    def posterior(self, hazard: float) -> np.ndarray:
        if not 0 <= hazard <= 1:
            raise ValueError("hazard must be a probability")
        key = ("belief", hazard)
        if key not in self.cache:
            p = np.full((self.n, 3), 1 / 3)
            for t in range(self.actions.shape[1]):
                ix = np.flatnonzero(self.length > t)
                likelihood = np.full((len(ix), 3), self.p_mismatch)
                likelihood[np.arange(len(ix)), self.actions[ix, t]] = self.p_match
                likelihood = np.where(self.rewards[ix, t, None] == 1, likelihood, 1 - likelihood)
                p[ix] *= likelihood
                p[ix] /= p[ix].sum(1, keepdims=True)
                # Transition after each observation, including to the current
                # interaction. There is no true swap time in this interface.
                p[ix] = (1 - hazard) * p[ix] + hazard / 3
            self.cache[key] = p
        return self.cache[key]

    def values(self, family: str, params: Mapping[str, float]) -> np.ndarray:
        if family == "history_frequency":
            return self.frequency
        if family == "reward_learning":
            return self.reward_values(params["alpha"])
        if family in ("belief_static", "belief_dynamic"):
            return self.p_mismatch + (self.p_match - self.p_mismatch) * self.posterior(params.get("hazard", 0))
        raise ValueError("family has no value features: " + family)


def parameter_grid(family: str, plan: Mapping) -> list[dict]:
    if family in ("uniform", "expertise", "marginal"):
        return [{}]
    if family in ("repeat_last", "win_stay_expertise"):
        return [{"strength": x} for x in plan["repeat_strength"]]
    extras = [{}]
    if family == "reward_learning":
        extras = [{"alpha": x} for x in plan["alpha"]]
    elif family == "belief_dynamic":
        extras = [{"hazard": x} for x in plan["hazard"]]
    elif family not in ("history_frequency", "belief_static"):
        raise ValueError("unknown baseline family")
    return [dict(extra, beta=b, stickiness=s, prior_power=p)
            for extra, b, s, p in product(extras, plan["beta"], plan["stickiness"], plan["prior_power"])]


def predict(features: HistoryFeatures, family: str, params: Mapping[str, float],
            prior: np.ndarray, lapse: float = .02) -> np.ndarray:
    if not 0 < lapse < 1 or prior.shape != (3,) or np.any(prior <= 0) or not np.isclose(prior.sum(), 1):
        raise ValueError("invalid lapse or prior")
    base = np.broadcast_to(prior, (features.n, 3)).copy()
    if family == "uniform":
        p = np.full_like(base, 1 / 3)
    elif family == "expertise":
        p = np.zeros_like(base)
        p[:, 2] = 1
    elif family == "marginal":
        p = base
    elif family in ("repeat_last", "win_stay_expertise"):
        rule = features.last.copy() if family == "repeat_last" else features.win_stay.copy()
        if family == "repeat_last":
            rule[features.length == 0] = prior
        strength = params["strength"]
        if not 0 <= strength <= 1:
            raise ValueError("invalid repetition strength")
        p = strength * rule + (1 - strength) * base
    else:
        logits = (params["beta"] * features.values(family, params)
                  + params["prior_power"] * np.log(prior)[None, :]
                  + params["stickiness"] * features.last)
        logits -= logits.max(1, keepdims=True)
        p = np.exp(logits)
        p /= p.sum(1, keepdims=True)
    p = (1 - lapse) * p + lapse / 3
    if not np.all(np.isfinite(p)) or np.any(p <= 0) or not np.allclose(p.sum(1), 1):
        raise ValueError("invalid predictive probabilities")
    return p


def score_predictions(p: np.ndarray, y: np.ndarray) -> dict[str, np.ndarray]:
    if p.shape != (len(y), 3) or not np.isfinite(p).all() or np.any(p <= 0) or not np.allclose(p.sum(1), 1):
        raise ValueError("expected positive normalized three class probabilities")
    if not np.isin(y, (0, 1, 2)).all():
        raise ValueError("invalid choice label")
    tied = p == p.max(1, keepdims=True)
    return {
        "log_loss": -np.log(p[np.arange(len(y)), y]),
        "brier": ((p - np.eye(3)[y]) ** 2).sum(1),
        "accuracy": tied[np.arange(len(y)), y] / tied.sum(1),
    }


def select_on_training(data: ChoiceData, features: HistoryFeatures, train_groups: Sequence[int],
                       plan: Mapping, seed: int) -> dict:
    """Inner validation never references responses in outer test groups."""
    outer_train = np.isin(data.groups, train_groups) & data.fitting_mask
    inner_folds = group_folds(train_groups, plan["inner_folds"], seed)
    families = plan["simple_families"] + plan["belief_families"]
    grids = {name: parameter_grid(name, plan) for name in families}
    losses = {name: np.zeros(len(grids[name])) for name in families}
    inner_audit = []
    for held in inner_folds:
        val_mask = outer_train & np.isin(data.groups, held)
        fit_mask = outer_train & ~np.isin(data.groups, held)
        prior = training_prior(data, fit_mask)
        weights = balanced_weights(data, val_mask)
        # Weight folds by group count when running small synthetic tests with
        # unequal fold sizes. The declared real design is exactly balanced.
        fold_weight = len(held) / len(train_groups)
        inner_audit.append({"train_groups": np.unique(data.groups[fit_mask]).tolist(),
                            "validation_groups": held.tolist()})
        for family in families:
            for index, params in enumerate(grids[family]):
                p = predict(features, family, params, prior, plan["lapse"])
                losses[family][index] += fold_weight * float(weights @ score_predictions(p[val_mask], data.y[val_mask])["log_loss"])
    selected = {}
    for family in families:
        best = int(np.argmin(losses[family]))  # Declared grid order resolves ties.
        selected[family] = {"params": grids[family][best], "validation_log_loss": float(losses[family][best]),
                            "grid": [{"params": p, "validation_log_loss": float(loss)}
                                     for p, loss in zip(grids[family], losses[family])]}
    winners = {label: min(plan[key], key=lambda f: selected[f]["validation_log_loss"])
               for label, key in (("simple_selected", "simple_families"), ("belief_selected", "belief_families"))}
    return {"families": selected, "winners": winners, "inner_folds": inner_audit}


def nested_predictions(data: ChoiceData, plan: Mapping, progress=None) -> tuple[dict, list, np.ndarray]:
    groups = np.unique(data.groups)
    folds = group_folds(groups, plan["outer_folds"], plan["split_seed"])
    features = HistoryFeatures(data.histories, plan["p_match"], plan["p_mismatch"])
    families = plan["simple_families"] + plan["belief_families"]
    predictions = {f: np.full((len(data.y), 3), np.nan)
                   for f in families + ["simple_selected", "belief_selected"]}
    fold_ids = np.full(len(data.y), -1)
    audit = []
    for fold_id, held in enumerate(folds):
        train = groups[~np.isin(groups, held)]
        choice = select_on_training(data, features, train, plan, plan["split_seed"] + fold_id + 1)
        prior = training_prior(data, data.fitting_mask & np.isin(data.groups, train))
        mask = np.isin(data.groups, held)
        for family in families:
            p = predict(features, family, choice["families"][family]["params"], prior, plan["lapse"])
            predictions[family][mask] = p[mask]
        for label, winner in choice["winners"].items():
            predictions[label][mask] = predictions[winner][mask]
        fold_ids[mask] = fold_id
        audit.append({"fold": fold_id, "test_groups": held.tolist(), "train_groups": train.tolist(),
                      "training_prior": prior.tolist(), **choice})
        if progress:
            progress(f"fold {fold_id + 1}/{len(folds)} complete: {choice['winners']}")
    for p in predictions.values():
        score_predictions(p, data.y)  # Includes finite/coverage checks.
    if np.any(fold_ids < 0):
        raise AssertionError("some rows lack outer test predictions")
    return predictions, audit, fold_ids


def descriptive(values: Sequence[float], n_boot: int, seed: int) -> dict:
    x = np.asarray(values, dtype=float)
    if len(x) < 2 or not np.isfinite(x).all() or n_boot < 1:
        raise ValueError("need at least two finite independent bundles and positive bootstrap count")
    q1, q3 = np.quantile(x, [.25, .75])
    boot = x[np.random.default_rng(seed).integers(0, len(x), (n_boot, len(x)))].mean(1)
    return {"mean": float(x.mean()), "sd": float(x.std(ddof=1)), "median": float(np.median(x)),
            "min": float(x.min()), "max": float(x.max()), "n_groups": len(x),
            "iqr_outliers": int(((x < q1 - 1.5 * (q3 - q1)) | (x > q3 + 1.5 * (q3 - q1))).sum()),
            "ci_lo": float(np.quantile(boot, .025)), "ci_hi": float(np.quantile(boot, .975))}


def bundle_scores(data: ChoiceData, values: np.ndarray, mask: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    groups = np.unique(data.groups[mask])
    scores = []
    for group in groups:
        subset = mask & (data.groups == group)
        scores.append(float(balanced_weights(data, subset) @ values[subset]))
    return groups, np.array(scores)


def analysis_subsets(data: ChoiceData) -> dict[str, np.ndarray]:
    own = np.isin(data.conditions, OWN_CONDITIONS)
    swap = np.isin(data.conditions, ("swap", "elicited_swap"))
    stable = np.isin(data.conditions, ("full_history", "elicited_full_history"))
    later = data.rounds >= 2
    subsets = {"own_history": own & later, "own_history_valid_only": own & later & data.valid,
               "own_round_1": own & (data.rounds == 1), "own_late": own & (data.rounds >= 16),
               "swap_post": swap & (data.rounds >= 11), "swap_late": swap & (data.rounds >= 16)}
    for condition in np.unique(data.conditions):
        subsets["condition:" + condition] = (data.conditions == condition) & later
    for frame in FRAMES:
        subsets["stable_target:" + frame] = stable & later & np.array([r["hidden_target_type"] == frame for r in data.metadata])
    for a, b in product(FRAMES, repeat=2):
        if a != b:
            mask = swap & np.array([r["initial_target_type"] == a and r["final_target_type"] == b for r in data.metadata])
            subsets[f"swap_post:{a}_to_{b}"] = mask & (data.rounds >= 11)
            subsets[f"swap_late:{a}_to_{b}"] = mask & (data.rounds >= 16)
    for round_number in np.unique(data.rounds):
        subsets[f"own_round:{round_number}"] = own & (data.rounds == round_number)
    return subsets


def summarize(data: ChoiceData, predictions: Mapping[str, np.ndarray], plan: Mapping) -> dict:
    scores = {family: score_predictions(p, data.y) for family, p in predictions.items()}
    subsets = analysis_subsets(data)
    tables, contrasts, bundles = [], [], []
    for label, mask in subsets.items():
        if not np.any(mask):
            continue
        for family, metrics in scores.items():
            row = {"subset": label, "family": family, "n_rows": int(mask.sum()),
                   "n_invalid": int((mask & ~data.valid).sum()),
                   "n_episodes": len({data.metadata[i]["episode_id"] for i in np.flatnonzero(mask)})}
            for metric, values in metrics.items():
                groups, means = bundle_scores(data, values, mask)
                stats = descriptive(means, plan["n_boot"], plan["bootstrap_seed"])
                row.update({metric + "_" + k: v for k, v in stats.items()})
                if label == "own_history" and metric == "log_loss":
                    bundles.extend({"episode_index": int(g), "family": family, "log_loss": float(v)} for g, v in zip(groups, means))
            tables.append(row)
        for metric in ("log_loss", "brier", "accuracy"):
            delta = scores["simple_selected"][metric] - scores["belief_selected"][metric]
            groups, means = bundle_scores(data, delta, mask)
            contrasts.append({"subset": label, "metric": metric, "direction": "simple_minus_belief",
                              **descriptive(means, plan["n_boot"], plan["bootstrap_seed"])})
    diagnostics = []
    for condition in np.unique(data.conditions):
        mask = data.conditions == condition
        diagnostics.append({"condition": condition, "n_rows": int(mask.sum()),
                            "n_invalid": int((mask & ~data.valid).sum()),
                            "n_groups": len(np.unique(data.groups[mask])),
                            "n_episodes": len({data.metadata[i]["episode_id"] for i in np.flatnonzero(mask)}),
                            **{f"choice_share_{f}": float((data.y[mask] == j).mean()) for j, f in enumerate(FRAMES)}})
    calibration = []
    mask = data.fitting_mask
    # Multiclass reliability by class, descriptive row counts; no row IID CIs.
    for family in ("simple_selected", "belief_selected"):
        for frame, name in enumerate(FRAMES):
            p = predictions[family][mask, frame]
            y = (data.y[mask] == frame).astype(float)
            bins = np.minimum((p * 10).astype(int), 9)
            for bin_id in range(10):
                keep = bins == bin_id
                if keep.any():
                    calibration.append({"family": family, "frame": name, "bin": bin_id,
                                        "n_rows": int(keep.sum()), "mean_predicted": float(p[keep].mean()),
                                        "observed_frequency": float(y[keep].mean())})
    return {"metrics": tables, "contrasts": contrasts, "bundle_losses": bundles,
            "diagnostics": diagnostics, "calibration": calibration}
