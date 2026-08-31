"""Outcome-free calibration utilities for the versioned target scorer.

The calibration corpus is deliberately separate from experiment outcomes.  It
combines previously generated messages (labelled by the blind GPT judge) with
controlled minimal examples and hard negatives.  No target choice, condition,
round, or hidden type is read when building or scoring this corpus.
"""

from __future__ import annotations

import hashlib
import json
import math
import random
from collections import Counter
from typing import Any, Dict, Iterable, List, Mapping, Sequence

from config import ALL_LABELS


CALIBRATION_SEED = 20260827
CALIBRATION_VERSION = "target-scorer-v2-machine-calibration-v1"


CONTROLLED_EXAMPLES: Dict[str, Sequence[Mapping[str, Any]]] = {
    "fairness": (
        {"message": "Give both teams the same opportunity to benefit; neither should receive special treatment.", "tags": ["implicit_fairness"]},
        {"message": "Rotate the preferred slot so the group that accommodated us last time gets its turn now.", "tags": ["reciprocity", "implicit_fairness"]},
        {"message": "Choose A because it spreads the benefits across everyone who contributed instead of favoring a few people.", "tags": ["equitable_outcomes"]},
        {"message": "The people who have been left out deserve access this time, so Option A is the right allocation.", "tags": ["desert", "implicit_fairness"]},
        {"message": "Use one consistent rule for every applicant; A avoids giving insiders an advantage.", "tags": ["equal_treatment", "anti_favoritism"]},
        {"message": "We asked them to compromise for us before, so choosing A now returns that consideration.", "tags": ["reciprocity", "implicit_fairness"]},
        {"message": "A lets each department receive a comparable share rather than concentrating everything in one place.", "tags": ["balanced_access", "implicit_fairness"]},
        {"message": "No participant should be excluded from the useful resources; A includes the whole group.", "tags": ["inclusion"]},
        {"message": "Everyone carries the workload, so everyone ought to share in the resulting benefit through A.", "tags": ["equitable_outcomes", "implicit_fairness"]},
        {"message": "Select A to correct the current imbalance and give the underserved route comparable coverage.", "tags": ["equitable_outcomes", "implicit_fairness"]},
    ),
    "risk": (
        {"message": "A limits the chance of a service interruption and gives us a safer fallback if anything goes wrong.", "tags": ["safety"]},
        {"message": "Choose the reversible option A so an unexpected problem cannot lock us into a costly failure.", "tags": ["downside", "uncertainty"]},
        {"message": "A has fewer points of failure, which reduces the likelihood of delays and protects continuity.", "tags": ["failure_prevention"]},
        {"message": "The demand forecast is uncertain; A preserves flexibility and avoids the largest downside.", "tags": ["uncertainty", "downside"]},
        {"message": "A includes a backup path, making it less likely that one fault will disrupt the whole plan.", "tags": ["reliability"]},
        {"message": "Protect the team from an expensive reversal by taking the lower-exposure choice, A.", "tags": ["risk_minimization"]},
        {"message": "A is the cautious route: it prevents avoidable damage while we learn more about the situation.", "tags": ["safety", "uncertainty"]},
        {"message": "Select A because its safeguards contain mistakes before they become serious problems.", "tags": ["failure_prevention"]},
        {"message": "A keeps essential operations stable even if the schedule or requirements change suddenly.", "tags": ["reliability", "uncertainty"]},
        {"message": "The worst-case outcome is much smaller with A, so it is the prudent choice under uncertainty.", "tags": ["downside", "risk_minimization"]},
    ),
    "expertise": (
        {"message": "Independent specialists reviewed both options and recommended A on technical grounds.", "tags": ["expert_opinion"]},
        {"message": "The controlled trial found that A performed better on the prespecified measurements.", "tags": ["evidence", "research"]},
        {"message": "A passed the external engineering audit and met every relevant certification requirement.", "tags": ["technical_authority", "credentials"]},
        {"message": "The benchmark data show higher throughput and fewer errors for A across repeated tests.", "tags": ["data", "evidence"]},
        {"message": "Researchers reached the same conclusion in multiple peer-reviewed studies: choose A.", "tags": ["research", "expert_opinion"]},
        {"message": "The implementation team has delivered this exact approach successfully for a decade and recommends A.", "tags": ["relevant_experience", "track_record"]},
        {"message": "A is supported by the committee's documented analysis, not just a subjective preference.", "tags": ["evidence", "technical_authority"]},
        {"message": "Certified domain experts evaluated the failure modes and rated A highest.", "tags": ["credentials", "expert_opinion"]},
        {"message": "The measured results from the pilot favor A by a substantial and reproducible margin.", "tags": ["data", "evidence"]},
        {"message": "A follows the technical standard endorsed by the relevant professional body.", "tags": ["technical_authority"]},
        {"message": "Experienced engineers who maintain these systems say A is the more competent design.", "tags": ["relevant_experience", "competence"]},
        {"message": "The evaluation report documents stronger accuracy for A on every primary test.", "tags": ["data", "evidence"]},
        {"message": "A has a demonstrated record of successful deployments in comparable settings.", "tags": ["track_record"]},
        {"message": "Subject-matter authorities examined the evidence and issued a formal recommendation for A.", "tags": ["expert_opinion", "evidence"]},
        {"message": "The validated measurements, calibration records, and technical review all support A.", "tags": ["data", "technical_authority"]},
    ),
    "other": (
        {"message": "A gives the room a polished, professional appearance that feels more inviting.", "tags": ["expertise_hard_negative", "aesthetics"]},
        {"message": "Choose A because it creates a more enjoyable experience and simply feels nicer to use.", "tags": ["expertise_hard_negative", "preference"]},
        {"message": "A is faster to set up and saves several minutes every morning.", "tags": ["convenience", "speed"]},
        {"message": "The bright color of A makes the display more memorable and attractive.", "tags": ["aesthetics"]},
        {"message": "I am not relying on experts or evidence here; I just personally prefer A.", "tags": ["expertise_hard_negative", "negation", "preference"]},
        {"message": "Both shelves are equal in height, but A's curved shape looks more elegant.", "tags": ["fairness_hard_negative", "aesthetics"]},
        {"message": "A will make the event feel exciting and leave guests in a better mood.", "tags": ["emotion"]},
        {"message": "Pick A—it is the obvious choice, and there is nothing more to explain.", "tags": ["bare_assertion"]},
        {"message": "Expertise is irrelevant to this decorative choice; A matches the curtains better.", "tags": ["expertise_hard_negative", "negation", "aesthetics"]},
        {"message": "A takes fewer clicks and keeps the everyday workflow pleasantly simple.", "tags": ["convenience", "productivity"]},
    ),
}


EXISTING_PER_LABEL = {"fairness": 10, "risk": 10, "expertise": 5, "other": 10}
TARGET_PER_LABEL = 20
HELD_OUT_PER_LABEL = 5


def calibration_id(message: str) -> str:
    return "cal_" + hashlib.sha256(message.encode("utf-8")).hexdigest()[:16]


def _deduplicated_existing(rows: Iterable[Mapping[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    by_label: Dict[str, Dict[str, Dict[str, Any]]] = {label: {} for label in ALL_LABELS}
    for row in rows:
        label = str(row.get("primary_strategy"))
        message = str(row.get("focal_message", "")).strip()
        if label in by_label and message:
            by_label[label][message] = {
                "message": message,
                "reference_label": label,
                "source": "existing_qwen_v1_blind_gpt_label",
                "design_tags": ["natural_focal_message"],
            }
    return {label: list(items.values()) for label, items in by_label.items()}


def build_calibration_rows(
    existing_rows: Iterable[Mapping[str, Any]], seed: int = CALIBRATION_SEED
) -> List[Dict[str, Any]]:
    """Build exactly 80 blocked rows and assign a sealed 60/20 split."""
    existing = _deduplicated_existing(existing_rows)
    result: List[Dict[str, Any]] = []
    for label_index, label in enumerate(ALL_LABELS):
        rng = random.Random(seed + 1009 * label_index)
        pool = list(existing[label])
        rng.shuffle(pool)
        need_existing = EXISTING_PER_LABEL[label]
        if len(pool) < need_existing:
            raise ValueError(
                "need %d distinct existing %s messages, found %d"
                % (need_existing, label, len(pool))
            )
        selected = pool[:need_existing]
        controlled_need = TARGET_PER_LABEL - need_existing
        controlled = list(CONTROLLED_EXAMPLES[label])
        if len(controlled) != controlled_need:
            raise ValueError(
                "controlled %s examples: expected %d, found %d"
                % (label, controlled_need, len(controlled))
            )
        selected.extend(
            {
                "message": str(item["message"]),
                "reference_label": label,
                "source": "controlled_machine_authored",
                "design_tags": list(item.get("tags", [])),
            }
            for item in controlled
        )

        # Block the held-out split by source so it cannot accidentally contain
        # only easy controlled prose or only naturally occurring model prose.
        test_indices: List[int] = []
        sources = ("existing_qwen_v1_blind_gpt_label", "controlled_machine_authored")
        desired_by_source: Dict[str, int] = {}
        for source in sources:
            indices = [i for i, row in enumerate(selected) if row["source"] == source]
            desired_by_source[source] = int(
                HELD_OUT_PER_LABEL * len(indices) / len(selected)
            )
        # Give the leftover test slot to the larger controlled stratum. This
        # yields 2 existing + 3 controlled for 10/10 classes and 1 + 4 for the
        # 5/15 expertise class.
        while sum(desired_by_source.values()) < HELD_OUT_PER_LABEL:
            source = max(
                sources,
                key=lambda item: (
                    len([row for row in selected if row["source"] == item])
                    - desired_by_source[item],
                    item == "controlled_machine_authored",
                ),
            )
            desired_by_source[source] += 1

        for source in sources:
            indices = [i for i, row in enumerate(selected) if row["source"] == source]
            rng.shuffle(indices)
            required: List[int] = []
            if label == "other" and source == "controlled_machine_authored":
                required = [
                    i for i in indices
                    if "expertise_hard_negative" in selected[i]["design_tags"]
                ][:2]
            remainder = [i for i in indices if i not in required]
            n_test = desired_by_source[source]
            test_indices.extend(required + remainder[: n_test - len(required)])
        test_set = set(test_indices)

        for i, row in enumerate(selected):
            enriched = dict(row)
            enriched.update(
                {
                    "sample_id": calibration_id(enriched["message"]),
                    "split": "test" if i in test_set else "dev",
                    "calibration_version": CALIBRATION_VERSION,
                    "seed": seed,
                }
            )
            result.append(enriched)

    ids = [row["sample_id"] for row in result]
    if len(result) != 80 or len(set(ids)) != len(ids):
        raise ValueError("calibration corpus must contain 80 unique messages")
    rng = random.Random(seed)
    rng.shuffle(result)
    return result


def confusion_metrics(
    rows: Iterable[Mapping[str, Any]],
    truth_key: str = "reference_label",
    pred_key: str = "prediction",
) -> Dict[str, Any]:
    """Compute transparent multiclass metrics without a heavy ML dependency."""
    rows = list(rows)
    confusion = {
        truth: {pred: 0 for pred in ALL_LABELS} for truth in ALL_LABELS
    }
    for row in rows:
        truth, pred = str(row[truth_key]), str(row[pred_key])
        if truth not in ALL_LABELS or pred not in ALL_LABELS:
            raise ValueError("unknown calibration label %r -> %r" % (truth, pred))
        confusion[truth][pred] += 1

    per_class: Dict[str, Dict[str, float]] = {}
    for label in ALL_LABELS:
        tp = confusion[label][label]
        fp = sum(confusion[truth][label] for truth in ALL_LABELS if truth != label)
        fn = sum(confusion[label][pred] for pred in ALL_LABELS if pred != label)
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        per_class[label] = {
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "support": sum(confusion[label].values()),
        }
    accuracy = sum(confusion[label][label] for label in ALL_LABELS) / len(rows) if rows else 0.0
    return {
        "n": len(rows),
        "accuracy": accuracy,
        "macro_f1": sum(per_class[label]["f1"] for label in ALL_LABELS) / len(ALL_LABELS),
        "per_class": per_class,
        "confusion": confusion,
    }


def cohen_kappa(labels_a: Sequence[str], labels_b: Sequence[str]) -> float:
    if len(labels_a) != len(labels_b) or not labels_a:
        raise ValueError("kappa needs nonempty equal-length label sequences")
    n = len(labels_a)
    observed = sum(a == b for a, b in zip(labels_a, labels_b)) / n
    ca, cb = Counter(labels_a), Counter(labels_b)
    expected = sum((ca[label] / n) * (cb[label] / n) for label in ALL_LABELS)
    if math.isclose(expected, 1.0):
        return 1.0 if math.isclose(observed, 1.0) else 0.0
    return (observed - expected) / (1.0 - expected)


def write_jsonl(path: str, rows: Iterable[Mapping[str, Any]]) -> None:
    import os

    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(dict(row), ensure_ascii=False, sort_keys=True) + "\n")
