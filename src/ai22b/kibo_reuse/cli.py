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
from .models import CurriculumPlan, PatternCandidate, WeaknessRecord
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
from .token_meter import build_token_saving_report


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
    kibo_search.add_argument("--limit", type=int, default=5)
    kibo_search.add_argument("--output")

    kibo_plan = subparsers.add_parser(
        "kibo-plan",
        help="Build a kibo reuse plan and isolate the parts that still need an LLM.",
    )
    kibo_plan.add_argument("--task", required=True)
    kibo_plan.add_argument("--repo-root", default=".")
    kibo_plan.add_argument("--kibo-path", action="append")
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

    curriculum_complete = subparsers.add_parser(
        "curriculum-complete",
        help="Apply adaptive exam completion evidence to a WeaknessRecord.",
    )
    curriculum_complete.add_argument("--weakness-id")
    curriculum_complete.add_argument("--weakness-path", action="append", default=["runs/weakness_detection.json"])
    curriculum_complete.add_argument("--passed", required=True, type=_bool_arg)
    curriculum_complete.add_argument("--score", required=True, type=float)
    curriculum_complete.add_argument("--output", default="runs/curriculum_completion.json")


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

    if args.command == "curriculum-complete":
        weakness = _select_weakness(
            load_weakness_records(_existing_paths(args.weakness_path)),
            args.weakness_id,
        )
        report = apply_curriculum_completion(
            weakness,
            passed=args.passed,
            score=args.score,
        )
        _write_json(Path(args.output), report)
        print(str(Path(args.output)))
        return 0

    return None
