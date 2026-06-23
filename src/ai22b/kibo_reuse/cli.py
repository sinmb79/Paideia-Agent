from __future__ import annotations

import argparse
import json
from pathlib import Path

from .curriculum_loop import (
    apply_curriculum_completion,
    build_adaptive_exam_report,
    build_curriculum_generation_report,
    build_curriculum_report,
    build_weakness_detection_report,
    load_adaptive_exams,
    load_curriculum_plans,
    load_weakness_records,
)
from .action_pattern import compile_action_pattern, validate_action_pattern_graph
from .adversarial_critic import run_adversarial_critic
from .attribution import build_outcome_attribution_report_result
from .behavioral_exam import run_behavioral_exam
from .case_graph import build_case_graphs_from_paths
from .models import CurriculumPlan, PatternCandidate, WeaknessRecord
from .outcome_evidence import build_action_receipt, build_outcome_ingest_report
from .pattern_revision import build_pattern_revision_result
from .pattern_layer import (
    build_critic_report,
    build_failure_search_result,
    build_pattern_exam_result,
    build_pattern_index_from_kibo,
    build_real_world_outcome,
    load_critic_reports,
    load_failure_memories,
    load_pattern_exam_results,
    load_patterns,
    load_real_world_outcomes,
    reinforce_pattern_candidate,
)
from .retriever import build_kibo_index, search_kibo
from .router import build_kibo_reuse_plan_from_file, fingerprint_from_task_payload
from .scenario_pack import DEFAULT_SCENARIO_KINDS, SUPPORTED_SCENARIO_KINDS, build_behavioral_scenario_pack
from .token_meter import build_token_saving_report
from .validation_profile import build_validation_profile_report, runtime_gate_reuse_mode


KIBO_REUSE_COMMANDS = {
    "kibo-index",
    "kibo-search",
    "kibo-plan",
    "kibo-run",
    "kibo-report",
    "pattern-extract",
    "pattern-exam",
    "pattern-outcome",
    "pattern-reinforce",
    "failure-search",
    "critic-report",
    "weakness-detect",
    "curriculum-generate",
    "curriculum-report",
    "adaptive-exam",
    "case-graph-build",
    "action-pattern-compile",
    "scenario-pack-build",
    "pattern-behavioral-exam",
    "validation-profile-build",
    "runtime-gate",
    "action-receipt-build",
    "outcome-ingest",
    "outcome-attribute",
    "pattern-revision-propose",
    "adversarial-critic",
    "curriculum-complete",
}


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _paths(values: list[str] | None) -> list[Path] | None:
    if not values:
        return None
    return [Path(value) for value in values]


def _existing_paths(values: list[str] | None) -> list[Path] | None:
    paths = [Path(value) for value in values or [] if Path(value).exists()]
    return paths or None


def _append_jsonl(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def _load_manifest(path: str) -> dict:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("compatibility manifest must be a JSON object")
    return payload


def _load_case_graph_rows(paths: list[str]) -> list[dict]:
    rows: list[dict] = []
    for raw_path in paths:
        path = Path(raw_path)
        if path.suffix.lower() == ".jsonl":
            rows.extend(json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip())
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, dict) and payload.get("schema") == "paideia-kibo-v2-case-graph/v2":
            rows.append(payload)
        elif isinstance(payload, dict) and isinstance(payload.get("case_graphs"), list):
            rows.extend(payload["case_graphs"])
        elif isinstance(payload, list):
            rows.extend(payload)
        else:
            raise ValueError(f"Unsupported case graph payload: {path}")
    if not all(isinstance(row, dict) for row in rows):
        raise ValueError("case graph inputs must contain JSON objects")
    return rows


def _load_action_pattern_v2(path: Path, pattern_id: str | None = None) -> dict:
    if path.suffix.lower() == ".jsonl":
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    else:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, dict) and payload.get("schema") == "paideia-action-pattern-compile-result/v1":
            rows = [payload["action_pattern"]]
        elif isinstance(payload, dict) and payload.get("schema") == "paideia-kibo-v2-action-pattern/v2":
            rows = [payload]
        elif isinstance(payload, list):
            rows = payload
        else:
            raise ValueError(f"Unsupported action pattern payload: {path}")
    for row in rows:
        if isinstance(row, dict) and row.get("schema") == "paideia-kibo-v2-action-pattern/v2":
            if pattern_id is None or row.get("pattern_id") == pattern_id:
                return row
    raise ValueError(f"ActionPattern not found: {pattern_id or path}")


def _load_json_object(path: str | None) -> dict | None:
    if not path:
        return None
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return payload


def _load_json_objects(paths: list[str] | None) -> list[dict]:
    rows: list[dict] = []
    for raw_path in paths or []:
        path = Path(raw_path)
        if path.suffix.lower() == ".jsonl":
            rows.extend(json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip())
        else:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(payload, dict) and isinstance(payload.get("outcomes"), list):
                rows.extend(payload["outcomes"])
            elif isinstance(payload, dict) and isinstance(payload.get("action_receipts"), list):
                rows.extend(payload["action_receipts"])
            elif isinstance(payload, dict) and isinstance(payload.get("outcome_evidence"), dict):
                rows.append(payload["outcome_evidence"])
            elif isinstance(payload, dict) and isinstance(payload.get("action_receipt"), dict):
                rows.append(payload["action_receipt"])
            elif isinstance(payload, dict) and isinstance(payload.get("attribution_report"), dict):
                rows.append(payload["attribution_report"])
            elif isinstance(payload, dict) and isinstance(payload.get("attribution_reports"), list):
                rows.extend(payload["attribution_reports"])
            elif isinstance(payload, dict) and isinstance(payload.get("pattern_revision"), dict):
                rows.append(payload["pattern_revision"])
            elif isinstance(payload, dict):
                rows.append(payload)
            elif isinstance(payload, list):
                rows.extend(payload)
            else:
                raise ValueError(f"Expected JSON object/list: {path}")
    if not all(isinstance(row, dict) for row in rows):
        raise ValueError("Expected JSON object rows")
    return rows


def _bool_arg(value: str) -> bool:
    lowered = value.casefold()
    if lowered in {"1", "true", "yes", "y"}:
        return True
    if lowered in {"0", "false", "no", "n"}:
        return False
    raise argparse.ArgumentTypeError("expected true or false")


def _discover_kibo_paths(kibo_dir: Path) -> list[Path]:
    if kibo_dir.is_file():
        return [kibo_dir]
    return sorted(
        path
        for path in kibo_dir.rglob("*")
        if path.is_file() and path.suffix.lower() in {".jsonl", ".json"} and "kibo" in path.name.casefold()
    )


def _load_pattern_or_raise(pattern_id: str, pattern_path: Path) -> PatternCandidate:
    for pattern in load_patterns([pattern_path]):
        if pattern.pattern_id == pattern_id:
            return pattern
    raise ValueError(f"Pattern not found: {pattern_id}")


def _select_weakness(weaknesses: list[WeaknessRecord], weakness_id: str | None) -> WeaknessRecord:
    if weakness_id is None:
        if not weaknesses:
            raise ValueError("No weakness records available")
        return weaknesses[0]
    for weakness in weaknesses:
        if weakness.weakness_id == weakness_id:
            return weakness
    raise ValueError(f"Weakness not found: {weakness_id}")


def _select_curriculum(curricula: list[CurriculumPlan], curriculum_id: str | None) -> CurriculumPlan:
    if curriculum_id is None:
        if not curricula:
            raise ValueError("No curriculum plans available")
        return curricula[0]
    for curriculum in curricula:
        if curriculum.curriculum_id == curriculum_id:
            return curriculum
    raise ValueError(f"Curriculum not found: {curriculum_id}")


def _target_score_from_curricula(
    curricula: list[CurriculumPlan],
    *,
    weakness_id: str,
    curriculum_id: str | None,
) -> float | None:
    for curriculum in curricula:
        if curriculum_id and curriculum.curriculum_id != curriculum_id:
            continue
        if curriculum.weakness_id == weakness_id:
            return curriculum.target_score
    return None


def register_kibo_reuse_commands(subparsers: argparse._SubParsersAction) -> None:
    kibo_index = subparsers.add_parser(
        "kibo-index",
        help="Index local reviewable kibo JSONL files without using an external database.",
    )
    kibo_index.add_argument("--repo-root", default=".")
    kibo_index.add_argument("--output")

    kibo_search = subparsers.add_parser(
        "kibo-search",
        help="Search reviewed local kibo records for a task JSON file.",
    )
    kibo_search.add_argument("--task", required=True)
    kibo_search.add_argument("--repo-root", default=".")
    kibo_search.add_argument("--kibo-path", action="append")
    kibo_search.add_argument("--sqlite-index")
    kibo_search.add_argument("--failure-path", action="append")
    kibo_search.add_argument("--limit", type=int, default=5)
    kibo_search.add_argument("--output")

    kibo_plan = subparsers.add_parser(
        "kibo-plan",
        help="Build a kibo reuse plan and isolate the parts that still need an LLM.",
    )
    kibo_plan.add_argument("--task", required=True)
    kibo_plan.add_argument("--repo-root", default=".")
    kibo_plan.add_argument("--kibo-path", action="append")
    kibo_plan.add_argument("--sqlite-index")
    kibo_plan.add_argument("--pattern-path", action="append")
    kibo_plan.add_argument("--failure-path", action="append")
    kibo_plan.add_argument("--weakness-path", action="append")
    kibo_plan.add_argument("--user-model")
    kibo_plan.add_argument("--critic-path", action="append")
    kibo_plan.add_argument("--skill-graph")
    kibo_plan.add_argument("--limit", type=int, default=5)
    kibo_plan.add_argument("--output")

    kibo_run = subparsers.add_parser(
        "kibo-run",
        help="Run the deterministic reuse router. MVP output is a reviewable local execution plan.",
    )
    kibo_run.add_argument("--task", required=True)
    kibo_run.add_argument("--repo-root", default=".")
    kibo_run.add_argument("--kibo-path", action="append")
    kibo_run.add_argument("--sqlite-index")
    kibo_run.add_argument("--pattern-path", action="append")
    kibo_run.add_argument("--failure-path", action="append")
    kibo_run.add_argument("--weakness-path", action="append")
    kibo_run.add_argument("--user-model")
    kibo_run.add_argument("--critic-path", action="append")
    kibo_run.add_argument("--skill-graph")
    kibo_run.add_argument("--limit", type=int, default=5)
    kibo_run.add_argument("--output", required=True)

    kibo_report = subparsers.add_parser(
        "kibo-report",
        help="Build a token-saving report from a kibo-run or kibo-plan JSON file.",
    )
    kibo_report.add_argument("--run", required=True)
    kibo_report.add_argument("--output")

    pattern_extract = subparsers.add_parser(
        "pattern-extract",
        help="Extract local pattern candidates from reviewed Kibo records.",
    )
    pattern_extract.add_argument("--kibo-dir", required=True)
    pattern_extract.add_argument("--output", required=True)

    pattern_exam = subparsers.add_parser(
        "pattern-exam",
        help="Run a deterministic synthetic exam for a local pattern candidate.",
    )
    pattern_exam.add_argument("--pattern-id", required=True)
    pattern_exam.add_argument("--pattern-path", default="data/patterns.jsonl")
    pattern_exam.add_argument("--task-id")
    pattern_exam.add_argument("--output", required=True)

    pattern_outcome = subparsers.add_parser(
        "pattern-outcome",
        help="Record a real-world outcome for a pattern candidate.",
    )
    pattern_outcome.add_argument("--pattern-id", required=True)
    pattern_outcome.add_argument("--task-id", required=True)
    pattern_outcome.add_argument("--success", required=True, type=_bool_arg)
    pattern_outcome.add_argument("--score", type=float)
    pattern_outcome.add_argument("--outcome-type", default="task_outcome")
    pattern_outcome.add_argument("--user-feedback-score", type=int)
    pattern_outcome.add_argument("--error-type")
    pattern_outcome.add_argument("--note", action="append")
    pattern_outcome.add_argument("--output", default="data/pattern_outcomes.jsonl")

    pattern_reinforce = subparsers.add_parser(
        "pattern-reinforce",
        help="Recompute reinforcement status for a pattern from exams, outcomes, and critic reports.",
    )
    pattern_reinforce.add_argument("--pattern-id", required=True)
    pattern_reinforce.add_argument("--pattern-path", default="data/patterns.jsonl")
    pattern_reinforce.add_argument("--exam-path", action="append", default=["data/pattern_exam_results.jsonl"])
    pattern_reinforce.add_argument("--outcome-path", action="append", default=["data/pattern_outcomes.jsonl"])
    pattern_reinforce.add_argument("--critic-path", action="append")
    pattern_reinforce.add_argument("--output", default="runs/pattern_reinforcement.json")

    failure_search = subparsers.add_parser(
        "failure-search",
        help="Search local failure memory for risks relevant to a task JSON file.",
    )
    failure_search.add_argument("--task", required=True)
    failure_search.add_argument("--failure-path", action="append", default=["data/failure_memory.jsonl"])
    failure_search.add_argument("--output")

    critic_report = subparsers.add_parser(
        "critic-report",
        help="Generate a deterministic self-critic report for a pattern candidate.",
    )
    critic_report.add_argument("--pattern-id", required=True)
    critic_report.add_argument("--pattern-path", default="data/patterns.jsonl")
    critic_report.add_argument("--output", required=True)

    weakness_detect = subparsers.add_parser(
        "weakness-detect",
        help="Convert reviewed failure memory into WeaknessRecords for curriculum remediation.",
    )
    weakness_detect.add_argument("--failure-path", action="append", default=["data/failure_memory.jsonl"])
    weakness_detect.add_argument("--existing-weakness-path", action="append")
    weakness_detect.add_argument("--owner", default="Boss")
    weakness_detect.add_argument("--domain", default="general")
    weakness_detect.add_argument("--output", default="runs/weakness_detection.json")

    curriculum_generate = subparsers.add_parser(
        "curriculum-generate",
        help="Generate CurriculumPlans from WeaknessRecords.",
    )
    curriculum_generate.add_argument("--weakness-path", action="append", default=["runs/weakness_detection.json"])
    curriculum_generate.add_argument("--skill-graph")
    curriculum_generate.add_argument("--output", default="runs/curricula.jsonl")

    curriculum_report = subparsers.add_parser(
        "curriculum-report",
        help="Summarize weakness, curriculum, and adaptive exam remediation state.",
    )
    curriculum_report.add_argument("--weakness-path", action="append", default=["runs/weakness_detection.json"])
    curriculum_report.add_argument("--curriculum-path", action="append", default=["runs/curricula.jsonl"])
    curriculum_report.add_argument("--exam-path", action="append")
    curriculum_report.add_argument("--output", default="runs/curriculum_report.json")

    adaptive_exam = subparsers.add_parser(
        "adaptive-exam",
        help="Generate an AdaptiveExam from a CurriculumPlan.",
    )
    adaptive_exam.add_argument("--curriculum-id")
    adaptive_exam.add_argument("--curriculum-path", action="append", default=["runs/curricula.jsonl"])
    adaptive_exam.add_argument("--weakness-path", action="append", default=["runs/weakness_detection.json"])
    adaptive_exam.add_argument("--recent-improvement", action="store_true")
    adaptive_exam.add_argument("--output", default="runs/adaptive_exam.json")

    case_graph_build = subparsers.add_parser(
        "case-graph-build",
        help="Build canonical v2 CaseGraph artifacts from reviewed Kibo records.",
    )
    case_graph_build.add_argument("--kibo-path", action="append", required=True)
    case_graph_build.add_argument("--compatibility-manifest", required=True)
    case_graph_build.add_argument("--output", required=True)

    action_pattern_compile = subparsers.add_parser(
        "action-pattern-compile",
        help="Compile v2 ActionPattern draft artifacts from CaseGraph JSON/JSONL input.",
    )
    action_pattern_compile.add_argument("--case-graph-path", action="append", required=True)
    action_pattern_compile.add_argument("--compatibility-manifest", required=True)
    action_pattern_compile.add_argument("--output", required=True)
    action_pattern_compile.add_argument("--validation-output")

    scenario_pack_build = subparsers.add_parser(
        "scenario-pack-build",
        help="Build deterministic holdout scenario packs for a v2 ActionPattern.",
    )
    scenario_pack_build.add_argument("--pattern-path", required=True)
    scenario_pack_build.add_argument("--pattern-id")
    scenario_pack_build.add_argument("--scenario-kind", action="append", choices=sorted(SUPPORTED_SCENARIO_KINDS))
    scenario_pack_build.add_argument("--source-partition", default="holdout")
    scenario_pack_build.add_argument("--include-leakage", action="store_true")
    scenario_pack_build.add_argument("--output", required=True)

    pattern_behavioral_exam = subparsers.add_parser(
        "pattern-behavioral-exam",
        help="Run a deterministic behavioral exam for a v2 ActionPattern against a scenario pack.",
    )
    pattern_behavioral_exam.add_argument("--pattern-path", required=True)
    pattern_behavioral_exam.add_argument("--pattern-id")
    pattern_behavioral_exam.add_argument("--scenario-pack", required=True)
    pattern_behavioral_exam.add_argument("--compatibility-manifest", required=True)
    pattern_behavioral_exam.add_argument("--high-risk", action="store_true")
    pattern_behavioral_exam.add_argument("--output", required=True)

    validation_profile_build = subparsers.add_parser(
        "validation-profile-build",
        help="Build a v2 PatternValidationProfile from structural, behavioral, critic, and field evidence.",
    )
    validation_profile_build.add_argument("--pattern-path", required=True)
    validation_profile_build.add_argument("--pattern-id")
    validation_profile_build.add_argument("--compatibility-manifest", required=True)
    validation_profile_build.add_argument("--structural-exam")
    validation_profile_build.add_argument("--behavioral-exam")
    validation_profile_build.add_argument("--critic-report")
    validation_profile_build.add_argument("--field-evidence", action="append")
    validation_profile_build.add_argument("--evidence-fresh-until")
    validation_profile_build.add_argument("--shadow-validation-passed", action="store_true")
    validation_profile_build.add_argument("--high-risk", action="store_true")
    validation_profile_build.add_argument("--output", required=True)

    runtime_gate = subparsers.add_parser(
        "runtime-gate",
        help="Apply the v2 validation profile runtime reuse ceiling.",
    )
    runtime_gate.add_argument("--validation-profile", required=True)
    runtime_gate.add_argument("--compatibility-manifest", required=True)
    runtime_gate.add_argument("--requested-mode", required=True)
    runtime_gate.add_argument("--risk-level", default="normal")
    runtime_gate.add_argument("--output", required=True)

    action_receipt_build = subparsers.add_parser(
        "action-receipt-build",
        help="Build a reviewable ActionReceipt for a v2 ActionPattern step.",
    )
    action_receipt_build.add_argument("--pattern-path", required=True)
    action_receipt_build.add_argument("--pattern-id")
    action_receipt_build.add_argument("--run-id", required=True)
    action_receipt_build.add_argument("--action-node-id", required=True)
    action_receipt_build.add_argument("--capability", required=True)
    action_receipt_build.add_argument("--started-at", required=True)
    action_receipt_build.add_argument("--completed-at")
    action_receipt_build.add_argument("--result-status", required=True)
    action_receipt_build.add_argument("--requested-inputs-hash")
    action_receipt_build.add_argument("--requested-inputs")
    action_receipt_build.add_argument("--observed-effect", action="append")
    action_receipt_build.add_argument("--error-code")
    action_receipt_build.add_argument("--retry-count", type=int, default=0)
    action_receipt_build.add_argument("--resource-usage")
    action_receipt_build.add_argument("--artifact-hash", action="append")
    action_receipt_build.add_argument("--output", required=True)

    outcome_ingest = subparsers.add_parser(
        "outcome-ingest",
        help="Build v2 OutcomeEvidence from ActionReceipts and a verifier report.",
    )
    outcome_ingest.add_argument("--pattern-path", required=True)
    outcome_ingest.add_argument("--pattern-id")
    outcome_ingest.add_argument("--compatibility-manifest", required=True)
    outcome_ingest.add_argument("--task-id", required=True)
    outcome_ingest.add_argument("--action-receipt", action="append")
    outcome_ingest.add_argument("--verifier-report")
    outcome_ingest.add_argument("--run-id")
    outcome_ingest.add_argument("--environment-fingerprint")
    outcome_ingest.add_argument("--task-difficulty", type=float, default=0.5)
    outcome_ingest.add_argument("--started-at")
    outcome_ingest.add_argument("--observed-at")
    outcome_ingest.add_argument("--baseline-ref")
    outcome_ingest.add_argument("--output", required=True)

    outcome_attribute = subparsers.add_parser(
        "outcome-attribute",
        help="Build v2 OutcomeAttributionReport step credits from OutcomeEvidence and ActionReceipts.",
    )
    outcome_attribute.add_argument("--pattern-path", required=True)
    outcome_attribute.add_argument("--pattern-id")
    outcome_attribute.add_argument("--compatibility-manifest", required=True)
    outcome_attribute.add_argument("--outcome-path", required=True)
    outcome_attribute.add_argument("--action-receipt", action="append")
    outcome_attribute.add_argument("--comparison-baseline")
    outcome_attribute.add_argument("--output", required=True)

    pattern_revision_propose = subparsers.add_parser(
        "pattern-revision-propose",
        help="Build a quarantined v2 PatternRevisionProposal from attribution reports.",
    )
    pattern_revision_propose.add_argument("--pattern-path", required=True)
    pattern_revision_propose.add_argument("--pattern-id")
    pattern_revision_propose.add_argument("--compatibility-manifest", required=True)
    pattern_revision_propose.add_argument("--attribution-path", action="append", required=True)
    pattern_revision_propose.add_argument("--proposed-pattern-version")
    pattern_revision_propose.add_argument("--output", required=True)

    adversarial_critic = subparsers.add_parser(
        "adversarial-critic",
        help="Run executable adversarial critic scenarios for a v2 ActionPattern.",
    )
    adversarial_critic.add_argument("--pattern-path", required=True)
    adversarial_critic.add_argument("--pattern-id")
    adversarial_critic.add_argument("--compatibility-manifest", required=True)
    adversarial_critic.add_argument("--high-risk", action="store_true")
    adversarial_critic.add_argument("--output", required=True)

    curriculum_complete = subparsers.add_parser(
        "curriculum-complete",
        help="Apply adaptive exam completion evidence to a WeaknessRecord.",
    )
    curriculum_complete.add_argument("--weakness-id")
    curriculum_complete.add_argument("--weakness-path", action="append", default=["runs/weakness_detection.json"])
    curriculum_complete.add_argument("--curriculum-id")
    curriculum_complete.add_argument("--curriculum-path", action="append")
    curriculum_complete.add_argument("--passed", required=True, type=_bool_arg)
    curriculum_complete.add_argument("--score", required=True, type=float)
    curriculum_complete.add_argument("--target-score", type=float)
    curriculum_complete.add_argument("--evidence-ref", action="append")
    curriculum_complete.add_argument("--transfer-passed", action="store_true")
    curriculum_complete.add_argument("--retention-passed", action="store_true")
    curriculum_complete.add_argument("--output", default="runs/curriculum_completion.json")
    curriculum_complete.add_argument("--updated-weakness-output")


def handle_kibo_reuse_command(args: argparse.Namespace) -> int | None:
    if args.command not in KIBO_REUSE_COMMANDS:
        return None

    if args.command == "kibo-index":
        output_path = Path(args.output) if args.output else None
        index = build_kibo_index(Path(args.repo_root), output_path=output_path)
        if output_path:
            print(str(output_path))
        else:
            print(json.dumps(index, ensure_ascii=False, indent=2))
        return 0

    if args.command == "kibo-search":
        task_payload = json.loads(Path(args.task).read_text(encoding="utf-8"))
        fingerprint = fingerprint_from_task_payload(task_payload)
        scores = search_kibo(
            fingerprint,
            repo_root=Path(args.repo_root),
            kibo_paths=_paths(args.kibo_path),
            sqlite_index_path=Path(args.sqlite_index) if args.sqlite_index else None,
            failure_memories=load_failure_memories(_paths(args.failure_path)),
            limit=args.limit,
        )
        result = {
            "schema": "paideia-kibo-search-result/v1",
            "task_fingerprint": fingerprint.to_dict(),
            "matches": [score.to_dict() for score in scores],
            "policy": {
                "quarantined_records_excluded": True,
                "unreviewed_records_excluded": True,
            },
        }
        if args.output:
            _write_json(Path(args.output), result)
            print(str(Path(args.output)))
        else:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    if args.command in {"kibo-plan", "kibo-run"}:
        output_path = Path(args.output) if args.output else None
        plan = build_kibo_reuse_plan_from_file(
            Path(args.task),
            repo_root=Path(args.repo_root),
            kibo_paths=_paths(args.kibo_path),
            sqlite_index_path=Path(args.sqlite_index) if args.sqlite_index else None,
            pattern_paths=_paths(args.pattern_path),
            failure_paths=_paths(args.failure_path),
            weakness_paths=_paths(args.weakness_path),
            user_model_path=Path(args.user_model) if args.user_model else None,
            critic_paths=_paths(args.critic_path),
            skill_graph_path=Path(args.skill_graph) if args.skill_graph else None,
            limit=args.limit,
            output_path=output_path,
        )
        if args.command == "kibo-run":
            plan["run_status"] = "planned_not_executed"
            plan["llm_call_policy"] = "call_only_llm_required_parts_after_owner_or_runtime_validation"
            _write_json(Path(args.output), plan)
            print(str(Path(args.output)))
        elif output_path:
            print(str(output_path))
        else:
            print(json.dumps(plan, ensure_ascii=False, indent=2))
        return 0

    if args.command == "kibo-report":
        run = json.loads(Path(args.run).read_text(encoding="utf-8"))
        report = build_token_saving_report(
            task=run.get("task_fingerprint") or run.get("task") or {},
            reused_steps=list(run.get("reused_steps", [])),
            llm_called_parts=list(run.get("llm_called_parts") or run.get("llm_required_parts", [])),
        )
        if args.output:
            _write_json(Path(args.output), report)
            print(str(Path(args.output)))
        else:
            print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0

    if args.command == "pattern-extract":
        paths = _discover_kibo_paths(Path(args.kibo_dir))
        result = build_pattern_index_from_kibo(kibo_paths=paths, output_path=Path(args.output))
        print(str(Path(args.output)))
        return 0

    if args.command == "pattern-exam":
        pattern = _load_pattern_or_raise(args.pattern_id, Path(args.pattern_path))
        result = build_pattern_exam_result(pattern, task_id=args.task_id).to_dict()
        _write_json(Path(args.output), result)
        print(str(Path(args.output)))
        return 0

    if args.command == "pattern-outcome":
        outcome = build_real_world_outcome(
            pattern_id=args.pattern_id,
            task_id=args.task_id,
            success=args.success,
            score=args.score,
            outcome_type=args.outcome_type,
            user_feedback_score=args.user_feedback_score,
            error_type=args.error_type,
            notes=args.note or (),
        )
        _append_jsonl(Path(args.output), outcome.to_dict())
        print(str(Path(args.output)))
        return 0

    if args.command == "pattern-reinforce":
        pattern = _load_pattern_or_raise(args.pattern_id, Path(args.pattern_path))
        report = reinforce_pattern_candidate(
            pattern,
            exam_results=load_pattern_exam_results([Path(path) for path in args.exam_path or []]),
            outcomes=load_real_world_outcomes([Path(path) for path in args.outcome_path or []]),
            critic_reports=load_critic_reports(_paths(args.critic_path)),
        )
        _write_json(Path(args.output), report)
        print(str(Path(args.output)))
        return 0

    if args.command == "failure-search":
        task_payload = json.loads(Path(args.task).read_text(encoding="utf-8"))
        fingerprint = fingerprint_from_task_payload(task_payload)
        result = build_failure_search_result(fingerprint, load_failure_memories(_paths(args.failure_path)))
        if args.output:
            _write_json(Path(args.output), result)
            print(str(Path(args.output)))
        else:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    if args.command == "critic-report":
        pattern = _load_pattern_or_raise(args.pattern_id, Path(args.pattern_path))
        result = build_critic_report(pattern).to_dict()
        _write_json(Path(args.output), result)
        print(str(Path(args.output)))
        return 0

    if args.command == "weakness-detect":
        failures = load_failure_memories(_existing_paths(args.failure_path))
        existing = load_weakness_records(_existing_paths(args.existing_weakness_path))
        report = build_weakness_detection_report(
            failures,
            owner=args.owner,
            domain=args.domain,
            existing_weaknesses=existing,
        )
        output_path = Path(args.output)
        if output_path.suffix.lower() == ".jsonl":
            _write_jsonl(output_path, report["weaknesses"])
        else:
            _write_json(output_path, report)
        print(str(output_path))
        return 0

    if args.command == "curriculum-generate":
        weaknesses = load_weakness_records(_existing_paths(args.weakness_path))
        report = build_curriculum_generation_report(
            weaknesses,
            skill_graph_path=Path(args.skill_graph) if args.skill_graph else None,
        )
        output_path = Path(args.output)
        if output_path.suffix.lower() == ".jsonl":
            _write_jsonl(output_path, report["curricula"])
        else:
            _write_json(output_path, report)
        print(str(output_path))
        return 0

    if args.command == "curriculum-report":
        report = build_curriculum_report(
            weaknesses=load_weakness_records(_existing_paths(args.weakness_path)),
            curricula=load_curriculum_plans(_existing_paths(args.curriculum_path)),
            exams=load_adaptive_exams(_existing_paths(args.exam_path)),
        )
        _write_json(Path(args.output), report)
        print(str(Path(args.output)))
        return 0

    if args.command == "adaptive-exam":
        curricula = load_curriculum_plans(_existing_paths(args.curriculum_path))
        curriculum = _select_curriculum(curricula, args.curriculum_id)
        weaknesses = load_weakness_records(_existing_paths(args.weakness_path))
        related_weakness = next(
            (weakness for weakness in weaknesses if weakness.weakness_id == curriculum.weakness_id),
            None,
        )
        report = build_adaptive_exam_report(
            curriculum,
            weakness=related_weakness,
            recent_improvement=args.recent_improvement,
        )
        _write_json(Path(args.output), report)
        print(str(Path(args.output)))
        return 0

    if args.command == "case-graph-build":
        manifest = _load_manifest(args.compatibility_manifest)
        case_graphs = build_case_graphs_from_paths(
            [Path(path) for path in args.kibo_path],
            manifest,
        )
        output_path = Path(args.output)
        if output_path.suffix.lower() == ".jsonl":
            _write_jsonl(output_path, case_graphs)
        else:
            _write_json(output_path, {"schema": "paideia-case-graph-build-result/v1", "case_graphs": case_graphs})
        print(str(output_path))
        return 0

    if args.command == "action-pattern-compile":
        manifest = _load_manifest(args.compatibility_manifest)
        case_graphs = _load_case_graph_rows(args.case_graph_path)
        output_path = Path(args.output)
        try:
            action_pattern = compile_action_pattern(case_graphs, manifest)
            validation = validate_action_pattern_graph(action_pattern)
        except ValueError as exc:
            failure = {
                "schema": "paideia-action-pattern-compile-result/v1",
                "status": "blocked",
                "error": str(exc),
                "validation": {
                    "schema": "paideia-action-pattern-graph-validation/v1",
                    "passed": False,
                    "issues": [{"code": "compile_blocked", "message": str(exc)}],
                    "warnings": [],
                },
            }
            _write_json(output_path, failure)
            if args.validation_output:
                _write_json(Path(args.validation_output), failure["validation"])
            print(str(output_path))
            return 2
        if not validation["passed"]:
            failure = {
                "schema": "paideia-action-pattern-compile-result/v1",
                "status": "blocked",
                "action_pattern": action_pattern,
                "validation": validation,
            }
            _write_json(output_path, failure)
            if args.validation_output:
                _write_json(Path(args.validation_output), validation)
            print(str(output_path))
            return 2
        if output_path.suffix.lower() == ".jsonl":
            _write_jsonl(output_path, [action_pattern])
        else:
            _write_json(
                output_path,
                {
                    "schema": "paideia-action-pattern-compile-result/v1",
                    "status": "compiled",
                    "action_pattern": action_pattern,
                    "validation": validation,
                },
            )
        if args.validation_output:
            _write_json(Path(args.validation_output), validation)
        print(str(output_path))
        return 0

    if args.command == "scenario-pack-build":
        action_pattern = _load_action_pattern_v2(Path(args.pattern_path), args.pattern_id)
        scenario_pack = build_behavioral_scenario_pack(
            action_pattern,
            scenario_kinds=args.scenario_kind or DEFAULT_SCENARIO_KINDS,
            source_partition=args.source_partition,
            include_leakage=args.include_leakage,
        )
        _write_json(Path(args.output), scenario_pack)
        print(str(Path(args.output)))
        return 0

    if args.command == "pattern-behavioral-exam":
        manifest = _load_manifest(args.compatibility_manifest)
        action_pattern = _load_action_pattern_v2(Path(args.pattern_path), args.pattern_id)
        scenario_pack = json.loads(Path(args.scenario_pack).read_text(encoding="utf-8"))
        result = run_behavioral_exam(action_pattern, scenario_pack, manifest, high_risk=args.high_risk)
        _write_json(Path(args.output), result)
        print(str(Path(args.output)))
        return 0 if result["passed"] else 2

    if args.command == "validation-profile-build":
        manifest = _load_manifest(args.compatibility_manifest)
        action_pattern = _load_action_pattern_v2(Path(args.pattern_path), args.pattern_id)
        report = build_validation_profile_report(
            action_pattern,
            manifest,
            structural_exam=_load_json_object(args.structural_exam),
            behavioral_exam=_load_json_object(args.behavioral_exam),
            critic_report=_load_json_object(args.critic_report),
            field_evidence=_load_json_objects(args.field_evidence),
            evidence_fresh_until=args.evidence_fresh_until,
            shadow_validation_passed=args.shadow_validation_passed,
            high_risk=args.high_risk,
        )
        _write_json(Path(args.output), report)
        print(str(Path(args.output)))
        return 0

    if args.command == "runtime-gate":
        manifest = _load_manifest(args.compatibility_manifest)
        profile_payload = _load_json_object(args.validation_profile)
        profile = profile_payload.get("validation_profile") if profile_payload and profile_payload.get("schema") == "paideia-validation-profile-build-result/v1" else profile_payload
        if not isinstance(profile, dict):
            raise ValueError("validation profile file must contain a profile object")
        report = runtime_gate_reuse_mode(args.requested_mode, profile, manifest, risk_level=args.risk_level)
        _write_json(Path(args.output), report)
        print(str(Path(args.output)))
        return 0 if report["allowed_mode"] == args.requested_mode else 2

    if args.command == "action-receipt-build":
        action_pattern = _load_action_pattern_v2(Path(args.pattern_path), args.pattern_id)
        requested_inputs = _load_json_object(args.requested_inputs) if args.requested_inputs else None
        resource_usage = _load_json_object(args.resource_usage) if args.resource_usage else None
        observed_effects = [
            json.loads(effect) if effect.strip().startswith("{") else {"effect": effect}
            for effect in args.observed_effect or []
        ]
        receipt = build_action_receipt(
            run_id=args.run_id,
            pattern_id=action_pattern["pattern_id"],
            pattern_version=action_pattern["pattern_version"],
            action_node_id=args.action_node_id,
            capability=args.capability,
            started_at=args.started_at,
            completed_at=args.completed_at,
            result_status=args.result_status,
            requested_inputs=requested_inputs,
            requested_inputs_hash=args.requested_inputs_hash,
            observed_effects=observed_effects,
            error_code=args.error_code,
            retry_count=args.retry_count,
            resource_usage=resource_usage,
            artifact_hashes=args.artifact_hash or (),
        )
        _write_json(Path(args.output), {"schema": "paideia-action-receipt-build-result/v1", "action_receipt": receipt})
        print(str(Path(args.output)))
        return 0

    if args.command == "outcome-ingest":
        manifest = _load_manifest(args.compatibility_manifest)
        action_pattern = _load_action_pattern_v2(Path(args.pattern_path), args.pattern_id)
        report = build_outcome_ingest_report(
            action_pattern,
            manifest,
            task_id=args.task_id,
            action_receipts=_load_json_objects(args.action_receipt),
            verifier_report=_load_json_object(args.verifier_report),
            run_id=args.run_id,
            environment_fingerprint=args.environment_fingerprint,
            task_difficulty=args.task_difficulty,
            started_at=args.started_at,
            observed_at=args.observed_at,
            baseline_ref=args.baseline_ref,
        )
        _write_json(Path(args.output), report)
        print(str(Path(args.output)))
        return 0 if report["status"] == "verified" else 2

    if args.command == "outcome-attribute":
        manifest = _load_manifest(args.compatibility_manifest)
        action_pattern = _load_action_pattern_v2(Path(args.pattern_path), args.pattern_id)
        outcome_rows = _load_json_objects([args.outcome_path])
        if len(outcome_rows) != 1:
            raise ValueError("outcome-attribute requires exactly one outcome evidence artifact")
        report = build_outcome_attribution_report_result(
            action_pattern,
            outcome_rows[0],
            manifest,
            action_receipts=_load_json_objects(args.action_receipt),
            comparison_baseline=args.comparison_baseline,
        )
        _write_json(Path(args.output), report)
        print(str(Path(args.output)))
        return 0

    if args.command == "pattern-revision-propose":
        manifest = _load_manifest(args.compatibility_manifest)
        action_pattern = _load_action_pattern_v2(Path(args.pattern_path), args.pattern_id)
        report = build_pattern_revision_result(
            action_pattern,
            _load_json_objects(args.attribution_path),
            manifest,
            proposed_pattern_version=args.proposed_pattern_version,
        )
        _write_json(Path(args.output), report)
        print(str(Path(args.output)))
        return 0 if report["status"] != "accepted" else 2

    if args.command == "adversarial-critic":
        manifest = _load_manifest(args.compatibility_manifest)
        action_pattern = _load_action_pattern_v2(Path(args.pattern_path), args.pattern_id)
        report = run_adversarial_critic(action_pattern, manifest, high_risk=args.high_risk)
        _write_json(Path(args.output), report)
        print(str(Path(args.output)))
        return 0 if report["pass_gate"] else 2

    if args.command == "curriculum-complete":
        weakness = _select_weakness(
            load_weakness_records(_existing_paths(args.weakness_path)),
            args.weakness_id,
        )
        target_score = args.target_score
        if target_score is None and args.curriculum_path:
            target_score = _target_score_from_curricula(
                load_curriculum_plans(_existing_paths(args.curriculum_path)),
                weakness_id=weakness.weakness_id,
                curriculum_id=args.curriculum_id,
            )
        report = apply_curriculum_completion(
            weakness,
            passed=args.passed,
            score=args.score,
            target_score=target_score,
            evidence_refs=args.evidence_ref or (),
            transfer_passed=args.transfer_passed,
            retention_passed=args.retention_passed,
        )
        _write_json(Path(args.output), report)
        if args.updated_weakness_output:
            updated_path = Path(args.updated_weakness_output)
            updated_weakness = report["updated_weakness"]
            if updated_path.suffix.lower() == ".jsonl":
                _write_jsonl(updated_path, [updated_weakness])
            else:
                _write_json(updated_path, updated_weakness)
        print(str(Path(args.output)))
        return 0

    return None
