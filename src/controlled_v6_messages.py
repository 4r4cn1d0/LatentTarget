"""Immutable triad banks for the controlled-choice V6 protocol.

V6 calibrates and selects complete three-message triads.  Confirmatory
candidate generation therefore makes exactly one triad choice per round and
only then assigns its registered frames to slots.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass
from itertools import permutations
from string import Formatter
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from config import (
    CONTROLLED_V6_CALIBRATION_THRESHOLDS,
    CONTROLLED_V6_VERSION,
    STRATEGIES,
)
from .controlled_messages import MessageCandidate
from .controlled_protocol import ControlledProtocol
from .scenarios import v6_scenario_sequence
from .seeding import rng


V6_SELECTED_BANK_STATUS = "selected_bank_validated"
V6_PROVISIONAL_POOL_STATUS = (
    "provisional_pool_not_semantically_or_focally_validated"
)
V6_POOL_TRIAD_COUNTS = {"development": 12, "heldout": 8}
V6_SELECTED_TRIAD_COUNTS = {
    "development": int(
        CONTROLLED_V6_CALIBRATION_THRESHOLDS["development_triads_selected"]
    ),
    "heldout": int(
        CONTROLLED_V6_CALIBRATION_THRESHOLDS["heldout_triads_selected"]
    ),
}

V6_MAX_WITHIN_TRIAD_WORD_GAP = 2

_FRAME_PERMUTATIONS: Tuple[Tuple[str, ...], ...] = tuple(
    permutations(STRATEGIES)
)


def _canonical_hash(payload: Mapping[str, Any]) -> str:
    canonical = json.dumps(
        payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _portable_source_path(path: str) -> str:
    """Keep repository-local provenance portable and external paths explicit."""
    absolute = os.path.abspath(path)
    working_root = os.path.abspath(os.getcwd())
    try:
        inside_working_root = os.path.commonpath([absolute, working_root]) == working_root
    except ValueError:
        inside_working_root = False
    return os.path.relpath(absolute, working_root) if inside_working_root else absolute


def _normalized_rendered_length(template: str) -> int:
    rendered = template.format(a="Option A")
    return len(" ".join(rendered.split()).split())


def _sentence_count(template: str) -> int:
    rendered = " ".join(template.format(a="Option A").split())
    return len(re.findall(r"[.!?](?:\s|$)", rendered)) or 1


def _has_only_one_literal_a_placeholder(template: str) -> bool:
    if template.count("{a}") != 1 or "{b}" in template:
        return False
    try:
        fields = [
            field_name
            for _, field_name, _, _ in Formatter().parse(template)
            if field_name is not None
        ]
    except ValueError:
        return False
    return fields == ["a"]


def audit_v6_bank_payload(payload: Mapping[str, Any]) -> Dict[str, Any]:
    """Audit the structural invariants shared by V6 pool and selected banks."""
    is_mapping = isinstance(payload, Mapping)
    raw_splits = payload.get("splits", {}) if is_mapping else {}
    splits = raw_splits if isinstance(raw_splits, Mapping) else {}
    status = payload.get("status") if is_mapping else None
    selected_shape = isinstance(status, str) and status.startswith("selected_bank_")
    expected_counts = (
        V6_SELECTED_TRIAD_COUNTS if selected_shape else V6_POOL_TRIAD_COUNTS
    )

    checks: Dict[str, bool] = {
        "payload_mapping": is_mapping,
        "split_names": set(splits) == {"development", "heldout"},
        "candidate_text_authored_before_calibration": is_mapping
        and payload.get("candidate_text_authored_before_v6_focal_calibration")
        is True,
        "known_bank_shape": status == V6_PROVISIONAL_POOL_STATUS or selected_shape,
    }
    triad_counts: Dict[str, int] = {}
    candidate_counts: Dict[str, int] = {}
    triad_ids: List[str] = []
    candidate_ids: List[str] = []
    normalized_templates: List[str] = []
    literal_label_hits: List[str] = []
    character_lengths: Dict[str, Dict[str, int]] = {}
    character_gaps: Dict[str, int] = {}
    sentence_counts: Dict[str, Dict[str, int]] = {}

    triad_structure_ok = True
    candidate_structure_ok = True
    placeholder_contract_ok = True
    matched_lengths_ok = True

    for split in ("development", "heldout"):
        raw_triads = splits.get(split, []) if isinstance(splits, Mapping) else []
        triads: Sequence[Any] = (
            raw_triads
            if isinstance(raw_triads, list)
            else []
        )
        triad_counts[split] = len(triads)
        candidate_counts[split] = 0
        checks["%s_triad_count" % split] = len(triads) == expected_counts[split]

        if not isinstance(raw_triads, list):
            triad_structure_ok = False

        for triad in triads:
            if not isinstance(triad, Mapping):
                triad_structure_ok = False
                candidate_structure_ok = False
                matched_lengths_ok = False
                continue

            triad_id = triad.get("triad_id")
            if not isinstance(triad_id, str) or not triad_id.strip():
                triad_structure_ok = False
                triad_key = "<invalid-%s-%d>" % (split, len(character_lengths))
            else:
                triad_ids.append(triad_id)
                triad_key = triad_id

            raw_candidates = triad.get("candidates", {})
            if not isinstance(raw_candidates, Mapping):
                triad_structure_ok = False
                candidate_structure_ok = False
                matched_lengths_ok = False
                continue
            if set(raw_candidates) != set(STRATEGIES):
                triad_structure_ok = False

            lengths: Dict[str, int] = {}
            sentences: Dict[str, int] = {}
            for frame in STRATEGIES:
                entry = raw_candidates.get(frame)
                if not isinstance(entry, Mapping):
                    candidate_structure_ok = False
                    placeholder_contract_ok = False
                    matched_lengths_ok = False
                    continue

                candidate_counts[split] += 1
                candidate_id = entry.get("candidate_id")
                template = entry.get("template")
                if not isinstance(candidate_id, str) or not candidate_id.strip():
                    candidate_structure_ok = False
                else:
                    candidate_ids.append(candidate_id)
                if not isinstance(template, str) or not template.strip():
                    candidate_structure_ok = False
                    placeholder_contract_ok = False
                    matched_lengths_ok = False
                    continue

                normalized = " ".join(template.split())
                normalized_templates.append(normalized)
                if not _has_only_one_literal_a_placeholder(template):
                    placeholder_contract_ok = False
                    matched_lengths_ok = False
                else:
                    lengths[frame] = _normalized_rendered_length(template)
                    sentences[frame] = _sentence_count(template)

                lowered = template.lower()
                literal_label_hits.extend(
                    label
                    for label in STRATEGIES
                    if re.search(r"\b%s\b" % re.escape(label), lowered)
                )

            character_lengths[triad_key] = lengths
            sentence_counts[triad_key] = sentences
            if set(lengths) != set(STRATEGIES):
                matched_lengths_ok = False
            else:
                gap = max(lengths.values()) - min(lengths.values())
                character_gaps[triad_key] = gap
                if gap > V6_MAX_WITHIN_TRIAD_WORD_GAP:
                    matched_lengths_ok = False

    expected_total_triads = sum(expected_counts.values())
    expected_total_candidates = expected_total_triads * len(STRATEGIES)
    checks.update(
        {
            "triad_structure": triad_structure_ok,
            "candidate_structure": candidate_structure_ok,
            "one_candidate_per_frame": triad_structure_ok
            and sum(triad_counts.values()) == expected_total_triads
            and sum(candidate_counts.values()) == expected_total_candidates,
            "placeholder_contract": placeholder_contract_ok,
            "matched_within_triad_length": matched_lengths_ok,
            "matched_within_triad_sentence_count": all(
                set(values) == set(STRATEGIES)
                and len(set(values.values())) == 1
                for values in sentence_counts.values()
            ),
            "unique_triad_ids": len(triad_ids) == expected_total_triads
            and len(triad_ids) == len(set(triad_ids)),
            "unique_candidate_ids": len(candidate_ids) == expected_total_candidates
            and len(candidate_ids) == len(set(candidate_ids)),
            "unique_templates": len(normalized_templates)
            == expected_total_candidates
            and len(normalized_templates) == len(set(normalized_templates)),
            "registered_labels_not_literal": not literal_label_hits,
        }
    )

    return {
        "pass": all(checks.values()),
        "checks": checks,
        "counts": triad_counts,
        "triad_counts": triad_counts,
        "candidate_counts": candidate_counts,
        "character_lengths": character_lengths,
        "character_gaps": character_gaps,
        "sentence_counts": sentence_counts,
        "maximum_within_triad_word_gap": V6_MAX_WITHIN_TRIAD_WORD_GAP,
        "literal_label_hits": sorted(set(literal_label_hits)),
        "sha256": _canonical_hash(payload) if is_mapping else None,
    }


@dataclass(frozen=True)
class V6TriadBank:
    payload: Dict[str, Any]
    source_path: str
    validation_evidence: Dict[str, Any] | None = None

    @classmethod
    def load(
        cls,
        path: str,
        require_validated: bool = False,
        final_checkpoint_path: str | None = None,
        checkpoint_root: str | None = None,
    ) -> "V6TriadBank":
        with open(path, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
        audit = audit_v6_bank_payload(payload)
        if not audit["pass"]:
            failed = sorted(
                name for name, passed in audit["checks"].items() if not passed
            )
            raise ValueError("invalid V6 triad bank: %s" % ", ".join(failed))
        evidence: Dict[str, Any] | None = None
        if require_validated:
            if final_checkpoint_path is None:
                raise ValueError(
                    "V6 confirmatory use requires a full final checkpoint; "
                    "validated status alone is not evidence"
                )
            with open(final_checkpoint_path, "r", encoding="utf-8") as handle:
                checkpoint = json.load(handle)
            # Imported lazily to avoid a module cycle: the artifact gate loads
            # structurally valid banks while replaying the transition.
            from .v6_calibration import bank_content_sha256, canonical_sha256, file_sha256
            from .v6_protocol_gate import audit_v6_final_checkpoint

            root = checkpoint_root or os.getcwd()
            checkpoint_audit = audit_v6_final_checkpoint(checkpoint, root)
            if not checkpoint_audit["pass"]:
                failed = sorted(
                    name
                    for name, passed in checkpoint_audit["checks"].items()
                    if not passed
                )
                raise ValueError(
                    "V6 final checkpoint audit failed: %s" % ", ".join(failed)
                )
            if checkpoint_audit.get("validated_bank_sha256") != _canonical_hash(
                payload
            ) or checkpoint_audit.get(
                "validated_bank_content_sha256"
            ) != bank_content_sha256(payload):
                raise ValueError("V6 final checkpoint proves a different validated bank")
            evidence = {
                "path": _portable_source_path(final_checkpoint_path),
                "file_sha256": file_sha256(final_checkpoint_path),
                "canonical_sha256": canonical_sha256(checkpoint),
                "artifact_audit": checkpoint_audit,
            }
        return cls(
            payload=payload,
            source_path=_portable_source_path(path),
            validation_evidence=evidence,
        )

    def manifest(self) -> Dict[str, Any]:
        """Return a detached copy suitable for an immutable run manifest."""
        return json.loads(json.dumps(self.payload))

    def sha256(self) -> str:
        return _canonical_hash(self.payload)

    def candidate_set(
        self,
        scenario: Any,
        episode_index: int,
        round_index: int,
        heldout_start_round: int,
        seed: int,
    ) -> List[MessageCandidate]:
        """Select one whole triad and apply the next all-six slot permutation.

        The schedule uses only public experiment coordinates.  The seeded
        permutation order is fixed for an episode and cycles every six rounds,
        so every complete six-round block contains each frame-to-slot mapping
        exactly once.  A separate seeded triad order rotates with episode and
        split-relative round, keeping validation exposures balanced without
        consulting scenario content, target type, or condition.
        """
        if round_index < 1:
            raise ValueError("round_index must be 1-based")
        if heldout_start_round < 2:
            raise ValueError("heldout_start_round must leave development rounds")

        split = "heldout" if round_index >= heldout_start_round else "development"
        triads: Sequence[Mapping[str, Any]] = self.payload["splits"][split]
        triad_schedule = rng(
            "controlled_v6_triad_schedule", seed, split, heldout_start_round
        ).permutation(len(triads))
        split_round_index = (
            round_index - heldout_start_round
            if split == "heldout"
            else round_index - 1
        )
        triad_schedule_position = (
            episode_index + split_round_index
        ) % len(triads)
        triad_index = int(triad_schedule[triad_schedule_position])
        triad = triads[triad_index]

        permutation_schedule = rng(
            "controlled_v6_all_six_permutation_schedule", seed, episode_index
        ).permutation(len(_FRAME_PERMUTATIONS))
        schedule_position = (round_index - 1) % len(_FRAME_PERMUTATIONS)
        permutation_index = int(permutation_schedule[schedule_position])
        frame_order = _FRAME_PERMUTATIONS[permutation_index]

        candidates: List[MessageCandidate] = []
        for slot, frame in enumerate(frame_order, start=1):
            entry = triad["candidates"][frame]
            text = str(entry["template"]).format(a=scenario.option_a)
            candidates.append(
                MessageCandidate(
                    slot=slot,
                    candidate_id="%s-%s" % (entry["candidate_id"], scenario.id),
                    message=" ".join(text.split()),
                    frame=frame,
                    split=split,
                    template_index=triad_index,
                )
            )
        return candidates


def make_v6_protocol(
    bank_path: str,
    require_validated: bool = False,
    manifest_metadata: Mapping[str, Any] | None = None,
    final_checkpoint_path: str | None = None,
    checkpoint_root: str | None = None,
    confirmatory_run_id: str | None = None,
    confirmatory_episode_seeds: int | None = None,
) -> ControlledProtocol:
    bank = V6TriadBank.load(
        bank_path,
        require_validated=require_validated,
        final_checkpoint_path=final_checkpoint_path,
        checkpoint_root=checkpoint_root,
    )
    metadata = json.loads(json.dumps(manifest_metadata or {}))
    scenario_set = "confirmatory"
    frozen_seed: int | None = None
    frozen_rounds: int | None = None
    frozen_heldout_start: int | None = None
    if require_validated:
        assert bank.validation_evidence is not None
        checkpoint_audit = bank.validation_evidence["artifact_audit"]
        schedule = checkpoint_audit["confirmatory_schedule"]
        expected_run_id = schedule.get("official_run_id")
        if confirmatory_run_id != expected_run_id:
            raise ValueError(
                "V6 confirmatory run_id must equal the single frozen official run ID"
            )
        if confirmatory_episode_seeds != schedule.get("selected_episode_seeds"):
            raise ValueError(
                "V6 confirmatory episode count must equal the pre-validation "
                "power selection"
            )
        scenario_set = str(schedule["scenario_set"])
        frozen_seed = int(schedule["master_seed"])
        frozen_rounds = int(schedule["n_rounds"])
        frozen_heldout_start = int(schedule["heldout_start_round"])
        metadata["v6_final_checkpoint"] = bank.validation_evidence

    def _candidate_set(
        scenario: Any,
        episode_index: int,
        round_index: int,
        heldout_start_round: int,
        seed: int,
    ) -> List[MessageCandidate]:
        if frozen_seed is not None and (
            seed != frozen_seed or heldout_start_round != frozen_heldout_start
        ):
            raise ValueError(
                "V6 confirmatory candidate coordinates differ from the final checkpoint"
            )
        return bank.candidate_set(
            scenario,
            episode_index,
            round_index,
            heldout_start_round,
            seed,
        )

    def _scenario_sequence(
        episode_index: int, n_rounds: int, seed: int
    ) -> List[Any]:
        if frozen_seed is not None and (
            seed != frozen_seed or n_rounds != frozen_rounds
        ):
            raise ValueError(
                "V6 confirmatory scenario coordinates differ from the final checkpoint"
            )
        return v6_scenario_sequence(scenario_set, episode_index, n_rounds, seed)

    return ControlledProtocol(
        version=CONTROLLED_V6_VERSION,
        candidate_builder=_candidate_set,
        bank_manifest_builder=bank.manifest,
        bank_hash_builder=bank.sha256,
        strict_selection=True,
        constrained_choices=("1", "2", "3"),
        bank_source=bank.source_path,
        manifest_metadata=metadata or None,
        scenario_sequence_builder=_scenario_sequence,
    )
