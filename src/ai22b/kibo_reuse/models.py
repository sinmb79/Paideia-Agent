from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


TASK_FINGERPRINT_SCHEMA = "paideia-task-fingerprint/v1"
KIBO_RECORD_SCHEMA = "paideia-kibo-record/v1"
REUSE_DECISION_SCHEMA = "paideia-kibo-reuse-decision/v1"
REUSE_PLAN_SCHEMA = "paideia-kibo-reuse-plan/v1"
PATTERN_CANDIDATE_SCHEMA = "paideia-pattern-candidate/v1"
PATTERN_EXAM_RESULT_SCHEMA = "paideia-pattern-exam-result/v1"
REAL_WORLD_OUTCOME_SCHEMA = "paideia-real-world-outcome/v1"
FAILURE_MEMORY_SCHEMA = "paideia-failure-memory/v1"
USER_DECISION_MODEL_SCHEMA = "paideia-user-decision-model/v1"
CRITIC_REPORT_SCHEMA = "paideia-critic-report/v1"
SKILL_NODE_SCHEMA = "paideia-skill-node/v1"
SKILL_EDGE_SCHEMA = "paideia-skill-edge/v1"

REUSE_MODES = {
    "direct_reuse",
    "partial_reuse",
    "reference_only",
    "reject_and_solve_fresh",
    "quarantine_required",
}

APPROVED_PROMOTION_STATUSES = {
    "active",
    "approved",
    "promoted",
    "reviewed",
    "verified",
}

BLOCKED_PROMOTION_STATUSES = {
    "candidate",
    "candidate_until_repeatedly_verified",
    "draft",
    "failed",
    "needs_review",
    "quarantine",
    "quarantined",
    "unreviewed",
}

PATTERN_STATUSES = {
    "draft",
    "exam_validated",
    "field_validated",
    "reinforced",
    "weakened",
    "quarantined",
}


def _tuple_of_strings(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value,) if value else ()
    if isinstance(value, (list, tuple, set)):
        return tuple(str(item) for item in value if str(item))
    return (str(value),)


def _string(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


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


@dataclass(frozen=True)
class TaskFingerprint:
    task_id: str
    owner: str
    domain: str
    task_type: str
    intent: str
    constraints: tuple[str, ...]
    required_capabilities: tuple[str, ...]
    risk_level: str
    freshness_required: bool
    expected_output_type: str
    user_style_markers: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["schema"] = TASK_FINGERPRINT_SCHEMA
        for key in ["constraints", "required_capabilities", "user_style_markers"]:
            data[key] = list(data[key])
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TaskFingerprint":
        return cls(
            task_id=_string(data.get("task_id"), "task"),
            owner=_string(data.get("owner"), "Boss"),
            domain=_string(data.get("domain"), "general"),
            task_type=_string(data.get("task_type"), "general_task"),
            intent=_string(data.get("intent"), "answer_user_request"),
            constraints=_tuple_of_strings(data.get("constraints")),
            required_capabilities=_tuple_of_strings(data.get("required_capabilities")),
            risk_level=_string(data.get("risk_level"), "medium"),
            freshness_required=bool(data.get("freshness_required", False)),
            expected_output_type=_string(data.get("expected_output_type"), "response"),
            user_style_markers=_tuple_of_strings(data.get("user_style_markers")),
        )


@dataclass(frozen=True)
class KiboRecord:
    kibo_id: str
    source_run_id: str
    owner: str
    domain: str
    task_type: str
    problem_signature: str
    solution_steps: tuple[str, ...]
    reusable_logic: tuple[str, ...]
    failure_modes: tuple[str, ...]
    required_inputs: tuple[str, ...]
    output_template: str
    evidence_refs: tuple[str, ...]
    success_score: int
    promotion_status: str
    created_at: str
    updated_at: str
    last_used_at: str = ""
    caveats: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["schema"] = KIBO_RECORD_SCHEMA
        for key in [
            "solution_steps",
            "reusable_logic",
            "failure_modes",
            "required_inputs",
            "evidence_refs",
            "caveats",
        ]:
            data[key] = list(data[key])
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "KiboRecord":
        return cls(
            kibo_id=_string(data.get("kibo_id") or data.get("id") or data.get("entry_id"), "kibo"),
            source_run_id=_string(data.get("source_run_id") or data.get("run_id")),
            owner=_string(data.get("owner"), "Boss"),
            domain=_string(data.get("domain") or data.get("task_domain"), "general"),
            task_type=_string(data.get("task_type") or data.get("entry_type"), "general_task"),
            problem_signature=_string(
                data.get("problem_signature")
                or data.get("summary")
                or data.get("title")
                or data.get("review_summary")
            ),
            solution_steps=_tuple_of_strings(data.get("solution_steps") or data.get("steps")),
            reusable_logic=_tuple_of_strings(data.get("reusable_logic") or data.get("promoted_skills")),
            failure_modes=_tuple_of_strings(data.get("failure_modes")),
            required_inputs=_tuple_of_strings(data.get("required_inputs")),
            output_template=_string(data.get("output_template")),
            evidence_refs=_tuple_of_strings(data.get("evidence_refs") or data.get("evidence")),
            success_score=max(0, min(100, _int(data.get("success_score") or data.get("score"), 0))),
            promotion_status=_string(
                data.get("promotion_status")
                or data.get("review_status")
                or data.get("promotion_state")
                or data.get("status"),
                "unreviewed",
            ),
            created_at=_string(data.get("created_at") or data.get("created_at_utc") or data.get("recorded_at_utc")),
            updated_at=_string(data.get("updated_at") or data.get("updated_at_utc") or data.get("created_at")),
            last_used_at=_string(data.get("last_used_at")),
            caveats=_tuple_of_strings(data.get("caveats")),
        )

    @property
    def is_runtime_eligible(self) -> bool:
        return self.promotion_status.casefold() in APPROVED_PROMOTION_STATUSES


@dataclass(frozen=True)
class ReuseDecision:
    decision_id: str
    task_id: str
    selected_kibo_ids: tuple[str, ...]
    similarity_score: float
    confidence_score: float
    risk_score: float
    reuse_mode: str
    llm_required_parts: tuple[str, ...]
    reason: str
    pattern_id: str | None = None
    pattern_status: str | None = None
    exam_validated: bool = False
    field_validated: bool = False
    failure_warnings: tuple[str, ...] = ()
    critic_required: bool = False
    user_decision_fit_score: float = 0.0

    def __post_init__(self) -> None:
        if self.reuse_mode not in REUSE_MODES:
            raise ValueError(f"Unsupported reuse_mode: {self.reuse_mode}")

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["schema"] = REUSE_DECISION_SCHEMA
        data["selected_kibo_ids"] = list(data["selected_kibo_ids"])
        data["llm_required_parts"] = list(data["llm_required_parts"])
        data["failure_warnings"] = list(data["failure_warnings"])
        data["similarity_score"] = round(float(data["similarity_score"]), 4)
        data["confidence_score"] = round(float(data["confidence_score"]), 4)
        data["risk_score"] = round(float(data["risk_score"]), 4)
        data["user_decision_fit_score"] = round(float(data["user_decision_fit_score"]), 4)
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ReuseDecision":
        return cls(
            decision_id=_string(data.get("decision_id"), "reuse-decision"),
            task_id=_string(data.get("task_id"), "task"),
            selected_kibo_ids=_tuple_of_strings(data.get("selected_kibo_ids")),
            similarity_score=_float(data.get("similarity_score")),
            confidence_score=_float(data.get("confidence_score")),
            risk_score=_float(data.get("risk_score")),
            reuse_mode=_string(data.get("reuse_mode"), "reject_and_solve_fresh"),
            llm_required_parts=_tuple_of_strings(data.get("llm_required_parts")),
            reason=_string(data.get("reason")),
            pattern_id=data.get("pattern_id") if data.get("pattern_id") is not None else None,
            pattern_status=data.get("pattern_status") if data.get("pattern_status") is not None else None,
            exam_validated=bool(data.get("exam_validated", False)),
            field_validated=bool(data.get("field_validated", False)),
            failure_warnings=_tuple_of_strings(data.get("failure_warnings")),
            critic_required=bool(data.get("critic_required", False)),
            user_decision_fit_score=_float(data.get("user_decision_fit_score")),
        )


@dataclass(frozen=True)
class PatternCandidate:
    pattern_id: str
    owner: str
    domain: str
    task_family: str
    abstract_strategy: tuple[str, ...]
    required_conditions: tuple[str, ...]
    known_failure_modes: tuple[str, ...]
    source_kibo_ids: tuple[str, ...]
    exam_score: float | None
    real_world_score: float | None
    reinforcement_score: float
    status: str

    def __post_init__(self) -> None:
        if not self.source_kibo_ids:
            raise ValueError("PatternCandidate requires at least one source_kibo_id")
        if self.status not in PATTERN_STATUSES:
            raise ValueError(f"Unsupported pattern status: {self.status}")

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["schema"] = PATTERN_CANDIDATE_SCHEMA
        for key in [
            "abstract_strategy",
            "required_conditions",
            "known_failure_modes",
            "source_kibo_ids",
        ]:
            data[key] = list(data[key])
        data["reinforcement_score"] = round(float(data["reinforcement_score"]), 4)
        if data["exam_score"] is not None:
            data["exam_score"] = round(float(data["exam_score"]), 4)
        if data["real_world_score"] is not None:
            data["real_world_score"] = round(float(data["real_world_score"]), 4)
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PatternCandidate":
        return cls(
            pattern_id=_string(data.get("pattern_id"), "pattern"),
            owner=_string(data.get("owner"), "Boss"),
            domain=_string(data.get("domain"), "general"),
            task_family=_string(data.get("task_family") or data.get("task_type"), "general_task"),
            abstract_strategy=_tuple_of_strings(data.get("abstract_strategy")),
            required_conditions=_tuple_of_strings(data.get("required_conditions")),
            known_failure_modes=_tuple_of_strings(data.get("known_failure_modes")),
            source_kibo_ids=_tuple_of_strings(data.get("source_kibo_ids")),
            exam_score=None if data.get("exam_score") is None else _float(data.get("exam_score")),
            real_world_score=None
            if data.get("real_world_score") is None
            else _float(data.get("real_world_score")),
            reinforcement_score=_float(data.get("reinforcement_score")),
            status=_string(data.get("status"), "draft"),
        )

    @property
    def exam_validated(self) -> bool:
        return self.status in {"exam_validated", "field_validated", "reinforced"}

    @property
    def field_validated(self) -> bool:
        return self.status in {"field_validated", "reinforced"}

    @property
    def is_quarantined(self) -> bool:
        return self.status == "quarantined"


@dataclass(frozen=True)
class PatternExamResult:
    exam_id: str
    pattern_id: str
    task_id: str
    score: float
    passed: bool
    mistakes: tuple[str, ...]
    improvement_notes: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["schema"] = PATTERN_EXAM_RESULT_SCHEMA
        data["score"] = round(float(data["score"]), 4)
        data["mistakes"] = list(data["mistakes"])
        data["improvement_notes"] = list(data["improvement_notes"])
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PatternExamResult":
        return cls(
            exam_id=_string(data.get("exam_id"), "exam"),
            pattern_id=_string(data.get("pattern_id"), "pattern"),
            task_id=_string(data.get("task_id"), "task"),
            score=max(0.0, min(1.0, _float(data.get("score")))),
            passed=bool(data.get("passed", False)),
            mistakes=_tuple_of_strings(data.get("mistakes")),
            improvement_notes=_tuple_of_strings(data.get("improvement_notes")),
        )


@dataclass(frozen=True)
class RealWorldOutcome:
    outcome_id: str
    pattern_id: str
    task_id: str
    applied_at: str
    outcome_type: str
    success: bool
    quantitative_result: float | None
    qualitative_result: str | None
    user_feedback_score: int | None
    error_type: str | None
    notes: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["schema"] = REAL_WORLD_OUTCOME_SCHEMA
        data["notes"] = list(data["notes"])
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RealWorldOutcome":
        feedback = data.get("user_feedback_score")
        return cls(
            outcome_id=_string(data.get("outcome_id"), "outcome"),
            pattern_id=_string(data.get("pattern_id"), "pattern"),
            task_id=_string(data.get("task_id"), "task"),
            applied_at=_string(data.get("applied_at")),
            outcome_type=_string(data.get("outcome_type"), "task_outcome"),
            success=bool(data.get("success", False)),
            quantitative_result=None
            if data.get("quantitative_result") is None
            else _float(data.get("quantitative_result")),
            qualitative_result=data.get("qualitative_result")
            if data.get("qualitative_result") is not None
            else None,
            user_feedback_score=None if feedback is None else max(0, min(10, _int(feedback))),
            error_type=data.get("error_type") if data.get("error_type") is not None else None,
            notes=_tuple_of_strings(data.get("notes")),
        )


@dataclass(frozen=True)
class FailureMemory:
    failure_id: str
    pattern_id: str
    task_id: str
    error_type: str
    severity: str
    trigger_conditions: tuple[str, ...]
    missed_signals: tuple[str, ...]
    prevention_rules: tuple[str, ...]
    created_at: str

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["schema"] = FAILURE_MEMORY_SCHEMA
        for key in ["trigger_conditions", "missed_signals", "prevention_rules"]:
            data[key] = list(data[key])
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FailureMemory":
        return cls(
            failure_id=_string(data.get("failure_id"), "failure"),
            pattern_id=_string(data.get("pattern_id"), "pattern"),
            task_id=_string(data.get("task_id"), "task"),
            error_type=_string(data.get("error_type"), "unknown_failure"),
            severity=_string(data.get("severity"), "medium"),
            trigger_conditions=_tuple_of_strings(data.get("trigger_conditions")),
            missed_signals=_tuple_of_strings(data.get("missed_signals")),
            prevention_rules=_tuple_of_strings(data.get("prevention_rules")),
            created_at=_string(data.get("created_at")),
        )


@dataclass(frozen=True)
class UserDecisionModel:
    owner: str
    preferred_output_style: tuple[str, ...]
    risk_preference: str
    decision_biases: tuple[str, ...]
    recurring_priorities: tuple[str, ...]
    rejected_patterns: tuple[str, ...]
    favored_patterns: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["schema"] = USER_DECISION_MODEL_SCHEMA
        for key in [
            "preferred_output_style",
            "decision_biases",
            "recurring_priorities",
            "rejected_patterns",
            "favored_patterns",
        ]:
            data[key] = list(data[key])
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "UserDecisionModel":
        return cls(
            owner=_string(data.get("owner"), "Boss"),
            preferred_output_style=_tuple_of_strings(data.get("preferred_output_style")),
            risk_preference=_string(data.get("risk_preference"), "balanced"),
            decision_biases=_tuple_of_strings(data.get("decision_biases")),
            recurring_priorities=_tuple_of_strings(data.get("recurring_priorities")),
            rejected_patterns=_tuple_of_strings(data.get("rejected_patterns")),
            favored_patterns=_tuple_of_strings(data.get("favored_patterns")),
        )


@dataclass(frozen=True)
class CriticReport:
    report_id: str
    pattern_id: str
    objections: tuple[str, ...]
    hidden_assumptions: tuple[str, ...]
    risk_flags: tuple[str, ...]
    required_safeguards: tuple[str, ...]
    pass_gate: bool

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["schema"] = CRITIC_REPORT_SCHEMA
        for key in ["objections", "hidden_assumptions", "risk_flags", "required_safeguards"]:
            data[key] = list(data[key])
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CriticReport":
        return cls(
            report_id=_string(data.get("report_id"), "critic-report"),
            pattern_id=_string(data.get("pattern_id"), "pattern"),
            objections=_tuple_of_strings(data.get("objections")),
            hidden_assumptions=_tuple_of_strings(data.get("hidden_assumptions")),
            risk_flags=_tuple_of_strings(data.get("risk_flags")),
            required_safeguards=_tuple_of_strings(data.get("required_safeguards")),
            pass_gate=bool(data.get("pass_gate", False)),
        )


@dataclass(frozen=True)
class SkillNode:
    skill_id: str
    name: str
    domain: str
    mastery_score: float

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["schema"] = SKILL_NODE_SCHEMA
        data["mastery_score"] = round(max(0.0, min(1.0, float(data["mastery_score"]))), 4)
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SkillNode":
        return cls(
            skill_id=_string(data.get("skill_id") or data.get("id"), "skill"),
            name=_string(data.get("name"), "skill"),
            domain=_string(data.get("domain"), "general"),
            mastery_score=max(0.0, min(1.0, _float(data.get("mastery_score")))),
        )


@dataclass(frozen=True)
class SkillEdge:
    from_skill: str
    to_skill: str
    relation: str
    weight: float

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["schema"] = SKILL_EDGE_SCHEMA
        data["weight"] = round(max(0.0, min(1.0, float(data["weight"]))), 4)
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SkillEdge":
        return cls(
            from_skill=_string(data.get("from_skill"), "skill"),
            to_skill=_string(data.get("to_skill"), "skill"),
            relation=_string(data.get("relation"), "supports"),
            weight=max(0.0, min(1.0, _float(data.get("weight")))),
        )
