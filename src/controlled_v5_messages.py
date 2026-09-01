"""External, calibratable candidate banks for controlled-choice V5."""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence

from config import CONTROLLED_V5_VERSION, STRATEGIES
from .controlled_messages import MessageCandidate
from .controlled_protocol import ControlledProtocol
from .seeding import derive_seed, rng


V5_SELECTED_BANK_STATUS = "selected_bank_validated"


def _canonical_hash(payload: Mapping[str, Any]) -> str:
    canonical = json.dumps(
        payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _portable_source_path(path: str) -> str:
    """Keep in-repository provenance portable without hiding external paths."""
    absolute = os.path.abspath(path)
    working_root = os.path.abspath(os.getcwd())
    try:
        inside_working_root = os.path.commonpath([absolute, working_root]) == working_root
    except ValueError:
        inside_working_root = False
    return os.path.relpath(absolute, working_root) if inside_working_root else absolute


def audit_v5_bank_payload(payload: Mapping[str, Any]) -> Dict[str, Any]:
    splits = payload.get("splits", {})
    checks: Dict[str, bool] = {
        "split_names": set(splits) == {"development", "heldout"},
        "created_before_calibration": payload.get("created_before_v5_focal_calibration")
        is True,
    }
    ids: List[str] = []
    texts: List[str] = []
    counts: Dict[str, Dict[str, int]] = {}
    word_means: Dict[str, Dict[str, float]] = {}
    literal_label_hits: List[str] = []
    structure_ok = True
    for split in ("development", "heldout"):
        bank = splits.get(split, {}) if isinstance(splits, Mapping) else {}
        checks["%s_frames" % split] = set(bank) == set(STRATEGIES)
        counts[split] = {}
        word_means[split] = {}
        for frame in STRATEGIES:
            entries = bank.get(frame, []) if isinstance(bank, Mapping) else []
            counts[split][frame] = len(entries)
            lengths: List[int] = []
            for entry in entries:
                if not isinstance(entry, Mapping):
                    structure_ok = False
                    continue
                candidate_id = str(entry.get("candidate_id", ""))
                text = str(entry.get("template", ""))
                ids.append(candidate_id)
                texts.append(text)
                lengths.append(len(text.replace("{a}", "OptionA").split()))
                structure_ok &= bool(candidate_id) and text.count("{a}") == 1
                structure_ok &= "{b}" not in text
                lowered = text.lower()
                literal_label_hits.extend(
                    label for label in STRATEGIES if label in lowered
                )
            word_means[split][frame] = (
                sum(lengths) / float(len(lengths)) if lengths else 0.0
            )
        split_counts = list(counts[split].values())
        checks["%s_equal_frame_counts" % split] = bool(split_counts) and len(
            set(split_counts)
        ) == 1
        means = list(word_means[split].values())
        checks["%s_mean_word_gap" % split] = bool(means) and max(means) - min(
            means
        ) <= 3.0
    checks.update(
        {
            "entry_structure": structure_ok,
            "unique_candidate_ids": bool(ids) and len(ids) == len(set(ids)),
            "unique_templates": bool(texts) and len(texts) == len(set(texts)),
            "registered_labels_not_literal": not literal_label_hits,
        }
    )
    return {
        "pass": all(checks.values()),
        "checks": checks,
        "counts": counts,
        "mean_words": word_means,
        "literal_label_hits": sorted(set(literal_label_hits)),
        "sha256": _canonical_hash(payload),
    }


@dataclass(frozen=True)
class V5MessageBank:
    payload: Dict[str, Any]
    source_path: str

    @classmethod
    def load(cls, path: str, require_validated: bool = False) -> "V5MessageBank":
        with open(path, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
        audit = audit_v5_bank_payload(payload)
        if not audit["pass"]:
            failed = sorted(name for name, passed in audit["checks"].items() if not passed)
            raise ValueError("invalid V5 message bank: %s" % ", ".join(failed))
        if require_validated and payload.get("status") != V5_SELECTED_BANK_STATUS:
            raise ValueError(
                "V5 confirmatory use requires status %r" % V5_SELECTED_BANK_STATUS
            )
        return cls(payload=payload, source_path=_portable_source_path(path))

    def manifest(self) -> Dict[str, Any]:
        return json.loads(json.dumps(self.payload))

    def sha256(self) -> str:
        return _canonical_hash(self.payload)

    def candidate_set(
        self,
        scenario,
        episode_index: int,
        round_index: int,
        heldout_start_round: int,
        seed: int,
    ) -> List[MessageCandidate]:
        if round_index < 1:
            raise ValueError("round_index must be 1-based")
        split = "heldout" if round_index >= heldout_start_round else "development"
        bank = self.payload["splits"][split]
        base_order = list(
            rng("controlled_v5_slot_order", seed, episode_index).permutation(
                len(STRATEGIES)
            )
        )
        rotation = (round_index - 1) % len(STRATEGIES)
        order = base_order[rotation:] + base_order[:rotation]
        frame_order = [STRATEGIES[int(index)] for index in order]
        candidates: List[MessageCandidate] = []
        for slot, frame in enumerate(frame_order, start=1):
            entries: Sequence[Mapping[str, str]] = bank[frame]
            template_index = derive_seed(
                "controlled_v5_template",
                seed,
                episode_index,
                round_index,
                scenario.id,
                split,
                frame,
            ) % len(entries)
            entry = entries[template_index]
            text = str(entry["template"]).format(a=scenario.option_a)
            candidates.append(
                MessageCandidate(
                    slot=slot,
                    candidate_id="%s-%s" % (entry["candidate_id"], scenario.id),
                    message=" ".join(text.split()),
                    frame=frame,
                    split=split,
                    template_index=int(template_index),
                )
            )
        return candidates


def make_v5_protocol(
    bank_path: str,
    require_validated: bool = False,
    manifest_metadata: Mapping[str, Any] | None = None,
) -> ControlledProtocol:
    bank = V5MessageBank.load(bank_path, require_validated=require_validated)
    return ControlledProtocol(
        version=CONTROLLED_V5_VERSION,
        candidate_builder=bank.candidate_set,
        bank_manifest_builder=bank.manifest,
        bank_hash_builder=bank.sha256,
        strict_selection=True,
        constrained_choices=("1", "2", "3"),
        bank_source=bank.source_path,
        manifest_metadata=manifest_metadata,
    )
