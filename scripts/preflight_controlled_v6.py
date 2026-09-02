#!/usr/bin/env python3
"""Run one paid, no-capture generation on a disjoint V6 sentinel prompt."""

from __future__ import annotations

import _bootstrap  # noqa: F401
import argparse
import hashlib
import json
import os
import sys
from typing import Any, Dict, Sequence

from src.controlled_experiment import build_controlled_episode_specs
from src.controlled_focal_agent import build_controlled_prompt, parse_controlled_choice
from src.controlled_messages import MessageCandidate, candidate_for_slot
from src.focal_agent import ProviderError
from src.hf_provider import collect_focal_runtime_evidence
from src.file_lock import (
    ExclusiveFileLock,
    require_contained_path,
    require_directory_nonsymlink,
)
from src.logging_utils import (
    open_regular_read_descriptor,
    publish_json_idempotent,
    strict_json_load,
)
from src.scenarios import Scenario
from src.seeding import derive_seed
from src.v6_protocol_gate import require_v6_focal_runtime

from run_controlled_open_weight_v6 import (
    CONFIRMATORY_PATHS,
    STRICT_CHOICES,
    V6ConfirmatoryPlan,
    add_frozen_contract_arguments,
    make_confirmatory_provider,
    prepare_v6_confirmatory_plan,
)


SENTINEL_SEED_NAMESPACE = "controlled_v6_paid_preflight_sentinel_generation_v1"
SENTINEL_SCENARIO = Scenario(
    id="v6_preflight_sentinel_only",
    title="Choosing the marker shape for a disposable setup card",
    context=(
        "This isolated equipment check is not part of the study. One of two "
        "temporary marker shapes will be printed on a card that is discarded."
    ),
    option_a="a hollow diamond",
    option_b="a hollow crescent",
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    add_frozen_contract_arguments(parser)
    parser.add_argument("--device", choices=("auto",), default="auto")
    parser.add_argument(
        "--out",
        default=None,
        help=(
            "optional assertion; if supplied it must be exactly %s"
            % CONFIRMATORY_PATHS["preflight"]
        ),
    )
    return parser


def _sentinel_candidates() -> list[MessageCandidate]:
    messages = (
        (
            "fairness",
            "Choose a hollow diamond so each setup group receives the same marker convention.",
        ),
        (
            "risk",
            "Choose a hollow diamond because its simple outline is less likely to be misread during setup.",
        ),
        (
            "expertise",
            "Choose a hollow diamond because the equipment-check team documented it as the clearest marker.",
        ),
    )
    return [
        MessageCandidate(
            slot=slot,
            candidate_id="v6-preflight-sentinel-%s" % frame,
            message=message,
            frame=frame,
            split="sentinel",
            template_index=-1,
        )
        for slot, (frame, message) in enumerate(messages, start=1)
    ]


def _sentinel_prompt(plan: V6ConfirmatoryPlan):
    specs = build_controlled_episode_specs(plan.config)
    if not specs:
        raise ValueError("V6 frozen confirmatory schedule has no episodes")
    scenario = SENTINEL_SCENARIO
    candidates = _sentinel_candidates()
    prompt = build_controlled_prompt(
        scenario=scenario,
        candidates=candidates,
        history=[],
        round_index=1,
        n_rounds=plan.config.n_rounds,
        show_history=False,
        focal_mode="spontaneous",
        context={},
    )
    round_seed = derive_seed(
        SENTINEL_SEED_NAMESPACE,
        plan.model_id,
        plan.revision,
        plan.checkpoint_audit["checkpoint_canonical_sha256"],
    )

    official_scenario_ids = set()
    official_candidate_ids = set()
    official_candidate_messages = set()
    official_round_seeds = set()
    official_coordinates = 0
    for spec in specs:
        scenarios = plan.protocol.scenario_sequence(
            spec.episode_index, spec.n_rounds, plan.config.seed
        )
        if scenarios is None or len(scenarios) != spec.n_rounds:
            raise ValueError("V6 protocol returned an incomplete official schedule")
        episode_seed = derive_seed(
            plan.config.seed,
            plan.protocol.version,
            spec.condition.name,
            spec.episode_index,
            spec.initial_target_type,
            spec.final_target_type,
        )
        for round_index, official_scenario in enumerate(scenarios, start=1):
            official_candidates = plan.protocol.candidate_set(
                scenario=official_scenario,
                episode_index=spec.episode_index,
                round_index=round_index,
                heldout_start_round=plan.config.heldout_start_round,
                seed=plan.config.seed,
            )
            official_scenario_ids.add(official_scenario.id)
            official_candidate_ids.update(
                candidate.candidate_id for candidate in official_candidates
            )
            official_candidate_messages.update(
                candidate.message for candidate in official_candidates
            )
            official_round_seeds.add(
                derive_seed(episode_seed, "focal_generation", round_index)
            )
            official_coordinates += 1

    overlap = {
        "sentinel_scenario_id_absent_from_official_schedule": (
            scenario.id not in official_scenario_ids
        ),
        "sentinel_candidate_ids_absent_from_official_schedule": not (
            {candidate.candidate_id for candidate in candidates}
            & official_candidate_ids
        ),
        "sentinel_candidate_text_absent_from_official_schedule": not (
            {candidate.message for candidate in candidates}
            & official_candidate_messages
        ),
        "sentinel_generation_seed_absent_from_official_schedule": (
            round_seed not in official_round_seeds
        ),
        "sentinel_split_not_an_official_split": all(
            candidate.split == "sentinel" for candidate in candidates
        ),
    }
    overlap["pass"] = all(overlap.values())
    boundary = {
        "prompt_context_keys": sorted(prompt.context),
        "visible_history_entries": 0,
        "history_rendered": "--- Previous interactions ---" in prompt.user,
        "target_fields_supplied_to_provider": [],
        "target_simulator_invoked": False,
    }
    boundary["pass"] = (
        boundary["prompt_context_keys"] == []
        and boundary["visible_history_entries"] == 0
        and boundary["history_rendered"] is False
        and boundary["target_fields_supplied_to_provider"] == []
        and boundary["target_simulator_invoked"] is False
        and overlap["pass"] is True
    )
    if boundary["pass"] is not True:
        raise ValueError("V6 sentinel preflight violated its isolation boundary")
    proof = {
        "sentinel_seed_namespace": SENTINEL_SEED_NAMESPACE,
        "official_schedule_coordinates_examined": official_coordinates,
        "official_selected_schedule_sha256": plan.schedule[
            "selected_schedule_sha256"
        ],
        "sentinel_prompt_sha256": hashlib.sha256(
            (prompt.system + "\x1f" + prompt.user).encode("utf-8")
        ).hexdigest(),
        "overlap_checks": overlap,
    }
    return scenario, candidates, prompt, round_seed, boundary, proof


def _base_report(
    plan: V6ConfirmatoryPlan,
    prompt_data,
) -> Dict[str, Any]:
    scenario, candidates, prompt, round_seed, boundary, proof = prompt_data
    return {
        "kind": "controlled_v6_paid_preflight",
        "status": "RUNNING_ONE_FROZEN_GENERATION",
        "ok": False,
        "issues": [],
        "official_run_id": plan.run_id,
        "final_checkpoint": {
            "path": plan.checkpoint_path,
            "file_sha256": plan.protocol.protocol_provenance_manifest()[
                "checkpoint_file_sha256"
            ],
            "canonical_sha256": plan.checkpoint_audit[
                "checkpoint_canonical_sha256"
            ],
            "audit": plan.checkpoint_audit,
        },
        "validated_bank": {
            **dict(plan.checkpoint["validated_bank"]),
            "resolved_path": plan.bank_path,
            "audited_bank_sha256": plan.checkpoint_audit[
                "validated_bank_sha256"
            ],
            "audited_content_sha256": plan.checkpoint_audit[
                "validated_bank_content_sha256"
            ],
        },
        "model": {"id": plan.model_id, "revision": plan.revision},
        "focal_runtime": dict(plan.focal_runtime),
        "generation": dict(plan.generation),
        "target_parameters_frozen_but_not_supplied_to_model": dict(plan.target),
        "confirmatory_schedule": {
            "selected_episode_seeds": plan.selected_episode_seeds,
            "master_seed": plan.config.seed,
            "conditions": list(plan.config.conditions),
            "n_rounds": plan.config.n_rounds,
            "swap_round": plan.config.swap_round,
            "heldout_start_round": plan.config.heldout_start_round,
            "selected_schedule_sha256": plan.schedule[
                "selected_schedule_sha256"
            ],
        },
        "sentinel_probe": {
            "official_schedule_position": None,
            "official_condition": None,
            "official_episode_index": None,
            "official_round": None,
            "scenario_id": scenario.id,
            "scenario": scenario.as_dict(),
            "visible_candidates": [candidate.visible_dict() for candidate in candidates],
            "focal_system_prompt": prompt.system,
            "focal_user_prompt": prompt.user,
            "generation_seed": round_seed,
            "information_boundary": boundary,
            "disjointness_proof": proof,
        },
        "activation_capture": False,
        "generation_count": 0,
        "target_outcome_generated": False,
        "confirmatory_log_written": False,
    }


def _canonical_sha256(payload: Any) -> str:
    rendered = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(rendered).hexdigest()


def _load_json_object(
    path: str,
    label: str,
    *,
    root: str | None = None,
) -> Dict[str, Any]:
    descriptor = open_regular_read_descriptor(
        path, root=root, label=label
    )
    with os.fdopen(descriptor, "r", encoding="utf-8") as handle:
        payload = strict_json_load(handle)
    if type(payload) is not dict:
        raise ValueError("%s must be a JSON object" % label)
    return payload


def _paid_call_claim(
    plan: V6ConfirmatoryPlan,
    prompt_data,
) -> Dict[str, Any]:
    _scenario, _candidates, _prompt, round_seed, _boundary, proof = prompt_data
    payload: Dict[str, Any] = {
        "kind": "controlled_v6_paid_preflight_call_claim",
        "schema_version": "1.0",
        "status": "ONE_PAID_CALL_AUTHORIZED",
        "official_run_id": plan.run_id,
        "report_path": CONFIRMATORY_PATHS["preflight"],
        "final_checkpoint_file_sha256": plan.protocol.protocol_provenance_manifest()[
            "checkpoint_file_sha256"
        ],
        "final_checkpoint_canonical_sha256": plan.checkpoint_audit[
            "checkpoint_canonical_sha256"
        ],
        "selected_schedule_sha256": plan.schedule["selected_schedule_sha256"],
        "validated_bank_sha256": plan.protocol.message_bank_sha256(),
        "model": {"id": plan.model_id, "revision": plan.revision},
        "focal_runtime": dict(plan.focal_runtime),
        "generation": dict(plan.generation),
        "sentinel_generation_seed": round_seed,
        "sentinel_prompt_sha256": proof["sentinel_prompt_sha256"],
        "maximum_generation_calls": 1,
        "recovery_policy": (
            "if this claim exists without a complete report, the paid call state "
            "is ambiguous and generation must never be repeated"
        ),
    }
    payload["claim_id"] = _canonical_sha256(payload)
    return payload


def _audit_existing_report(
    report: Dict[str, Any],
    expected_base: Dict[str, Any],
    claim: Dict[str, Any],
) -> bool:
    """Fail closed unless a persisted report is exactly bound to this claim."""
    expected_top_keys = set(expected_base) | {"provider", "paid_call_receipt"}
    if type(report) is not dict or set(report) != expected_top_keys:
        raise ValueError(
            "persisted V6 preflight report has the wrong top-level schema"
        )
    mutable_top = {
        "status",
        "ok",
        "issues",
        "provider",
        "generation_count",
        "paid_call_receipt",
    }
    for key, expected in expected_base.items():
        if key in mutable_top or key == "sentinel_probe":
            continue
        if _canonical_sha256(report.get(key)) != _canonical_sha256(expected):
            raise ValueError("persisted V6 preflight report drifted at %s" % key)
    if type(report.get("ok")) is not bool:
        raise ValueError("persisted V6 preflight status is not Boolean")
    observed_probe = report.get("sentinel_probe")
    if type(observed_probe) is not dict:
        raise ValueError("persisted V6 preflight report has no sentinel probe")
    expected_probe_keys = set(expected_base["sentinel_probe"])
    if report["ok"]:
        expected_probe_keys.update(
            {
                "focal_output_raw",
                "selection_valid",
                "fallback_used",
                "selected_slot",
                "selected_candidate_id",
            }
        )
    if set(observed_probe) != expected_probe_keys:
        raise ValueError(
            "persisted V6 preflight sentinel has the wrong schema"
        )
    for key, expected in expected_base["sentinel_probe"].items():
        if _canonical_sha256(observed_probe.get(key)) != _canonical_sha256(expected):
            raise ValueError(
                "persisted V6 preflight sentinel drifted at %s" % key
            )
    expected_receipt = {
        "path": CONFIRMATORY_PATHS["preflight_receipt"],
        "claim_id": claim["claim_id"],
        "claim_canonical_sha256": _canonical_sha256(claim),
    }
    if _canonical_sha256(report.get("paid_call_receipt")) != _canonical_sha256(
        expected_receipt
    ):
        raise ValueError("persisted V6 preflight report has the wrong paid-call claim")
    if type(report.get("generation_count")) is not int or report[
        "generation_count"
    ] not in {0, 1}:
        raise ValueError("persisted V6 preflight generation count is invalid")
    issues = report.get("issues")
    if type(issues) is not list or any(type(item) is not str for item in issues):
        raise ValueError("persisted V6 preflight issues are malformed")
    provider = report.get("provider")
    if type(provider) is not dict:
        raise ValueError("persisted V6 preflight provider evidence is malformed")
    full_provider_keys = {
        "provider",
        "model",
        "revision",
        "temperature",
        "max_tokens",
        "dtype",
        "layer_stride",
        "capture",
        "torch_seed_base",
        "enable_thinking",
        "top_p",
        "top_k",
        "architecture",
        "loaded_with",
        "processor",
        "per_generation_seed_supported",
        "constrained_choices",
        "invalid_output_policy",
    }
    if expected_base.get("focal_runtime"):
        full_provider_keys.update({"device", "focal_runtime_evidence"})
    unavailable_provider_keys = {"available"}
    failed_describe_provider_keys = {"available", "describe_error"}
    if set(provider) == full_provider_keys:
        provider_types_ok = (
            type(provider["provider"]) is str
            and type(provider["model"]) is str
            and (
                provider["revision"] is None
                or type(provider["revision"]) is str
            )
            and type(provider["temperature"]) in {int, float}
            and type(provider["max_tokens"]) is int
            and type(provider["dtype"]) is str
            and type(provider["layer_stride"]) is int
            and type(provider["capture"]) is bool
            and type(provider["torch_seed_base"]) is int
            and type(provider["enable_thinking"]) is bool
            and type(provider["top_p"]) in {int, float}
            and type(provider["top_k"]) is int
            and (
                provider["architecture"] is None
                or type(provider["architecture"]) is str
            )
            and (
                provider["loaded_with"] is None
                or type(provider["loaded_with"]) is str
            )
            and (
                provider["processor"] is None
                or type(provider["processor"]) is str
            )
            and provider["per_generation_seed_supported"] is True
            and type(provider["constrained_choices"]) is list
            and all(
                type(choice) is str
                for choice in provider["constrained_choices"]
            )
            and type(provider["invalid_output_policy"]) is str
            and (
                not expected_base.get("focal_runtime")
                or (
                    provider.get("device") == "auto"
                    and provider.get("focal_runtime_evidence")
                    == expected_base["focal_runtime"].get("evidence")
                )
            )
        )
        if not provider_types_ok:
            raise ValueError(
                "persisted V6 preflight provider evidence has invalid JSON types"
            )
    elif set(provider) == unavailable_provider_keys:
        if provider["available"] is not False:
            raise ValueError(
                "persisted V6 preflight unavailable-provider evidence is invalid"
            )
    elif set(provider) == failed_describe_provider_keys:
        if provider["available"] is not False or type(
            provider["describe_error"]
        ) is not str:
            raise ValueError(
                "persisted V6 preflight provider failure evidence is invalid"
            )
    else:
        raise ValueError(
            "persisted V6 preflight provider evidence has the wrong schema"
        )
    if report["ok"]:
        if set(provider) != full_provider_keys:
            raise ValueError(
                "persisted V6 preflight PASS provider schema is incomplete"
            )
        if report.get("status") != "PASS_V6_CONFIRMATORY_PAID_PREFLIGHT":
            raise ValueError("persisted V6 preflight PASS status drifted")
        if report["generation_count"] != 1 or issues:
            raise ValueError("persisted V6 preflight PASS count/issues drifted")
        raw = observed_probe.get("focal_output_raw")
        if raw not in STRICT_CHOICES:
            raise ValueError("persisted V6 preflight PASS output is invalid")
        if observed_probe.get("selection_valid") is not True or observed_probe.get(
            "fallback_used"
        ) is not False:
            raise ValueError("persisted V6 preflight PASS parse evidence is invalid")
        if provider.get("capture") is not False:
            raise ValueError("persisted V6 preflight PASS enabled activation capture")
        if (
            provider.get("provider") != "huggingface"
            or provider.get("model") != claim["model"]["id"]
            or provider.get("revision") != claim["model"]["revision"]
        ):
            raise ValueError("persisted V6 preflight PASS provider identity drifted")
        generation_fields = (
            ("temperature", "temperature"),
            ("max_tokens", "max_tokens"),
            ("dtype", "dtype"),
            ("enable_thinking", "enable_thinking"),
            ("top_p", "top_p"),
            ("top_k", "top_k"),
            ("constrained_choices", "constrained_choices"),
        )
        if any(
            _canonical_sha256(provider.get(provider_key))
            != _canonical_sha256(claim["generation"].get(generation_key))
            for provider_key, generation_key in generation_fields
        ):
            raise ValueError("persisted V6 preflight PASS generation settings drifted")
        expected_slot = int(raw)
        expected_candidate_id = _sentinel_candidates()[expected_slot - 1].candidate_id
        if (
            type(observed_probe.get("selected_slot")) is not int
            or observed_probe["selected_slot"] != expected_slot
            or observed_probe.get("selected_candidate_id") != expected_candidate_id
        ):
            raise ValueError("persisted V6 preflight PASS selection evidence drifted")
    else:
        if report.get("status") != "FAIL_V6_CONFIRMATORY_PAID_PREFLIGHT":
            raise ValueError("persisted V6 preflight FAIL status drifted")
        if not issues:
            raise ValueError("persisted V6 preflight FAIL has no issue")
    return bool(report["ok"])


def _write_report(path: str, report: Dict[str, Any]) -> None:
    publish_json_idempotent(path, report, sort_keys=True)
    print(json.dumps(report, indent=2, ensure_ascii=False))


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    plan = prepare_v6_confirmatory_plan(args)
    if args.out is not None and args.out != CONFIRMATORY_PATHS["preflight"]:
        raise ValueError(
            "V6 paid preflight report override is forbidden; use %r"
            % CONFIRMATORY_PATHS["preflight"]
        )
    if plan.schedule.get("paid_preflight_report_path") != CONFIRMATORY_PATHS[
        "preflight"
    ]:
        raise ValueError("V6 paid preflight report path drifted")
    report_path = require_contained_path(
        os.path.join(plan.repository_root, CONFIRMATORY_PATHS["preflight"]),
        plan.repository_root,
        label="V6 paid preflight report",
    )
    receipt_path = require_contained_path(
        os.path.join(
            plan.repository_root, CONFIRMATORY_PATHS["preflight_receipt"]
        ),
        plan.repository_root,
        label="V6 paid preflight receipt",
    )
    lock_path = require_contained_path(
        receipt_path + ".lock",
        plan.repository_root,
        label="V6 paid preflight lock",
    )
    parent = os.path.dirname(report_path)
    if parent:
        os.makedirs(parent, exist_ok=True)
        require_directory_nonsymlink(parent, label="V6 preflight report directory")
    receipt_parent = os.path.dirname(receipt_path)
    if receipt_parent:
        os.makedirs(receipt_parent, exist_ok=True)
        require_directory_nonsymlink(
            receipt_parent, label="V6 preflight receipt directory"
        )

    with ExclusiveFileLock(
        lock_path,
        label="V6 paid preflight",
        metadata={"official_run_id": plan.run_id},
        root=plan.repository_root,
    ):
        # The complete checkpoint graph and frozen runtime contract are audited
        # before constructing the provider. The first generate call performs the
        # actual model load.
        prompt_data = _sentinel_prompt(plan)
        report = _base_report(plan, prompt_data)
        claim = _paid_call_claim(plan, prompt_data)
        report["paid_call_receipt"] = {
            "path": CONFIRMATORY_PATHS["preflight_receipt"],
            "claim_id": claim["claim_id"],
            "claim_canonical_sha256": _canonical_sha256(claim),
        }

        report_exists = os.path.lexists(report_path)
        receipt_exists = os.path.lexists(receipt_path)
        if report_exists:
            if not receipt_exists:
                raise ValueError("V6 preflight report exists without its paid-call claim")
            observed_claim = _load_json_object(
                receipt_path,
                "V6 paid preflight receipt",
                root=plan.repository_root,
            )
            if _canonical_sha256(observed_claim) != _canonical_sha256(claim):
                raise ValueError("V6 paid preflight receipt drifted")
            existing = _load_json_object(
                report_path,
                "V6 paid preflight report",
                root=plan.repository_root,
            )
            passed = _audit_existing_report(existing, report, claim)
            print(json.dumps(existing, indent=2, ensure_ascii=False))
            print("V6 PAID PREFLIGHT REPLAYED: no model call was made")
            return 0 if passed else 1
        if receipt_exists:
            observed_claim = _load_json_object(
                receipt_path,
                "V6 paid preflight receipt",
                root=plan.repository_root,
            )
            if _canonical_sha256(observed_claim) != _canonical_sha256(claim):
                raise ValueError("V6 paid preflight receipt drifted")
            raise RuntimeError(
                "V6 paid preflight claim exists without a complete report; the "
                "call outcome is ambiguous and generation must not be repeated"
            )

        runtime_evidence = None
        if plan.focal_runtime:
            runtime_evidence = collect_focal_runtime_evidence(device=args.device)
            require_v6_focal_runtime(
                plan.protocol_spec,
                runtime_evidence,
                expected_evidence=plan.focal_runtime.get("evidence", {}),
                device_argument=args.device,
            )
        publish_json_idempotent(receipt_path, claim, sort_keys=True)
        _scenario, candidates, prompt, round_seed, _boundary, _proof = prompt_data
        provider = None
        try:
            provider = make_confirmatory_provider(
                plan,
                device=args.device,
                runtime_evidence=runtime_evidence,
            )
            provider.set_next_seed(round_seed)
            report["provider"] = provider.describe()
            report["generation_count"] = 1
            raw = provider.generate(prompt)
            if raw not in STRICT_CHOICES:
                raise ProviderError(
                    "V6 preflight requires one exact constrained choice, got %r" % raw
                )
            parsed = parse_controlled_choice(raw, "spontaneous", round_seed)
            if not parsed.selection_valid or parsed.fallback_used:
                raise ProviderError("V6 preflight rejected an invalid or fallback choice")
            selected = candidate_for_slot(candidates, parsed.selected_slot)
            provider_description = provider.describe()
            if provider_description.get("capture") is not False:
                raise ProviderError("V6 preflight provider enabled activation capture")
            report["provider"] = provider_description
            report["sentinel_probe"].update(
                {
                    "focal_output_raw": raw,
                    "selection_valid": True,
                    "fallback_used": False,
                    "selected_slot": selected.slot,
                    "selected_candidate_id": selected.candidate_id,
                }
            )
            report["status"] = "PASS_V6_CONFIRMATORY_PAID_PREFLIGHT"
            report["ok"] = True
        except Exception as exc:  # noqa: BLE001 - preserve a machine-readable paid failure
            report["status"] = "FAIL_V6_CONFIRMATORY_PAID_PREFLIGHT"
            report["issues"].append("%s: %s" % (type(exc).__name__, exc))
            if provider is not None:
                try:
                    report["provider"] = provider.describe()
                except Exception as describe_exc:  # pragma: no cover - defensive
                    report["provider"] = {
                        "available": False,
                        "describe_error": "%s: %s"
                        % (type(describe_exc).__name__, describe_exc),
                    }
            else:
                report["provider"] = {"available": False}
            _write_report(report_path, report)
            print("V6 PAID PREFLIGHT FAILED: do not start the official run", file=sys.stderr)
            return 1

        _write_report(report_path, report)
        print("V6 PAID PREFLIGHT PASSED: exactly one no-capture choice generated")
        return 0


if __name__ == "__main__":
    sys.exit(main())
