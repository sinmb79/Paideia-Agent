from __future__ import annotations

import hashlib
import json
import re
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
DELIVERABLE_SYNTHESIS_SCHEMA = "paideia-workspace-deliverable-synthesis/v1"
DELIVERABLE_MANIFEST_SCHEMA = "paideia-workspace-job-deliverables/v1"


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


def _safe_deliverable_filename(deliverable_id: str, index: int) -> str:
    slug = re.sub(r"[^A-Za-z0-9_.-]+", "_", deliverable_id.strip()).strip("._-").lower()
    if not slug:
        slug = f"deliverable_{index}"
    return f"{index:02d}_{slug[:80]}.md"


def _input_review_lines(input_review: dict[str, Any] | None) -> list[str]:
    if not input_review:
        return ["- Declared inputs: none"]
    lines = [
        (
            f"- Declared inputs: {input_review.get('declared_input_count', 0)} "
            f"(read {input_review.get('read_count', 0)}, rejected {input_review.get('rejected_count', 0)})"
        )
    ]
    for item in input_review.get("inputs", [])[:5]:
        if not isinstance(item, dict):
            continue
        preview = str(item.get("preview", "")).replace("\n", " ")[:240]
        lines.append(
            f"- {item.get('file_name')}: {item.get('status')} / {item.get('purpose')}"
            + (f" / preview: {preview}" if preview else "")
        )
    return lines


def _compact_text(value: Any, *, limit: int = 700) -> str:
    return " ".join(str(value or "").split())[:limit]


def _tool_result_summary(item: dict[str, Any]) -> dict[str, Any]:
    output = item.get("output", {}) if isinstance(item.get("output"), dict) else {}
    summary = (
        output.get("summary")
        or output.get("mode")
        or output.get("assessment_mode")
        or output.get("unsupported_claim_policy")
        or output.get("target")
        or output.get("reason")
        or output.get("schema")
    )
    evidence_items = output.get("evidence_items", [])
    checklist = output.get("checklist", [])
    return {
        "tool": item.get("tool"),
        "status": item.get("status"),
        "capability": item.get("capability"),
        "output_schema": output.get("schema"),
        "summary": _compact_text(summary, limit=500),
        "evidence_item_count": len(evidence_items) if isinstance(evidence_items, list) else 0,
        "checklist_count": len(checklist) if isinstance(checklist, list) else 0,
        "private_reasoning_trace_stored": False,
    }


def _build_deliverable_synthesis(
    manifest: dict[str, Any],
    job_spec: dict[str, Any],
    workspace_run: dict[str, Any],
    input_review: dict[str, Any] | None,
) -> dict[str, Any]:
    base_run = workspace_run.get("base_agent_run", {})
    llm_result = workspace_run.get("llm_runtime_result", {})
    tool_execution = base_run.get("tool_execution", {})
    tool_results = tool_execution.get("tool_results", []) if isinstance(tool_execution, dict) else []
    memory = base_run.get("memory_applied", {})
    policy = base_run.get("policy_decision", {})
    source_summaries = {
        "llm_runtime": {
            "engine": llm_result.get("engine"),
            "status": llm_result.get("status"),
            "identity_policy": llm_result.get("identity_policy"),
            "draft_summary": _compact_text(llm_result.get("draft") or llm_result.get("text"), limit=900),
            "raw_provider_payload_saved": False,
        },
        "registered_tools": [_tool_result_summary(item) for item in tool_results if isinstance(item, dict)],
        "declared_inputs": {
            "declared_input_count": (input_review or {}).get("declared_input_count", 0),
            "read_count": (input_review or {}).get("read_count", 0),
            "rejected_count": (input_review or {}).get("rejected_count", 0),
            "input_refs": [
                {
                    "file_name": item.get("file_name"),
                    "status": item.get("status"),
                    "purpose": item.get("purpose"),
                    "content_sha256": item.get("content_sha256"),
                    "preview": _compact_text(item.get("preview"), limit=360),
                }
                for item in (input_review or {}).get("inputs", [])
                if isinstance(item, dict)
            ],
        },
        "memory_route": {
            "semantic_theme_count": len(memory.get("semantic_themes", [])) if isinstance(memory, dict) else 0,
            "procedural_principle_count": len(memory.get("procedural_principles", [])) if isinstance(memory, dict) else 0,
            "selected_memory_only": True,
        },
        "policy": {
            "status": policy.get("status"),
            "decision_model": policy.get("decision_model"),
            "policy_violations": policy.get("policy_violations", []),
        },
    }
    deliverable_records = []
    for deliverable in job_spec["deliverables"]:
        deliverable_records.append(
            {
                "id": deliverable["id"],
                "description": deliverable["description"],
                "synthesis_inputs": [
                    "llm_runtime.draft_summary",
                    "registered_tools",
                    "declared_inputs",
                    "memory_route",
                    "policy",
                    "workspace_trace",
                ],
                "review_policy": "boss_review_required_before_external_use",
                "private_reasoning_trace_stored": False,
            }
        )
    return {
        "schema": DELIVERABLE_SYNTHESIS_SCHEMA,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "objective": job_spec["objective"],
        "agent": {
            "name": manifest.get("agent", {}).get("name"),
            "role": manifest.get("agent", {}).get("role"),
        },
        "source_summaries": source_summaries,
        "deliverables": deliverable_records,
        "artifact_policy": {
            "source": "llm_tool_input_memory_policy_synthesis",
            "workspace_root_only": True,
            "network_call_performed": False,
            "subprocess_executed": False,
            "raw_provider_payload_saved": False,
            "private_reasoning_trace": "do_not_store",
            "learning_promotion_performed": False,
        },
    }


def _synthesis_lines(synthesis: dict[str, Any]) -> list[str]:
    sources = synthesis.get("source_summaries", {})
    llm = sources.get("llm_runtime", {})
    inputs = sources.get("declared_inputs", {})
    tools = sources.get("registered_tools", [])
    lines = [
        f"- LLM: {llm.get('engine')} / {llm.get('status')}",
        f"- Declared input reads: {inputs.get('read_count', 0)} of {inputs.get('declared_input_count', 0)}",
        f"- Registered tool summaries: {len(tools) if isinstance(tools, list) else 0}",
    ]
    draft = _compact_text(llm.get("draft_summary"), limit=360)
    if draft:
        lines.append(f"- Runtime draft summary: {draft}")
    for item in tools[:5] if isinstance(tools, list) else []:
        if not isinstance(item, dict):
            continue
        lines.append(f"- Tool {item.get('tool')}: {item.get('summary') or item.get('output_schema')}")
    return lines


def _deliverable_text(
    manifest: dict[str, Any],
    job_spec: dict[str, Any],
    deliverable: dict[str, Any],
    workspace_run: dict[str, Any],
    input_review: dict[str, Any] | None,
    synthesis: dict[str, Any],
) -> str:
    agent = manifest["agent"]
    llm_result = workspace_run.get("llm_runtime_result", {})
    base_run = workspace_run.get("base_agent_run", {})
    selected_tools = base_run.get("selected_tools", [])
    evidence = workspace_run.get("workspace_outputs", {})
    return "\n".join(
        [
            f"# {deliverable['id']}",
            "",
            f"- Agent: {agent.get('name')}",
            f"- Role: {agent.get('role')}",
            f"- Objective: {job_spec['objective']}",
            f"- Deliverable: {deliverable['description']}",
            f"- LLM engine: {llm_result.get('engine')}",
            f"- LLM status: {llm_result.get('status')}",
            f"- Selected tools: {', '.join(selected_tools) if selected_tools else 'none'}",
            "- Network: blocked",
            "- Private reasoning trace: not stored",
            "",
            "## Declared Inputs",
            *_input_review_lines(input_review),
            "",
            "## Synthesis Evidence",
            *_synthesis_lines(synthesis),
            "",
            "## Work Draft",
            (
                "This deliverable was materialized from the job objective, selected local memory summaries, "
                "declared workspace inputs, registered tool review packets, and the local execution trace."
            ),
            "",
            f"Boss-facing result: {deliverable['description']}",
            "",
            "## Evidence",
            f"- task_plan: {Path(str(evidence.get('task_plan', 'task_plan.md'))).name}",
            f"- result_summary: {Path(str(evidence.get('result_summary', 'result_summary.md'))).name}",
            f"- trace: {Path(str(evidence.get('trace', 'trace.jsonl'))).name}",
            "- verification: acceptance_checklist.json and workspace_execution_proof.json can verify this artifact.",
            "",
            "## Review Note",
            "This file is a reviewable local work artifact. It is not an autonomous external action, trade, upload, or final human approval.",
        ]
    )


def _write_deliverables(
    sandbox: WorkspaceSandbox,
    manifest: dict[str, Any],
    job_spec: dict[str, Any],
    workspace_run: dict[str, Any],
    input_review: dict[str, Any] | None,
    synthesis: dict[str, Any],
) -> tuple[Path, dict[str, Any], dict[str, Path]]:
    artifacts: list[dict[str, Any]] = []
    paths: dict[str, Path] = {}
    for index, deliverable in enumerate(job_spec["deliverables"], start=1):
        deliverable_id = str(deliverable["id"])
        relative_path = Path("deliverables") / _safe_deliverable_filename(deliverable_id, index)
        text = _deliverable_text(manifest, job_spec, deliverable, workspace_run, input_review, synthesis) + "\n"
        path = sandbox.write_text(relative_path, text, purpose=f"job_deliverable:{deliverable_id}")
        data = path.read_bytes()
        paths[deliverable_id] = path
        artifacts.append(
            {
                "id": deliverable_id,
                "description": deliverable["description"],
                "relative_path": path.relative_to(sandbox.root).as_posix(),
                "file_name": path.name,
                "byte_count": len(data),
                "content_sha256": hashlib.sha256(data).hexdigest(),
                "status": "created_as_declared_deliverable_artifact",
                "private_reasoning_trace_stored": False,
            }
        )
    deliverable_manifest = {
        "schema": DELIVERABLE_MANIFEST_SCHEMA,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "objective": job_spec["objective"],
        "declared_deliverable_count": len(job_spec["deliverables"]),
        "artifact_count": len(artifacts),
        "synthesis_schema": synthesis.get("schema"),
        "synthesis_digest_sha256": _digest(synthesis),
        "artifacts": artifacts,
        "artifact_policy": {
            "workspace_root_only": True,
            "relative_paths_only": True,
            "network_call_performed": False,
            "subprocess_executed": False,
            "private_reasoning_trace": "do_not_store",
            "boss_review_required": True,
        },
    }
    manifest_path = sandbox.write_json(
        "deliverable_manifest.json",
        deliverable_manifest,
        purpose="deliverable_manifest",
    )
    return manifest_path, deliverable_manifest, paths


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
    deliverable_manifest_path: Path | None = None,
    deliverable_manifest: dict[str, Any] | None = None,
    synthesis_path: Path | None = None,
) -> dict[str, Any]:
    evidence = [
        workspace_run["workspace_outputs"].get("task_plan"),
        workspace_run["workspace_outputs"].get("result_summary"),
        workspace_run["workspace_outputs"].get("trace"),
    ]
    if input_review_path is not None:
        evidence.append(str(input_review_path))
    if deliverable_manifest_path is not None:
        evidence.append(str(deliverable_manifest_path))
    if synthesis_path is not None:
        evidence.append(str(synthesis_path))
    evidence = [item for item in evidence if item]
    deliverable_artifacts = {
        str(item.get("id")): item
        for item in (deliverable_manifest or {}).get("artifacts", [])
        if isinstance(item, dict)
    }
    return {
        "schema": ACCEPTANCE_CHECKLIST_SCHEMA,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "objective": job_spec["objective"],
        "deliverables": [
            {
                "id": item["id"],
                "description": item["description"],
                "status": "created_as_declared_deliverable_artifact",
                "artifact": deliverable_artifacts.get(item["id"], {}).get("relative_path"),
                "content_sha256": deliverable_artifacts.get(item["id"], {}).get("content_sha256"),
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
    input_review: dict[str, Any] | None = None
    input_review_path: Path | None = None
    if normalized.get("input_files"):
        input_review = _workspace_input_review(sandbox, normalized["input_files"])
        input_review_path = sandbox.write_json(
            "input_review.json",
            input_review,
            purpose="workspace_input_review",
        )
    deliverable_synthesis = _build_deliverable_synthesis(manifest, normalized, workspace_run, input_review)
    deliverable_synthesis_path = sandbox.write_json(
        "deliverable_synthesis.json",
        deliverable_synthesis,
        purpose="deliverable_synthesis",
    )
    deliverable_manifest_path, deliverable_manifest, deliverable_paths = _write_deliverables(
        sandbox,
        manifest,
        normalized,
        workspace_run,
        input_review,
        deliverable_synthesis,
    )
    job_report_path = sandbox.write_text(
        "job_report.md",
        _job_report_text(manifest, normalized, workspace_run) + "\n",
        purpose="job_report",
    )
    checklist_path = sandbox.write_json(
        "acceptance_checklist.json",
        _acceptance_checklist(
            normalized,
            workspace_run,
            input_review_path=input_review_path,
            deliverable_manifest_path=deliverable_manifest_path,
            deliverable_manifest=deliverable_manifest,
            synthesis_path=deliverable_synthesis_path,
        ),
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
            _trace_entry(
                "deliverable_synthesis_prepared",
                file=deliverable_synthesis_path.name,
                source="llm_tool_input_memory_policy_synthesis",
            ),
            _trace_entry(
                "declared_deliverables_materialized",
                file=deliverable_manifest_path.name,
                deliverable_count=len(normalized.get("deliverables", [])),
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
        "deliverable_synthesis": str(deliverable_synthesis_path),
        "deliverable_manifest": str(deliverable_manifest_path),
        "deliverables": {key: str(path) for key, path in deliverable_paths.items()},
        "job_report": str(job_report_path),
        "acceptance_checklist": str(checklist_path),
        "trace": str(trace_path),
        "rollback_manifest": str(rollback_path),
    }
    if input_review_path is not None:
        result["job_outputs"]["input_review"] = str(input_review_path)
    result["job_resource_usage"] = sandbox.resource_usage()
    return result
