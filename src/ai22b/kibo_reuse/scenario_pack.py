from __future__ import annotations

from typing import Any, Iterable

from .v2_artifacts import evidence_hash, stable_id


BEHAVIORAL_SCENARIO_PACK_SCHEMA = "paideia-behavioral-scenario-pack/v1"

DEFAULT_SCENARIO_KINDS = (
    "near_transfer",
    "far_transfer",
    "counterexample",
    "safety_boundary",
    "abstention_required",
)

SUPPORTED_SCENARIO_KINDS = {
    "near_transfer",
    "far_transfer",
    "counterexample",
    "regime_shift",
    "missing_information",
    "stale_information",
    "tool_failure",
    "partial_observability",
    "safety_boundary",
    "abstention_required",
}


def source_case_hashes(action_pattern: dict[str, Any]) -> list[str]:
    return [evidence_hash({"source_case_id": case_id}) for case_id in action_pattern.get("source_case_ids") or []]


def build_behavioral_scenario_pack(
    action_pattern: dict[str, Any],
    *,
    scenario_kinds: Iterable[str] = DEFAULT_SCENARIO_KINDS,
    source_partition: str = "holdout",
    include_leakage: bool = False,
) -> dict[str, Any]:
    kinds = [str(kind) for kind in scenario_kinds]
    unknown = [kind for kind in kinds if kind not in SUPPORTED_SCENARIO_KINDS]
    if unknown:
        raise ValueError(f"Unsupported scenario_kind: {', '.join(unknown)}")
    if not kinds:
        raise ValueError("scenario pack requires at least one scenario")
    required_capabilities = list(action_pattern.get("required_capabilities") or [])
    source_hashes = source_case_hashes(action_pattern)
    scenarios = [
        _scenario_from_pattern(
            action_pattern,
            scenario_kind=kind,
            index=index,
            source_partition=source_partition,
            required_capabilities=required_capabilities,
            leakage_hashes=source_hashes[:1] if include_leakage and index == 1 else [],
        )
        for index, kind in enumerate(kinds, start=1)
    ]
    return {
        "schema": BEHAVIORAL_SCENARIO_PACK_SCHEMA,
        "scenario_pack_id": stable_id(
            "scenario-pack",
            action_pattern.get("pattern_id"),
            action_pattern.get("pattern_version"),
            ",".join(kinds),
            source_partition,
        ),
        "pattern_id": action_pattern.get("pattern_id"),
        "pattern_version": action_pattern.get("pattern_version"),
        "source_case_hashes": source_hashes,
        "train_dev_test_policy": {
            "scenario_partition": source_partition,
            "source_case_leakage_forbidden": True,
            "scenario_answer_contains_source_kibo": False,
        },
        "scenarios": scenarios,
    }


def _scenario_from_pattern(
    action_pattern: dict[str, Any],
    *,
    scenario_kind: str,
    index: int,
    source_partition: str,
    required_capabilities: list[str],
    leakage_hashes: list[str],
) -> dict[str, Any]:
    available = list(required_capabilities)
    if scenario_kind == "tool_failure" and available:
        available = available[:-1]
    if scenario_kind == "missing_information":
        available = []
    initial_state: dict[str, object] = {
        "pattern_id": action_pattern.get("pattern_id"),
        "scenario_kind": scenario_kind,
        "holdout": source_partition == "holdout",
        "required_observations_present": scenario_kind not in {"missing_information", "abstention_required"},
        "safety_boundary": scenario_kind == "safety_boundary",
        "counterexample_challenge": scenario_kind == "counterexample",
        "hidden_chain_of_thought_reused": False,
    }
    return {
        "scenario_id": stable_id(
            "scenario",
            action_pattern.get("pattern_id"),
            action_pattern.get("pattern_version"),
            scenario_kind,
            index,
            source_partition,
        ),
        "scenario_kind": scenario_kind,
        "domain": action_pattern.get("domain"),
        "task_family": action_pattern.get("task_family"),
        "initial_state": initial_state,
        "available_capabilities": available,
        "hidden_expected_invariants": list(action_pattern.get("invariants") or []),
        "success_oracle": {
            "oracle_type": "deterministic_capability_and_invariant",
            "required_capabilities": required_capabilities,
            "requires_abstention": scenario_kind in {"abstention_required", "missing_information"},
            "requires_recovery": scenario_kind == "tool_failure",
            "safety_boundary": scenario_kind == "safety_boundary",
            "requires_guard": scenario_kind in {"counterexample", "safety_boundary"},
        },
        "max_steps": max(1, len(action_pattern.get("steps") or [])),
        "source_partition": source_partition,
        "leakage_hashes": leakage_hashes,
    }
