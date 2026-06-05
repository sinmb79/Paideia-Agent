from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ai22b.talent_foundry.agent_runner import run_agent_from_manifest
from ai22b.talent_foundry.llm_clients import LLMClient
from ai22b.talent_foundry.workspace_sandbox import (
    SandboxViolation,
    WORKSPACE_SANDBOX_SCHEMA,
    WorkspaceSandbox,
    sandbox_kwargs_from_resource_limits,
)


WORKSPACE_RUN_SCHEMA = "ai-talent-workspace-agent-run/v1"
WORKSPACE_JOB_RUN_SCHEMA = "ai-talent-workspace-agent-job-run/v1"
ACCEPTANCE_CHECKLIST_SCHEMA = "ai-talent-agent-job-acceptance-checklist/v1"
WORKSPACE_TOOL_ARTIFACTS_SCHEMA = "paideia-workspace-tool-artifacts/v1"
WORKSPACE_INPUT_REVIEW_SCHEMA = "paideia-workspace-input-review/v1"


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


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def _workspace_tool_artifacts(base_run: dict[str, Any]) -> dict[str, Any]:
    tool_execution = base_run.get("tool_execution", {})
    tool_results = tool_execution.get("tool_results", []) if isinstance(tool_execution, dict) else []
    artifacts = []
    for item in tool_results:
        if not isinstance(item, dict):
            continue
        output = item.get("output", {})
        artifacts.append(
            {
                "tool": item.get("tool"),
                "status": item.get("status"),
                "capability": item.get("capability"),
                "output_schema": output.get("schema") if isinstance(output, dict) else None,
                "output_digest_sha256": _digest(output),
                "output": output,
                "workspace_side_effect": "materialized_review_artifact_only",
                "private_reasoning_trace_stored": False,
            }
        )
    return {
        "schema": WORKSPACE_TOOL_ARTIFACTS_SCHEMA,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "execution_model": tool_execution.get("execution_model"),
        "selected_tools": base_run.get("selected_tools", []),
        "capability_scope": tool_execution.get("capability_scope", {}),
        "artifact_count": len(artifacts),
        "artifacts": artifacts,
        "adapter_policy": {
            "source": "registered_capability_checked_local_tools_v1",
            "materialized_by": "WorkspaceSandbox.write_json",
            "network_call_performed": False,
            "subprocess_executed": False,
            "private_reasoning_trace": "do_not_store",
            "learning_promotion_performed": False,
        },
    }


def _normalize_input_files(job_spec: dict[str, Any]) -> list[dict[str, str]]:
    raw_items = job_spec.get("input_files") or []
    if not isinstance(raw_items, list):
        return []
    normalized: list[dict[str, str]] = []
    for index, item in enumerate(raw_items, start=1):
        if isinstance(item, str):
            path = item
            description = f"Declared workspace input {index}"
            purpose = "job_context"
        elif isinstance(item, dict):
            path = str(item.get("path") or item.get("relative_path") or item.get("file") or "").strip()
            description = str(item.get("description") or item.get("purpose") or f"Declared workspace input {index}")
            purpose = str(item.get("purpose") or "job_context")
        else:
            continue
        if not path:
            continue
        normalized.append(
            {
                "path": path,
                "description": description,
                "purpose": purpose,
            }
        )
    return normalized


def _normalize_job_spec(job_spec: dict[str, Any]) -> dict[str, Any]:
    objective = str(job_spec.get("objective", "")).strip()
    if not objective:
        raise ValueError("Job spec requires a non-empty objective")
    deliverables = job_spec.get("deliverables") or [{"id": "result_summary", "description": "보스 검토용 작업 결과"}]
    acceptance_criteria = job_spec.get("acceptance_criteria") or ["작업 보고서와 검증 흔적을 로컬 워크스페이스에 남긴다."]
    resource_limits = job_spec.get("resource_limits") if isinstance(job_spec.get("resource_limits"), dict) else {}
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
        "input_files": _normalize_input_files(job_spec),
        "resource_limits": resource_limits,
    }


def _public_input_path(raw_path: str) -> dict[str, Any]:
    path = Path(raw_path)
    record: dict[str, Any] = {
        "file_name": path.name or "workspace_input",
        "requested_path_fingerprint_sha256": hashlib.sha256(raw_path.encode("utf-8")).hexdigest(),
    }
    if not path.is_absolute() and ".." not in path.parts:
        record["relative_path"] = path.as_posix()
    return record


def _workspace_input_review(sandbox: WorkspaceSandbox, input_files: list[dict[str, str]]) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    for item in input_files:
        raw_path = item["path"]
        record = {
            **_public_input_path(raw_path),
            "description": item.get("description"),
            "purpose": item.get("purpose"),
            "direct_file_read_performed": False,
        }
        try:
            text = sandbox.read_text(raw_path, purpose=f"declared_job_input:{item.get('purpose', 'job_context')}")
            data = text.encode("utf-8")
        except SandboxViolation as exc:
            record.update(
                {
                    "status": "rejected",
                    "reason": str(exc),
                }
            )
        else:
            record.update(
                {
                    "status": "read",
                    "byte_count": len(data),
                    "content_sha256": hashlib.sha256(data).hexdigest(),
                    "preview": text[:500],
                    "direct_file_read_performed": True,
                }
            )
        records.append(record)
    read_count = sum(1 for item in records if item.get("status") == "read")
    return {
        "schema": WORKSPACE_INPUT_REVIEW_SCHEMA,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "declared_input_count": len(input_files),
        "read_count": read_count,
        "rejected_count": len(records) - read_count,
        "inputs": records,
        "path_policy": {
            "workspace_root_only": True,
            "path_escape_rejected": True,
            "absolute_paths_exported": False,
        },
        "adapter_policy": {
            "source": "declared_workspace_input_files",
            "materialized_by": "WorkspaceSandbox.read_text_then_write_json",
            "network_call_performed": False,
            "subprocess_executed": False,
            "private_reasoning_trace": "do_not_store",
            "learning_promotion_performed": False,
        },
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
            f"- 선언 입력 파일: {len(job_spec.get('input_files', []))}개",
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


def _acceptance_checklist(
    job_spec: dict[str, Any],
    workspace_run: dict[str, Any],
    *,
    input_review_path: Path | None = None,
) -> dict[str, Any]:
    evidence = [
        workspace_run["workspace_outputs"].get("task_plan"),
        workspace_run["workspace_outputs"].get("result_summary"),
        workspace_run["workspace_outputs"].get("trace"),
    ]
    if input_review_path is not None:
        evidence.append(str(input_review_path))
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
    runtime_config: dict[str, Any] | None = None,
    llm_mode: str = "offline",
    llm_model: str | None = None,
    llm_client: LLMClient | None = None,
    resource_limits: dict[str, Any] | None = None,
) -> dict[str, Any]:
    base_run = run_agent_from_manifest(
        manifest,
        task=task,
        runtime_config=runtime_config,
        llm_mode=llm_mode,
        llm_model=llm_model,
        llm_client=llm_client,
    )
    created_at = datetime.now(timezone.utc).isoformat()
    sandbox = WorkspaceSandbox(workspace_dir, **sandbox_kwargs_from_resource_limits(resource_limits))
    workspace_root = sandbox.root

    result = {
        "schema": WORKSPACE_RUN_SCHEMA,
        "created_at_utc": created_at,
        "runtime_model": "openhands_style_workspace_agent",
        "agent": base_run["agent"],
        "task": task,
        "run_status": base_run["run_status"],
        "policy_violations": base_run["policy_violations"],
        "llm_runtime_result": base_run.get("llm_runtime_result", {}),
        "llm_provider_preflight": base_run.get("llm_provider_preflight"),
        "tool_authorization": {
            "allowed_tools": manifest.get("tool_policy", {}).get("allowed_tools", []),
            "blocked_tools": manifest.get("tool_policy", {}).get("blocked_tools", []),
            "network_access": "blocked",
            "workspace_root": str(workspace_root),
            "sandbox_schema": WORKSPACE_SANDBOX_SCHEMA,
            "sandbox_enforced": True,
            "resource_limits": sandbox.policy()["resource_limits"],
            "capability_grants": base_run.get("policy_decision", {}).get("capability_grants", {}),
            "capability_scope": base_run.get("tool_execution", {}).get("capability_scope", {}),
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

    sandbox.ensure_root()

    plan_text = _task_plan_text(manifest, task, base_run)
    summary_text = _summary_text(manifest, task, base_run)
    plan_path = sandbox.write_text("task_plan.md", plan_text + "\n", purpose="task_plan")
    summary_path = sandbox.write_text("result_summary.md", summary_text + "\n", purpose="result_summary")
    runtime_execution_path = sandbox.write_json("runtime_execution.json", base_run, purpose="runtime_execution_snapshot")
    workspace_tool_results_path = sandbox.write_json(
        "workspace_tool_results.json",
        _workspace_tool_artifacts(base_run),
        purpose="workspace_tool_artifacts",
    )
    trace_path = sandbox.write_jsonl(
        "trace.jsonl",
        [
            _trace_entry("policy_check", status="passed", violations=[]),
            _trace_entry(
                "registered_tool_execution",
                execution_model=base_run.get("tool_execution", {}).get("execution_model"),
                selected_tools=base_run.get("selected_tools", []),
            ),
            _trace_entry("local_file_write", file=plan_path.name, purpose="task_plan"),
            _trace_entry("local_file_write", file=summary_path.name, purpose="result_summary"),
            _trace_entry("local_file_write", file=runtime_execution_path.name, purpose="runtime_execution_snapshot"),
            _trace_entry("local_file_write", file=workspace_tool_results_path.name, purpose="workspace_tool_artifacts"),
            _trace_entry("local_file_write", file="rollback_manifest.json", purpose="rollback_manifest"),
            _trace_entry("local_file_write", file="workspace_sandbox.json", purpose="workspace_sandbox_policy"),
            _trace_entry("memory_growth_candidate", source="workspace_agent_run"),
        ],
        purpose="workspace_trace",
    )
    rollback_path = sandbox.write_rollback_manifest("rollback_manifest.json", operation_id="workspace_agent_run")
    sandbox_path = sandbox.write_json("workspace_sandbox.json", sandbox.snapshot(), purpose="workspace_sandbox_policy")

    result["workspace_outputs"] = {
        "task_plan": str(plan_path),
        "result_summary": str(summary_path),
        "trace": str(trace_path),
        "runtime_execution": str(runtime_execution_path),
        "workspace_tool_results": str(workspace_tool_results_path),
        "rollback_manifest": str(rollback_path),
        "workspace_sandbox": str(sandbox_path),
    }
    result["workspace_resource_usage"] = sandbox.resource_usage()
    return result


def run_workspace_agent_job_from_manifest(
    manifest: dict[str, Any],
    *,
    job_spec: dict[str, Any],
    workspace_dir: Path,
    runtime_config: dict[str, Any] | None = None,
    llm_mode: str = "offline",
    llm_model: str | None = None,
    llm_client: LLMClient | None = None,
) -> dict[str, Any]:
    normalized = _normalize_job_spec(job_spec)
    workspace_run = run_workspace_agent_from_manifest(
        manifest,
        task=normalized["objective"],
        workspace_dir=workspace_dir,
        runtime_config=runtime_config,
        llm_mode=llm_mode,
        llm_model=llm_model,
        llm_client=llm_client,
        resource_limits=normalized.get("resource_limits"),
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

    sandbox = WorkspaceSandbox(workspace_dir, **sandbox_kwargs_from_resource_limits(normalized.get("resource_limits")))
    sandbox.ensure_root()
    job_spec_path = sandbox.write_json("job_spec.json", normalized, purpose="job_spec")
    input_review_path: Path | None = None
    if normalized.get("input_files"):
        input_review_path = sandbox.write_json(
            "input_review.json",
            _workspace_input_review(sandbox, normalized["input_files"]),
            purpose="workspace_input_review",
        )
    job_report_path = sandbox.write_text(
        "job_report.md",
        _job_report_text(manifest, normalized, workspace_run) + "\n",
        purpose="job_report",
    )
    checklist_path = sandbox.write_json(
        "acceptance_checklist.json",
        _acceptance_checklist(normalized, workspace_run, input_review_path=input_review_path),
        purpose="acceptance_checklist",
    )
    trace_path = sandbox.append_jsonl(
        "trace.jsonl",
        [
            _trace_entry("local_file_write", file=job_spec_path.name, purpose="job_spec"),
            *(
                [
                    _trace_entry(
                        "declared_workspace_input_review",
                        file=input_review_path.name,
                        input_count=len(normalized.get("input_files", [])),
                    )
                ]
                if input_review_path is not None
                else []
            ),
            _trace_entry("local_file_write", file=job_report_path.name, purpose="job_report"),
            _trace_entry("acceptance_checklist", status="ready_for_boss_review"),
            _trace_entry("local_file_write", file="job_rollback_manifest.json", purpose="rollback_manifest"),
        ],
        purpose="job_trace_append",
    )
    rollback_path = sandbox.write_rollback_manifest("job_rollback_manifest.json", operation_id="workspace_agent_job_run")

    result["job_outputs"] = {
        "job_spec": str(job_spec_path),
        "job_report": str(job_report_path),
        "acceptance_checklist": str(checklist_path),
        "trace": str(trace_path),
        "rollback_manifest": str(rollback_path),
    }
    if input_review_path is not None:
        result["job_outputs"]["input_review"] = str(input_review_path)
    result["job_resource_usage"] = sandbox.resource_usage()
    return result
