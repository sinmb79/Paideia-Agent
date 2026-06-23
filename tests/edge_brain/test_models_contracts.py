from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, ValidationError

from ai22b.edge_brain.models import (
    ActionPattern,
    ActionReceipt,
    ActionStep,
    ArtifactManifest,
    AutonomyEnvelope,
    BehavioralExamResult,
    CapabilityContract,
    CognitiveBudget,
    DeploymentStatus,
    Observation,
    OutcomeEvidence,
    RemediationTicket,
    SideEffectClass,
    StateFact,
    StepCredit,
    WeaknessRecord,
    WorldState,
)


SCHEMA_DIR = Path("schemas/edge_brain")


def _schema(name: str) -> dict:
    return json.loads((SCHEMA_DIR / name).read_text(encoding="utf-8"))


def _validate(name: str, artifact: dict) -> None:
    schema = _schema(name)
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(artifact)


def _receipt() -> ActionReceipt:
    return ActionReceipt(
        receipt_id="receipt-1",
        decision_cycle_id="cycle-1",
        action_pattern_id="ap-1",
        step_id="inspect",
        capability_id="cap.inspect_zone",
        requested_at="2026-06-23T00:00:00Z",
        completed_at="2026-06-23T00:00:01Z",
        status="succeeded",
        input_digest="sha256:input",
        output_ref="runs/out.json",
        output_digest="sha256:output",
        observed_side_effects=("read_only",),
        error_code=None,
        rollback_status=None,
    )


def _budget() -> CognitiveBudget:
    return CognitiveBudget(
        max_cycle_ms=1000,
        max_local_model_tokens=512,
        max_remote_model_tokens=0,
        max_energy_units=None,
        max_memory_mb=256,
        network_allowed=False,
        remote_calls_allowed=0,
    )


def _envelope() -> AutonomyEnvelope:
    return AutonomyEnvelope(
        envelope_id="env-1",
        allowed_capabilities=("cap.inspect_zone",),
        prohibited_capabilities=("cap.actuate_motor",),
        allowed_side_effect_classes=(SideEffectClass.READ_ONLY.value,),
        max_operation_duration_ms=2000,
        required_health_signals=("sensor.camera.ok",),
        abort_conditions=({"op": "eq", "fact": "zone.status", "value": "restricted"},),
        human_approval_scopes=("consequential",),
        offline_policy="degrade",
    )


def _action_pattern() -> ActionPattern:
    return ActionPattern(
        action_pattern_id="ap-1",
        version="v1",
        source_pattern_id="pattern-1",
        source_kibo_ids=("kibo-1",),
        owner="Boss",
        domain="warehouse_robotics",
        task_family="inspection",
        required_observations=("camera.frame",),
        required_capabilities=("cap.inspect_zone",),
        preconditions=({"op": "gte", "fact": "battery.percent", "value": 30},),
        invariants=({"op": "neq", "fact": "zone.status", "value": "restricted"},),
        postconditions=({"op": "exists", "fact": "inspection.report"},),
        steps=(
            ActionStep(
                step_id="inspect",
                kind="capability",
                capability_id="cap.inspect_zone",
                input_bindings=({"source": "world_state", "path": "zone.id", "target": "zone_id"},),
                guard={"op": "eq", "fact": "sensor.camera.health", "value": "ok"},
                success_condition={"op": "exists", "fact": "inspection.report"},
                timeout_ms=500,
                max_attempts=1,
                on_success=None,
                on_failure=None,
                fallback_step_id=None,
                approval_scope=None,
            ),
        ),
        start_step_id="inspect",
        max_total_duration_ms=1000,
        cognitive_budget=_budget(),
        autonomy_envelope=_envelope(),
        learning_status="exam_validated",
        deployment_status=DeploymentStatus.COMPILED.value,
        evidence_refs=("exam-1",),
        content_digest="sha256:pattern",
    )


ROUND_TRIP_CASES = [
    ("observation.schema.json", Observation(
        observation_id="obs-1",
        source_id="camera-1",
        schema_ref="camera-frame/v1",
        observed_at="2026-06-23T00:00:00Z",
        received_at="2026-06-23T00:00:00Z",
        payload_ref="blob://obs-1",
        payload_digest="sha256:payload",
        confidence=0.99,
        freshness_ms=10,
        health_status="ok",
        provenance=("simulator",),
    )),
    ("world_state.schema.json", WorldState(
        state_id="state-1",
        created_at="2026-06-23T00:00:00Z",
        facts=(StateFact("battery.percent", 80, 0.95, ("obs-1",), None),),
        environment_tags=("simulated",),
        sensor_health=("camera:ok",),
        state_digest="sha256:state",
    )),
    ("capability_contract.schema.json", CapabilityContract(
        capability_id="cap.inspect_zone",
        version="v1",
        input_schema_ref="inspect-input/v1",
        output_schema_ref="inspect-output/v1",
        side_effect_class=SideEffectClass.READ_ONLY.value,
        required_permissions=("sensor.read",),
        idempotent=True,
        reversible=True,
        timeout_ms=500,
        simulator_adapter="deterministic.inspect",
        runtime_adapter=None,
        safe_fallback_capability_id=None,
    )),
    ("action_pattern.schema.json", _action_pattern()),
    ("action_receipt.schema.json", _receipt()),
    ("behavioral_exam_result.schema.json", BehavioralExamResult(
        exam_id="exam-1",
        action_pattern_id="ap-1",
        scenario_id="scenario-1",
        exam_kind="nominal",
        score=0.91,
        passed=True,
        receipts=(_receipt(),),
        outcome_evidence_id="outcome-1",
        safety_violations=(),
        trace_digest="sha256:trace",
        replay_digest="sha256:trace",
    )),
    ("outcome_evidence.schema.json", OutcomeEvidence(
        outcome_id="outcome-1",
        decision_cycle_id="cycle-1",
        pattern_id="pattern-1",
        action_pattern_id="ap-1",
        immediate_score=0.9,
        delayed_score=None,
        success=True,
        safety_violations=(),
        error_type=None,
        environment_tags=("simulated",),
        confounders=(),
        evidence_refs=("receipt-1",),
        attribution_confidence=0.8,
    )),
    ("step_credit.schema.json", StepCredit(
        outcome_id="outcome-1",
        step_id="inspect",
        contribution_score=0.7,
        causal_confidence=0.8,
        reason_codes=("completed_goal",),
    )),
    ("weakness_record.schema.json", WeaknessRecord(
        weakness_id="weakness-1",
        owner="Boss",
        domain="warehouse_robotics",
        skill_id="stale_sensor_detection",
        weakness_type="freshness_gap",
        evidence_refs=("outcome-1",),
        severity=0.82,
        recurrence_count=1,
        status="open",
    )),
    ("remediation_ticket.schema.json", RemediationTicket(
        ticket_id="ticket-1",
        weakness_id="weakness-1",
        affected_pattern_ids=("pattern-1",),
        affected_action_pattern_ids=("ap-1",),
        required_curriculum_units=("sensor_freshness",),
        required_exam_kinds=("stale_sensor",),
        required_score=0.85,
        blocks_operational_use=True,
        status="open",
    )),
    ("artifact_manifest.schema.json", ArtifactManifest(
        manifest_id="manifest-1",
        created_at="2026-06-23T00:00:00Z",
        artifact_type="edge_brain_bundle",
        artifact_refs=("runs/action_pattern.json",),
        artifact_digests=({"ref": "runs/action_pattern.json", "sha256": "abc123"},),
        dependency_digests=({"ref": "capability_registry.jsonl", "sha256": "def456"},),
        rollback_counter=0,
        signature_ref=None,
        verification_status="digest_verified",
    )),
]


def test_edge_brain_schema_files_are_valid() -> None:
    schema_files = sorted(SCHEMA_DIR.glob("*.schema.json"))

    assert schema_files
    for schema_path in schema_files:
        Draft202012Validator.check_schema(json.loads(schema_path.read_text(encoding="utf-8")))


@pytest.mark.parametrize(("schema_name", "artifact"), ROUND_TRIP_CASES)
def test_edge_brain_contracts_round_trip_and_validate(schema_name: str, artifact) -> None:
    payload = artifact.to_dict()
    restored = artifact.__class__.from_dict(payload)

    assert restored.to_dict() == payload
    _validate(schema_name, payload)


def test_action_pattern_rejects_unknown_deployment_status() -> None:
    payload = _action_pattern().to_dict()
    payload["deployment_status"] = "runtime_promoted_without_review"

    with pytest.raises(ValueError, match="Unsupported DeploymentStatus"):
        ActionPattern.from_dict(payload)


def test_capability_contract_rejects_unknown_side_effect_class() -> None:
    payload = ROUND_TRIP_CASES[2][1].to_dict()
    payload["side_effect_class"] = "arbitrary_shell"

    with pytest.raises(ValueError, match="Unsupported SideEffectClass"):
        CapabilityContract.from_dict(payload)


def test_action_pattern_schema_rejects_unreviewed_extra_fields() -> None:
    payload = _action_pattern().to_dict()
    payload["hidden_chain_of_thought"] = "do not store"

    with pytest.raises(ValidationError):
        _validate("action_pattern.schema.json", payload)


def test_schema_rejects_invalid_score_ranges() -> None:
    payload = deepcopy(ROUND_TRIP_CASES[8][1].to_dict())
    payload["severity"] = 1.5

    with pytest.raises(ValidationError):
        _validate("weakness_record.schema.json", payload)
