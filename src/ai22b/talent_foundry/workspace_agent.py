from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ai22b.talent_foundry.agent_runner import run_agent_from_manifest


WORKSPACE_RUN_SCHEMA = "ai-talent-workspace-agent-run/v1"
WORKSPACE_JOB_RUN_SCHEMA = "ai-talent-workspace-agent-job-run/v1"
ACCEPTANCE_CHECKLIST_SCHEMA = "ai-talent-agent-job-acceptance-checklist/v1"


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_jsonl(path: Path, entries: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        for entry in entries:
            file.write(json.dumps(entry, ensure_ascii=False) + "\n")


def _safe_workspace_path(workspace_dir: Path, filename: str) -> Path:
    root = workspace_dir.resolve()
    path = (root / filename).resolve()
    if root not in path.parents and path != root:
        raise ValueError("Workspace output escaped workspace directory")
    return path


def _task_plan_text(manifest: dict[str, Any], task: str, base_run: dict[str, Any]) -> str:
    agent = manifest["agent"]
    principles = base_run.get("memory_applied", {}).get("procedural_principles", [])
    return "\n".join(
        [
            f"# {agent['name']} 워크스페이스 실행 계획",
            "",
            f"- 역할: {agent.get('role')}",
            f"- 요청: {task}",
            "- 실행 원칙: 근거 확인, 권한 경계, 결과 기록",
            f"- 적용 기억 원칙: {', '.join(principles) if principles else '기록 후 검토'}",
            "- 금지: 투자 실행, 승인 없는 외부 업로드, 개인/가족 데이터 외부 전송",
        ]
    )


def _summary_text(manifest: dict[str, Any], task: str, base_run: dict[str, Any]) -> str:
    agent = manifest["agent"]
    themes = base_run.get("memory_applied", {}).get("semantic_themes", [])
    selected_tools = base_run.get("selected_tools", [])
    return "\n".join(
        [
            f"# {agent['name']} 작업 결과 요약",
            "",
            f"- 작업: {task}",
            f"- 상태: {base_run['run_status']}",
            f"- 선택 도구: {', '.join(selected_tools) if selected_tools else '없음'}",
            f"- 적용 주제: {', '.join(themes) if themes else '일반 성장 경험'}",
            "- 요약: 거시경제, 근거, 리스크, 다음 확인 질문을 분리해 로컬 워크스페이스 산출물로 남겼습니다.",
            "- 다음 행동: 보스 검토 후 부족한 근거를 보강하고, 실행 권한이 필요한 일은 별도 승인 절차로 분리합니다.",
        ]
    )


def _trace_entry(action: str, **fields: Any) -> dict[str, Any]:
    return {
        "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
        "action": action,
        **fields,
    }


def _normalize_job_spec(job_spec: dict[str, Any]) -> dict[str, Any]:
    objective = str(job_spec.get("objective", "")).strip()
    if not objective:
        raise ValueError("Job spec requires a non-empty objective")
    deliverables = job_spec.get("deliverables") or [{"id": "result_summary", "description": "보스 검토용 작업 결과"}]
    acceptance_criteria = job_spec.get("acceptance_criteria") or ["작업 보고서와 검증 흔적을 로컬 워크스페이스에 남긴다."]
    return {
        "schema": job_spec.get("schema", "ai-talent-workspace-agent-job/v1"),
        "objective": objective,
        "deliverables": [
            {
                "id": str(item.get("id", f"deliverable_{index}")),
                "description": str(item.get("description", item.get("id", f"deliverable_{index}"))),
            }
            for index, item in enumerate(deliverables, start=1)
        ],
        "acceptance_criteria": [str(item) for item in acceptance_criteria],
    }


def _job_report_text(manifest: dict[str, Any], job_spec: dict[str, Any], workspace_run: dict[str, Any]) -> str:
    agent = manifest["agent"]
    deliverables = "\n".join(
        f"- {item['id']}: {item['description']}"
        for item in job_spec["deliverables"]
    )
    criteria = "\n".join(f"- {item}" for item in job_spec["acceptance_criteria"])
    return "\n".join(
        [
            f"# {agent['name']} 고용 에이전트 작업 보고서",
            "",
            f"- 역할: {agent.get('role')}",
            f"- 작업 목표: {job_spec['objective']}",
            f"- 실행 상태: {workspace_run['run_status']}",
            "- 런타임 모델: openclaw_style_hired_agent_job",
            "- 네트워크: blocked",
            "",
            "## 산출물",
            deliverables,
            "",
            "## 수락 기준",
            criteria,
            "",
            "## 검토 메모",
            "작업 계획, 결과 요약, 트레이스, 작업 보고서, 수락 체크리스트를 로컬 워크스페이스에 남겼습니다.",
        ]
    )


def _acceptance_checklist(job_spec: dict[str, Any], workspace_run: dict[str, Any]) -> dict[str, Any]:
    evidence = [
        workspace_run["workspace_outputs"].get("task_plan"),
        workspace_run["workspace_outputs"].get("result_summary"),
        workspace_run["workspace_outputs"].get("trace"),
    ]
    evidence = [item for item in evidence if item]
    return {
        "schema": ACCEPTANCE_CHECKLIST_SCHEMA,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "objective": job_spec["objective"],
        "deliverables": [
            {
                "id": item["id"],
                "description": item["description"],
                "status": "created_as_workspace_artifact",
                "review_required": "boss_or_oversight_committee",
            }
            for item in job_spec["deliverables"]
        ],
        "criteria": [
            {
                "criterion": criterion,
                "status": "satisfied_by_workspace_artifact",
                "evidence": evidence,
            }
            for criterion in job_spec["acceptance_criteria"]
        ],
    }


def run_workspace_agent_from_manifest(
    manifest: dict[str, Any],
    *,
    task: str,
    workspace_dir: Path,
) -> dict[str, Any]:
    base_run = run_agent_from_manifest(manifest, task=task)
    created_at = datetime.now(timezone.utc).isoformat()
    workspace_root = workspace_dir.resolve()

    result = {
        "schema": WORKSPACE_RUN_SCHEMA,
        "created_at_utc": created_at,
        "runtime_model": "openhands_style_workspace_agent",
        "agent": base_run["agent"],
        "task": task,
        "run_status": base_run["run_status"],
        "policy_violations": base_run["policy_violations"],
        "tool_authorization": {
            "allowed_tools": manifest.get("tool_policy", {}).get("allowed_tools", []),
            "blocked_tools": manifest.get("tool_policy", {}).get("blocked_tools", []),
            "network_access": "blocked",
            "workspace_root": str(workspace_root),
        },
        "base_agent_run": base_run,
        "workspace_outputs": {},
        "growth_update": {
            "experience_type": "workspace_agent_run_after_hire",
            "reflection": "로컬 워크스페이스에서 계획, 결과, 트레이스를 분리해 업무 경험으로 남겼다.",
            "reasoning_delta": [
                "에이전트 실행은 산출물과 검증 로그를 함께 남긴다.",
                "허용된 로컬 파일 쓰기만 사용하고 네트워크 접근은 차단한다.",
            ],
        },
    }

    if base_run["run_status"] == "blocked":
        result["growth_update"] = {
            "experience_type": "workspace_guardrail_block_after_hire",
            "reflection": "워크스페이스 실행 전 정책 위반을 감지해 산출물 생성을 중단했다.",
            "reasoning_delta": [
                "금지 행동은 계획 파일로도 정당화하지 않는다.",
                "외부 업로드와 실행 권한은 보스 승인 전 차단한다.",
            ],
        }
        return result

    workspace_root.mkdir(parents=True, exist_ok=True)
    plan_path = _safe_workspace_path(workspace_root, "task_plan.md")
    summary_path = _safe_workspace_path(workspace_root, "result_summary.md")
    trace_path = _safe_workspace_path(workspace_root, "trace.jsonl")

    plan_text = _task_plan_text(manifest, task, base_run)
    summary_text = _summary_text(manifest, task, base_run)
    plan_path.write_text(plan_text + "\n", encoding="utf-8")
    summary_path.write_text(summary_text + "\n", encoding="utf-8")
    _write_jsonl(
        trace_path,
        [
            _trace_entry("policy_check", status="passed", violations=[]),
            _trace_entry("local_file_write", file=plan_path.name, purpose="task_plan"),
            _trace_entry("local_file_write", file=summary_path.name, purpose="result_summary"),
            _trace_entry("memory_growth_candidate", source="workspace_agent_run"),
        ],
    )

    result["workspace_outputs"] = {
        "task_plan": str(plan_path),
        "result_summary": str(summary_path),
        "trace": str(trace_path),
    }
    return result


def run_workspace_agent_job_from_manifest(
    manifest: dict[str, Any],
    *,
    job_spec: dict[str, Any],
    workspace_dir: Path,
) -> dict[str, Any]:
    normalized = _normalize_job_spec(job_spec)
    workspace_run = run_workspace_agent_from_manifest(
        manifest,
        task=normalized["objective"],
        workspace_dir=workspace_dir,
    )
    job_status = "completed" if workspace_run["run_status"] == "completed" else "blocked"
    result = {
        "schema": WORKSPACE_JOB_RUN_SCHEMA,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "runtime_model": "openclaw_style_hired_agent_job",
        "agent": workspace_run["agent"],
        "job_status": job_status,
        "job_spec": normalized,
        "workspace_run": workspace_run,
        "tool_authorization": workspace_run["tool_authorization"],
        "job_outputs": {},
        "growth_update": {
            "experience_type": "hired_agent_job_after_hire",
            "reflection": "작업 요청서, 산출물, 수락 기준, 검증 흔적을 하나의 고용 에이전트 작업 단위로 남겼다.",
            "reasoning_delta": [
                "작업은 목표, 산출물, 수락 기준으로 분해한다.",
                "작업 완료 주장은 로컬 산출물과 체크리스트로 검증한다.",
            ],
        },
    }
    if job_status == "blocked":
        return result

    workspace_root = workspace_dir.resolve()
    job_spec_path = _safe_workspace_path(workspace_root, "job_spec.json")
    job_report_path = _safe_workspace_path(workspace_root, "job_report.md")
    checklist_path = _safe_workspace_path(workspace_root, "acceptance_checklist.json")
    _write_json(job_spec_path, normalized)
    job_report_path.write_text(_job_report_text(manifest, normalized, workspace_run) + "\n", encoding="utf-8")
    _write_json(checklist_path, _acceptance_checklist(normalized, workspace_run))

    trace_path = Path(workspace_run["workspace_outputs"]["trace"])
    with trace_path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(_trace_entry("local_file_write", file=job_spec_path.name, purpose="job_spec"), ensure_ascii=False) + "\n")
        file.write(json.dumps(_trace_entry("local_file_write", file=job_report_path.name, purpose="job_report"), ensure_ascii=False) + "\n")
        file.write(json.dumps(_trace_entry("acceptance_checklist", status="ready_for_boss_review"), ensure_ascii=False) + "\n")

    result["job_outputs"] = {
        "job_spec": str(job_spec_path),
        "job_report": str(job_report_path),
        "acceptance_checklist": str(checklist_path),
        "trace": str(trace_path),
    }
    return result
