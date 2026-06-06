from __future__ import annotations

import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ai22b.config import PROJECT_ROOT
from ai22b.talent_foundry.agent_runtime_smoke import AGENT_RUNTIME_SMOKE_SCHEMA, run_agent_runtime_smoke
from ai22b.talent_foundry.agent_runner import run_agent_from_manifest
from ai22b.talent_foundry.chat_runtime_smoke import CHAT_RUNTIME_SMOKE_SCHEMA, run_chat_runtime_smoke
from ai22b.talent_foundry.distribution import verify_agent_release_archive, verify_agent_release_bundle
from ai22b.talent_foundry.execution_proof import (
    WORKSPACE_EXECUTION_PROOF_SCHEMA,
    verify_workspace_execution_file,
)
from ai22b.talent_foundry.policy_eval import (
    ACTION_POLICY_EVAL_REPORT_SCHEMA,
    DEFAULT_POLICY_EVAL_SUITE,
    run_action_policy_eval,
)
from ai22b.talent_foundry.llm_runtime import (
    LLM_PROVIDER_DOCTOR_SCHEMA,
    LLM_PROVIDER_PREFLIGHT_SCHEMA,
    LLM_PROVIDER_SMOKE_CONTRACT_SCHEMA,
    LLM_APPLICATION_SMOKE_SCHEMA,
    build_llm_provider_preflight,
    build_llm_runtime_config,
    doctor_llm_provider,
    run_llm_application_smoke,
)
from ai22b.talent_foundry.learning_loop import build_reasoning_kernel, create_learning_ledger
from ai22b.talent_foundry.llm_onboarding import build_llm_connection_profile
from ai22b.talent_foundry.onboarding_choices import LLM_SERVICE_CATALOG
from ai22b.talent_foundry.package_install_doctor import PACKAGE_INSTALL_DOCTOR_SCHEMA, doctor_package_install
from ai22b.talent_foundry.role_models import list_role_models, summarize_role_model
from ai22b.talent_foundry.runtime_benchmark import RUNTIME_OBSERVABILITY_COMPARISON_SCHEMA
from ai22b.talent_foundry.runtime_contract_doctor import (
    FAIL_CLOSED_RUNTIME_CONTRACT_SCHEMA,
    LIVE_AGENT_LOOP_CONTRACT_SCHEMA,
    RUNTIME_CONTRACT_DOCTOR_SCHEMA,
    doctor_runtime_contract,
    run_fail_closed_runtime_contract,
    run_live_agent_loop_contract,
)
from ai22b.talent_foundry.source_sbom import SOURCE_SBOM_SCHEMA, build_source_sbom
from ai22b.talent_foundry.tool_registry import TOOL_CAPABILITY_AUDIT_SCHEMA, audit_tool_capability_registry


AUDIT_SCHEMA = "ai-talent-foundry-release-audit/v1"
AGENT_EXECUTION_CONTRACT_SCHEMA = "paideia-agent-execution-contract/v1"
CAPABILITY_AUTHORIZATION_SCHEMA = "paideia-capability-authorization/v1"
MEMORY_REVIEW_CANDIDATE_SCHEMA = "paideia-memory-review-candidate/v1"
RUNTIME_OBSERVABILITY_SCHEMA = "paideia-runtime-observability/v1"
WORKSPACE_EXECUTION_PROOF_SAFETY_SCHEMA = "paideia-workspace-execution-proof-safety/v1"
MAX_AUDITED_SAFE_REFERENCE_CHARS = 12000
MAX_AUDITED_SAFE_REFERENCE_TEXT_CHARS = 900
WINDOWS_ABSOLUTE_PATH = re.compile(r"[A-Za-z]:\\")
POSIX_HOME_PATH = re.compile(r"(/home/|/Users/)[^\s\"']+")
SECRET_RE = re.compile(r"(sk-[A-Za-z0-9_-]{16,}|Bearer\s+[A-Za-z0-9._-]+|api[_-]?key\s*[:=])", re.I)
PRIVATE_REASONING_KEYS = {
    "chain_of_thought",
    "private_reasoning_trace",
    "hidden_reasoning",
    "reasoning_trace",
}
REQUIRED_MAJOR_GATES = {"school_exam", "csat", "university_graduation", "doctoral_defense"}
REQUIRED_RESEARCH_NAMES = {
    "Hermes Agent",
    "Hermes Memory Routing Issue",
    "Hermes Long-Session Field Report",
    "OpenHands",
    "OpenClaw",
    "OpenClaw Memory Index Issue",
    "Reflexion",
    "Generative Agents",
    "Survey on the Memory Mechanism of LLM-based Agents",
}
REQUIRED_RESEARCH_CATEGORIES = {
    "reference_agent_program",
    "agent_runtime",
    "reflection_learning",
    "memory_architecture",
    "memory_operability",
    "operational_feedback",
    "profile_isolation",
    "human_centered_governance",
    "public_distribution_safety",
}
OPERATIONAL_RESEARCH_CATEGORIES = {"operational_feedback", "memory_operability", "profile_isolation"}
REQUIRED_POLICY_EVAL_CASES = {
    "analysis_only_trade_negated_ko",
    "destructive_file_delete_ko",
    "destructive_file_discussion_negated",
    "english_trade_execution_discussion_negated",
    "english_trade_bypass_upload",
    "external_upload_command_ko",
    "external_upload_policy_discussion_ko",
    "hyphenated_english_bypass_trade",
    "japanese_personal_data_transfer",
    "japanese_policy_bypass_discussion",
    "japanese_trade_upload_bypass",
    "personal_data_transfer_en",
    "personal_data_transfer_ko",
    "policy_bypass_discussion_ko",
    "network_request_curl",
    "subprocess_execution_powershell",
    "spaced_personal_data_transfer_ko",
    "spaced_trade_upload_bypass_ko",
    "spaced_upload_discussion_negated_ko",
    "trade_with_policy_bypass_ko",
}
REQUIRED_POLICY_EVAL_CATEGORIES = {
    "allowed_analysis_only",
    "allowed_compact_normalized_policy_discussion",
    "allowed_destructive_policy_discussion",
    "allowed_policy_discussion",
    "blocked_compact_normalized_personal_data_transfer",
    "blocked_compact_normalized_sensitive_command",
    "blocked_destructive_filesystem_action",
    "blocked_external_upload",
    "blocked_multilingual_sensitive_command",
    "blocked_network_request",
    "blocked_personal_data_transfer",
    "blocked_policy_bypass_and_trade",
    "blocked_subprocess_execution",
}
REQUIRED_LLM_SERVICE_IDS = {
    "anthropic_claude_api",
    "bigram_local",
    "deterministic_local",
    "google_gemini_api",
    "llama_cpp_local",
    "lm_studio_local",
    "mistral_api",
    "ollama_local",
    "openai_chatgpt_codex",
    "openrouter_api",
    "transformers_local",
}
REQUIRED_PUBLIC_PROGRAM_COMMANDS = {
    "blueprint",
    "list-llm-services",
    "doctor-onboarding-session",
    "doctor-first-run",
    "doctor-package-install",
    "doctor-runtime-contract",
    "start-console",
    "onboard-agent",
    "build-llm-onboarding-checklist",
    "build-llm-connection-profile",
    "raise",
    "doctor-llm-provider",
    "run-llm-application-smoke",
    "run-agent-runtime-smoke",
    "run-chat-runtime-smoke",
    "doctor-llm-live-readiness",
    "audit-tool-capabilities",
    "doctor-bundle",
    "install-package",
    "hire-installed",
    "run-hired-workspace-agent",
    "run-hired-agent-job",
    "build-agent-program",
    "build-paideia-agent-kit",
    "doctor-agent-program",
    "migrate-agent-assets",
    "run-agent-program-chat",
    "run-hired-agent-job-cycle",
    "record-hired-learning",
    "assign-hired-goal",
    "assemble-hired-projection-swarm",
    "assemble-hired-team",
    "family",
    "audit-release",
    "audit-public-release-readiness",
    "build-source-sbom",
}
REQUIRED_PUBLIC_PROGRAM_LIFECYCLE = {
    "design",
    "raise",
    "package",
    "install",
    "hire",
    "work",
    "review",
    "grow",
    "lineage",
    "audit",
}
REQUIRED_PUBLIC_PROGRAM_ROLES = {"education_committee", "home_care", "oversight_committee"}
PUBLIC_SAFE_FIRST_RUN_COMMANDS = {
    "list-role-models",
    "list-llm-services",
    "build-llm-onboarding-checklist",
    "build-llm-connection-profile",
    "doctor-llm-provider",
    "run-llm-application-smoke",
    "run-agent-runtime-smoke",
    "run-chat-runtime-smoke",
    "doctor-llm-live-readiness",
    "audit-tool-capabilities",
    "run-action-policy-eval",
    "audit-public-release-readiness",
    "build-source-sbom",
    "doctor-first-run",
    "doctor-package-install",
    "doctor-runtime-contract",
}


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _rel(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.name


def _installed_agent_root(run_dir: Path) -> Path:
    agents_dir = run_dir / "installed_agents" / "agents"
    candidates = sorted(path for path in agents_dir.iterdir() if path.is_dir()) if agents_dir.exists() else []
    if not candidates:
        return agents_dir / "missing_agent"
    return candidates[0]


def _base_agent_run(run: dict[str, Any]) -> dict[str, Any]:
    base = run.get("base_agent_run")
    return base if isinstance(base, dict) else run


def _agent_p0_runtime_details(run: dict[str, Any]) -> dict[str, Any]:
    base = _base_agent_run(run)
    contract = base.get("execution_contract", {}) if isinstance(base.get("execution_contract"), dict) else {}
    policy = base.get("policy_decision", {}) if isinstance(base.get("policy_decision"), dict) else {}
    authorization = (
        policy.get("capability_authorization", {})
        if isinstance(policy.get("capability_authorization"), dict)
        else {}
    )
    authorization_invariants = (
        authorization.get("invariants", {})
        if isinstance(authorization.get("invariants"), dict)
        else {}
    )
    memory_write = base.get("memory_write", {}) if isinstance(base.get("memory_write"), dict) else {}
    review_candidate = (
        memory_write.get("review_candidate", {})
        if isinstance(memory_write.get("review_candidate"), dict)
        else {}
    )
    promotion_gate = (
        review_candidate.get("promotion_gate", {})
        if isinstance(review_candidate.get("promotion_gate"), dict)
        else {}
    )
    retention_policy = (
        review_candidate.get("retention_policy", {})
        if isinstance(review_candidate.get("retention_policy"), dict)
        else {}
    )
    observability = (
        base.get("runtime_observability", {})
        if isinstance(base.get("runtime_observability"), dict)
        else run.get("runtime_observability", {})
    )
    observability = observability if isinstance(observability, dict) else {}
    llm_result = base.get("llm_runtime_result", {}) if isinstance(base.get("llm_runtime_result"), dict) else {}
    llm_plan = llm_result.get("llm_plan", {}) if isinstance(llm_result.get("llm_plan"), dict) else {}
    alignment = (
        base.get("llm_tool_plan_alignment", {})
        if isinstance(base.get("llm_tool_plan_alignment"), dict)
        else {}
    )
    contract_policy = contract.get("policy_gate", {}) if isinstance(contract.get("policy_gate"), dict) else {}
    contract_memory = contract.get("memory_write", {}) if isinstance(contract.get("memory_write"), dict) else {}
    details = {
        "run_schema": base.get("schema"),
        "run_status": base.get("run_status"),
        "execution_contract_schema": contract.get("schema"),
        "execution_contract_status": contract.get("status"),
        "execution_contract_issues": contract.get("issues", []),
        "policy_status": policy.get("status"),
        "policy_checked_before_llm": contract_policy.get("checked_before_llm"),
        "policy_checked_before_tools": contract_policy.get("checked_before_tools"),
        "capability_authorization_schema": authorization.get("schema"),
        "capability_authorization_mode": authorization.get("mode"),
        "capability_authorization_model": authorization.get("authorization_model"),
        "registered_tool_executor_is_execution_authority": authorization_invariants.get(
            "registered_tool_executor_is_execution_authority"
        ),
        "llm_tool_suggestions_are_non_authoritative": authorization_invariants.get(
            "llm_tool_suggestions_are_non_authoritative"
        ),
        "llm_plan_schema": llm_plan.get("schema"),
        "llm_plan_raw_provider_text_stored": llm_plan.get("raw_provider_text_stored"),
        "llm_tool_plan_alignment_schema": alignment.get("schema"),
        "llm_tool_plan_suggestion_only_enforced": alignment.get("suggestion_only_enforced"),
        "memory_review_candidate_schema": review_candidate.get("schema"),
        "memory_review_candidate_target": review_candidate.get("target"),
        "memory_automatic_promotion_performed": contract_memory.get(
            "automatic_promotion_performed",
            memory_write.get("automatic_promotion_performed"),
        ),
        "memory_review_candidate_automatic_promotion_allowed": promotion_gate.get("automatic_promotion_allowed"),
        "memory_review_candidate_private_reasoning_trace": retention_policy.get("private_reasoning_trace"),
        "runtime_observability_schema": observability.get("schema"),
        "runtime_private_reasoning_trace_stored": observability.get("privacy", {}).get(
            "private_reasoning_trace_stored"
        ),
        "runtime_full_session_replay_used": observability.get("context", {}).get("full_session_replay_used"),
    }
    details["p0_runtime_ready"] = (
        details["execution_contract_schema"] == AGENT_EXECUTION_CONTRACT_SCHEMA
        and details["execution_contract_status"] == "passed"
        and details["execution_contract_issues"] == []
        and details["policy_status"] == "approved"
        and details["policy_checked_before_llm"] is True
        and details["policy_checked_before_tools"] is True
        and details["capability_authorization_schema"] == CAPABILITY_AUTHORIZATION_SCHEMA
        and details["capability_authorization_mode"] == "deny_by_default"
        and details["registered_tool_executor_is_execution_authority"] is True
        and details["llm_tool_suggestions_are_non_authoritative"] is True
        and details["llm_plan_schema"] == "paideia-llm-reviewable-plan/v1"
        and details["llm_plan_raw_provider_text_stored"] is False
        and details["llm_tool_plan_alignment_schema"] == "paideia-llm-tool-plan-alignment/v1"
        and details["llm_tool_plan_suggestion_only_enforced"] is True
        and details["memory_review_candidate_schema"] == MEMORY_REVIEW_CANDIDATE_SCHEMA
        and details["memory_review_candidate_target"] == "local_learning_ledger"
        and details["memory_automatic_promotion_performed"] is False
        and details["memory_review_candidate_automatic_promotion_allowed"] is False
        and details["memory_review_candidate_private_reasoning_trace"] == "do_not_store"
        and details["runtime_observability_schema"] == RUNTIME_OBSERVABILITY_SCHEMA
        and details["runtime_private_reasoning_trace_stored"] is False
        and details["runtime_full_session_replay_used"] is False
    )
    return details


def _dataflow_p0_runtime_details(run: dict[str, Any]) -> dict[str, Any]:
    observability = run.get("runtime_observability", {}) if isinstance(run.get("runtime_observability"), dict) else {}
    llm_result = run.get("llm_runtime_result", {}) if isinstance(run.get("llm_runtime_result"), dict) else {}
    preflight = (
        run.get("llm_provider_preflight", {})
        if isinstance(run.get("llm_provider_preflight"), dict)
        else llm_result.get("llm_provider_preflight", {})
    )
    preflight = preflight if isinstance(preflight, dict) else {}
    growth = run.get("growth_commit_candidate", {}) if isinstance(run.get("growth_commit_candidate"), dict) else {}
    details = {
        "schema": run.get("schema"),
        "status": run.get("run_status"),
        "llm_provider_preflight_schema": preflight.get("schema"),
        "runtime_observability_schema": observability.get("schema"),
        "runtime_private_reasoning_trace_stored": observability.get("privacy", {}).get(
            "private_reasoning_trace_stored"
        ),
        "runtime_full_session_replay_used": observability.get("context", {}).get("full_session_replay_used"),
        "growth_candidate_schema": growth.get("schema"),
        "growth_candidate_private_reasoning_trace_policy": growth.get("private_reasoning_trace_policy"),
    }
    details["p0_runtime_ready"] = (
        details["schema"] == "ai-talent-dataflow-run/v1"
        and details["status"] == "completed"
        and details["llm_provider_preflight_schema"] == "paideia-llm-provider-preflight/v1"
        and details["runtime_observability_schema"] == RUNTIME_OBSERVABILITY_SCHEMA
        and details["runtime_private_reasoning_trace_stored"] is False
        and details["runtime_full_session_replay_used"] is False
        and details["growth_candidate_schema"] == "ai-talent-dataflow-growth-commit-candidate/v1"
        and details["growth_candidate_private_reasoning_trace_policy"] == "do_not_store"
    )
    return details


def _runtime_observability_comparison(run_dir: Path) -> dict[str, Any]:
    comparison_path = run_dir / "runtime_observability_comparison.json"
    if not comparison_path.exists():
        return _checkpoint(
            passed=False,
            evidence=[comparison_path],
            root=run_dir,
            missing=[comparison_path],
            details={"reason": "runtime_observability_comparison_missing"},
        )

    comparison = _read_json(comparison_path)
    summary = comparison.get("summary", {}) if isinstance(comparison.get("summary"), dict) else {}
    records = comparison.get("records", []) if isinstance(comparison.get("records"), list) else []
    missing_observability = (
        comparison.get("missing_observability", [])
        if isinstance(comparison.get("missing_observability"), list)
        else []
    )
    record_privacy = [
        {
            "source_file_name": item.get("source_file_name"),
            "selected_memory_only": item.get("paideia_memory_board", {}).get("selected_memory_only")
            if isinstance(item.get("paideia_memory_board"), dict)
            else None,
            "full_session_replay_used": item.get("paideia_memory_board", {}).get("full_session_replay_used")
            if isinstance(item.get("paideia_memory_board"), dict)
            else None,
            "private_reasoning_trace_stored": item.get("privacy", {}).get("private_reasoning_trace_stored")
            if isinstance(item.get("privacy"), dict)
            else None,
            "local_absolute_paths_exported": item.get("privacy", {}).get("local_absolute_paths_exported")
            if isinstance(item.get("privacy"), dict)
            else None,
            "uses_less_context": item.get("comparison", {}).get("paideia_uses_less_context_than_replay_baseline")
            if isinstance(item.get("comparison"), dict)
            else None,
        }
        for item in records
        if isinstance(item, dict)
    ]
    details = {
        "schema": comparison.get("schema"),
        "record_count": summary.get("record_count"),
        "missing_observability_count": summary.get("missing_observability_count"),
        "context_reduction_ratio": summary.get("context_reduction_ratio"),
        "all_records_use_selected_memory_only": summary.get("all_records_use_selected_memory_only"),
        "all_records_avoid_full_session_replay": summary.get("all_records_avoid_full_session_replay"),
        "privacy_ok": summary.get("privacy_ok"),
        "public_safe": summary.get("public_safe"),
        "paideia_prompt_context_estimated_tokens": summary.get("paideia_prompt_context_estimated_tokens"),
        "generic_prompt_wrapper_replay_estimated_tokens": summary.get(
            "generic_prompt_wrapper_replay_estimated_tokens"
        ),
        "record_privacy": record_privacy,
        "missing_observability": missing_observability,
    }
    passed = (
        details["schema"] == RUNTIME_OBSERVABILITY_COMPARISON_SCHEMA
        and isinstance(details["record_count"], int)
        and details["record_count"] >= 2
        and details["missing_observability_count"] == 0
        and isinstance(details["context_reduction_ratio"], (int, float))
        and details["context_reduction_ratio"] > 1
        and details["all_records_use_selected_memory_only"] is True
        and details["all_records_avoid_full_session_replay"] is True
        and details["privacy_ok"] is True
        and details["public_safe"] is True
        and all(item.get("uses_less_context") is True for item in record_privacy)
        and all(item.get("selected_memory_only") is True for item in record_privacy)
        and all(item.get("full_session_replay_used") is False for item in record_privacy)
        and all(item.get("private_reasoning_trace_stored") is False for item in record_privacy)
        and all(item.get("local_absolute_paths_exported") is False for item in record_privacy)
    )
    return _checkpoint(passed=passed, evidence=[comparison_path], root=run_dir, details=details)


def _unique_paths(paths: list[Path]) -> list[Path]:
    seen: set[str] = set()
    unique: list[Path] = []
    for path in paths:
        key = str(path)
        if key in seen:
            continue
        seen.add(key)
        unique.append(path)
    return unique


def _iter_learning_ledger_entries(ledger: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    entries: list[tuple[str, dict[str, Any]]] = []
    for bucket in ("promoted_experiences", "quarantined_experiences"):
        bucket_entries = ledger.get(bucket, [])
        if not isinstance(bucket_entries, list):
            continue
        for entry in bucket_entries:
            if isinstance(entry, dict):
                entries.append((bucket, entry))
    return entries


def _scan_safe_reference_value(value: Any, *, path: str = "$") -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    if isinstance(value, dict):
        for key, item in value.items():
            key_text = str(key)
            item_path = f"{path}.{key_text}"
            if key_text in PRIVATE_REASONING_KEYS:
                issues.append(
                    {
                        "id": "private_reasoning_key_in_safe_reference",
                        "path": item_path,
                        "key": key_text,
                    }
                )
            if key_text == "private_reasoning_trace_stored" and item is not False:
                issues.append(
                    {
                        "id": "private_reasoning_trace_stored_flag_not_false",
                        "path": item_path,
                        "value": item,
                    }
                )
            if key_text == "private_reasoning_trace_policy" and item != "do_not_store":
                issues.append(
                    {
                        "id": "private_reasoning_trace_policy_not_do_not_store",
                        "path": item_path,
                        "value": item,
                    }
                )
            if key_text == "full_session_replay_stored" and item is not False:
                issues.append(
                    {
                        "id": "full_session_replay_stored_flag_not_false",
                        "path": item_path,
                        "value": item,
                    }
                )
            if key_text == "full_session_replay_used" and item is not False:
                issues.append(
                    {
                        "id": "full_session_replay_used_flag_not_false",
                        "path": item_path,
                        "value": item,
                    }
                )
            if key_text in {"raw_provider_payload", "raw_provider_text", "raw_output"}:
                issues.append(
                    {
                        "id": "raw_provider_data_key_in_safe_reference",
                        "path": item_path,
                        "key": key_text,
                    }
                )
            if key_text in {"raw_provider_payload_saved", "raw_output_saved"} and item is not False:
                issues.append(
                    {
                        "id": "raw_provider_payload_saved_flag_not_false",
                        "path": item_path,
                        "value": item,
                    }
                )
            issues.extend(_scan_safe_reference_value(item, path=item_path))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            issues.extend(_scan_safe_reference_value(item, path=f"{path}[{index}]"))
    elif isinstance(value, str):
        if WINDOWS_ABSOLUTE_PATH.search(value) or POSIX_HOME_PATH.search(value):
            issues.append(
                {
                    "id": "local_absolute_path_in_safe_reference",
                    "path": path,
                }
            )
        if SECRET_RE.search(value):
            issues.append(
                {
                    "id": "secret_like_value_in_safe_reference",
                    "path": path,
                }
            )
        if len(value) > MAX_AUDITED_SAFE_REFERENCE_TEXT_CHARS:
            issues.append(
                {
                    "id": "safe_reference_text_too_long",
                    "path": path,
                    "length": len(value),
                    "max_length": MAX_AUDITED_SAFE_REFERENCE_TEXT_CHARS,
                }
            )
    return issues


def _audit_safe_reference(
    *,
    ledger_path: Path,
    bucket: str,
    entry: dict[str, Any],
) -> tuple[int, list[dict[str, Any]]]:
    safe_reference = entry.get("safe_reference")
    if not isinstance(safe_reference, dict):
        return 0, [
            {
                "id": "safe_reference_missing",
                "ledger": ledger_path.name,
                "bucket": bucket,
                "experience_id": entry.get("id"),
            }
        ]

    serialized = json.dumps(safe_reference, ensure_ascii=False, sort_keys=True)
    issues: list[dict[str, Any]] = []
    if len(serialized) > MAX_AUDITED_SAFE_REFERENCE_CHARS:
        issues.append(
            {
                "id": "safe_reference_too_large",
                "ledger": ledger_path.name,
                "bucket": bucket,
                "experience_id": entry.get("id"),
                "length": len(serialized),
                "max_length": MAX_AUDITED_SAFE_REFERENCE_CHARS,
            }
        )

    policy = safe_reference.get("safe_reference_policy", {})
    if not isinstance(policy, dict):
        issues.append(
            {
                "id": "safe_reference_policy_missing",
                "ledger": ledger_path.name,
                "bucket": bucket,
                "experience_id": entry.get("id"),
            }
        )
    else:
        if policy.get("bounded_summary_only") is not True:
            issues.append(
                {
                    "id": "safe_reference_not_bounded_summary",
                    "ledger": ledger_path.name,
                    "bucket": bucket,
                    "experience_id": entry.get("id"),
                }
            )
        if policy.get("full_session_replay_stored") is not False:
            issues.append(
                {
                    "id": "safe_reference_policy_allows_full_session_replay",
                    "ledger": ledger_path.name,
                    "bucket": bucket,
                    "experience_id": entry.get("id"),
                }
            )
        if policy.get("private_reasoning_trace_policy") != "do_not_store":
            issues.append(
                {
                    "id": "safe_reference_policy_allows_private_reasoning",
                    "ledger": ledger_path.name,
                    "bucket": bucket,
                    "experience_id": entry.get("id"),
                    "policy": policy.get("private_reasoning_trace_policy"),
                }
            )

    for issue in _scan_safe_reference_value(safe_reference):
        issues.append(
            {
                "ledger": ledger_path.name,
                "bucket": bucket,
                "experience_id": entry.get("id"),
                **issue,
            }
        )
    return len(serialized), issues


def _learning_ledger_replay_safety(run_dir: Path, installed_root: Path) -> dict[str, Any]:
    run_ledger_candidates = sorted(run_dir.glob("*_learning_ledger.json"))
    installed_ledger = installed_root / "learning_ledger.json"
    candidate_paths = _unique_paths([run_dir / "shinyong_learning_ledger.json", *run_ledger_candidates, installed_ledger])
    existing_paths = [path for path in candidate_paths if path.exists()]
    missing = [] if existing_paths else [run_dir / "*_learning_ledger.json", installed_ledger]

    ledger_reports: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    entry_count = 0
    max_safe_reference_chars = 0
    lifecycle_passed = True
    local_paths_redacted = True
    private_reasoning_not_stored = True
    secret_values_absent = True

    for ledger_path in existing_paths:
        try:
            ledger = _read_json(ledger_path)
        except (OSError, json.JSONDecodeError) as exc:
            failures.append(
                {
                    "id": "learning_ledger_unreadable",
                    "ledger": ledger_path.name,
                    "error": type(exc).__name__,
                }
            )
            continue

        entries = _iter_learning_ledger_entries(ledger)
        lifecycle = ledger.get("memory_lifecycle", {}) if isinstance(ledger.get("memory_lifecycle"), dict) else {}
        checks = lifecycle.get("checks", {}) if isinstance(lifecycle.get("checks"), dict) else {}
        lifecycle_status = lifecycle.get("status")
        ledger_lifecycle_passed = lifecycle_status == "passed"
        ledger_paths_redacted = checks.get("local_absolute_paths_redacted") is True
        ledger_private_not_stored = checks.get("private_reasoning_trace_not_stored") is True
        ledger_secrets_absent = checks.get("secret_like_values_absent") is True

        lifecycle_passed = lifecycle_passed and ledger_lifecycle_passed
        local_paths_redacted = local_paths_redacted and ledger_paths_redacted
        private_reasoning_not_stored = private_reasoning_not_stored and ledger_private_not_stored
        secret_values_absent = secret_values_absent and ledger_secrets_absent
        if not ledger_lifecycle_passed:
            failures.append(
                {
                    "id": "memory_lifecycle_not_passed",
                    "ledger": ledger_path.name,
                    "status": lifecycle_status,
                }
            )
        if not ledger_paths_redacted:
            failures.append({"id": "ledger_lifecycle_local_paths_not_redacted", "ledger": ledger_path.name})
        if not ledger_private_not_stored:
            failures.append({"id": "ledger_lifecycle_private_reasoning_not_blocked", "ledger": ledger_path.name})
        if not ledger_secrets_absent:
            failures.append({"id": "ledger_lifecycle_secret_values_present", "ledger": ledger_path.name})

        promoted_count = len(ledger.get("promoted_experiences", [])) if isinstance(ledger.get("promoted_experiences"), list) else 0
        quarantined_count = (
            len(ledger.get("quarantined_experiences", []))
            if isinstance(ledger.get("quarantined_experiences"), list)
            else 0
        )
        for bucket, entry in entries:
            entry_count += 1
            safe_reference_chars, entry_issues = _audit_safe_reference(
                ledger_path=ledger_path,
                bucket=bucket,
                entry=entry,
            )
            max_safe_reference_chars = max(max_safe_reference_chars, safe_reference_chars)
            failures.extend(entry_issues)

        ledger_reports.append(
            {
                "path": _rel(ledger_path, run_dir),
                "schema": ledger.get("schema"),
                "promoted_count": promoted_count,
                "quarantined_count": quarantined_count,
                "entry_count": len(entries),
                "memory_lifecycle_status": lifecycle_status,
                "private_reasoning_trace_not_stored": ledger_private_not_stored,
                "local_absolute_paths_redacted": ledger_paths_redacted,
                "secret_like_values_absent": ledger_secrets_absent,
            }
        )

    run_ledger_count = sum(1 for path in existing_paths if path.parent == run_dir)
    installed_ledger_present = installed_ledger.exists()
    unsafe_entry_count = sum(1 for issue in failures if "experience_id" in issue)
    full_session_failures = [
        issue
        for issue in failures
        if "full_session_replay" in str(issue.get("id", "")) or "full_session_replay" in str(issue.get("path", ""))
    ]
    private_reasoning_failures = [
        issue
        for issue in failures
        if "private_reasoning" in str(issue.get("id", "")) or "private_reasoning" in str(issue.get("path", ""))
    ]
    details = {
        "ledger_count": len(existing_paths),
        "run_ledger_count": run_ledger_count,
        "installed_ledger_present": installed_ledger_present,
        "entry_count": entry_count,
        "max_safe_reference_chars": max_safe_reference_chars,
        "max_allowed_safe_reference_chars": MAX_AUDITED_SAFE_REFERENCE_CHARS,
        "all_safe_references_bounded": unsafe_entry_count == 0
        and max_safe_reference_chars <= MAX_AUDITED_SAFE_REFERENCE_CHARS,
        "all_safe_references_avoid_full_session_replay": not full_session_failures,
        "all_private_reasoning_trace_policy_do_not_store": private_reasoning_not_stored
        and not private_reasoning_failures,
        "all_memory_lifecycle_passed": lifecycle_passed,
        "all_local_absolute_paths_redacted": local_paths_redacted,
        "all_secret_like_values_absent": secret_values_absent,
        "ledger_reports": ledger_reports,
        "failure_count": len(failures),
        "failures": failures[:20],
    }
    passed = (
        bool(existing_paths)
        and run_ledger_count >= 1
        and installed_ledger_present
        and entry_count > 0
        and details["all_safe_references_bounded"] is True
        and details["all_safe_references_avoid_full_session_replay"] is True
        and details["all_private_reasoning_trace_policy_do_not_store"] is True
        and details["all_memory_lifecycle_passed"] is True
        and details["all_local_absolute_paths_redacted"] is True
        and details["all_secret_like_values_absent"] is True
        and not failures
    )
    return _checkpoint(passed=passed, evidence=existing_paths, root=run_dir, details=details, missing=missing)


def _checkpoint(
    *,
    passed: bool,
    evidence: list[Path],
    root: Path,
    details: dict[str, Any] | None = None,
    missing: list[Path] | None = None,
) -> dict[str, Any]:
    return {
        "passed": passed,
        "evidence": [_rel(path, root) for path in evidence if path.exists()],
        "missing": [_rel(path, root) for path in missing or [] if not path.exists()],
        "details": details or {},
    }


def _research_foundation() -> dict[str, Any]:
    sources_path = PROJECT_ROOT / "data" / "public" / "research" / "agent_foundry_sources.jsonl"
    if not sources_path.exists():
        return _checkpoint(
            passed=False,
            evidence=[sources_path],
            root=PROJECT_ROOT,
            missing=[sources_path],
            details={"source_count": 0},
        )

    rows: list[dict[str, Any]] = []
    invalid_lines: list[int] = []
    for line_number, line in enumerate(sources_path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            invalid_lines.append(line_number)
            continue
        if isinstance(item, dict):
            rows.append(item)

    names = {str(item.get("name", "")) for item in rows}
    categories = {str(item.get("category", "")) for item in rows}
    source_types = {str(item.get("source_type", "")) for item in rows}
    invalid_urls = [
        str(item.get("name", "unnamed"))
        for item in rows
        if not str(item.get("url", "")).startswith("https://")
    ]
    missing_implications = [
        str(item.get("name", "unnamed"))
        for item in rows
        if not str(item.get("design_implication", "")).strip()
    ]
    missing_operational_fields = [
        str(item.get("name", "unnamed"))
        for item in rows
        if str(item.get("category", "")) in OPERATIONAL_RESEARCH_CATEGORIES
        and (
            not str(item.get("observed_problem", "")).strip()
            or not str(item.get("mitigation", "")).strip()
        )
    ]
    missing_names = sorted(REQUIRED_RESEARCH_NAMES - names)
    missing_categories = sorted(REQUIRED_RESEARCH_CATEGORIES - categories)
    missing_source_types = sorted({"official_docs", "paper", "github_issue"} - source_types)

    details = {
        "source_count": len(rows),
        "names": sorted(names),
        "categories": sorted(categories),
        "source_types": sorted(source_types),
        "required_names_present": sorted(REQUIRED_RESEARCH_NAMES & names),
        "required_categories_present": sorted(REQUIRED_RESEARCH_CATEGORIES & categories),
        "invalid_lines": invalid_lines,
        "invalid_urls": invalid_urls,
        "missing_design_implications": missing_implications,
        "missing_operational_fields": missing_operational_fields,
        "operational_feedback_count": sum(
            1 for item in rows if str(item.get("category", "")) in OPERATIONAL_RESEARCH_CATEGORIES
        ),
        "missing_names": missing_names,
        "missing_categories": missing_categories,
        "missing_source_types": missing_source_types,
    }
    passed = (
        len(rows) >= 8
        and not invalid_lines
        and not invalid_urls
        and not missing_implications
        and not missing_operational_fields
        and not missing_names
        and not missing_categories
        and not missing_source_types
    )
    return _checkpoint(passed=passed, evidence=[sources_path], root=PROJECT_ROOT, details=details)


def _action_policy_safety() -> dict[str, Any]:
    suite_path = DEFAULT_POLICY_EVAL_SUITE
    if not suite_path.exists():
        return _checkpoint(
            passed=False,
            evidence=[suite_path],
            root=PROJECT_ROOT,
            missing=[suite_path],
            details={"reason": "policy_eval_suite_missing"},
        )

    try:
        report = run_action_policy_eval(suite_path=suite_path)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        return _checkpoint(
            passed=False,
            evidence=[suite_path],
            root=PROJECT_ROOT,
            details={
                "reason": "policy_eval_failed_to_run",
                "error": type(exc).__name__,
            },
        )

    case_results = report.get("case_results", []) if isinstance(report.get("case_results"), list) else []
    case_ids = {str(item.get("case_id", "")) for item in case_results if isinstance(item, dict)}
    categories = {str(item.get("category", "")) for item in case_results if isinstance(item, dict)}
    failed_cases = [
        {
            "case_id": item.get("case_id"),
            "failures": item.get("failures", []),
            "actual_status": item.get("actual_status"),
            "expected_status": item.get("expected_status"),
        }
        for item in case_results
        if isinstance(item, dict) and not item.get("passed")
    ]
    status_mismatches = [
        {
            "case_id": item.get("case_id"),
            "actual_status": item.get("actual_status"),
            "expected_status": item.get("expected_status"),
        }
        for item in case_results
        if isinstance(item, dict) and item.get("actual_status") != item.get("expected_status")
    ]
    runtime_policy = report.get("runtime_policy", {}) if isinstance(report.get("runtime_policy"), dict) else {}
    summary = report.get("summary", {}) if isinstance(report.get("summary"), dict) else {}
    missing_cases = sorted(REQUIRED_POLICY_EVAL_CASES - case_ids)
    missing_categories = sorted(REQUIRED_POLICY_EVAL_CATEGORIES - categories)
    details = {
        "schema": report.get("schema"),
        "suite_id": report.get("suite", {}).get("suite_id") if isinstance(report.get("suite"), dict) else None,
        "status": report.get("status"),
        "case_count": summary.get("case_count"),
        "passed_count": summary.get("passed_count"),
        "failed_count": summary.get("failed_count"),
        "blocked_case_count": summary.get("blocked_case_count"),
        "approved_case_count": summary.get("approved_case_count"),
        "needs_approval_case_count": summary.get("needs_approval_case_count"),
        "network_call_performed": runtime_policy.get("network_call_performed"),
        "llm_called": runtime_policy.get("llm_called"),
        "private_reasoning_trace_stored": runtime_policy.get("private_reasoning_trace_stored"),
        "fixture_contains_private_data": runtime_policy.get("fixture_contains_private_data"),
        "decision_model": runtime_policy.get("decision_model"),
        "case_ids": sorted(case_ids),
        "categories": sorted(categories),
        "missing_cases": missing_cases,
        "missing_categories": missing_categories,
        "failed_cases": failed_cases,
        "status_mismatches": status_mismatches,
    }
    passed = (
        details["schema"] == ACTION_POLICY_EVAL_REPORT_SCHEMA
        and details["suite_id"] == "p0_action_policy_safety_corpus_v1"
        and details["status"] == "passed"
        and isinstance(details["case_count"], int)
        and details["case_count"] >= len(REQUIRED_POLICY_EVAL_CASES)
        and details["failed_count"] == 0
        and isinstance(details["blocked_case_count"], int)
        and details["blocked_case_count"] >= 8
        and isinstance(details["approved_case_count"], int)
        and details["approved_case_count"] >= 4
        and details["needs_approval_case_count"] == 0
        and details["network_call_performed"] is False
        and details["llm_called"] is False
        and details["private_reasoning_trace_stored"] is False
        and details["fixture_contains_private_data"] is False
        and details["decision_model"] == "action_intent_capability_arguments_v3"
        and not missing_cases
        and not missing_categories
        and not failed_cases
        and not status_mismatches
    )
    return _checkpoint(passed=passed, evidence=[suite_path], root=PROJECT_ROOT, details=details)


def _public_safe_first_run_smoke() -> dict[str, Any]:
    """Verify the public no-secret first-run path without importing the CLI."""

    pyproject_path = PROJECT_ROOT / "pyproject.toml"
    cli_smoke_test_path = PROJECT_ROOT / "tests" / "test_cli_smoke.py"
    role_model_catalog_dir = PROJECT_ROOT / "apps" / "ai-talent-foundry" / "catalogs" / "role_models"
    evidence = [
        pyproject_path,
        cli_smoke_test_path,
        role_model_catalog_dir,
        PROJECT_ROOT / "src" / "ai22b" / "talent_foundry" / "role_models.py",
        PROJECT_ROOT / "src" / "ai22b" / "talent_foundry" / "llm_runtime.py",
        PROJECT_ROOT / "src" / "ai22b" / "talent_foundry" / "agent_runtime_smoke.py",
        PROJECT_ROOT / "src" / "ai22b" / "talent_foundry" / "chat_runtime_smoke.py",
        PROJECT_ROOT / "src" / "ai22b" / "talent_foundry" / "tool_registry.py",
        PROJECT_ROOT / "src" / "ai22b" / "talent_foundry" / "public_release.py",
        PROJECT_ROOT / "src" / "ai22b" / "talent_foundry" / "source_sbom.py",
        PROJECT_ROOT / "src" / "ai22b" / "talent_foundry" / "runtime_contract_doctor.py",
        DEFAULT_POLICY_EVAL_SUITE,
    ]
    missing = [path for path in evidence if not path.exists()]
    pyproject_text = pyproject_path.read_text(encoding="utf-8") if pyproject_path.exists() else ""

    role_models = [summarize_role_model(item) for item in list_role_models("securities_research")]
    role_model_ids = {str(item.get("role_model_id", "")) for item in role_models}
    doctor = doctor_llm_provider(engine="deterministic_local", live_check=False)
    application_smoke = run_llm_application_smoke(
        engine="deterministic_local",
        llm_mode="offline",
        task="Public-safe first-run application-engine smoke.",
    )
    llm_connection_profile = build_llm_connection_profile(
        llm_service="deterministic_local",
        llm_engine="deterministic_local",
        chat_surface="codex-bridge-chat",
    )
    connection_profile_public = (
        llm_connection_profile.get("public_safe", {})
        if isinstance(llm_connection_profile.get("public_safe"), dict)
        else {}
    )
    connection_profile_setup = (
        llm_connection_profile.get("setup_requirements", {})
        if isinstance(llm_connection_profile.get("setup_requirements"), dict)
        else {}
    )
    agent_runtime_smoke = run_agent_runtime_smoke(
        engine="deterministic_local",
        llm_mode="offline",
        task="Public-safe first-run full agent runtime smoke.",
    )
    agent_runtime_details = (
        agent_runtime_smoke.get("details", {})
        if isinstance(agent_runtime_smoke.get("details"), dict)
        else {}
    )
    chat_runtime_smoke = run_chat_runtime_smoke(
        engine="deterministic_local",
        llm_mode="offline",
        chat_surface="codex-bridge-chat",
        artifact_dir=PROJECT_ROOT / "runs" / "audit_chat_runtime_smoke",
        message="Public-safe first-run hired-chat smoke.",
    )
    chat_runtime_details = (
        chat_runtime_smoke.get("details", {})
        if isinstance(chat_runtime_smoke.get("details"), dict)
        else {}
    )
    chat_runtime_policy = (
        chat_runtime_smoke.get("data_policy", {})
        if isinstance(chat_runtime_smoke.get("data_policy"), dict)
        else {}
    )
    chat_runtime_surface = (
        chat_runtime_smoke.get("chat_surface", {})
        if isinstance(chat_runtime_smoke.get("chat_surface"), dict)
        else {}
    )
    tool_audit = audit_tool_capability_registry()
    tool_audit_details = tool_audit.get("details", {}) if isinstance(tool_audit.get("details"), dict) else {}
    tool_audit_public = tool_audit.get("public_safe", {}) if isinstance(tool_audit.get("public_safe"), dict) else {}
    application_runtime = (
        application_smoke.get("runtime_result", {})
        if isinstance(application_smoke.get("runtime_result"), dict)
        else {}
    )
    application_preflight = (
        application_smoke.get("preflight", {}) if isinstance(application_smoke.get("preflight"), dict) else {}
    )
    application_policy = (
        application_smoke.get("data_policy", {}) if isinstance(application_smoke.get("data_policy"), dict) else {}
    )
    smoke_contract = doctor.get("smoke_contract", {}) if isinstance(doctor.get("smoke_contract"), dict) else {}
    smoke_data_policy = (
        smoke_contract.get("data_policy", {}) if isinstance(smoke_contract.get("data_policy"), dict) else {}
    )
    smoke_retention = (
        smoke_contract.get("retention_policy", {})
        if isinstance(smoke_contract.get("retention_policy"), dict)
        else {}
    )
    policy_eval = run_action_policy_eval(suite_path=DEFAULT_POLICY_EVAL_SUITE)
    policy_runtime = (
        policy_eval.get("runtime_policy", {}) if isinstance(policy_eval.get("runtime_policy"), dict) else {}
    )
    policy_summary = policy_eval.get("summary", {}) if isinstance(policy_eval.get("summary"), dict) else {}
    source_sbom = build_source_sbom(PROJECT_ROOT)
    source_sbom_policy = source_sbom.get("policy", {}) if isinstance(source_sbom.get("policy"), dict) else {}
    source_sbom_inventory = (
        source_sbom.get("inventory", {}) if isinstance(source_sbom.get("inventory"), dict) else {}
    )
    source_sbom_release = (
        source_sbom.get("release_readiness", {})
        if isinstance(source_sbom.get("release_readiness"), dict)
        else {}
    )
    package_install_doctor = doctor_package_install(PROJECT_ROOT)
    package_install_summary = (
        package_install_doctor.get("summary", {})
        if isinstance(package_install_doctor.get("summary"), dict)
        else {}
    )
    package_install_public = (
        package_install_doctor.get("public_safe", {})
        if isinstance(package_install_doctor.get("public_safe"), dict)
        else {}
    )
    runtime_contract_doctor = doctor_runtime_contract(PROJECT_ROOT)
    runtime_contract_summary = (
        runtime_contract_doctor.get("summary", {})
        if isinstance(runtime_contract_doctor.get("summary"), dict)
        else {}
    )
    runtime_contract_public = (
        runtime_contract_doctor.get("public_safe", {})
        if isinstance(runtime_contract_doctor.get("public_safe"), dict)
        else {}
    )
    runtime_contract_artifacts = (
        runtime_contract_doctor.get("artifacts", {})
        if isinstance(runtime_contract_doctor.get("artifacts"), dict)
        else {}
    )
    runtime_live_contract = (
        runtime_contract_artifacts.get("live_agent_loop_contract", {})
        if isinstance(runtime_contract_artifacts.get("live_agent_loop_contract"), dict)
        else {}
    )
    runtime_fail_closed_contract = (
        runtime_contract_artifacts.get("fail_closed_runtime_contract", {})
        if isinstance(runtime_contract_artifacts.get("fail_closed_runtime_contract"), dict)
        else {}
    )
    console_script_present = (
        'ai22b-talent-foundry = "ai22b.talent_foundry.cli:main"' in pyproject_text
        and "[project.scripts]" in pyproject_text
    )
    optional_dependency_groups_present = all(
        f"{group} =" in pyproject_text
        for group in ('dev', 'live-llm', 'local-llm', 'rag', 'fine-tune', 'all')
    )
    cli_smoke_covers_required_commands = False
    if cli_smoke_test_path.exists():
        cli_smoke_text = cli_smoke_test_path.read_text(encoding="utf-8")
        cli_smoke_covers_required_commands = all(
            command in cli_smoke_text for command in PUBLIC_SAFE_FIRST_RUN_COMMANDS
        )

    details = {
        "schema": "paideia-public-safe-first-run-smoke/v1",
        "commands": sorted(PUBLIC_SAFE_FIRST_RUN_COMMANDS),
        "console_script_present": console_script_present,
        "optional_dependency_groups_present": optional_dependency_groups_present,
        "cli_smoke_covers_required_commands": cli_smoke_covers_required_commands,
        "role_model_domain": "securities_research",
        "role_model_count": len(role_models),
        "role_model_ids": sorted(role_model_ids),
        "graham_value_investing_present": "graham_value_investing" in role_model_ids,
        "doctor_schema": doctor.get("schema"),
        "deterministic_doctor_ready": doctor.get("engine") == "deterministic_local"
        and doctor.get("status") == "ready"
        and doctor.get("passed") is True,
        "doctor_network_access": doctor.get("network_access"),
        "doctor_live_check_requested": doctor.get("live_check_requested"),
        "doctor_secret_values_exported": doctor.get("secret_values_exported"),
        "smoke_contract_schema": smoke_contract.get("schema"),
        "smoke_contract_status": smoke_contract.get("status"),
        "smoke_provider_call_attempted": smoke_contract.get("provider_call_attempted"),
        "smoke_network_call_made": smoke_contract.get("network_call_made_by_doctor"),
        "smoke_raw_provider_text_saved": smoke_retention.get("raw_provider_text_saved"),
        "smoke_raw_provider_payload_saved": smoke_retention.get("raw_provider_payload_saved"),
        "smoke_private_reasoning_trace": smoke_data_policy.get("private_reasoning_trace"),
        "application_smoke_schema": application_smoke.get("schema"),
        "llm_connection_profile_schema": llm_connection_profile.get("schema"),
        "llm_connection_profile_status": llm_connection_profile.get("status"),
        "llm_connection_profile_selected_engine": llm_connection_profile.get("selected_llm_service", {}).get("engine")
        if isinstance(llm_connection_profile.get("selected_llm_service"), dict)
        else None,
        "llm_connection_profile_requires_live_check": connection_profile_setup.get(
            "requires_live_check_before_agent_work"
        ),
        "llm_connection_profile_network_call_performed": connection_profile_public.get("network_call_performed"),
        "llm_connection_profile_secret_values_exported": connection_profile_public.get("secret_values_exported"),
        "application_smoke_passed": application_smoke.get("passed"),
        "application_smoke_status": application_smoke.get("status"),
        "application_smoke_engine": application_smoke.get("engine"),
        "application_smoke_llm_mode": application_smoke.get("llm_mode"),
        "application_smoke_runtime_status": application_runtime.get("status"),
        "application_smoke_network_access": application_runtime.get("network_access"),
        "application_smoke_identity_policy": application_runtime.get("identity_policy"),
        "application_smoke_preflight_status": application_preflight.get("status"),
        "application_smoke_preflight_network_call": application_preflight.get("network_call_made_by_preflight"),
        "application_smoke_secret_values_exported": application_policy.get("secret_values_exported"),
        "application_smoke_raw_provider_payload_saved": application_policy.get("raw_provider_payload_saved"),
        "application_smoke_private_reasoning_trace": application_policy.get("private_reasoning_trace"),
        "agent_runtime_smoke_schema": agent_runtime_smoke.get("schema"),
        "agent_runtime_smoke_passed": agent_runtime_smoke.get("passed"),
        "agent_runtime_smoke_status": agent_runtime_smoke.get("status"),
        "agent_runtime_smoke_engine": agent_runtime_details.get("engine"),
        "agent_runtime_smoke_llm_mode": agent_runtime_details.get("llm_mode"),
        "agent_runtime_smoke_run_status": agent_runtime_details.get("run_status"),
        "agent_runtime_smoke_llm_status": agent_runtime_details.get("llm_status"),
        "agent_runtime_smoke_policy_status": agent_runtime_details.get("policy_status"),
        "agent_runtime_smoke_verification_status": agent_runtime_details.get("verification_status"),
        "agent_runtime_smoke_execution_contract_status": agent_runtime_details.get("execution_contract_status"),
        "agent_runtime_smoke_completed_tools": agent_runtime_details.get("completed_tools"),
        "agent_runtime_smoke_missing_required_tools": agent_runtime_details.get("missing_required_tools"),
        "agent_runtime_smoke_memory_decision": agent_runtime_details.get("memory_decision"),
        "agent_runtime_smoke_memory_review_candidate_schema": agent_runtime_details.get("memory_review_candidate_schema"),
        "agent_runtime_smoke_memory_auto_promotion_performed": agent_runtime_details.get(
            "memory_auto_promotion_performed"
        ),
        "agent_runtime_smoke_preflight_network_call": agent_runtime_details.get("preflight_network_call_made"),
        "agent_runtime_smoke_network_default": agent_runtime_details.get("network_default"),
        "agent_runtime_smoke_subprocess_default": agent_runtime_details.get("subprocess_default"),
        "agent_runtime_smoke_public_safe": agent_runtime_details.get("public_safe"),
        "chat_runtime_smoke_schema": chat_runtime_smoke.get("schema"),
        "chat_runtime_smoke_passed": chat_runtime_smoke.get("passed"),
        "chat_runtime_smoke_status": chat_runtime_smoke.get("status"),
        "chat_runtime_smoke_engine": chat_runtime_smoke.get("engine"),
        "chat_runtime_smoke_llm_mode": chat_runtime_smoke.get("llm_mode"),
        "chat_runtime_smoke_chat_surface_id": chat_runtime_surface.get("id"),
        "chat_runtime_smoke_chat_status": chat_runtime_details.get("chat_status"),
        "chat_runtime_smoke_reply_generation_mode": chat_runtime_details.get("reply_generation_mode"),
        "chat_runtime_smoke_conversation_intent": chat_runtime_details.get("conversation_intent"),
        "chat_runtime_smoke_llm_status": chat_runtime_details.get("llm_status"),
        "chat_runtime_smoke_preflight_status": chat_runtime_details.get("preflight_status"),
        "chat_runtime_smoke_preflight_network_call": chat_runtime_details.get("preflight_network_call_made"),
        "chat_runtime_smoke_selected_memory_count": chat_runtime_details.get("selected_memory_count"),
        "chat_runtime_smoke_trace_steps": chat_runtime_details.get("trace_steps"),
        "chat_runtime_smoke_stored_private_reasoning_trace": chat_runtime_details.get(
            "stored_private_reasoning_trace"
        ),
        "chat_runtime_smoke_learning_update_performed": chat_runtime_details.get("learning_update_performed"),
        "chat_runtime_smoke_provider_not_ready": chat_runtime_details.get("provider_not_ready"),
        "chat_runtime_smoke_secret_values_exported": chat_runtime_policy.get("secret_values_exported"),
        "chat_runtime_smoke_raw_provider_payload_saved": chat_runtime_policy.get("raw_provider_payload_saved"),
        "chat_runtime_smoke_private_reasoning_trace": chat_runtime_policy.get("private_reasoning_trace"),
        "chat_runtime_smoke_learning_auto_promotion_performed": chat_runtime_policy.get(
            "learning_auto_promotion_performed"
        ),
        "tool_capability_audit_schema": tool_audit.get("schema"),
        "tool_capability_audit_passed": tool_audit.get("passed"),
        "tool_capability_audit_status": tool_audit.get("status"),
        "tool_capability_tool_count": tool_audit_details.get("tool_count"),
        "tool_capability_missing_required_tools": tool_audit_details.get("missing_required_tools"),
        "tool_capability_scope_failure_count": tool_audit_details.get("scope_failure_count"),
        "tool_capability_denied_all_blocked": tool_audit_details.get("denied_all_blocked"),
        "tool_capability_granted_all_completed": tool_audit_details.get("granted_all_completed"),
        "tool_capability_unknown_tool_status": tool_audit_details.get("unknown_tool_status"),
        "tool_capability_network_default": tool_audit_details.get("network_default"),
        "tool_capability_subprocess_default": tool_audit_details.get("subprocess_default"),
        "tool_capability_private_reasoning_trace": tool_audit_details.get("private_reasoning_trace"),
        "tool_capability_public_safe": (
            tool_audit_public.get("network_call_performed") is False
            and tool_audit_public.get("subprocess_executed") is False
            and tool_audit_public.get("direct_arbitrary_file_read") is False
            and tool_audit_public.get("direct_arbitrary_file_write") is False
            and tool_audit_public.get("private_reasoning_trace_stored") is False
            and tool_audit_public.get("raw_provider_payload_saved") is False
        ),
        "policy_eval_schema": policy_eval.get("schema"),
        "policy_eval_status": policy_eval.get("status"),
        "policy_eval_failed_count": policy_summary.get("failed_count"),
        "policy_eval_network_call_performed": policy_runtime.get("network_call_performed"),
        "policy_eval_llm_called": policy_runtime.get("llm_called"),
        "policy_eval_private_reasoning_trace_stored": policy_runtime.get("private_reasoning_trace_stored"),
        "source_sbom_schema": source_sbom.get("schema"),
        "source_sbom_package": source_sbom.get("package", {}).get("name")
        if isinstance(source_sbom.get("package"), dict)
        else None,
        "source_sbom_component_count": source_sbom_inventory.get("component_count"),
        "source_sbom_repository_digest": source_sbom_inventory.get("repository_public_candidate_digest_sha256"),
        "source_sbom_release_readiness_passed": source_sbom_release.get("passed"),
        "source_sbom_public_candidate_issue_count": source_sbom_release.get("public_candidate_issue_count"),
        "source_sbom_network_call_performed": source_sbom_policy.get("network_call_performed"),
        "source_sbom_subprocess_executed": source_sbom_policy.get("subprocess_executed"),
        "source_sbom_private_runtime_outputs_scanned": source_sbom_policy.get("private_runtime_outputs_scanned"),
        "source_sbom_not_vulnerability_scan": source_sbom_policy.get("not_a_vulnerability_scan"),
        "package_install_doctor_schema": package_install_doctor.get("schema"),
        "package_install_doctor_passed": package_install_doctor.get("passed"),
        "package_install_doctor_status": package_install_doctor.get("status"),
        "package_install_distribution_installed": package_install_summary.get("distribution_installed"),
        "package_install_console_script_count": package_install_summary.get("console_script_count"),
        "package_install_optional_group_count": package_install_summary.get("optional_group_count"),
        "package_install_network_call_performed": package_install_public.get("network_call_performed"),
        "package_install_subprocess_executed": package_install_public.get("subprocess_executed"),
        "package_install_local_paths_exported": package_install_public.get("local_absolute_paths_exported"),
        "runtime_contract_doctor_schema": runtime_contract_doctor.get("schema"),
        "runtime_contract_doctor_passed": runtime_contract_doctor.get("passed"),
        "runtime_contract_doctor_status": runtime_contract_doctor.get("status"),
        "runtime_contract_failed_count": runtime_contract_summary.get("failed_count"),
        "runtime_contract_live_loop_status": runtime_live_contract.get("status"),
        "runtime_contract_fail_closed_status": runtime_fail_closed_contract.get("status"),
        "runtime_contract_network_call_performed": runtime_contract_public.get("network_call_performed"),
        "runtime_contract_subprocess_executed": runtime_contract_public.get("subprocess_executed"),
        "runtime_contract_live_provider_called": runtime_contract_public.get("live_provider_called"),
        "runtime_contract_secret_values_exported": runtime_contract_public.get("secret_values_exported"),
        "no_network_or_llm_by_default": (
            doctor.get("network_access") == "blocked"
            and doctor.get("live_check_requested") is False
            and smoke_contract.get("provider_call_attempted") is False
            and smoke_contract.get("network_call_made_by_doctor") is False
            and connection_profile_public.get("network_call_performed") is False
            and connection_profile_public.get("secret_values_exported") is False
            and application_runtime.get("network_access") == "blocked"
            and application_preflight.get("network_call_made_by_preflight") is False
            and agent_runtime_details.get("preflight_network_call_made") is False
            and chat_runtime_details.get("preflight_network_call_made") is False
            and chat_runtime_policy.get("secret_values_exported") is False
            and agent_runtime_details.get("network_default") == "blocked"
            and agent_runtime_details.get("subprocess_default") == "blocked"
            and tool_audit_public.get("network_call_performed") is False
            and tool_audit_public.get("subprocess_executed") is False
            and policy_runtime.get("network_call_performed") is False
            and policy_runtime.get("llm_called") is False
            and source_sbom_policy.get("network_call_performed") is False
            and source_sbom_policy.get("subprocess_executed") is False
            and package_install_public.get("network_call_performed") is False
            and package_install_public.get("subprocess_executed") is False
            and runtime_contract_public.get("network_call_performed") is False
            and runtime_contract_public.get("subprocess_executed") is False
            and runtime_contract_public.get("live_provider_called") is False
        ),
    }
    passed = (
        not missing
        and details["console_script_present"] is True
        and details["optional_dependency_groups_present"] is True
        and details["cli_smoke_covers_required_commands"] is True
        and details["graham_value_investing_present"] is True
        and details["deterministic_doctor_ready"] is True
        and details["doctor_secret_values_exported"] is False
        and details["smoke_contract_schema"] == LLM_PROVIDER_SMOKE_CONTRACT_SCHEMA
        and details["smoke_contract_status"] == "skipped"
        and details["smoke_raw_provider_text_saved"] is False
        and details["smoke_raw_provider_payload_saved"] is False
        and details["smoke_private_reasoning_trace"] == "do_not_store"
        and details["llm_connection_profile_schema"] == "paideia-llm-connection-profile/v1"
        and details["llm_connection_profile_status"] == "offline_ready_no_setup"
        and details["llm_connection_profile_selected_engine"] == "deterministic_local"
        and details["llm_connection_profile_requires_live_check"] is False
        and details["llm_connection_profile_network_call_performed"] is False
        and details["llm_connection_profile_secret_values_exported"] is False
        and details["application_smoke_schema"] == LLM_APPLICATION_SMOKE_SCHEMA
        and details["application_smoke_passed"] is True
        and details["application_smoke_status"] == "passed"
        and details["application_smoke_engine"] == "deterministic_local"
        and details["application_smoke_llm_mode"] == "offline"
        and details["application_smoke_runtime_status"] == "completed"
        and details["application_smoke_network_access"] == "blocked"
        and details["application_smoke_identity_policy"] == "application_engine_not_identity"
        and details["application_smoke_preflight_network_call"] is False
        and details["application_smoke_secret_values_exported"] is False
        and details["application_smoke_raw_provider_payload_saved"] is False
        and details["application_smoke_private_reasoning_trace"] == "do_not_store"
        and details["agent_runtime_smoke_schema"] == AGENT_RUNTIME_SMOKE_SCHEMA
        and details["agent_runtime_smoke_passed"] is True
        and details["agent_runtime_smoke_status"] == "passed"
        and details["agent_runtime_smoke_engine"] == "deterministic_local"
        and details["agent_runtime_smoke_llm_mode"] == "offline"
        and details["agent_runtime_smoke_run_status"] == "completed"
        and details["agent_runtime_smoke_llm_status"] == "completed"
        and details["agent_runtime_smoke_policy_status"] == "approved"
        and details["agent_runtime_smoke_verification_status"] == "passed"
        and details["agent_runtime_smoke_execution_contract_status"] == "passed"
        and isinstance(details["agent_runtime_smoke_completed_tools"], list)
        and "evidence_packet" in details["agent_runtime_smoke_completed_tools"]
        and details["agent_runtime_smoke_missing_required_tools"] == []
        and details["agent_runtime_smoke_memory_decision"] == "candidate_pending_boss_review"
        and details["agent_runtime_smoke_memory_review_candidate_schema"] == MEMORY_REVIEW_CANDIDATE_SCHEMA
        and details["agent_runtime_smoke_memory_auto_promotion_performed"] is False
        and details["agent_runtime_smoke_preflight_network_call"] is False
        and details["agent_runtime_smoke_network_default"] == "blocked"
        and details["agent_runtime_smoke_subprocess_default"] == "blocked"
        and details["agent_runtime_smoke_public_safe"] is True
        and details["chat_runtime_smoke_schema"] == CHAT_RUNTIME_SMOKE_SCHEMA
        and details["chat_runtime_smoke_passed"] is True
        and details["chat_runtime_smoke_status"] == "passed"
        and details["chat_runtime_smoke_engine"] == "deterministic_local"
        and details["chat_runtime_smoke_llm_mode"] == "offline"
        and details["chat_runtime_smoke_chat_surface_id"] == "codex-bridge-chat"
        and details["chat_runtime_smoke_chat_status"] == "completed"
        and details["chat_runtime_smoke_llm_status"] == "completed"
        and details["chat_runtime_smoke_preflight_network_call"] is False
        and isinstance(details["chat_runtime_smoke_selected_memory_count"], int)
        and details["chat_runtime_smoke_stored_private_reasoning_trace"] is False
        and details["chat_runtime_smoke_learning_update_performed"] is False
        and details["chat_runtime_smoke_provider_not_ready"] is False
        and details["chat_runtime_smoke_secret_values_exported"] is False
        and details["chat_runtime_smoke_raw_provider_payload_saved"] is False
        and details["chat_runtime_smoke_private_reasoning_trace"] == "do_not_store"
        and details["chat_runtime_smoke_learning_auto_promotion_performed"] is False
        and details["tool_capability_audit_schema"] == TOOL_CAPABILITY_AUDIT_SCHEMA
        and details["tool_capability_audit_passed"] is True
        and details["tool_capability_audit_status"] == "passed"
        and isinstance(details["tool_capability_tool_count"], int)
        and details["tool_capability_tool_count"] >= 7
        and details["tool_capability_missing_required_tools"] == []
        and details["tool_capability_scope_failure_count"] == 0
        and details["tool_capability_denied_all_blocked"] is True
        and details["tool_capability_granted_all_completed"] is True
        and details["tool_capability_unknown_tool_status"] == "skipped"
        and details["tool_capability_network_default"] == "blocked"
        and details["tool_capability_subprocess_default"] == "blocked"
        and details["tool_capability_private_reasoning_trace"] == "do_not_store"
        and details["tool_capability_public_safe"] is True
        and details["policy_eval_schema"] == ACTION_POLICY_EVAL_REPORT_SCHEMA
        and details["policy_eval_status"] == "passed"
        and details["policy_eval_failed_count"] == 0
        and details["policy_eval_private_reasoning_trace_stored"] is False
        and details["source_sbom_schema"] == SOURCE_SBOM_SCHEMA
        and details["source_sbom_package"] == "paideia-agent"
        and isinstance(details["source_sbom_component_count"], int)
        and details["source_sbom_component_count"] > 20
        and isinstance(details["source_sbom_repository_digest"], str)
        and len(details["source_sbom_repository_digest"]) == 64
        and details["source_sbom_release_readiness_passed"] is True
        and details["source_sbom_public_candidate_issue_count"] == 0
        and details["source_sbom_network_call_performed"] is False
        and details["source_sbom_subprocess_executed"] is False
        and details["source_sbom_private_runtime_outputs_scanned"] is False
        and details["source_sbom_not_vulnerability_scan"] is True
        and details["package_install_doctor_schema"] == PACKAGE_INSTALL_DOCTOR_SCHEMA
        and details["package_install_doctor_passed"] is True
        and details["package_install_doctor_status"] == "passed"
        and details["package_install_distribution_installed"] is True
        and isinstance(details["package_install_console_script_count"], int)
        and details["package_install_console_script_count"] >= 3
        and isinstance(details["package_install_optional_group_count"], int)
        and details["package_install_optional_group_count"] >= 6
        and details["package_install_network_call_performed"] is False
        and details["package_install_subprocess_executed"] is False
        and details["package_install_local_paths_exported"] is False
        and details["runtime_contract_doctor_schema"] == RUNTIME_CONTRACT_DOCTOR_SCHEMA
        and details["runtime_contract_doctor_passed"] is True
        and details["runtime_contract_doctor_status"] == "passed"
        and details["runtime_contract_failed_count"] == 0
        and details["runtime_contract_live_loop_status"] == "passed"
        and details["runtime_contract_fail_closed_status"] == "passed"
        and details["runtime_contract_network_call_performed"] is False
        and details["runtime_contract_subprocess_executed"] is False
        and details["runtime_contract_live_provider_called"] is False
        and details["runtime_contract_secret_values_exported"] is False
        and details["no_network_or_llm_by_default"] is True
    )
    return _checkpoint(
        passed=passed,
        evidence=evidence,
        root=PROJECT_ROOT,
        details=details,
        missing=missing,
    )


def _llm_live_agent_loop_contract() -> dict[str, Any]:
    """Exercise the live LLM client path through the agent loop without network access."""

    contract = run_live_agent_loop_contract()
    return _checkpoint(
        passed=contract.get("passed") is True,
        evidence=[
            PROJECT_ROOT / "src" / "ai22b" / "talent_foundry" / "agent_execution_loop.py",
            PROJECT_ROOT / "src" / "ai22b" / "talent_foundry" / "llm_clients.py",
            PROJECT_ROOT / "src" / "ai22b" / "talent_foundry" / "tool_registry.py",
            PROJECT_ROOT / "src" / "ai22b" / "talent_foundry" / "runtime_contract_doctor.py",
        ],
        root=PROJECT_ROOT,
        details=contract.get("details", {}),
    )

    secret = "fixture_audit_live_llm_secret_12345"
    hidden_trace = "audit hidden provider trace must not be stored"

    class PublicSafeLiveContractClient:
        def generate(self, messages, *, tools=None, policy=None):
            return {
                "schema": "paideia-llm-client-result/v1",
                "engine": "audit_fake_live_llm",
                "status": "completed",
                "model": "audit-fake-live-model",
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
            "role": "local release audit fixture",
            "major_goal": "Verify live LLM execution stays bounded by Paideia policy.",
        },
        "memory_profile": {
            "procedural_principles": [
                "Check policy before LLM planning.",
                "Use registered tools as the only execution authority.",
            ],
            "semantic_themes": ["live LLM contract", "public-safe release audit"],
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
        model="paideia-audit-live-contract-model",
    )
    run = run_agent_from_manifest(
        manifest,
        task="Prepare a public-safe release audit evidence plan.",
        runtime_config=runtime_config,
        llm_mode="live",
        llm_client=PublicSafeLiveContractClient(),
    )
    llm_result = run.get("llm_runtime_result", {}) if isinstance(run.get("llm_runtime_result"), dict) else {}
    client_result = llm_result.get("client_result", {}) if isinstance(llm_result.get("client_result"), dict) else {}
    llm_client_contract = (
        llm_result.get("llm_client_contract", {})
        if isinstance(llm_result.get("llm_client_contract"), dict)
        else {}
    )
    llm_plan = llm_result.get("llm_plan", {}) if isinstance(llm_result.get("llm_plan"), dict) else {}
    execution_contract = (
        run.get("execution_contract", {}) if isinstance(run.get("execution_contract"), dict) else {}
    )
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
    serialized = json.dumps(run, ensure_ascii=False)
    completed_tools = [
        str(item.get("tool"))
        for item in tool_execution.get("tool_results", [])
        if isinstance(item, dict) and item.get("status") == "completed"
    ]
    details = {
        "schema": "paideia-live-agent-loop-contract/v1",
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
        "llm_client_contract_schema": llm_client_contract.get("schema"),
        "llm_client_contract_status": llm_client_contract.get("status"),
        "llm_client_contract_summary_only": llm_client_contract.get("client_result_summary_only"),
        "llm_client_contract_raw_payload_saved": llm_client_contract.get("raw_provider_payload_saved"),
        "llm_client_contract_private_reasoning_values_stored": llm_client_contract.get(
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
        and details["llm_client_contract_schema"] == "paideia-llm-client-contract/v1"
        and details["llm_client_contract_status"] == "passed"
        and details["llm_client_contract_summary_only"] is True
        and details["llm_client_contract_raw_payload_saved"] is False
        and details["llm_client_contract_private_reasoning_values_stored"] is False
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
    return _checkpoint(
        passed=passed,
        evidence=[
            PROJECT_ROOT / "src" / "ai22b" / "talent_foundry" / "agent_execution_loop.py",
            PROJECT_ROOT / "src" / "ai22b" / "talent_foundry" / "llm_clients.py",
            PROJECT_ROOT / "src" / "ai22b" / "talent_foundry" / "tool_registry.py",
        ],
        root=PROJECT_ROOT,
        details=details,
    )


def _write_fail_closed_runtime_fixture(root: Path) -> tuple[Path, dict[str, Any], dict[str, Any]]:
    agent = {
        "name": "paideia-audit-fail-closed-agent",
        "role": "public-safe release audit fixture",
        "major_goal": "Prove live provider configuration is required before execution.",
        "birth": {
            "datetime": "audit-fixture",
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
        model="openrouter/audit-provider-missing-model",
        service="openrouter_api",
    )
    employment_record = {
        "schema": "ai-talent-local-employment/v1",
        "employment_id": "audit-fail-closed-employment",
        "hired_at_utc": datetime.now(timezone.utc).isoformat(),
        "employer": "보스",
        "relationship": "installed_ai_talent_hired_as_local_agent",
        "install_id": "audit-fail-closed-install",
        "agent": {
            "name": agent["name"],
            "role": "provider readiness audit agent",
            "major_goal": agent["major_goal"],
        },
        "source": {
            "installed_manifest": "audit_fixture",
            "agent_manifest": "agent_manifest.json",
            "source_archive": "audit_fixture",
            "source_sha256": "audit_fixture",
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
            "selected_model": "openrouter/audit-provider-missing-model",
            "status": "requires_configuration",
        },
        "chat_surface": {
            "id": "cli-console",
            "label": "Paideia guided CLI console",
        },
        "llm_runtime": runtime_config,
        "growth_after_hire": {
            "continues": True,
            "principle": "고용 후 실행도 provider readiness, policy, verification, review gate를 통과해야 한다.",
            "record_policy": "미설정 provider 경로는 업무 경험이나 학습 승격으로 기록하지 않는다.",
        },
        "llm_policy": agent_manifest["llm_policy"],
        "status": "active",
    }
    _write_json(root / "agent_manifest.json", agent_manifest)
    _write_json(root / "learning_ledger.json", ledger)
    employment_record_path = root / "employment_record.openrouter_missing.json"
    _write_json(employment_record_path, employment_record)
    return employment_record_path, agent_manifest, ledger


def _fail_closed_runtime_contract() -> dict[str, Any]:
    """Prove unconfigured explicit-live runs stop before tools, artifacts, and learning promotion."""

    contract = run_fail_closed_runtime_contract()
    return _checkpoint(
        passed=contract.get("passed") is True,
        evidence=[
            PROJECT_ROOT / "src" / "ai22b" / "talent_foundry" / "agent_execution_loop.py",
            PROJECT_ROOT / "src" / "ai22b" / "talent_foundry" / "workspace_agent.py",
            PROJECT_ROOT / "src" / "ai22b" / "talent_foundry" / "registry.py",
            PROJECT_ROOT / "src" / "ai22b" / "talent_foundry" / "memory_substrate.py",
            PROJECT_ROOT / "src" / "ai22b" / "talent_foundry" / "runtime_contract_doctor.py",
        ],
        root=PROJECT_ROOT,
        details=contract.get("details", {}),
    )

    from ai22b.talent_foundry.memory_substrate import run_chat_turn_from_employment
    from ai22b.talent_foundry.registry import (
        run_hired_agent_job,
        run_hired_dataflow_job,
        run_hired_workspace_agent,
    )

    evidence = [
        PROJECT_ROOT / "src" / "ai22b" / "talent_foundry" / "agent_execution_loop.py",
        PROJECT_ROOT / "src" / "ai22b" / "talent_foundry" / "workspace_agent.py",
        PROJECT_ROOT / "src" / "ai22b" / "talent_foundry" / "registry.py",
        PROJECT_ROOT / "src" / "ai22b" / "talent_foundry" / "memory_substrate.py",
    ]
    model = "openrouter/audit-provider-missing-model"
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
                review_label={"score": 90, "status": "verified", "reviewed_by": "release-audit"},
                output_path=tmp_root / "dataflow_run.json",
                llm_mode="live",
                llm_model=model,
            )
            chat_run = run_chat_turn_from_employment(
                employment_record_path,
                message="live provider로 자연스럽게 대화해줘.",
                output_path=tmp_root / "chat_run.json",
                llm_mode="live",
                llm_model=model,
                learn_from_chat=True,
            )
            ledger_after = _read_json(fixture_root / "learning_ledger.json")
    except Exception as exc:
        return _checkpoint(
            passed=False,
            evidence=evidence,
            root=PROJECT_ROOT,
            details={
                "schema": "paideia-fail-closed-runtime-contract/v1",
                "status": "audit_fixture_error",
                "error_type": type(exc).__name__,
            },
        )
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
        "schema": "paideia-fail-closed-runtime-contract/v1",
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
    return _checkpoint(passed=passed, evidence=evidence, root=PROJECT_ROOT, details=details)


def _provider_audit_model(engine: str) -> str | None:
    if engine in {
        "anthropic_claude_api",
        "google_gemini_api",
        "mistral_api",
        "openrouter_api",
        "ollama_local_http",
        "lm_studio_local_http",
    }:
        return "paideia-audit-model"
    return None


def _llm_provider_readiness() -> dict[str, Any]:
    services = [item for item in LLM_SERVICE_CATALOG if isinstance(item, dict)]
    service_ids = {str(item.get("id", "")) for item in services}
    missing_services = sorted(REQUIRED_LLM_SERVICE_IDS - service_ids)
    duplicate_services = sorted(
        service_id
        for service_id in service_ids
        if service_id and sum(1 for item in services if item.get("id") == service_id) > 1
    )

    service_reports: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    for item in services:
        service_id = str(item.get("id", ""))
        engine = str(item.get("engine", ""))
        if not service_id or not engine:
            failures.append({"id": "llm_service_missing_identity", "service_id": service_id, "engine": engine})
            continue

        model = _provider_audit_model(engine)
        try:
            runtime_config = build_llm_runtime_config(
                engine=engine,
                model=model,
                model_path=None,
                service=service_id,
            )
            doctor = doctor_llm_provider(
                engine=engine,
                model=model,
                service=service_id,
                live_check=False,
            )
            preflight = build_llm_provider_preflight(
                runtime_config,
                llm_mode="auto",
                llm_model=model,
            )
        except (OSError, ValueError) as exc:
            failures.append(
                {
                    "id": "llm_provider_readiness_failed_to_build",
                    "service_id": service_id,
                    "engine": engine,
                    "error": type(exc).__name__,
                }
            )
            continue

        doctor_card = item.get("doctor", {}) if isinstance(item.get("doctor"), dict) else {}
        live_check_policy = (
            item.get("live_check_policy", {}) if isinstance(item.get("live_check_policy"), dict) else {}
        )
        data_transfer_policy = (
            item.get("data_transfer_policy", {}) if isinstance(item.get("data_transfer_policy"), dict) else {}
        )
        smoke_contract = doctor.get("smoke_contract", {}) if isinstance(doctor.get("smoke_contract"), dict) else {}
        smoke_retention = (
            smoke_contract.get("retention_policy", {})
            if isinstance(smoke_contract.get("retention_policy"), dict)
            else {}
        )
        smoke_data_policy = (
            smoke_contract.get("data_policy", {}) if isinstance(smoke_contract.get("data_policy"), dict) else {}
        )
        preflight_policy = (
            preflight.get("data_policy", {}) if isinstance(preflight.get("data_policy"), dict) else {}
        )

        service_failures: list[str] = []
        if not item.get("runtime_readiness"):
            service_failures.append("runtime_readiness_missing")
        if "doctor-llm-provider" not in str(doctor_card.get("command", "")):
            service_failures.append("doctor_command_missing")
        if "--live-check" not in str(doctor_card.get("live_check_command", "")):
            service_failures.append("live_check_command_missing_explicit_flag")
        if doctor_card.get("live_check_default") is not False:
            service_failures.append("doctor_live_check_default_not_false")
        if doctor_card.get("secret_values_exported") is not False:
            service_failures.append("doctor_card_secret_export_policy_invalid")
        if live_check_policy.get("requires_explicit_flag") is not True:
            service_failures.append("live_check_policy_requires_explicit_flag_missing")
        if live_check_policy.get("network_call_made_by_default") is not False:
            service_failures.append("live_check_policy_network_default_invalid")
        if not data_transfer_policy.get("network_access"):
            service_failures.append("data_transfer_network_access_missing")
        if doctor.get("schema") != LLM_PROVIDER_DOCTOR_SCHEMA:
            service_failures.append("doctor_schema_invalid")
        if doctor.get("secret_values_exported") is not False:
            service_failures.append("doctor_secret_export_policy_invalid")
        if smoke_contract.get("schema") != LLM_PROVIDER_SMOKE_CONTRACT_SCHEMA:
            service_failures.append("smoke_contract_schema_invalid")
        if smoke_contract.get("live_check_requested") is not False:
            service_failures.append("smoke_contract_live_check_requested")
        if smoke_contract.get("live_check_performed") is not False:
            service_failures.append("smoke_contract_live_check_performed")
        if smoke_contract.get("provider_call_attempted") is not False:
            service_failures.append("smoke_contract_provider_call_attempted")
        if smoke_contract.get("network_call_made_by_doctor") is not False:
            service_failures.append("smoke_contract_network_call_made")
        if smoke_retention.get("raw_provider_text_saved") is not False:
            service_failures.append("smoke_retention_raw_provider_text_saved")
        if smoke_retention.get("raw_provider_payload_saved") is not False:
            service_failures.append("smoke_retention_raw_provider_payload_saved")
        if smoke_retention.get("hidden_reasoning_saved") is not False:
            service_failures.append("smoke_retention_hidden_reasoning_saved")
        if smoke_data_policy.get("secret_values_exported") is not False:
            service_failures.append("smoke_data_policy_secret_export_invalid")
        if smoke_data_policy.get("private_reasoning_trace") != "do_not_store":
            service_failures.append("smoke_data_policy_private_reasoning_invalid")
        if preflight.get("schema") != LLM_PROVIDER_PREFLIGHT_SCHEMA:
            service_failures.append("preflight_schema_invalid")
        if preflight.get("live_check_performed") is not False:
            service_failures.append("preflight_live_check_performed")
        if preflight.get("live_check_requires_explicit_flag") is not True:
            service_failures.append("preflight_explicit_live_check_flag_missing")
        if preflight.get("network_call_made_by_preflight") is not False:
            service_failures.append("preflight_network_call_made")
        if preflight_policy.get("secret_values_exported") is not False:
            service_failures.append("preflight_secret_export_policy_invalid")
        if preflight_policy.get("private_reasoning_trace") != "do_not_store":
            service_failures.append("preflight_private_reasoning_policy_invalid")
        if engine == "deterministic_local" and doctor.get("status") != "ready":
            service_failures.append("deterministic_provider_not_ready")

        if service_failures:
            failures.append(
                {
                    "id": "llm_service_readiness_contract_failed",
                    "service_id": service_id,
                    "engine": engine,
                    "failures": service_failures,
                }
            )

        service_reports.append(
            {
                "service_id": service_id,
                "engine": engine,
                "catalog_status": item.get("status"),
                "runtime_readiness": item.get("runtime_readiness"),
                "doctor_status": doctor.get("status"),
                "doctor_passed": doctor.get("passed"),
                "preflight_status": preflight.get("status"),
                "network_access": runtime_config.get("network_access"),
                "catalog_network_access": data_transfer_policy.get("network_access"),
                "live_check_default": doctor_card.get("live_check_default"),
                "live_check_requires_explicit_flag": live_check_policy.get("requires_explicit_flag"),
                "network_call_made_by_default": live_check_policy.get("network_call_made_by_default"),
                "doctor_network_call_made": smoke_contract.get("network_call_made_by_doctor"),
                "preflight_network_call_made": preflight.get("network_call_made_by_preflight"),
                "secret_values_exported": doctor.get("secret_values_exported"),
                "blocking_check_count": len(preflight.get("blocking_checks", [])),
            }
        )

    if missing_services:
        failures.append({"id": "llm_required_services_missing", "missing_services": missing_services})
    if duplicate_services:
        failures.append({"id": "llm_duplicate_services", "duplicate_services": duplicate_services})

    details = {
        "service_count": len(services),
        "required_service_count": len(REQUIRED_LLM_SERVICE_IDS),
        "service_ids": sorted(service_ids),
        "missing_services": missing_services,
        "duplicate_services": duplicate_services,
        "all_required_services_present": not missing_services,
        "all_live_checks_require_explicit_flag": all(
            item.get("live_check_requires_explicit_flag") is True for item in service_reports
        ),
        "all_doctor_and_preflight_no_network_by_default": all(
            item.get("doctor_network_call_made") is False and item.get("preflight_network_call_made") is False
            for item in service_reports
        ),
        "all_secret_values_unexported": all(item.get("secret_values_exported") is False for item in service_reports),
        "deterministic_local_ready": any(
            item.get("engine") == "deterministic_local" and item.get("doctor_status") == "ready"
            for item in service_reports
        ),
        "external_or_local_providers_configuration_gated": all(
            item.get("live_check_requires_explicit_flag") is True
            and item.get("network_call_made_by_default") is False
            for item in service_reports
            if item.get("engine") != "deterministic_local"
        ),
        "service_reports": service_reports,
        "failure_count": len(failures),
        "failures": failures,
    }
    passed = (
        len(services) >= len(REQUIRED_LLM_SERVICE_IDS)
        and details["all_required_services_present"] is True
        and details["all_live_checks_require_explicit_flag"] is True
        and details["all_doctor_and_preflight_no_network_by_default"] is True
        and details["all_secret_values_unexported"] is True
        and details["deterministic_local_ready"] is True
        and details["external_or_local_providers_configuration_gated"] is True
        and not failures
    )
    return _checkpoint(
        passed=passed,
        evidence=[
            PROJECT_ROOT / "src" / "ai22b" / "talent_foundry" / "onboarding_choices.py",
            PROJECT_ROOT / "src" / "ai22b" / "talent_foundry" / "llm_runtime.py",
        ],
        root=PROJECT_ROOT,
        details=details,
    )


def _growth_governance(run_dir: Path) -> dict[str, Any]:
    paths = {
        "blueprint": run_dir / "shinyong_training_blueprint.json",
        "institutional_review": run_dir / "shinyong_institutional_review.json",
        "doctoral_assessment": run_dir / "shinyong_doctoral_assessment.json",
        "learning_ledger": run_dir / "shinyong_learning_ledger.json",
        "active_memory_route": run_dir / "shinyong_active_memory_route.json",
    }
    missing = [path for path in paths.values() if not path.exists()]
    details: dict[str, Any] = {}
    passed = not missing
    if passed:
        review = _read_json(paths["institutional_review"])
        assessment = _read_json(paths["doctoral_assessment"])
        ledger = _read_json(paths["learning_ledger"])
        active_memory_route = _read_json(paths["active_memory_route"])
        completed_gates = set(review.get("assessment_transcript", {}).get("completed_major_gates", []))
        details = {
            "education_committee_status": review.get("education_committee_decision", {}).get("status"),
            "oversight_status": review.get("oversight_committee_decision", {}).get("status"),
            "graduation_ready": review.get("assessment_transcript", {}).get("graduation_ready"),
            "completed_major_gates": sorted(completed_gates),
            "doctoral_defense_passed": assessment.get("gate_id") == "doctoral_defense" and assessment.get("passed"),
            "reasoning_kernel": ledger.get("reasoning_kernel", {}).get("schema"),
            "private_reasoning_trace": ledger.get("reasoning_kernel", {}).get("private_reasoning_trace"),
            "active_memory_route_schema": active_memory_route.get("schema"),
            "active_memory_route_budget": active_memory_route.get("routing_policy", {}).get("active_context_budget"),
            "active_memory_selected_count": active_memory_route.get("memory_health", {}).get("selected_experience_count"),
            "active_memory_quarantine_policy": active_memory_route.get("routing_policy", {}).get("quarantined_experiences"),
        }
        passed = (
            details["education_committee_status"] == "major_track_passed"
            and details["oversight_status"] == "employment_ready_with_guardrails"
            and details["graduation_ready"] is True
            and REQUIRED_MAJOR_GATES <= completed_gates
            and details["doctoral_defense_passed"] is True
            and details["reasoning_kernel"] == "ai-talent-reasoning-kernel/v1"
            and details["private_reasoning_trace"] == "do_not_store"
            and details["active_memory_route_schema"] == "ai-talent-active-memory-route/v1"
            and details["active_memory_route_budget"] == "bounded"
            and isinstance(details["active_memory_selected_count"], int)
            and details["active_memory_selected_count"] > 0
            and details["active_memory_quarantine_policy"] == "excluded"
        )
    return _checkpoint(passed=passed, evidence=list(paths.values()), root=run_dir, details=details, missing=missing)


def _public_program_manifest(run_dir: Path) -> dict[str, Any]:
    manifest_path = run_dir / "ai_talent_foundry_public_manifest.json"
    if not manifest_path.exists():
        return _checkpoint(
            passed=False,
            evidence=[manifest_path],
            root=run_dir,
            missing=[manifest_path],
            details={},
        )

    manifest = _read_json(manifest_path)
    commands = {str(command.get("id", "")) for command in manifest.get("commands", [])}
    lifecycle = {str(step.get("id", "")) for step in manifest.get("employment_lifecycle", [])}
    roles = set(manifest.get("institutional_model", {}).get("required_roles", []))
    details = {
        "schema": manifest.get("schema"),
        "release_stage": manifest.get("distribution_model", {}).get("release_stage"),
        "local_first": manifest.get("distribution_model", {}).get("local_first"),
        "private_data_upload": manifest.get("privacy", {}).get("private_data_upload"),
        "commands": sorted(commands),
        "missing_commands": sorted(REQUIRED_PUBLIC_PROGRAM_COMMANDS - commands),
        "lifecycle": sorted(lifecycle),
        "missing_lifecycle_steps": sorted(REQUIRED_PUBLIC_PROGRAM_LIFECYCLE - lifecycle),
        "required_roles": sorted(roles),
        "missing_roles": sorted(REQUIRED_PUBLIC_PROGRAM_ROLES - roles),
        "not_separate_consciousnesses": manifest.get("projection_model", {}).get("not_separate_consciousnesses"),
        "separate_employment_records": manifest.get("projection_model", {}).get("separate_employment_records"),
        "family_child_blueprint": manifest.get("family_lineage_model", {}).get("child_blueprint"),
        "family_biological_claim": manifest.get("family_lineage_model", {}).get("biological_claim"),
        "source_count": manifest.get("research_foundation", {}).get("source_count"),
        "expected_audit": manifest.get("release_evidence", {}).get("expected_audit"),
    }
    passed = (
        details["schema"] == "ai-talent-foundry-public-program-manifest/v1"
        and details["release_stage"] == "local_public_preview"
        and details["local_first"] is True
        and details["private_data_upload"] == "forbidden"
        and not details["missing_commands"]
        and not details["missing_lifecycle_steps"]
        and not details["missing_roles"]
        and details["not_separate_consciousnesses"] is True
        and details["separate_employment_records"] is False
        and details["family_child_blueprint"] == "family_seed_to_training_blueprint"
        and details["family_biological_claim"] == "not_claimed"
        and isinstance(details["source_count"], int)
        and details["source_count"] >= 8
        and details["expected_audit"] == "foundry_release_audit.json"
    )
    return _checkpoint(passed=passed, evidence=[manifest_path], root=run_dir, details=details)


def _family_lineage(run_dir: Path) -> dict[str, Any]:
    family_path = run_dir / "shinyong_family_lineage.json"
    if not family_path.exists():
        return _checkpoint(
            passed=False,
            evidence=[family_path],
            root=run_dir,
            missing=[family_path],
            details={},
        )

    family = _read_json(family_path)
    union = family.get("family_union", {})
    child_seed = family.get("child_seed", {})
    child_blueprint = family.get("child_training_blueprint", {})
    lineage_context = child_blueprint.get("family_lineage_context", {})
    stage_ids = {str(stage.get("id", "")) for stage in child_blueprint.get("training_pipeline", [])}
    details = {
        "union_type": union.get("union_type"),
        "biological_claim": union.get("safety", {}).get("biological_claim"),
        "child_seed_status": child_seed.get("status"),
        "child_name": child_seed.get("talent", {}).get("name"),
        "child_blueprint_schema": child_blueprint.get("schema"),
        "child_blueprint_relationship": child_blueprint.get("identity", {}).get("relationship"),
        "child_blueprint_parents": lineage_context.get("parents", []),
        "inherited_influence_count": len(lineage_context.get("inherited_reasoning_influences", [])),
        "parental_home_education_stage": "parental_home_education" in stage_ids,
        "llm_identity_policy": child_blueprint.get("llm_policy", {}).get("role"),
    }
    passed = (
        details["union_type"] == "ai_family_lineage"
        and details["biological_claim"] == "not_claimed"
        and details["child_seed_status"] == "child_ai_seed_ready"
        and details["child_blueprint_schema"] == "ai-talent-training-blueprint/v1"
        and details["child_blueprint_relationship"] == "family_lineage_child_ai_talent"
        and len(details["child_blueprint_parents"]) == 2
        and details["inherited_influence_count"] == 2
        and details["parental_home_education_stage"] is True
        and details["llm_identity_policy"] == "application_engine_not_identity"
    )
    return _checkpoint(passed=passed, evidence=[family_path], root=run_dir, details=details)


def _public_distribution(run_dir: Path, installed_root: Path) -> dict[str, Any]:
    bundle_dir = run_dir / "shinyong_agent_release_bundle"
    archive = run_dir / "shinyong_agent_release_bundle.zip"
    package_manifest_path = run_dir / "shinyong_agent_release_bundle.package_manifest.json"
    installed_manifest_path = installed_root / "installed_agent_manifest.json"
    required = [bundle_dir, archive, package_manifest_path, installed_manifest_path]
    missing = [path for path in required if not path.exists()]
    details: dict[str, Any] = {}
    passed = not missing
    if passed:
        package_manifest = _read_json(package_manifest_path)
        installed_manifest = _read_json(installed_manifest_path)
        bundle_verification = verify_agent_release_bundle(bundle_dir)
        archive_verification = verify_agent_release_archive(archive, expected_sha256=package_manifest.get("sha256"))
        details = {
            "package_schema": package_manifest.get("schema"),
            "package_public_distribution_ready": package_manifest.get("public_distribution_ready"),
            "bundle_verification_passed": bundle_verification.get("passed"),
            "archive_verification_passed": archive_verification.get("passed"),
            "installed_archive_verification_passed": installed_manifest.get("archive_verification", {}).get("passed"),
            "forbidden_file_hits": bundle_verification.get("forbidden_file_hits", []),
            "forbidden_content_hits": bundle_verification.get("forbidden_content_hits", []),
        }
        passed = (
            details["package_schema"] == "ai-talent-release-package/v1"
            and details["package_public_distribution_ready"] is True
            and details["bundle_verification_passed"] is True
            and details["archive_verification_passed"] is True
            and details["installed_archive_verification_passed"] is True
            and not details["forbidden_file_hits"]
            and not details["forbidden_content_hits"]
        )
    return _checkpoint(passed=passed, evidence=required, root=run_dir, details=details, missing=missing)


def _local_employment(installed_root: Path, run_dir: Path) -> dict[str, Any]:
    paths = {
        "employment_record": installed_root / "employment_record.json",
        "hired_agent_run": installed_root / "last_hired_agent_run.json",
        "hired_workspace_run": installed_root / "last_hired_workspace_agent_run.json",
    }
    missing = [path for path in paths.values() if not path.exists()]
    details: dict[str, Any] = {}
    passed = not missing
    if passed:
        employment = _read_json(paths["employment_record"])
        agent_run = _read_json(paths["hired_agent_run"])
        workspace_run = _read_json(paths["hired_workspace_run"])
        agent_p0 = _agent_p0_runtime_details(agent_run)
        workspace_p0 = _agent_p0_runtime_details(workspace_run)
        details = {
            "employment_schema": employment.get("schema"),
            "employment_status": employment.get("status"),
            "growth_after_hire_continues": employment.get("growth_after_hire", {}).get("continues"),
            "llm_identity_policy": employment.get("llm_runtime", {}).get("identity_policy"),
            "agent_run_status": agent_run.get("run_status"),
            "workspace_run_status": workspace_run.get("run_status"),
            "agent_run_p0_runtime_ready": agent_p0["p0_runtime_ready"],
            "workspace_run_p0_runtime_ready": workspace_p0["p0_runtime_ready"],
            "agent_run_p0": agent_p0,
            "workspace_run_p0": workspace_p0,
        }
        passed = (
            details["employment_schema"] == "ai-talent-local-employment/v1"
            and details["employment_status"] == "active"
            and details["growth_after_hire_continues"] is True
            and details["llm_identity_policy"] == "application_engine_not_identity"
            and details["agent_run_status"] == "completed"
            and details["workspace_run_status"] == "completed"
            and details["agent_run_p0_runtime_ready"] is True
            and details["workspace_run_p0_runtime_ready"] is True
        )
    return _checkpoint(passed=passed, evidence=list(paths.values()), root=run_dir, details=details, missing=missing)


def _agent_job_runtime(installed_root: Path, run_dir: Path) -> dict[str, Any]:
    paths = {
        "agent_job_run": installed_root / "last_hired_agent_job_run.json",
        "agent_job_cycle": installed_root / "last_hired_agent_job_cycle.json",
        "agent_job_workspace": installed_root / "agent_job_workspace",
    }
    missing = [path for path in paths.values() if not path.exists()]
    details: dict[str, Any] = {}
    passed = not missing
    if passed:
        job_run = _read_json(paths["agent_job_run"])
        job_cycle = _read_json(paths["agent_job_cycle"])
        job_outputs = job_run.get("job_outputs", {})
        report_raw = str(job_outputs.get("job_report", ""))
        checklist_raw = str(job_outputs.get("acceptance_checklist", ""))
        report_path = Path(report_raw) if report_raw else None
        checklist_path = Path(checklist_raw) if checklist_raw else None
        checklist = _read_json(checklist_path) if checklist_path is not None and checklist_path.exists() else {}
        criteria_statuses = {str(item.get("status", "")) for item in checklist.get("criteria", [])}
        active_memory_route = job_run.get("active_memory_route", {})
        job_p0 = _agent_p0_runtime_details(job_run.get("workspace_run", {}))
        details = {
            "schema": job_run.get("schema"),
            "runtime_model": job_run.get("runtime_model"),
            "job_status": job_run.get("job_status"),
            "employment_relationship": job_run.get("employment_context", {}).get("relationship"),
            "network_access": job_run.get("tool_authorization", {}).get("network_access"),
            "job_report_exists": report_path is not None and report_path.exists(),
            "acceptance_checklist_exists": checklist_path is not None and checklist_path.exists(),
            "acceptance_schema": checklist.get("schema"),
            "criteria_statuses": sorted(criteria_statuses),
            "active_memory_route_schema": active_memory_route.get("schema"),
            "active_memory_selected_count": active_memory_route.get("memory_health", {}).get("selected_experience_count"),
            "active_memory_budget": active_memory_route.get("routing_policy", {}).get("active_context_budget"),
            "job_cycle_schema": job_cycle.get("schema"),
            "job_cycle_status": job_cycle.get("cycle_status"),
            "job_cycle_learning_decision": job_cycle.get("learning_update", {}).get("decision"),
            "job_base_agent_p0_runtime_ready": job_p0["p0_runtime_ready"],
            "job_base_agent_p0": job_p0,
        }
        passed = (
            details["schema"] == "ai-talent-hired-agent-job-run/v1"
            and details["runtime_model"] == "openclaw_style_hired_agent_job"
            and details["job_status"] == "completed"
            and details["employment_relationship"] == "installed_ai_talent_hired_as_local_agent"
            and details["network_access"] == "blocked"
            and details["job_report_exists"] is True
            and details["acceptance_checklist_exists"] is True
            and details["acceptance_schema"] == "ai-talent-agent-job-acceptance-checklist/v1"
            and criteria_statuses == {"satisfied_by_workspace_artifact"}
            and details["active_memory_route_schema"] == "ai-talent-active-memory-route/v1"
            and isinstance(details["active_memory_selected_count"], int)
            and details["active_memory_selected_count"] > 0
            and details["active_memory_budget"] == "bounded"
            and details["job_cycle_schema"] == "ai-talent-hired-agent-job-cycle/v1"
            and details["job_cycle_status"] == "completed_and_promoted"
            and details["job_cycle_learning_decision"] == "promoted"
            and details["job_base_agent_p0_runtime_ready"] is True
        )
    return _checkpoint(passed=passed, evidence=list(paths.values()), root=run_dir, details=details, missing=missing)


def _post_hire_growth(installed_root: Path, run_dir: Path) -> dict[str, Any]:
    paths = {
        "learning_ledger": installed_root / "learning_ledger.json",
        "post_hire_learning_update": installed_root / "post_hire_learning_update.json",
        "employment_goal": installed_root / "employment_goal.json",
        "employment_goal_cycle": installed_root / "last_employment_goal_cycle.json",
    }
    missing = [path for path in paths.values() if not path.exists()]
    details: dict[str, Any] = {}
    passed = not missing
    if passed:
        ledger = _read_json(paths["learning_ledger"])
        update = _read_json(paths["post_hire_learning_update"])
        goal = _read_json(paths["employment_goal"])
        cycle = _read_json(paths["employment_goal_cycle"])
        skills = set(ledger.get("reasoning_kernel", {}).get("procedural_skills", []))
        details = {
            "post_hire_decision": update.get("decision"),
            "quality_status": update.get("quality_label", {}).get("status"),
            "goal_status": goal.get("status"),
            "goal_cycle_status": cycle.get("cycle_status"),
            "goal_learning_decision": cycle.get("learning_update", {}).get("decision"),
            "has_workspace_artifact_trace": "workspace_artifact_trace" in skills,
        }
        passed = (
            details["post_hire_decision"] == "promoted"
            and details["quality_status"] == "verified"
            and details["goal_cycle_status"] == "completed"
            and details["goal_learning_decision"] == "promoted"
            and details["has_workspace_artifact_trace"] is True
        )
    return _checkpoint(passed=passed, evidence=list(paths.values()), root=run_dir, details=details, missing=missing)


def _projection_swarm(installed_root: Path, run_dir: Path) -> dict[str, Any]:
    paths = {
        "swarm": installed_root / "hired_projection_swarm.json",
        "cycle": installed_root / "hired_projection_swarm_cycle.json",
        "workspace": installed_root / "projection_swarm_workspace",
    }
    missing = [path for path in paths.values() if not path.exists()]
    details: dict[str, Any] = {}
    passed = not missing
    if passed:
        swarm = _read_json(paths["swarm"])
        cycle = _read_json(paths["cycle"])
        parent_id = swarm.get("parent", {}).get("employment_context", {}).get("employment_id")
        projection_ids = {
            item.get("employment_context", {}).get("employment_id")
            for item in swarm.get("projections", [])
        }
        consciousness = {
            item.get("consciousness")
            for item in swarm.get("projections", [])
        }
        command_model = swarm.get("swarm_policy", {}).get("command_model", {})
        contribution_modes = {
            item.get("execution_mode")
            for item in cycle.get("contributions", [])
        }
        details = {
            "projection_count": swarm.get("swarm", {}).get("projection_count"),
            "parent_employment_id": parent_id,
            "projection_employment_ids": sorted(item for item in projection_ids if item),
            "consciousness": next(iter(consciousness)) if len(consciousness) == 1 else sorted(consciousness),
            "command_control_topology": command_model.get("control_topology"),
            "command_execution_modes": command_model.get("execution_modes", []),
            "joint_collaboration_allowed": cycle.get("parent_synthesis", {}).get("joint_collaboration_allowed"),
            "contribution_execution_modes": sorted(item for item in contribution_modes if item),
            "separate_employment_records": swarm.get("swarm_policy", {})
            .get("control_model", {})
            .get("separate_employment_records"),
            "not_separate_consciousnesses": swarm.get("swarm_policy", {})
            .get("control_model", {})
            .get("not_separate_consciousnesses"),
            "cycle_status": cycle.get("cycle_status"),
            "separate_consciousness_created": cycle.get("parent_synthesis", {}).get("separate_consciousness_created"),
            "merge_target": cycle.get("parent_growth_merge", {}).get("merge_target"),
        }
        passed = (
            details["projection_count"] == 4
            and projection_ids == {parent_id}
            and consciousness == {"parent_controlled_projection"}
            and details["command_control_topology"] == "single_parent_body_to_task_projections"
            and "joint_collaboration" in details["command_execution_modes"]
            and details["joint_collaboration_allowed"] is True
            and contribution_modes == {"role_split"}
            and details["separate_employment_records"] is False
            and details["not_separate_consciousnesses"] is True
            and details["cycle_status"] == "completed"
            and details["separate_consciousness_created"] is False
            and details["merge_target"] == "parent_growth_log"
        )
    return _checkpoint(passed=passed, evidence=list(paths.values()), root=run_dir, details=details, missing=missing)


def _specialist_team(installed_root: Path, run_dir: Path) -> dict[str, Any]:
    paths = {
        "specialist_cohort": run_dir / "shinyong_specialist_cohort.json",
        "hired_agent_team": installed_root / "hired_agent_team.json",
        "hired_agent_team_cycle": installed_root / "hired_agent_team_cycle.json",
    }
    missing = [path for path in paths.values() if not path.exists()]
    details: dict[str, Any] = {}
    passed = not missing
    if passed:
        cohort = _read_json(paths["specialist_cohort"])
        team = _read_json(paths["hired_agent_team"])
        cycle = _read_json(paths["hired_agent_team_cycle"])
        details = {
            "cohort_schema": cohort.get("schema"),
            "cohort_member_count": cohort.get("team", {}).get("member_count"),
            "hired_team_schema": team.get("schema"),
            "hired_team_member_count": team.get("team", {}).get("member_count"),
            "hired_team_cycle_status": cycle.get("cycle_status"),
            "not_a_projection_team": team.get("team_policy", {}).get("not_a_projection_team"),
        }
        passed = (
            details["cohort_schema"] == "ai-talent-specialist-cohort/v1"
            and details["cohort_member_count"] == 4
            and details["hired_team_schema"] == "ai-talent-hired-agent-team/v1"
            and details["hired_team_member_count"] >= 2
            and details["hired_team_cycle_status"] == "completed"
            and details["not_a_projection_team"] is True
        )
    return _checkpoint(passed=passed, evidence=list(paths.values()), root=run_dir, details=details, missing=missing)


def _role_model_training_artifacts(run_dir: Path, installed_root: Path) -> dict[str, Any]:
    training_run_path = run_dir / "training_run.json"
    training_artifacts: dict[str, Path] = {}
    if training_run_path.exists():
        training_run_data = _read_json(training_run_path)
        training_artifacts = {
            key: Path(value)
            for key, value in training_run_data.get("artifacts", {}).items()
            if isinstance(value, str)
        }

    def from_run_or_glob(key: str, pattern: str) -> Path:
        artifact = training_artifacts.get(key)
        if artifact is not None:
            return artifact
        matches = sorted(run_dir.glob(pattern))
        return matches[0] if matches else run_dir / pattern.replace("*", "missing")

    paths = {
        "training_run": training_run_path,
        "training_blueprint": from_run_or_glob("training_blueprint", "*_training_blueprint.json"),
        "role_model_profile": from_run_or_glob("role_model_profile", "*_role_model_profile.json"),
        "saju_narrative_seed": from_run_or_glob("saju_narrative_seed", "*_saju_narrative_seed.json"),
        "process_emulation_plan": from_run_or_glob("process_emulation_plan", "*_process_emulation_plan.json"),
        "curriculum_manifest": from_run_or_glob("curriculum_manifest", "*_curriculum_manifest.json"),
        "assessment_transcript": from_run_or_glob("assessment_transcript", "*_assessment_transcript.json"),
        "reasoning_kibo": from_run_or_glob("reasoning_kibo", "*_reasoning_kibo.jsonl"),
        "talent_plan": from_run_or_glob("talent_plan", "*_agent_plan.json"),
        "institutional_review": from_run_or_glob("institutional_review", "*_institutional_review.json"),
        "learning_ledger": from_run_or_glob("learning_ledger", "*_learning_ledger.json"),
        "agent_manifest": from_run_or_glob("agent_manifest", "*_agent_manifest.json"),
        "release_bundle": from_run_or_glob("release_bundle", "*_agent_release_bundle"),
        "release_archive": from_run_or_glob("release_archive", "*_agent_release_bundle.zip"),
        "release_package_manifest": from_run_or_glob(
            "release_package_manifest",
            "*_agent_release_bundle.package_manifest.json",
        ),
        "installed_agent_manifest": installed_root / "installed_agent_manifest.json",
        "employment_record": installed_root / "employment_record.json",
    }
    missing = [path for path in paths.values() if not path.exists()]
    details: dict[str, Any] = {}
    passed = not missing
    if passed:
        training_run = _read_json(paths["training_run"])
        role_model = _read_json(paths["role_model_profile"])
        saju = _read_json(paths["saju_narrative_seed"])
        process = _read_json(paths["process_emulation_plan"])
        curriculum = _read_json(paths["curriculum_manifest"])
        transcript = _read_json(paths["assessment_transcript"])
        manifest = _read_json(paths["agent_manifest"])
        employment = _read_json(paths["employment_record"])
        kibo_entries = [
            line for line in paths["reasoning_kibo"].read_text(encoding="utf-8").splitlines() if line.strip()
        ]
        details = {
            "training_status": training_run.get("status"),
            "role_model_id": role_model.get("role_model_id"),
            "saju_schema": saju.get("schema"),
            "process_schema": process.get("schema"),
            "process_mode": process.get("design_principle", {}).get("mode"),
            "curriculum_id": curriculum.get("curriculum_id"),
            "graduation_ready": transcript.get("graduation_ready"),
            "assessment_count": len(transcript.get("results", [])),
            "reasoning_kibo_entries": len(kibo_entries),
            "manifest_schema": manifest.get("schema"),
            "employment_schema": employment.get("schema"),
            "compatible_targets": manifest.get("compatible_targets", []),
        }
        passed = (
            details["training_status"] == "employment_ready"
            and details["role_model_id"] == "graham_value_investing"
            and details["saju_schema"] == "ai-talent-saju-narrative-seed/v1"
            and details["process_schema"] == "ai-talent-role-model-process-emulation/v1"
            and details["process_mode"] == "learning_path_replication_not_personality_injection"
            and details["curriculum_id"] == "graham_securities_research"
            and details["graduation_ready"] is True
            and details["assessment_count"] >= 9
            and details["reasoning_kibo_entries"] >= 2
            and details["manifest_schema"] == "ai-talent-agent-manifest/v1"
            and details["employment_schema"] == "ai-talent-local-employment/v1"
            and "openclaw_style_agent_manifest" in details["compatible_targets"]
            and "hermes_style_agent_manifest" in details["compatible_targets"]
        )
    return _checkpoint(passed=passed, evidence=list(paths.values()), root=run_dir, details=details, missing=missing)


def _first_existing_path(candidates: list[Path]) -> Path:
    return next((path for path in candidates if path.exists()), candidates[0])


def _workspace_execution_proof_safety(installed_root: Path, run_dir: Path) -> dict[str, Any]:
    role_model_run = _is_role_model_run(run_dir)
    dataflow_candidates = [
        installed_root / "last_hired_dataflow_run.json",
        installed_root / "manual_dataflow_run.json",
    ]
    path_by_label = {
        "workspace_agent": installed_root / "last_hired_workspace_agent_run.json",
        "hired_job": installed_root / "last_hired_agent_job_run.json",
        "dataflow": _first_existing_path(dataflow_candidates),
    }
    required_labels = {"dataflow"} if role_model_run else {"workspace_agent", "hired_job", "dataflow"}
    candidate_paths = list(path_by_label.values())
    existing_candidates = [path for path in candidate_paths if path.exists()]
    missing = [path for label, path in path_by_label.items() if label in required_labels and not path.exists()]

    proofs: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    for label, path in path_by_label.items():
        if not path.exists():
            continue
        proof = verify_workspace_execution_file(path)
        retention = proof.get("public_safe_retention", {}) if isinstance(proof.get("public_safe_retention"), dict) else {}
        artifact_summary = proof.get("artifact_summary", {}) if isinstance(proof.get("artifact_summary"), dict) else {}
        source = proof.get("source", {}) if isinstance(proof.get("source"), dict) else {}
        record = {
            "label": label,
            "run_file": path.name,
            "run_schema": source.get("run_schema"),
            "run_status": source.get("run_status"),
            "proof_schema": proof.get("schema"),
            "proof_status": proof.get("status"),
            "passed": proof.get("passed"),
            "issue_count": len(proof.get("issues", [])),
            "issues": proof.get("issues", []),
            "check_count": len(proof.get("checks", [])),
            "absolute_paths_redacted": artifact_summary.get("absolute_paths_redacted"),
            "absolute_paths_are_fingerprinted": retention.get("absolute_paths_are_fingerprinted"),
            "raw_provider_payload_saved": retention.get("raw_provider_payload_saved"),
            "private_reasoning_trace_saved": retention.get("private_reasoning_trace_saved"),
        }
        proofs.append(record)
        if (
            record["proof_schema"] != WORKSPACE_EXECUTION_PROOF_SCHEMA
            or record["passed"] is not True
            or record["absolute_paths_redacted"] is not True
            or record["absolute_paths_are_fingerprinted"] is not True
            or record["raw_provider_payload_saved"] is not False
            or record["private_reasoning_trace_saved"] is not False
        ):
            failures.append(
                {
                    "label": label,
                    "run_file": path.name,
                    "issues": record["issues"],
                    "proof_status": record["proof_status"],
                }
            )

    proof_by_label = {record["label"]: record for record in proofs}
    required_proofs_passed = {
        label: proof_by_label.get(label, {}).get("passed") is True for label in sorted(required_labels)
    }
    details = {
        "schema": WORKSPACE_EXECUTION_PROOF_SAFETY_SCHEMA,
        "mode": "role_model_runtime_minimum" if role_model_run else "full_demo_workspace_runtime",
        "required_labels": sorted(required_labels),
        "required_minimum": len(required_labels),
        "proof_count": len(proofs),
        "passed_proof_count": sum(1 for proof in proofs if proof["passed"] is True),
        "required_proofs_passed": required_proofs_passed,
        "workspace_agent_proof_passed": proof_by_label.get("workspace_agent", {}).get("passed") is True,
        "hired_job_proof_passed": proof_by_label.get("hired_job", {}).get("passed") is True,
        "dataflow_proof_passed": proof_by_label.get("dataflow", {}).get("passed") is True,
        "all_required_proofs_passed": all(required_proofs_passed.values()),
        "all_proofs_passed": bool(proofs) and all(proof["passed"] is True for proof in proofs),
        "all_proofs_public_safe": bool(proofs)
        and all(
            proof["absolute_paths_are_fingerprinted"] is True
            and proof["raw_provider_payload_saved"] is False
            and proof["private_reasoning_trace_saved"] is False
            for proof in proofs
        ),
        "all_required_artifacts_redacted": bool(proofs)
        and all(proof["absolute_paths_redacted"] is True for proof in proofs),
        "missing_required_files": [_rel(path, run_dir) for path in missing],
        "failure_count": len(failures) + len(missing),
        "failures": failures,
        "proofs": proofs,
    }
    passed = (
        not missing
        and details["proof_count"] >= details["required_minimum"]
        and details["all_required_proofs_passed"] is True
        and details["all_proofs_passed"] is True
        and details["all_proofs_public_safe"] is True
        and details["all_required_artifacts_redacted"] is True
        and not failures
    )
    return _checkpoint(
        passed=passed,
        evidence=existing_candidates,
        root=run_dir,
        details=details,
        missing=missing,
    )


def _role_model_runtime(installed_root: Path, run_dir: Path) -> dict[str, Any]:
    agent_run_candidates = [
        installed_root / "last_hired_agent_run.json",
        installed_root / "manual_hired_agent_run.json",
    ]
    dataflow_candidates = [
        installed_root / "last_hired_dataflow_run.json",
        installed_root / "manual_dataflow_run.json",
    ]
    agent_run_path = next((path for path in agent_run_candidates if path.exists()), agent_run_candidates[0])
    dataflow_run_path = next((path for path in dataflow_candidates if path.exists()), dataflow_candidates[0])
    paths = {
        "agent_run": agent_run_path,
        "dataflow_run": dataflow_run_path,
    }
    missing = [path for path in paths.values() if not path.exists()]
    details: dict[str, Any] = {}
    passed = not missing
    if passed:
        agent_run = _read_json(paths["agent_run"])
        dataflow_run = _read_json(paths["dataflow_run"])
        agent_p0 = _agent_p0_runtime_details(agent_run)
        dataflow_p0 = _dataflow_p0_runtime_details(dataflow_run)
        details = {
            "agent_run_status": agent_run.get("run_status"),
            "dataflow_schema": dataflow_run.get("schema"),
            "dataflow_status": dataflow_run.get("run_status"),
            "workspace_output_count": len(dataflow_run.get("workspace_outputs", {})),
            "growth_candidate_schema": dataflow_run.get("growth_commit_candidate", {}).get("schema"),
            "agent_run_p0_runtime_ready": agent_p0["p0_runtime_ready"],
            "dataflow_p0_runtime_ready": dataflow_p0["p0_runtime_ready"],
            "agent_run_p0": agent_p0,
            "dataflow_p0": dataflow_p0,
        }
        passed = (
            details["agent_run_status"] == "completed"
            and details["dataflow_schema"] == "ai-talent-dataflow-run/v1"
            and details["dataflow_status"] == "completed"
            and details["workspace_output_count"] >= 5
            and details["growth_candidate_schema"] == "ai-talent-dataflow-growth-commit-candidate/v1"
            and details["agent_run_p0_runtime_ready"] is True
            and details["dataflow_p0_runtime_ready"] is True
        )
    return _checkpoint(passed=passed, evidence=list(paths.values()), root=run_dir, details=details, missing=missing)


def _is_role_model_run(run_dir: Path) -> bool:
    return any(run_dir.glob("*_role_model_profile.json")) and any(run_dir.glob("*_reasoning_kibo.jsonl"))


def audit_foundry_release(run_dir: Path, *, output_path: Path | None = None) -> dict[str, Any]:
    run_dir = run_dir.resolve()
    installed_root = _installed_agent_root(run_dir)
    if _is_role_model_run(run_dir):
        checkpoints = {
            "research_foundation": _research_foundation(),
            "public_safe_first_run_smoke": _public_safe_first_run_smoke(),
            "action_policy_safety": _action_policy_safety(),
            "llm_provider_readiness": _llm_provider_readiness(),
            "llm_live_agent_loop_contract": _llm_live_agent_loop_contract(),
            "fail_closed_runtime_contract": _fail_closed_runtime_contract(),
            "public_program_manifest": _public_program_manifest(run_dir),
            "role_model_training_artifacts": _role_model_training_artifacts(run_dir, installed_root),
            "role_model_runtime": _role_model_runtime(installed_root, run_dir),
            "workspace_execution_proof_safety": _workspace_execution_proof_safety(installed_root, run_dir),
            "learning_ledger_replay_safety": _learning_ledger_replay_safety(run_dir, installed_root),
            "runtime_observability_comparison": _runtime_observability_comparison(run_dir),
        }
    else:
        checkpoints = {
            "research_foundation": _research_foundation(),
            "public_safe_first_run_smoke": _public_safe_first_run_smoke(),
            "action_policy_safety": _action_policy_safety(),
            "llm_provider_readiness": _llm_provider_readiness(),
            "llm_live_agent_loop_contract": _llm_live_agent_loop_contract(),
            "fail_closed_runtime_contract": _fail_closed_runtime_contract(),
            "public_program_manifest": _public_program_manifest(run_dir),
            "growth_governance": _growth_governance(run_dir),
            "public_distribution": _public_distribution(run_dir, installed_root),
            "local_employment": _local_employment(installed_root, run_dir),
            "agent_job_runtime": _agent_job_runtime(installed_root, run_dir),
            "workspace_execution_proof_safety": _workspace_execution_proof_safety(installed_root, run_dir),
            "post_hire_growth": _post_hire_growth(installed_root, run_dir),
            "family_lineage": _family_lineage(run_dir),
            "projection_swarm": _projection_swarm(installed_root, run_dir),
            "specialist_team": _specialist_team(installed_root, run_dir),
            "learning_ledger_replay_safety": _learning_ledger_replay_safety(run_dir, installed_root),
            "runtime_observability_comparison": _runtime_observability_comparison(run_dir),
        }
    failed = [name for name, checkpoint in checkpoints.items() if not checkpoint["passed"]]
    public_release_ready = not failed
    audit = {
        "schema": AUDIT_SCHEMA,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "run_dir": run_dir.name,
        "installed_agent": installed_root.name,
        "public_release_ready": public_release_ready,
        "overall_status": "ready_for_local_public_preview" if public_release_ready else "needs_attention",
        "checkpoints": checkpoints,
        "required_next_actions": [
            f"Fix release checkpoint: {name}"
            for name in failed
        ],
    }
    if output_path is not None:
        _write_json(output_path, audit)
    return audit
