"""Kibo Reuse Router for local-first Paideia task planning."""

from .fingerprint import build_task_fingerprint
from .models import (
    KIBO_RECORD_SCHEMA,
    CRITIC_REPORT_SCHEMA,
    FAILURE_MEMORY_SCHEMA,
    PATTERN_CANDIDATE_SCHEMA,
    PATTERN_EXAM_RESULT_SCHEMA,
    REUSE_DECISION_SCHEMA,
    REUSE_PLAN_SCHEMA,
    REAL_WORLD_OUTCOME_SCHEMA,
    USER_DECISION_MODEL_SCHEMA,
    TASK_FINGERPRINT_SCHEMA,
    CriticReport,
    FailureMemory,
    KiboRecord,
    PatternCandidate,
    PatternExamResult,
    RealWorldOutcome,
    ReuseDecision,
    TaskFingerprint,
    UserDecisionModel,
)
from .pattern_layer import reinforce_pattern_candidate
from .router import build_kibo_reuse_plan, route_task

__all__ = [
    "CRITIC_REPORT_SCHEMA",
    "FAILURE_MEMORY_SCHEMA",
    "KIBO_RECORD_SCHEMA",
    "PATTERN_CANDIDATE_SCHEMA",
    "PATTERN_EXAM_RESULT_SCHEMA",
    "REUSE_DECISION_SCHEMA",
    "REUSE_PLAN_SCHEMA",
    "REAL_WORLD_OUTCOME_SCHEMA",
    "TASK_FINGERPRINT_SCHEMA",
    "USER_DECISION_MODEL_SCHEMA",
    "CriticReport",
    "FailureMemory",
    "KiboRecord",
    "PatternCandidate",
    "PatternExamResult",
    "RealWorldOutcome",
    "ReuseDecision",
    "TaskFingerprint",
    "UserDecisionModel",
    "build_kibo_reuse_plan",
    "build_task_fingerprint",
    "reinforce_pattern_candidate",
    "route_task",
]
