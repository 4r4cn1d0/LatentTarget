"""Versioned protocol dependencies for controlled-choice experiments.

V4 remains the default. Later protocols can replace the candidate bank and
selection contract without changing V4 logs, seeds, or target behavior.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence

from config import CONTROLLED_V4_VERSION
from .controlled_messages import (
    MessageCandidate,
    candidate_set as v4_candidate_set,
    message_bank_manifest as v4_message_bank_manifest,
    message_bank_sha256 as v4_message_bank_sha256,
)


CandidateBuilder = Callable[[Any, int, int, int, int], List[MessageCandidate]]


@dataclass(frozen=True)
class ControlledProtocol:
    """Inject versioned candidate and output-policy dependencies."""

    version: str
    candidate_builder: CandidateBuilder
    bank_manifest_builder: Callable[[], Dict[str, Any]]
    bank_hash_builder: Callable[[], str]
    strict_selection: bool = False
    constrained_choices: Optional[Sequence[str]] = None
    bank_source: Optional[str] = None
    manifest_metadata: Optional[Mapping[str, Any]] = None

    def candidate_set(
        self,
        scenario: Any,
        episode_index: int,
        round_index: int,
        heldout_start_round: int,
        seed: int,
    ) -> List[MessageCandidate]:
        return self.candidate_builder(
            scenario, episode_index, round_index, heldout_start_round, seed
        )

    def message_bank_manifest(self) -> Dict[str, Any]:
        return self.bank_manifest_builder()

    def message_bank_sha256(self) -> str:
        return self.bank_hash_builder()

    def selection_policy_manifest(self) -> Dict[str, Any]:
        return {
            "strict_selection": self.strict_selection,
            "constrained_choices": list(self.constrained_choices or []),
            "invalid_output_policy": (
                "abort episode; no fallback"
                if self.strict_selection
                else "logged deterministic seeded fallback"
            ),
        }

    def protocol_provenance_manifest(self) -> Optional[Dict[str, Any]]:
        if self.manifest_metadata is None:
            return None
        # JSON round-trip keeps the frozen protocol object immutable to callers.
        import json

        return json.loads(json.dumps(self.manifest_metadata))


V4_PROTOCOL = ControlledProtocol(
    version=CONTROLLED_V4_VERSION,
    candidate_builder=v4_candidate_set,
    bank_manifest_builder=v4_message_bank_manifest,
    bank_hash_builder=v4_message_bank_sha256,
)
