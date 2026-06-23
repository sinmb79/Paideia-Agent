from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Iterable

from .contracts_adapter import validate_case_graph_v2
from .models import KiboRecord
from .retriever import eligible_records, load_kibo_records
from .v2_artifacts import evidence_hash, stable_id, v2_header


def _slug(value: str, fallback: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9_]+", "_", value.strip().casefold()).strip("_")
    return slug or fallback


def _predicate(predicate_id: str, op: str, field: str, value: object) -> dict[str, Any]:
    return {
        "predicate_id": predicate_id,
        "op": op,
        "field": field,
        "value": value,
    }


def _typed_value(name: str, value_type: str, value: object) -> dict[str, Any]:
    return {
        "name": name,
        "value_type": value_type,
        "value": value,
    }


def _observation(observation_id: str, name: str, value_type: str, required: bool = True) -> dict[str, Any]:
    return {
        "observation_id": observation_id,
        "name": name,
        "value_type": value_type,
        "required": required,
        "freshness_ms": None,
    }


def _constraint(constraint_id: str, predicate: dict[str, Any], severity: str = "medium") -> dict[str, Any]:
    return {
        "constraint_id": constraint_id,
        "predicate": predicate,
        "severity": severity,
    }


def case_graph_from_kibo(record: KiboRecord, manifest: dict[str, Any]) -> dict[str, Any]:
    if not record.is_runtime_eligible:
        raise ValueError(f"CaseGraph source Kibo is not runtime eligible: {record.kibo_id}")
    record_payload = record.to_dict()
    context_variables = [
        _typed_value(_slug(value, f"input_{index}"), "string", value)
        for index, value in enumerate(record.required_inputs, start=1)
    ]
    context_variables.extend(
        [
            _typed_value("source_run_id", "string", record.source_run_id),
            _typed_value("source_promotion_status", "string", record.promotion_status),
            _typed_value(
                "environment_fingerprint",
                "sha256",
                evidence_hash(
                    {
                        "domain": record.domain,
                        "task_family": record.task_type,
                        "required_inputs": list(record.required_inputs),
                        "output_template": record.output_template,
                        "source_run_id": record.source_run_id,
                        "evidence_refs": list(record.evidence_refs),
                    }
                ),
            ),
        ]
    )
    observations = [
        _observation(f"obs-input-{index}", value, "string", required=True)
        for index, value in enumerate(record.required_inputs, start=1)
    ]
    constraints = [
        _constraint(
            f"constraint-input-{index}",
            _predicate(f"predicate-input-{index}", "exists", _slug(value, f"input_{index}"), True),
            "hard",
        )
        for index, value in enumerate(record.required_inputs, start=1)
    ]
    action_steps = [
        {
            "step_id": f"step-{index:03d}",
            "action_type": _slug(step.split(" ", 1)[0], "act"),
            "capability": _slug(record.reusable_logic[index - 1] if index <= len(record.reusable_logic) else step, "general"),
            "input_refs": [item["name"] for item in context_variables],
            "output_ref": f"step-{index:03d}-output",
            "receipt_ref": None,
        }
        for index, step in enumerate(record.solution_steps or record.reusable_logic, start=1)
    ]
    case_graph = {
        **v2_header("case_graph", manifest),
        "case_id": stable_id("case", record.kibo_id, record.source_run_id, record.updated_at),
        "owner": record.owner,
        "domain": record.domain,
        "task_family": record.task_type,
        "goal": record.problem_signature,
        "context_variables": context_variables,
        "observations": observations,
        "constraints": constraints,
        "action_steps": action_steps,
        "branch_events": [],
        "outcome_refs": list(record.evidence_refs),
        "failure_refs": list(record.failure_modes),
        "source_kibo_ids": [record.kibo_id],
        "evidence_hashes": [evidence_hash(record_payload)],
    }
    validate_case_graph_v2(case_graph, manifest)
    return case_graph


def build_case_graphs_from_records(
    records: Iterable[KiboRecord],
    manifest: dict[str, Any],
) -> list[dict[str, Any]]:
    selected = eligible_records(records)
    return [case_graph_from_kibo(record, manifest) for record in selected]


def build_case_graphs_from_paths(
    kibo_paths: Iterable[Path],
    manifest: dict[str, Any],
) -> list[dict[str, Any]]:
    records: list[KiboRecord] = []
    for path in kibo_paths:
        records.extend(load_kibo_records(path))
    return build_case_graphs_from_records(records, manifest)
