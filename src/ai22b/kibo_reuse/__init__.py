"""Kibo Reuse Router for local-first Paideia task planning."""

from .fingerprint import build_task_fingerprint
from .models import (
    KIBO_RECORD_SCHEMA,
    CRITIC_REPORT_SCHEMA,
    FAILURE_MEMORY_SCHEMA,
    ADAPTIVE_EXAM_SCHEMA,
    CURRICULUM_PLAN_SCHEMA,
    PATTERN_CANDIDATE_SCHEMA,
    PATTERN_EXAM_RESULT_SCHEMA,
    REUSE_DECISION_SCHEMA,
    REUSE_PLAN_SCHEMA,
    REAL_WORLD_OUTCOME_SCHEMA,
    USER_DECISION_MODEL_SCHEMA,
    TASK_FINGERPRINT_SCHEMA,
    WEAKNESS_RECORD_SCHEMA,
    AdaptiveExam,
    CurriculumPlan,
    CriticReport,
    FailureMemory,
    KiboRecord,
    PatternCandidate,
    PatternExamResult,
    RealWorldOutcome,
    ReuseDecision,
    TaskFingerprint,
    UserDecisionModel,
    WeaknessRecord,
)
from .curriculum_loop import (
    apply_curriculum_completion,
    detect_weaknesses,
    generate_adaptive_exam,
    generate_curriculum_plan,
)
from .action_pattern import compile_action_pattern, validate_action_pattern_graph
from .applicability import evaluate_kibo_applicability, filter_applicable_kibo_records
from .attribution import build_outcome_attribution_report, build_outcome_attribution_report_result
from .adversarial_critic import run_adversarial_critic
from .benchmark_runner import build_pattern_loop_benchmark_report
from .behavioral_exam import run_behavioral_exam
from .case_graph import build_case_graphs_from_paths, build_case_graphs_from_records, case_graph_from_kibo
from .outcome_evidence import build_action_receipt, build_outcome_evidence, build_outcome_ingest_report
from .pattern_layer import reinforce_pattern_candidate
from .pattern_revision import build_pattern_revision_proposal, build_pattern_revision_result
from .router import build_kibo_reuse_plan, route_task
from .scenario_pack import build_behavioral_scenario_pack
from .sqlite_index import build_sqlite_kibo_index, search_sqlite_kibo_index
from .token_telemetry import build_token_usage_receipt, build_token_usage_receipt_result, summarize_token_usage
from .validation_profile import build_pattern_validation_profile, build_validation_profile_report, runtime_gate_reuse_mode

__all__ = [
    "CRITIC_REPORT_SCHEMA",
    "ADAPTIVE_EXAM_SCHEMA",
    "CURRICULUM_PLAN_SCHEMA",
    "FAILURE_MEMORY_SCHEMA",
    "KIBO_RECORD_SCHEMA",
    "PATTERN_CANDIDATE_SCHEMA",
    "PATTERN_EXAM_RESULT_SCHEMA",
    "REUSE_DECISION_SCHEMA",
    "REUSE_PLAN_SCHEMA",
    "REAL_WORLD_OUTCOME_SCHEMA",
    "TASK_FINGERPRINT_SCHEMA",
    "USER_DECISION_MODEL_SCHEMA",
    "WEAKNESS_RECORD_SCHEMA",
    "AdaptiveExam",
    "CriticReport",
    "CurriculumPlan",
    "FailureMemory",
    "KiboRecord",
    "PatternCandidate",
    "PatternExamResult",
    "RealWorldOutcome",
    "ReuseDecision",
    "TaskFingerprint",
    "UserDecisionModel",
    "WeaknessRecord",
    "apply_curriculum_completion",
    "build_case_graphs_from_paths",
    "build_case_graphs_from_records",
    "build_kibo_reuse_plan",
    "build_action_receipt",
    "evaluate_kibo_applicability",
    "filter_applicable_kibo_records",
    "build_pattern_validation_profile",
    "build_validation_profile_report",
    "build_outcome_attribution_report",
    "build_outcome_attribution_report_result",
    "build_outcome_evidence",
    "build_outcome_ingest_report",
    "build_pattern_revision_proposal",
    "build_pattern_revision_result",
    "build_pattern_loop_benchmark_report",
    "build_sqlite_kibo_index",
    "build_task_fingerprint",
    "build_token_usage_receipt",
    "build_token_usage_receipt_result",
    "case_graph_from_kibo",
    "compile_action_pattern",
    "detect_weaknesses",
    "build_behavioral_scenario_pack",
    "generate_adaptive_exam",
    "generate_curriculum_plan",
    "reinforce_pattern_candidate",
    "route_task",
    "run_behavioral_exam",
    "runtime_gate_reuse_mode",
    "run_adversarial_critic",
    "search_sqlite_kibo_index",
    "summarize_token_usage",
    "validate_action_pattern_graph",
]
