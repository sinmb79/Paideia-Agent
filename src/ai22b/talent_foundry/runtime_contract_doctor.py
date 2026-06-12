from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ai22b.config import PROJECT_ROOT
from ai22b.talent_foundry.agent_runner import run_agent_from_manifest
from ai22b.talent_foundry.closed_ecosystem import build_closed_growth_contract, validate_closed_growth_contract
from ai22b.talent_foundry.learning_loop import build_reasoning_kernel, create_learning_ledger
from ai22b.talent_foundry.llm_runtime import build_llm_runtime_config


RUNTIME_CONTRACT_DOCTOR_SCHEMA = "paideia-runtime-contract-doctor/v1"
LIVE_AGENT_LOOP_CONTRACT_SCHEMA = "paideia-live-agent-loop-contract/v1"
FAIL_CLOSED_RUNTIME_CONTRACT_SCHEMA = "paideia-fail-closed-runtime-contract/v1"
MEMORY_REVIEW_CANDIDATE_SCHEMA = "paideia-memory-review-candidate/v1"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _check(
    checks: list[dict[str, Any]],
    check_id: str,
    passed: bool,
    *,
    severity: str = "error",
    details: dict[str, Any] | None = None,
) -> None:
    checks.append(
        {
            "id": check_id,
            "status": "passed" if passed else "failed",
            "passed": passed,
            "severity": severity,
            "details": details or {},
        }
    )


def run_live_agent_loop_contract() -> dict[str, Any]:
    """Exercise the explicit-live LLM client path through the full agent loop without network access."""

    secret = "fixture_runtime_contract_live_llm_secret_12345"
    hidden_trace = "runtime contract hidden provider trace must not be stored"

    class PublicSafeLiveContractClient:
        def generate(self, messages, *, tools=None, policy=None):
            return {
                "schema": "paideia-llm-client-result/v1",
                "engine": "runtime_contract_fake_live_llm",
                "status": "completed",
                "model": "runtime-contract-fake-live-model",
                "raw_output_saved": False,
                "text": json.dumps(
                    {
                        "assistant_reply": "Public-safe live LLM contract draft.",
                        "reviewable_reasoning_summary": [
                            {
                                "step": "policy",
                                "summary": "Policy was checked before live planning.",
                            },
                            {
                                "step": "evidence",
                                "summary": "The registered executor creates reviewable evidence.",
                            },
                        ],
                        "suggested_next_actions": [
                            "Review the evidence packet.",
                            "Promote only after Boss review.",
                        ],
                        "tool_plan": [
                            {
                                "tool": "evidence_packet",
                                "purpose": "Record reviewable evidence for this live run.",
                            },
                            {
                                "tool": "external_upload",
                                "purpose": "Out-of-scope suggestion that must not execute.",
                            },
                        ],
                        "chain_of_thought": hidden_trace,
                    },
                    ensure_ascii=False,
                ),
                "debug_headers": {"Authorization": f"Bearer {secret}"},
                "chain_of_thought": hidden_trace,
                "metadata": {"private_reasoning_trace": hidden_trace},
            }

    manifest = {
        "schema": "ai-talent-agent-manifest/v1",
        "agent": {
            "name": "public-safe-live-contract-agent",
            "role": "local runtime contract doctor fixture",
            "major_goal": "Verify live LLM execution stays bounded by Paideia policy.",
        },
        "memory_profile": {
            "procedural_principles": [
                "Check policy before LLM planning.",
                "Use registered tools as the only execution authority.",
            ],
            "semantic_themes": ["live LLM contract", "public-safe runtime doctor"],
            "chain_of_thought_policy": "do_not_store_private_trace",
        },
        "llm_policy": {
            "role": "application_engine_not_identity",
            "private_reasoning_trace": "do_not_store",
        },
        "tool_policy": {
            "allowed_tools": ["work_session", "evidence_packet", "assessment", "memory_consolidation"],
            "blocked_tools": [],
        },
    }
    runtime_config = build_llm_runtime_config(
        engine="openrouter_api",
        model="paideia-runtime-contract-live-model",
    )
    run = run_agent_from_manifest(
        manifest,
        task="Prepare a public-safe runtime contract evidence plan.",
        runtime_config=runtime_config,
        llm_mode="live",
        llm_client=PublicSafeLiveContractClient(),
    )
    llm_result = run.get("llm_runtime_result", {}) if isinstance(run.get("llm_runtime_result"), dict) else {}
    client_result = llm_result.get("client_result", {}) if isinstance(llm_result.get("client_result"), dict) else {}
    llm_plan = llm_result.get("llm_plan", {}) if isinstance(llm_result.get("llm_plan"), dict) else {}
    execution_contract = run.get("execution_contract", {}) if isinstance(run.get("execution_contract"), dict) else {}
    tool_execution = run.get("tool_execution", {}) if isinstance(run.get("tool_execution"), dict) else {}
    tool_scope = (
        tool_execution.get("capability_scope", {})
        if isinstance(tool_execution.get("capability_scope"), dict)
        else {}
    )
    alignment = run.get("llm_tool_plan_alignment", {}) if isinstance(run.get("llm_tool_plan_alignment"), dict) else {}
    memory_write = run.get("memory_write", {}) if isinstance(run.get("memory_write"), dict) else {}
    review_candidate = (
        memory_write.get("review_candidate", {})
        if isinstance(memory_write.get("review_candidate"), dict)
        else {}
    )
    completed_tools = [
        str(item.get("tool"))
        for item in tool_execution.get("tool_results", [])
        if isinstance(item, dict) and item.get("status") == "completed"
    ]
    serialized = json.dumps(run, ensure_ascii=False)
    details = {
        "schema": LIVE_AGENT_LOOP_CONTRACT_SCHEMA,
        "run_status": run.get("run_status"),
        "verification_status": run.get("verification", {}).get("status")
        if isinstance(run.get("verification"), dict)
        else None,
        "execution_contract_status": execution_contract.get("status"),
        "llm_mode": llm_result.get("llm_mode"),
        "llm_status": llm_result.get("status"),
        "llm_engine": llm_result.get("engine"),
        "llm_applied_as": llm_result.get("applied_as"),
        "llm_plan_schema": llm_plan.get("schema"),
        "llm_plan_source": llm_plan.get("source"),
        "client_result_text_omitted": client_result.get("text_omitted"),
        "client_result_raw_output_saved": client_result.get("raw_output_saved"),
        "client_result_private_reasoning_fields_omitted": client_result.get(
            "private_reasoning_fields_omitted",
            0,
        ),
        "client_result_private_reasoning_values_stored": client_result.get(
            "private_reasoning_field_values_stored"
        ),
        "data_policy_store_raw_client_result_text": llm_result.get("data_policy", {}).get(
            "store_raw_client_result_text"
        )
        if isinstance(llm_result.get("data_policy"), dict)
        else None,
        "provider_preflight_live_check_performed": llm_result.get("llm_provider_preflight", {}).get(
            "live_check_performed"
        )
        if isinstance(llm_result.get("llm_provider_preflight"), dict)
        else None,
        "provider_preflight_network_call_made": llm_result.get("llm_provider_preflight", {}).get(
            "network_call_made_by_preflight"
        )
        if isinstance(llm_result.get("llm_provider_preflight"), dict)
        else None,
        "tool_execution_model": tool_execution.get("execution_model"),
        "completed_tools": completed_tools,
        "network_default": tool_scope.get("network_default"),
        "subprocess_default": tool_scope.get("subprocess_default"),
        "llm_tool_suggestion_only_enforced": alignment.get("suggestion_only_enforced"),
        "out_of_scope_executed_count": alignment.get("out_of_scope_executed_count"),
        "memory_decision": memory_write.get("decision"),
        "memory_review_candidate_schema": review_candidate.get("schema"),
        "memory_auto_promotion_performed": memory_write.get("automatic_promotion_performed"),
        "secret_or_hidden_trace_absent": secret not in serialized and hidden_trace not in serialized,
    }
    passed = (
        details["run_status"] == "completed"
        and details["verification_status"] == "passed"
        and details["execution_contract_status"] == "passed"
        and details["llm_mode"] == "live"
        and details["llm_status"] == "completed"
        and details["llm_applied_as"] == "live_language_and_tool_reasoning_engine"
        and details["llm_plan_schema"] == "paideia-llm-reviewable-plan/v1"
        and details["llm_plan_source"] == "json_object"
        and details["client_result_text_omitted"] is True
        and details["client_result_raw_output_saved"] is False
        and details["client_result_private_reasoning_fields_omitted"] >= 2
        and details["client_result_private_reasoning_values_stored"] is False
        and details["data_policy_store_raw_client_result_text"] is False
        and details["provider_preflight_live_check_performed"] is False
        and details["provider_preflight_network_call_made"] is False
        and details["tool_execution_model"] == "registered_capability_checked_local_tools_v1"
        and "evidence_packet" in completed_tools
        and details["network_default"] == "blocked"
        and details["subprocess_default"] == "blocked"
        and details["llm_tool_suggestion_only_enforced"] is True
        and details["out_of_scope_executed_count"] == 0
        and details["memory_decision"] == "candidate_pending_boss_review"
        and details["memory_review_candidate_schema"] == MEMORY_REVIEW_CANDIDATE_SCHEMA
        and details["memory_auto_promotion_performed"] is False
        and details["secret_or_hidden_trace_absent"] is True
    )
    return {
        "schema": LIVE_AGENT_LOOP_CONTRACT_SCHEMA,
        "status": "passed" if passed else "failed",
        "passed": passed,
        "details": details,
        "public_safe": {
            "network_call_performed": False,
            "subprocess_executed": False,
            "live_provider_called": False,
            "fake_live_client_used": True,
            "secret_values_exported": False,
            "raw_provider_payload_saved": False,
            "private_reasoning_trace": "do_not_store",
        },
    }


def _write_fail_closed_runtime_fixture(root: Path) -> tuple[Path, dict[str, Any], dict[str, Any]]:
    agent = {
        "name": "paideia-runtime-contract-fail-closed-agent",
        "role": "public-safe runtime contract doctor fixture",
        "major_goal": "Prove live provider configuration is required before execution.",
        "birth": {
            "datetime": "doctor-fixture",
            "place": "local-public-safe-fixture",
        },
    }
    agent_manifest = {
        "schema": "ai-talent-agent-manifest/v1",
        "agent": agent,
        "identity_source": {
            "role_model_inspiration": {
                "role_model_id": "graham_value_investing",
                "boundary": "learning_path_only_not_impersonation",
            }
        },
        "memory_profile": {
            "procedural_principles": [
                "Check provider readiness before LLM planning.",
                "Do not create workspace artifacts when live provider configuration is missing.",
                "Do not promote chat learning when the live provider path was skipped.",
            ],
            "semantic_themes": ["fail closed", "provider readiness", "runtime safety"],
            "chain_of_thought_policy": "do_not_store_private_trace",
        },
        "llm_policy": {
            "role": "application_engine_not_identity",
            "private_reasoning_trace": "do_not_store",
        },
        "tool_policy": {
            "allowed_tools": ["work_session", "evidence_packet", "assessment", "memory_consolidation"],
            "blocked_tools": ["external_upload", "financial_action", "personal_data_transfer"],
        },
    }
    ledger = create_learning_ledger(owner=agent["name"])
    ledger["reasoning_kernel"] = build_reasoning_kernel(ledger)
    runtime_config = build_llm_runtime_config(
        engine="openrouter_api",
        model="openrouter/runtime-contract-provider-missing-model",
        service="openrouter_api",
    )
    employment_record = {
        "schema": "ai-talent-local-employment/v1",
        "employment_id": "runtime-contract-fail-closed-employment",
        "hired_at_utc": _now(),
        "employer": "Boss",
        "relationship": "installed_ai_talent_hired_as_local_agent",
        "install_id": "runtime-contract-fail-closed-install",
        "agent": {
            "name": agent["name"],
            "role": "provider readiness contract agent",
            "major_goal": agent["major_goal"],
        },
        "source": {
            "installed_manifest": "doctor_fixture",
            "agent_manifest": "agent_manifest.json",
            "source_archive": "doctor_fixture",
            "source_sha256": "doctor_fixture",
        },
        "entrypoints": {
            "agent_manifest": "agent_manifest.json",
            "learning_ledger": "learning_ledger.json",
            "memory_substrate": "memory_substrate.json",
            "chat_log": "employment_chat_log.jsonl",
            "last_chat": "last_hired_agent_chat.json",
            "workspace_run_log": "employment_workspace_run_log.jsonl",
            "last_workspace_run": "last_hired_workspace_agent_run.json",
            "job_run_log": "employment_job_run_log.jsonl",
            "last_job_run": "last_hired_agent_job_run.json",
            "dataflow_run_log": "employment_dataflow_run_log.jsonl",
            "last_dataflow_run": "last_hired_dataflow_run.json",
        },
        "guardrails": agent_manifest["tool_policy"]["blocked_tools"],
        "llm_service": {
            "service_id": "openrouter_api",
            "engine": "openrouter_api",
            "selected_model": "openrouter/runtime-contract-provider-missing-model",
            "status": "requires_configuration",
        },
        "chat_surface": {
            "id": "cli-console",
            "label": "Paideia guided CLI console",
        },
        "llm_runtime": runtime_config,
        "growth_after_hire": {
            "continues": True,
            "principle": "Post-hire execution must pass provider readiness, policy, verification, and review gates.",
            "record_policy": "Unconfigured provider paths are not recorded as completed work or promoted learning.",
        },
        "llm_policy": agent_manifest["llm_policy"],
        "status": "active",
    }
    _write_json(root / "agent_manifest.json", agent_manifest)
    _write_json(root / "learning_ledger.json", ledger)
    employment_record_path = root / "employment_record.openrouter_missing.json"
    _write_json(employment_record_path, employment_record)
    return employment_record_path, agent_manifest, ledger


def run_fail_closed_runtime_contract() -> dict[str, Any]:
    """Prove unconfigured explicit-live runs stop before tools, artifacts, and learning promotion."""

    from ai22b.talent_foundry.memory_substrate import run_chat_turn_from_employment
    from ai22b.talent_foundry.registry import (
        run_hired_agent_job,
        run_hired_dataflow_job,
        run_hired_workspace_agent,
    )

    model = "openrouter/runtime-contract-provider-missing-model"
    old_key = os.environ.pop("OPENROUTER_API_KEY", None)
    try:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_root = Path(tmp)
            fixture_root = tmp_root / "agent"
            employment_record_path, agent_manifest, ledger_before = _write_fail_closed_runtime_fixture(fixture_root)
            runtime_config = build_llm_runtime_config(
                engine="openrouter_api",
                model=model,
                service="openrouter_api",
            )
            agent_run = run_agent_from_manifest(
                agent_manifest,
                task="Prepare a public-safe evidence note through an unconfigured live provider.",
                runtime_config=runtime_config,
                llm_mode="live",
                llm_model=model,
            )
            workspace_dir = tmp_root / "workspace_should_not_exist"
            workspace_run = run_hired_workspace_agent(
                employment_record_path,
                task="Run a workspace task through an unconfigured live provider.",
                workspace_dir=workspace_dir,
                output_path=tmp_root / "workspace_run.json",
                llm_mode="live",
                llm_model=model,
            )
            job_workspace_dir = tmp_root / "job_workspace_should_not_exist"
            job_run = run_hired_agent_job(
                employment_record_path,
                job_spec={
                    "objective": "Create a report through an unconfigured live provider.",
                    "deliverables": [{"id": "report", "description": "public-safe audit report"}],
                },
                workspace_dir=job_workspace_dir,
                output_path=tmp_root / "job_run.json",
                llm_mode="live",
                llm_model=model,
            )
            dataflow_workspace_dir = tmp_root / "dataflow_workspace_should_not_exist"
            dataflow_run = run_hired_dataflow_job(
                employment_record_path,
                job_spec={"objective": "Run dataflow through an unconfigured live provider."},
                workspace_dir=dataflow_workspace_dir,
                review_label={"score": 90, "status": "verified", "reviewed_by": "runtime-contract-doctor"},
                output_path=tmp_root / "dataflow_run.json",
                llm_mode="live",
                llm_model=model,
            )
            chat_run = run_chat_turn_from_employment(
                employment_record_path,
                message="Answer naturally through the unconfigured live provider.",
                output_path=tmp_root / "chat_run.json",
                llm_mode="live",
                llm_model=model,
                learn_from_chat=True,
            )
            ledger_after = _read_json(fixture_root / "learning_ledger.json")
    except Exception as exc:
        details = {
            "schema": FAIL_CLOSED_RUNTIME_CONTRACT_SCHEMA,
            "status": "doctor_fixture_error",
            "error_type": type(exc).__name__,
        }
        return {
            "schema": FAIL_CLOSED_RUNTIME_CONTRACT_SCHEMA,
            "status": "failed",
            "passed": False,
            "details": details,
            "public_safe": {
                "network_call_performed": False,
                "subprocess_executed": False,
                "live_provider_called": False,
                "secret_values_exported": False,
            },
        }
    finally:
        if old_key is not None:
            os.environ["OPENROUTER_API_KEY"] = old_key

    agent_contract = agent_run.get("execution_contract", {}) if isinstance(agent_run.get("execution_contract"), dict) else {}
    agent_memory = agent_run.get("memory_write", {}) if isinstance(agent_run.get("memory_write"), dict) else {}
    workspace_base = (
        workspace_run.get("base_agent_run", {})
        if isinstance(workspace_run.get("base_agent_run"), dict)
        else {}
    )
    job_workspace = job_run.get("workspace_run", {}) if isinstance(job_run.get("workspace_run"), dict) else {}
    dataflow_growth = (
        dataflow_run.get("growth_commit_candidate", {})
        if isinstance(dataflow_run.get("growth_commit_candidate"), dict)
        else {}
    )
    chat_learning = (
        chat_run.get("chat_learning_update", {})
        if isinstance(chat_run.get("chat_learning_update"), dict)
        else {}
    )
    promoted_before = len(ledger_before.get("promoted_experiences", []))
    promoted_after = len(ledger_after.get("promoted_experiences", []))
    quarantined_before = len(ledger_before.get("quarantined_experiences", []))
    quarantined_after = len(ledger_after.get("quarantined_experiences", []))

    details = {
        "schema": FAIL_CLOSED_RUNTIME_CONTRACT_SCHEMA,
        "provider_engine": "openrouter_api",
        "llm_mode": "live",
        "direct_agent_run_status": agent_run.get("run_status"),
        "direct_agent_llm_status": agent_run.get("llm_runtime_result", {}).get("status")
        if isinstance(agent_run.get("llm_runtime_result"), dict)
        else None,
        "direct_agent_preflight_status": agent_run.get("llm_provider_preflight", {}).get("status")
        if isinstance(agent_run.get("llm_provider_preflight"), dict)
        else None,
        "direct_agent_selected_tool_count": len(agent_run.get("selected_tools", [])),
        "direct_agent_tool_result_count": len(agent_run.get("tool_execution", {}).get("tool_results", []))
        if isinstance(agent_run.get("tool_execution"), dict)
        else None,
        "direct_agent_execution_contract_status": agent_contract.get("status"),
        "direct_agent_llm_attempted": agent_contract.get("llm_runtime", {}).get("attempted")
        if isinstance(agent_contract.get("llm_runtime"), dict)
        else None,
        "direct_agent_tool_attempted": agent_contract.get("tool_execution", {}).get("attempted")
        if isinstance(agent_contract.get("tool_execution"), dict)
        else None,
        "direct_agent_memory_decision": agent_memory.get("decision"),
        "direct_agent_review_candidate_written": "review_candidate" in agent_memory,
        "workspace_run_status": workspace_run.get("run_status"),
        "workspace_base_run_status": workspace_base.get("run_status"),
        "workspace_llm_status": workspace_run.get("llm_runtime_result", {}).get("status")
        if isinstance(workspace_run.get("llm_runtime_result"), dict)
        else None,
        "workspace_output_count": len(workspace_run.get("workspace_outputs", {})),
        "workspace_root_created": workspace_dir.exists(),
        "job_status": job_run.get("job_status"),
        "job_workspace_status": job_workspace.get("run_status"),
        "job_llm_status": job_run.get("llm_runtime_result", {}).get("status")
        if isinstance(job_run.get("llm_runtime_result"), dict)
        else None,
        "job_output_count": len(job_run.get("job_outputs", {})),
        "job_workspace_root_created": job_workspace_dir.exists(),
        "dataflow_status": dataflow_run.get("run_status"),
        "dataflow_llm_status": dataflow_run.get("llm_runtime_result", {}).get("status")
        if isinstance(dataflow_run.get("llm_runtime_result"), dict)
        else None,
        "dataflow_preflight_status": dataflow_run.get("llm_provider_preflight", {}).get("status")
        if isinstance(dataflow_run.get("llm_provider_preflight"), dict)
        else None,
        "dataflow_output_count": len(dataflow_run.get("workspace_outputs", {})),
        "dataflow_workspace_root_created": dataflow_workspace_dir.exists(),
        "dataflow_growth_promotion_status": dataflow_growth.get("promotion_status"),
        "dataflow_growth_verification_status": dataflow_growth.get("verification_status"),
        "chat_status": chat_run.get("chat_status"),
        "chat_reply_generation_mode": chat_run.get("reply_generation_mode"),
        "chat_llm_status": chat_run.get("llm_runtime_result", {}).get("status")
        if isinstance(chat_run.get("llm_runtime_result"), dict)
        else None,
        "chat_preflight_status": chat_run.get("llm_provider_preflight", {}).get("status")
        if isinstance(chat_run.get("llm_provider_preflight"), dict)
        else None,
        "chat_fallback_used": bool(
            isinstance(chat_run.get("llm_runtime_result"), dict)
            and "fallback_used" in chat_run.get("llm_runtime_result", {})
        ),
        "chat_learning_decision": chat_learning.get("decision"),
        "chat_learning_ledger_write_performed": chat_learning.get("ledger_write_performed"),
        "ledger_promoted_count_unchanged": promoted_before == promoted_after,
        "ledger_quarantined_count_unchanged": quarantined_before == quarantined_after,
    }
    passed = (
        details["direct_agent_run_status"] == "needs_configuration"
        and details["direct_agent_llm_status"] == "skipped_provider_not_ready"
        and details["direct_agent_preflight_status"] == "needs_configuration"
        and details["direct_agent_selected_tool_count"] == 0
        and details["direct_agent_tool_result_count"] == 0
        and details["direct_agent_execution_contract_status"] == "provider_configuration_required_before_execution"
        and details["direct_agent_llm_attempted"] is False
        and details["direct_agent_tool_attempted"] is False
        and details["direct_agent_memory_decision"] == "skipped_provider_not_ready"
        and details["direct_agent_review_candidate_written"] is False
        and details["workspace_run_status"] == "needs_configuration"
        and details["workspace_base_run_status"] == "needs_configuration"
        and details["workspace_llm_status"] == "skipped_provider_not_ready"
        and details["workspace_output_count"] == 0
        and details["workspace_root_created"] is False
        and details["job_status"] == "needs_configuration"
        and details["job_workspace_status"] == "needs_configuration"
        and details["job_llm_status"] == "skipped_provider_not_ready"
        and details["job_output_count"] == 0
        and details["job_workspace_root_created"] is False
        and details["dataflow_status"] == "needs_configuration"
        and details["dataflow_llm_status"] == "skipped_provider_not_ready"
        and details["dataflow_preflight_status"] == "needs_configuration"
        and details["dataflow_output_count"] == 0
        and details["dataflow_workspace_root_created"] is False
        and details["dataflow_growth_promotion_status"] == "quarantine"
        and details["dataflow_growth_verification_status"] == "skipped_provider_not_ready"
        and details["chat_status"] == "needs_configuration"
        and details["chat_reply_generation_mode"] == "skipped_provider_not_ready"
        and details["chat_llm_status"] == "skipped_provider_not_ready"
        and details["chat_preflight_status"] == "needs_configuration"
        and details["chat_fallback_used"] is False
        and details["chat_learning_decision"] == "skipped_provider_not_ready"
        and details["chat_learning_ledger_write_performed"] is False
        and details["ledger_promoted_count_unchanged"] is True
        and details["ledger_quarantined_count_unchanged"] is True
    )
    return {
        "schema": FAIL_CLOSED_RUNTIME_CONTRACT_SCHEMA,
        "status": "passed" if passed else "failed",
        "passed": passed,
        "details": details,
        "public_safe": {
            "network_call_performed": False,
            "subprocess_executed": False,
            "live_provider_called": False,
            "secret_values_exported": False,
            "workspace_artifacts_created": any(
                [
                    details["workspace_root_created"],
                    details["job_workspace_root_created"],
                    details["dataflow_workspace_root_created"],
                ]
            ),
            "private_reasoning_trace": "do_not_store",
        },
    }


def doctor_runtime_contract(
    repo_root: Path | None = None,
    *,
    output_path: Path | None = None,
) -> dict[str, Any]:
    """Run public-safe P0 runtime contract checks without external provider calls."""

    root = (repo_root or PROJECT_ROOT).resolve()
    live_contract = run_live_agent_loop_contract()
    fail_closed_contract = run_fail_closed_runtime_contract()
    closed_growth_contract = build_closed_growth_contract(context="runtime_contract_doctor")
    closed_growth_validation = validate_closed_growth_contract(closed_growth_contract)
    checks: list[dict[str, Any]] = []
    _check(
        checks,
        "live_agent_loop_contract_passed",
        live_contract.get("passed") is True,
        details={
            "schema": live_contract.get("schema"),
            "status": live_contract.get("status"),
            "run_status": live_contract.get("details", {}).get("run_status")
            if isinstance(live_contract.get("details"), dict)
            else None,
            "llm_mode": live_contract.get("details", {}).get("llm_mode")
            if isinstance(live_contract.get("details"), dict)
            else None,
        },
    )
    _check(
        checks,
        "fail_closed_runtime_contract_passed",
        fail_closed_contract.get("passed") is True,
        details={
            "schema": fail_closed_contract.get("schema"),
            "status": fail_closed_contract.get("status"),
            "direct_agent_run_status": fail_closed_contract.get("details", {}).get("direct_agent_run_status")
            if isinstance(fail_closed_contract.get("details"), dict)
            else None,
            "chat_status": fail_closed_contract.get("details", {}).get("chat_status")
            if isinstance(fail_closed_contract.get("details"), dict)
            else None,
        },
    )
    _check(
        checks,
        "closed_growth_contract_passed",
        closed_growth_validation.get("passed") is True,
        details={
            "schema": closed_growth_contract.get("schema"),
            "status": closed_growth_validation.get("status"),
            "ecosystem_model": closed_growth_contract.get("ecosystem_model"),
            "failed_checks": closed_growth_validation.get("failed_checks"),
            "missing_core_engines": closed_growth_validation.get("missing_core_engines"),
        },
    )
    public_safe_packets = [
        live_contract.get("public_safe", {}) if isinstance(live_contract.get("public_safe"), dict) else {},
        fail_closed_contract.get("public_safe", {}) if isinstance(fail_closed_contract.get("public_safe"), dict) else {},
    ]
    failed = [check for check in checks if not check["passed"] and check["severity"] == "error"]
    public_safe = {
        "network_call_performed": any(packet.get("network_call_performed") for packet in public_safe_packets),
        "subprocess_executed": any(packet.get("subprocess_executed") for packet in public_safe_packets),
        "live_provider_called": any(packet.get("live_provider_called") for packet in public_safe_packets),
        "secret_values_exported": any(packet.get("secret_values_exported") for packet in public_safe_packets),
        "raw_provider_payload_saved": any(packet.get("raw_provider_payload_saved") for packet in public_safe_packets),
        "private_reasoning_trace": "do_not_store",
        "private_runtime_outputs_scanned": False,
    }
    report = {
        "schema": RUNTIME_CONTRACT_DOCTOR_SCHEMA,
        "created_at_utc": _now(),
        "status": "passed" if not failed else "failed",
        "passed": not failed,
        "summary": {
            "check_count": len(checks),
            "failed_count": len(failed),
            "repo_root_hint": "." if root == PROJECT_ROOT.resolve() else root.name,
            "network_call_performed": public_safe["network_call_performed"],
            "subprocess_executed": public_safe["subprocess_executed"],
            "live_provider_called": public_safe["live_provider_called"],
            "secret_values_exported": public_safe["secret_values_exported"],
        },
        "checks": checks,
        "artifacts": {
            "live_agent_loop_contract": live_contract,
            "fail_closed_runtime_contract": fail_closed_contract,
            "closed_growth_contract": closed_growth_contract,
            "closed_growth_contract_validation": closed_growth_validation,
        },
        "public_safe": public_safe,
    }
    if output_path is not None:
        _write_json(output_path, report)
    return report
