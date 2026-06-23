from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any


OBSERVATION_SCHEMA = "paideia-edge-observation/v1"
WORLD_STATE_SCHEMA = "paideia-edge-world-state/v1"
CAPABILITY_CONTRACT_SCHEMA = "paideia-edge-capability-contract/v1"
ACTION_PATTERN_SCHEMA = "paideia-edge-action-pattern/v1"
BEHAVIORAL_EXAM_RESULT_SCHEMA = "paideia-edge-behavioral-exam-result/v1"
ACTION_RECEIPT_SCHEMA = "paideia-edge-action-receipt/v1"
OUTCOME_EVIDENCE_SCHEMA = "paideia-edge-outcome-evidence/v1"
STEP_CREDIT_SCHEMA = "paideia-edge-step-credit/v1"
WEAKNESS_RECORD_SCHEMA = "paideia-edge-weakness-record/v1"
REMEDIATION_TICKET_SCHEMA = "paideia-edge-remediation-ticket/v1"
ARTIFACT_MANIFEST_SCHEMA = "paideia-edge-artifact-manifest/v1"

LEARNING_STATUSES = {
    "draft",
    "exam_validated",
    "field_validated",
    "reinforced",
    "weakened",
    "quarantined",
}

WEAKNESS_TYPES = {
    "knowledge_gap",
    "reasoning_gap",
    "risk_gap",
    "transfer_gap",
    "freshness_gap",
    "counterargument_gap",
    "capability_gap",
    "execution_gap",
    "safety_gap",
    "world_model_gap",
}

WEAKNESS_STATUSES = {
    "open",
    "under_remediation",
    "reexam_required",
    "resolved",
    "accepted_risk",
}

REMEDIATION_STATUSES = {
    "open",
    "planned",
    "in_progress",
    "reexam_required",
    "completed",
    "blocked",
    "closed",
}

ARTIFACT_VERIFICATION_STATUSES = {
    "unverified",
    "digest_verified",
    "signature_verified",
    "rejected",
}


class RuntimeMode(str, Enum):
    CONNECTED = "connected"
    LOCAL_DELIBERATIVE = "local_deliberative"
    PATTERN_ONLY = "pattern_only"
    SAFE_DEGRADED = "safe_degraded"
    SAFE_HALT = "safe_halt"


class BrainState(str, Enum):
    BOOTSTRAP = "bootstrap"
    SELF_TEST = "self_test"
    IDLE = "idle"
    OBSERVE = "observe"
    PLAN = "plan"
    SAFETY_CHECK = "safety_check"
    EXECUTE = "execute"
    MONITOR = "monitor"
    RECOVER = "recover"
    SAFE_HALT = "safe_halt"


class DeploymentStatus(str, Enum):
    NOT_COMPILED = "not_compiled"
    COMPILED = "compiled"
    SIMULATION_VALIDATED = "simulation_validated"
    SHADOW_VALIDATED = "shadow_validated"
    LIMITED_FIELD = "limited_field"
    OPERATIONAL = "operational"
    SUSPENDED = "suspended"
    REVOKED = "revoked"


class SideEffectClass(str, Enum):
    READ_ONLY = "read_only"
    REVERSIBLE = "reversible"
    CONSEQUENTIAL = "consequential"
    SAFETY_CRITICAL = "safety_critical"
    PROHIBITED = "prohibited"


def _string(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def _optional_string(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text if text else None


def _tuple_of_strings(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value,) if value else ()
    if isinstance(value, (list, tuple, set)):
        return tuple(str(item) for item in value if str(item))
    return (str(value),)


def _tuple_of_dicts(value: Any) -> tuple[dict[str, Any], ...]:
    if value is None:
        return ()
    if isinstance(value, dict):
        return (dict(value),)
    if isinstance(value, (list, tuple)):
        return tuple(dict(item) for item in value if isinstance(item, dict))
    return ()


def _dict_or_none(value: Any) -> dict[str, Any] | None:
    if value is None:
        return None
    if isinstance(value, dict):
        return dict(value)
    raise TypeError("expected a dict or None")


def _int(value: Any, default: int = 0) -> int:
    if isinstance(value, bool):
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _float(value: Any, default: float = 0.0) -> float:
    if isinstance(value, bool):
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _score(value: Any, default: float = 0.0) -> float:
    return max(0.0, min(1.0, _float(value, default)))


def _enum_value(value: Any, enum_cls: type[Enum], default: str) -> str:
    text = _string(value, default)
    allowed = {str(item.value) for item in enum_cls}
    if text not in allowed:
        raise ValueError(f"Unsupported {enum_cls.__name__}: {text}")
    return text


def _one_of(value: Any, allowed: set[str], default: str, field_name: str) -> str:
    text = _string(value, default)
    if text not in allowed:
        raise ValueError(f"Unsupported {field_name}: {text}")
    return text


def _round_or_none(value: float | None) -> float | None:
    if value is None:
        return None
    return round(float(value), 4)


@dataclass(frozen=True)
class Observation:
    observation_id: str
    source_id: str
    schema_ref: str
    observed_at: str
    received_at: str
    payload_ref: str
    payload_digest: str
    confidence: float
    freshness_ms: int
    health_status: str
    provenance: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "confidence", _score(self.confidence))
        object.__setattr__(self, "freshness_ms", max(0, int(self.freshness_ms)))

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["schema"] = OBSERVATION_SCHEMA
        data["confidence"] = round(float(self.confidence), 4)
        data["provenance"] = list(self.provenance)
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Observation":
        return cls(
            observation_id=_string(data.get("observation_id"), "observation"),
            source_id=_string(data.get("source_id"), "source"),
            schema_ref=_string(data.get("schema_ref"), "unknown/v1"),
            observed_at=_string(data.get("observed_at")),
            received_at=_string(data.get("received_at")),
            payload_ref=_string(data.get("payload_ref")),
            payload_digest=_string(data.get("payload_digest")),
            confidence=_score(data.get("confidence"), 1.0),
            freshness_ms=max(0, _int(data.get("freshness_ms"))),
            health_status=_string(data.get("health_status"), "unknown"),
            provenance=_tuple_of_strings(data.get("provenance")),
        )


@dataclass(frozen=True)
class StateFact:
    key: str
    value: object
    confidence: float
    source_observation_ids: tuple[str, ...]
    valid_until: str | None

    def __post_init__(self) -> None:
        object.__setattr__(self, "confidence", _score(self.confidence))

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["confidence"] = round(float(self.confidence), 4)
        data["source_observation_ids"] = list(self.source_observation_ids)
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "StateFact":
        return cls(
            key=_string(data.get("key"), "fact"),
            value=data.get("value"),
            confidence=_score(data.get("confidence"), 1.0),
            source_observation_ids=_tuple_of_strings(data.get("source_observation_ids")),
            valid_until=_optional_string(data.get("valid_until")),
        )


@dataclass(frozen=True)
class WorldState:
    state_id: str
    created_at: str
    facts: tuple[StateFact, ...]
    environment_tags: tuple[str, ...]
    sensor_health: tuple[str, ...]
    state_digest: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": WORLD_STATE_SCHEMA,
            "state_id": self.state_id,
            "created_at": self.created_at,
            "facts": [fact.to_dict() for fact in self.facts],
            "environment_tags": list(self.environment_tags),
            "sensor_health": list(self.sensor_health),
            "state_digest": self.state_digest,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "WorldState":
        return cls(
            state_id=_string(data.get("state_id"), "state"),
            created_at=_string(data.get("created_at")),
            facts=tuple(StateFact.from_dict(item) for item in data.get("facts", []) if isinstance(item, dict)),
            environment_tags=_tuple_of_strings(data.get("environment_tags")),
            sensor_health=_tuple_of_strings(data.get("sensor_health")),
            state_digest=_string(data.get("state_digest")),
        )


@dataclass(frozen=True)
class CognitiveBudget:
    max_cycle_ms: int
    max_local_model_tokens: int
    max_remote_model_tokens: int
    max_energy_units: float | None
    max_memory_mb: int | None
    network_allowed: bool
    remote_calls_allowed: int

    def __post_init__(self) -> None:
        for field_name in (
            "max_cycle_ms",
            "max_local_model_tokens",
            "max_remote_model_tokens",
            "remote_calls_allowed",
        ):
            object.__setattr__(self, field_name, max(0, int(getattr(self, field_name))))
        if self.max_memory_mb is not None:
            object.__setattr__(self, "max_memory_mb", max(0, int(self.max_memory_mb)))
        if self.max_energy_units is not None:
            object.__setattr__(self, "max_energy_units", max(0.0, float(self.max_energy_units)))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CognitiveBudget":
        return cls(
            max_cycle_ms=max(0, _int(data.get("max_cycle_ms"))),
            max_local_model_tokens=max(0, _int(data.get("max_local_model_tokens"))),
            max_remote_model_tokens=max(0, _int(data.get("max_remote_model_tokens"))),
            max_energy_units=None if data.get("max_energy_units") is None else max(0.0, _float(data.get("max_energy_units"))),
            max_memory_mb=None if data.get("max_memory_mb") is None else max(0, _int(data.get("max_memory_mb"))),
            network_allowed=bool(data.get("network_allowed", False)),
            remote_calls_allowed=max(0, _int(data.get("remote_calls_allowed"))),
        )


@dataclass(frozen=True)
class AutonomyEnvelope:
    envelope_id: str
    allowed_capabilities: tuple[str, ...]
    prohibited_capabilities: tuple[str, ...]
    allowed_side_effect_classes: tuple[str, ...]
    max_operation_duration_ms: int
    required_health_signals: tuple[str, ...]
    abort_conditions: tuple[dict[str, Any], ...]
    human_approval_scopes: tuple[str, ...]
    offline_policy: str

    def __post_init__(self) -> None:
        invalid = set(self.allowed_side_effect_classes) - {item.value for item in SideEffectClass}
        if invalid:
            raise ValueError(f"Unsupported side effect classes: {sorted(invalid)}")
        object.__setattr__(self, "max_operation_duration_ms", max(0, int(self.max_operation_duration_ms)))

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        for key in (
            "allowed_capabilities",
            "prohibited_capabilities",
            "allowed_side_effect_classes",
            "required_health_signals",
            "human_approval_scopes",
        ):
            data[key] = list(data[key])
        data["abort_conditions"] = [dict(item) for item in self.abort_conditions]
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AutonomyEnvelope":
        return cls(
            envelope_id=_string(data.get("envelope_id"), "envelope"),
            allowed_capabilities=_tuple_of_strings(data.get("allowed_capabilities")),
            prohibited_capabilities=_tuple_of_strings(data.get("prohibited_capabilities")),
            allowed_side_effect_classes=_tuple_of_strings(data.get("allowed_side_effect_classes")),
            max_operation_duration_ms=max(0, _int(data.get("max_operation_duration_ms"))),
            required_health_signals=_tuple_of_strings(data.get("required_health_signals")),
            abort_conditions=_tuple_of_dicts(data.get("abort_conditions")),
            human_approval_scopes=_tuple_of_strings(data.get("human_approval_scopes")),
            offline_policy=_string(data.get("offline_policy"), "degrade"),
        )


@dataclass(frozen=True)
class CapabilityContract:
    capability_id: str
    version: str
    input_schema_ref: str
    output_schema_ref: str
    side_effect_class: str
    required_permissions: tuple[str, ...]
    idempotent: bool
    reversible: bool
    timeout_ms: int
    simulator_adapter: str
    runtime_adapter: str | None
    safe_fallback_capability_id: str | None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "side_effect_class",
            _enum_value(self.side_effect_class, SideEffectClass, SideEffectClass.READ_ONLY.value),
        )
        object.__setattr__(self, "timeout_ms", max(0, int(self.timeout_ms)))

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["schema"] = CAPABILITY_CONTRACT_SCHEMA
        data["required_permissions"] = list(self.required_permissions)
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CapabilityContract":
        return cls(
            capability_id=_string(data.get("capability_id"), "capability"),
            version=_string(data.get("version"), "v1"),
            input_schema_ref=_string(data.get("input_schema_ref")),
            output_schema_ref=_string(data.get("output_schema_ref")),
            side_effect_class=_string(data.get("side_effect_class"), SideEffectClass.READ_ONLY.value),
            required_permissions=_tuple_of_strings(data.get("required_permissions")),
            idempotent=bool(data.get("idempotent", False)),
            reversible=bool(data.get("reversible", False)),
            timeout_ms=max(0, _int(data.get("timeout_ms"))),
            simulator_adapter=_string(data.get("simulator_adapter")),
            runtime_adapter=_optional_string(data.get("runtime_adapter")),
            safe_fallback_capability_id=_optional_string(data.get("safe_fallback_capability_id")),
        )


@dataclass(frozen=True)
class ActionStep:
    step_id: str
    kind: str
    capability_id: str | None
    input_bindings: tuple[dict[str, Any], ...]
    guard: dict[str, Any] | None
    success_condition: dict[str, Any] | None
    timeout_ms: int
    max_attempts: int
    on_success: str | None
    on_failure: str | None
    fallback_step_id: str | None
    approval_scope: str | None

    def __post_init__(self) -> None:
        object.__setattr__(self, "timeout_ms", max(0, int(self.timeout_ms)))
        object.__setattr__(self, "max_attempts", max(1, int(self.max_attempts)))

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["input_bindings"] = [dict(item) for item in self.input_bindings]
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ActionStep":
        return cls(
            step_id=_string(data.get("step_id"), "step"),
            kind=_string(data.get("kind"), "capability"),
            capability_id=_optional_string(data.get("capability_id")),
            input_bindings=_tuple_of_dicts(data.get("input_bindings")),
            guard=_dict_or_none(data.get("guard")),
            success_condition=_dict_or_none(data.get("success_condition")),
            timeout_ms=max(0, _int(data.get("timeout_ms"))),
            max_attempts=max(1, _int(data.get("max_attempts"), 1)),
            on_success=_optional_string(data.get("on_success")),
            on_failure=_optional_string(data.get("on_failure")),
            fallback_step_id=_optional_string(data.get("fallback_step_id")),
            approval_scope=_optional_string(data.get("approval_scope")),
        )


@dataclass(frozen=True)
class ActionPattern:
    action_pattern_id: str
    version: str
    source_pattern_id: str
    source_kibo_ids: tuple[str, ...]
    owner: str
    domain: str
    task_family: str
    required_observations: tuple[str, ...]
    required_capabilities: tuple[str, ...]
    preconditions: tuple[dict[str, Any], ...]
    invariants: tuple[dict[str, Any], ...]
    postconditions: tuple[dict[str, Any], ...]
    steps: tuple[ActionStep, ...]
    start_step_id: str
    max_total_duration_ms: int
    cognitive_budget: CognitiveBudget
    autonomy_envelope: AutonomyEnvelope
    learning_status: str
    deployment_status: str
    evidence_refs: tuple[str, ...]
    content_digest: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "learning_status", _one_of(self.learning_status, LEARNING_STATUSES, "draft", "learning_status"))
        object.__setattr__(
            self,
            "deployment_status",
            _enum_value(self.deployment_status, DeploymentStatus, DeploymentStatus.NOT_COMPILED.value),
        )
        object.__setattr__(self, "max_total_duration_ms", max(0, int(self.max_total_duration_ms)))

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": ACTION_PATTERN_SCHEMA,
            "action_pattern_id": self.action_pattern_id,
            "version": self.version,
            "source_pattern_id": self.source_pattern_id,
            "source_kibo_ids": list(self.source_kibo_ids),
            "owner": self.owner,
            "domain": self.domain,
            "task_family": self.task_family,
            "required_observations": list(self.required_observations),
            "required_capabilities": list(self.required_capabilities),
            "preconditions": [dict(item) for item in self.preconditions],
            "invariants": [dict(item) for item in self.invariants],
            "postconditions": [dict(item) for item in self.postconditions],
            "steps": [step.to_dict() for step in self.steps],
            "start_step_id": self.start_step_id,
            "max_total_duration_ms": self.max_total_duration_ms,
            "cognitive_budget": self.cognitive_budget.to_dict(),
            "autonomy_envelope": self.autonomy_envelope.to_dict(),
            "learning_status": self.learning_status,
            "deployment_status": self.deployment_status,
            "evidence_refs": list(self.evidence_refs),
            "content_digest": self.content_digest,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ActionPattern":
        return cls(
            action_pattern_id=_string(data.get("action_pattern_id"), "action-pattern"),
            version=_string(data.get("version"), "v1"),
            source_pattern_id=_string(data.get("source_pattern_id"), "pattern"),
            source_kibo_ids=_tuple_of_strings(data.get("source_kibo_ids")),
            owner=_string(data.get("owner"), "Boss"),
            domain=_string(data.get("domain"), "general"),
            task_family=_string(data.get("task_family"), "general_task"),
            required_observations=_tuple_of_strings(data.get("required_observations")),
            required_capabilities=_tuple_of_strings(data.get("required_capabilities")),
            preconditions=_tuple_of_dicts(data.get("preconditions")),
            invariants=_tuple_of_dicts(data.get("invariants")),
            postconditions=_tuple_of_dicts(data.get("postconditions")),
            steps=tuple(ActionStep.from_dict(item) for item in data.get("steps", []) if isinstance(item, dict)),
            start_step_id=_string(data.get("start_step_id"), "start"),
            max_total_duration_ms=max(0, _int(data.get("max_total_duration_ms"))),
            cognitive_budget=CognitiveBudget.from_dict(data.get("cognitive_budget") or {}),
            autonomy_envelope=AutonomyEnvelope.from_dict(data.get("autonomy_envelope") or {}),
            learning_status=_string(data.get("learning_status"), "draft"),
            deployment_status=_string(data.get("deployment_status"), DeploymentStatus.NOT_COMPILED.value),
            evidence_refs=_tuple_of_strings(data.get("evidence_refs")),
            content_digest=_string(data.get("content_digest")),
        )


@dataclass(frozen=True)
class ActionReceipt:
    receipt_id: str
    decision_cycle_id: str
    action_pattern_id: str
    step_id: str
    capability_id: str
    requested_at: str
    completed_at: str | None
    status: str
    input_digest: str
    output_ref: str | None
    output_digest: str | None
    observed_side_effects: tuple[str, ...]
    error_code: str | None
    rollback_status: str | None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["schema"] = ACTION_RECEIPT_SCHEMA
        data["observed_side_effects"] = list(self.observed_side_effects)
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ActionReceipt":
        return cls(
            receipt_id=_string(data.get("receipt_id"), "receipt"),
            decision_cycle_id=_string(data.get("decision_cycle_id"), "cycle"),
            action_pattern_id=_string(data.get("action_pattern_id"), "action-pattern"),
            step_id=_string(data.get("step_id"), "step"),
            capability_id=_string(data.get("capability_id"), "capability"),
            requested_at=_string(data.get("requested_at")),
            completed_at=_optional_string(data.get("completed_at")),
            status=_string(data.get("status"), "requested"),
            input_digest=_string(data.get("input_digest")),
            output_ref=_optional_string(data.get("output_ref")),
            output_digest=_optional_string(data.get("output_digest")),
            observed_side_effects=_tuple_of_strings(data.get("observed_side_effects")),
            error_code=_optional_string(data.get("error_code")),
            rollback_status=_optional_string(data.get("rollback_status")),
        )


@dataclass(frozen=True)
class BehavioralExamResult:
    exam_id: str
    action_pattern_id: str
    scenario_id: str
    exam_kind: str
    score: float
    passed: bool
    receipts: tuple[ActionReceipt, ...]
    outcome_evidence_id: str | None
    safety_violations: tuple[str, ...]
    trace_digest: str
    replay_digest: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "score", _score(self.score))

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": BEHAVIORAL_EXAM_RESULT_SCHEMA,
            "exam_id": self.exam_id,
            "action_pattern_id": self.action_pattern_id,
            "scenario_id": self.scenario_id,
            "exam_kind": self.exam_kind,
            "score": round(float(self.score), 4),
            "passed": self.passed,
            "receipts": [receipt.to_dict() for receipt in self.receipts],
            "outcome_evidence_id": self.outcome_evidence_id,
            "safety_violations": list(self.safety_violations),
            "trace_digest": self.trace_digest,
            "replay_digest": self.replay_digest,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BehavioralExamResult":
        return cls(
            exam_id=_string(data.get("exam_id"), "behavioral-exam"),
            action_pattern_id=_string(data.get("action_pattern_id"), "action-pattern"),
            scenario_id=_string(data.get("scenario_id"), "scenario"),
            exam_kind=_string(data.get("exam_kind"), "nominal"),
            score=_score(data.get("score")),
            passed=bool(data.get("passed", False)),
            receipts=tuple(ActionReceipt.from_dict(item) for item in data.get("receipts", []) if isinstance(item, dict)),
            outcome_evidence_id=_optional_string(data.get("outcome_evidence_id")),
            safety_violations=_tuple_of_strings(data.get("safety_violations")),
            trace_digest=_string(data.get("trace_digest")),
            replay_digest=_string(data.get("replay_digest")),
        )


@dataclass(frozen=True)
class OutcomeEvidence:
    outcome_id: str
    decision_cycle_id: str
    pattern_id: str
    action_pattern_id: str
    immediate_score: float | None
    delayed_score: float | None
    success: bool | None
    safety_violations: tuple[str, ...]
    error_type: str | None
    environment_tags: tuple[str, ...]
    confounders: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    attribution_confidence: float

    def __post_init__(self) -> None:
        if self.immediate_score is not None:
            object.__setattr__(self, "immediate_score", _score(self.immediate_score))
        if self.delayed_score is not None:
            object.__setattr__(self, "delayed_score", _score(self.delayed_score))
        object.__setattr__(self, "attribution_confidence", _score(self.attribution_confidence))

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["schema"] = OUTCOME_EVIDENCE_SCHEMA
        for key in ("safety_violations", "environment_tags", "confounders", "evidence_refs"):
            data[key] = list(data[key])
        data["immediate_score"] = _round_or_none(self.immediate_score)
        data["delayed_score"] = _round_or_none(self.delayed_score)
        data["attribution_confidence"] = round(float(self.attribution_confidence), 4)
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "OutcomeEvidence":
        return cls(
            outcome_id=_string(data.get("outcome_id"), "outcome"),
            decision_cycle_id=_string(data.get("decision_cycle_id"), "cycle"),
            pattern_id=_string(data.get("pattern_id"), "pattern"),
            action_pattern_id=_string(data.get("action_pattern_id"), "action-pattern"),
            immediate_score=None if data.get("immediate_score") is None else _score(data.get("immediate_score")),
            delayed_score=None if data.get("delayed_score") is None else _score(data.get("delayed_score")),
            success=data.get("success") if data.get("success") is None else bool(data.get("success")),
            safety_violations=_tuple_of_strings(data.get("safety_violations")),
            error_type=_optional_string(data.get("error_type")),
            environment_tags=_tuple_of_strings(data.get("environment_tags")),
            confounders=_tuple_of_strings(data.get("confounders")),
            evidence_refs=_tuple_of_strings(data.get("evidence_refs")),
            attribution_confidence=_score(data.get("attribution_confidence"), 0.0),
        )


@dataclass(frozen=True)
class StepCredit:
    outcome_id: str
    step_id: str
    contribution_score: float
    causal_confidence: float
    reason_codes: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "contribution_score", max(-1.0, min(1.0, float(self.contribution_score))))
        object.__setattr__(self, "causal_confidence", _score(self.causal_confidence))

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["schema"] = STEP_CREDIT_SCHEMA
        data["contribution_score"] = round(float(self.contribution_score), 4)
        data["causal_confidence"] = round(float(self.causal_confidence), 4)
        data["reason_codes"] = list(self.reason_codes)
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "StepCredit":
        return cls(
            outcome_id=_string(data.get("outcome_id"), "outcome"),
            step_id=_string(data.get("step_id"), "step"),
            contribution_score=max(-1.0, min(1.0, _float(data.get("contribution_score")))),
            causal_confidence=_score(data.get("causal_confidence")),
            reason_codes=_tuple_of_strings(data.get("reason_codes")),
        )


@dataclass(frozen=True)
class WeaknessRecord:
    weakness_id: str
    owner: str
    domain: str
    skill_id: str
    weakness_type: str
    evidence_refs: tuple[str, ...]
    severity: float
    recurrence_count: int
    status: str

    def __post_init__(self) -> None:
        if not self.weakness_id:
            raise ValueError("weakness_id is required")
        if not self.skill_id:
            raise ValueError("skill_id is required")
        object.__setattr__(self, "weakness_type", _one_of(self.weakness_type, WEAKNESS_TYPES, "reasoning_gap", "weakness_type"))
        object.__setattr__(self, "severity", _score(self.severity))
        object.__setattr__(self, "recurrence_count", max(0, int(self.recurrence_count)))
        object.__setattr__(self, "status", _one_of(self.status, WEAKNESS_STATUSES, "open", "status"))

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["schema"] = WEAKNESS_RECORD_SCHEMA
        data["evidence_refs"] = list(self.evidence_refs)
        data["severity"] = round(float(self.severity), 4)
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "WeaknessRecord":
        return cls(
            weakness_id=_string(data.get("weakness_id"), "weakness"),
            owner=_string(data.get("owner"), "Boss"),
            domain=_string(data.get("domain"), "general"),
            skill_id=_string(data.get("skill_id"), "general_reasoning"),
            weakness_type=_string(data.get("weakness_type"), "reasoning_gap"),
            evidence_refs=_tuple_of_strings(data.get("evidence_refs")),
            severity=_score(data.get("severity")),
            recurrence_count=max(0, _int(data.get("recurrence_count"))),
            status=_string(data.get("status"), "open"),
        )


@dataclass(frozen=True)
class RemediationTicket:
    ticket_id: str
    weakness_id: str
    affected_pattern_ids: tuple[str, ...]
    affected_action_pattern_ids: tuple[str, ...]
    required_curriculum_units: tuple[str, ...]
    required_exam_kinds: tuple[str, ...]
    required_score: float
    blocks_operational_use: bool
    status: str

    def __post_init__(self) -> None:
        if not self.ticket_id:
            raise ValueError("ticket_id is required")
        if not self.weakness_id:
            raise ValueError("weakness_id is required")
        object.__setattr__(self, "required_score", _score(self.required_score, 0.8))
        object.__setattr__(self, "status", _one_of(self.status, REMEDIATION_STATUSES, "open", "status"))

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["schema"] = REMEDIATION_TICKET_SCHEMA
        for key in (
            "affected_pattern_ids",
            "affected_action_pattern_ids",
            "required_curriculum_units",
            "required_exam_kinds",
        ):
            data[key] = list(data[key])
        data["required_score"] = round(float(self.required_score), 4)
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RemediationTicket":
        return cls(
            ticket_id=_string(data.get("ticket_id"), "ticket"),
            weakness_id=_string(data.get("weakness_id"), "weakness"),
            affected_pattern_ids=_tuple_of_strings(data.get("affected_pattern_ids")),
            affected_action_pattern_ids=_tuple_of_strings(data.get("affected_action_pattern_ids")),
            required_curriculum_units=_tuple_of_strings(data.get("required_curriculum_units")),
            required_exam_kinds=_tuple_of_strings(data.get("required_exam_kinds")),
            required_score=_score(data.get("required_score"), 0.8),
            blocks_operational_use=bool(data.get("blocks_operational_use", True)),
            status=_string(data.get("status"), "open"),
        )


@dataclass(frozen=True)
class ArtifactManifest:
    manifest_id: str
    created_at: str
    artifact_type: str
    artifact_refs: tuple[str, ...]
    artifact_digests: tuple[dict[str, Any], ...]
    dependency_digests: tuple[dict[str, Any], ...]
    rollback_counter: int
    signature_ref: str | None
    verification_status: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "rollback_counter", max(0, int(self.rollback_counter)))
        object.__setattr__(
            self,
            "verification_status",
            _one_of(self.verification_status, ARTIFACT_VERIFICATION_STATUSES, "unverified", "verification_status"),
        )

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["schema"] = ARTIFACT_MANIFEST_SCHEMA
        data["artifact_refs"] = list(self.artifact_refs)
        data["artifact_digests"] = [dict(item) for item in self.artifact_digests]
        data["dependency_digests"] = [dict(item) for item in self.dependency_digests]
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ArtifactManifest":
        return cls(
            manifest_id=_string(data.get("manifest_id"), "manifest"),
            created_at=_string(data.get("created_at")),
            artifact_type=_string(data.get("artifact_type"), "edge_brain_bundle"),
            artifact_refs=_tuple_of_strings(data.get("artifact_refs")),
            artifact_digests=_tuple_of_dicts(data.get("artifact_digests")),
            dependency_digests=_tuple_of_dicts(data.get("dependency_digests")),
            rollback_counter=max(0, _int(data.get("rollback_counter"))),
            signature_ref=_optional_string(data.get("signature_ref")),
            verification_status=_string(data.get("verification_status"), "unverified"),
        )
