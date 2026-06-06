from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ai22b.talent_foundry.agent_runtime_smoke import run_agent_runtime_smoke
from ai22b.talent_foundry.chat_runtime_smoke import run_chat_runtime_smoke
from ai22b.talent_foundry.llm_runtime import doctor_llm_provider, run_llm_application_smoke


LLM_LIVE_READINESS_SCHEMA = "paideia-llm-live-readiness-suite/v1"
LIVE_CONNECTION_STATUS_CARD_SCHEMA = "paideia-live-connection-status-card/v1"


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _status(value: dict[str, Any]) -> str:
    if value.get("passed") is True:
        return "passed"
    return str(value.get("status") or "failed")


def _report_path(output_dir: Path, filename: str) -> str:
    return str(output_dir / filename)


def _first_blocking_step(checks: dict[str, dict[str, Any]]) -> dict[str, Any] | None:
    for step_id in ("provider_doctor", "application_smoke", "agent_runtime_smoke", "chat_runtime_smoke"):
        step = checks.get(step_id, {})
        if step.get("passed") is True:
            continue
        return {
            "id": step_id,
            "status": step.get("status"),
            "reason": (
                step.get("failure_mode")
                or step.get("runtime_status")
                or step.get("chat_status")
                or step.get("smoke_contract_status")
                or "check_not_passed"
            ),
        }
    return None


def _build_live_connection_status_card(
    *,
    engine: str,
    service: str | None,
    model: str | None,
    model_path: str | None,
    chat_surface: str | None,
    live_check: bool,
    passed: bool,
    live_ready: bool,
    checks: dict[str, dict[str, Any]],
    required_before_live: dict[str, str],
) -> dict[str, Any]:
    blocking_step = _first_blocking_step(checks)
    if live_ready:
        status = "ready_for_live_agent_work"
    elif not live_check and passed:
        status = "offline_verified_live_not_attempted"
    else:
        status = "needs_live_configuration"
    chat_check = checks.get("chat_runtime_smoke", {})
    provider_check = checks.get("provider_doctor", {})
    agent_check = checks.get("agent_runtime_smoke", {})
    agent_proof = agent_check.get("live_llm_agent_proof", {})
    agent_proof = agent_proof if isinstance(agent_proof, dict) else {}
    provider_doctor_call_attempted = bool(provider_check.get("provider_call_attempted"))
    provider_doctor_network_call_made = bool(provider_check.get("network_call_made_by_doctor"))
    provider_doctor_blocked_before_transport = bool(provider_check.get("network_call_blocked_before_transport"))
    agent_live_client_generate_called = bool(agent_proof.get("live_client_generate_called"))
    built_in_provider_client_called = bool(agent_proof.get("built_in_provider_client_called"))
    provider_client_generate_attempted = bool(
        provider_doctor_call_attempted
        or agent_live_client_generate_called
        or built_in_provider_client_called
    )
    check_statuses = {
        key: {
            "status": value.get("status"),
            "passed": value.get("passed"),
        }
        for key, value in checks.items()
    }
    return {
        "schema": LIVE_CONNECTION_STATUS_CARD_SCHEMA,
        "status": status,
        "live_check_requested": live_check,
        "offline_ready": bool(passed and not live_check),
        "ready_for_live_chat": bool(live_ready and chat_check.get("passed") is True),
        "ready_for_live_agent_work": bool(live_ready),
        "selected_llm": {
            "engine": engine,
            "service": service or engine,
            "model": model,
            "model_path_present": bool(model_path),
            "chat_surface": chat_surface,
        },
        "blocking_step": blocking_step,
        "check_statuses": check_statuses,
        "chat_runtime_status_card": {
            "schema": chat_check.get("runtime_status_card_schema"),
            "status": chat_check.get("runtime_status_card_status"),
            "fallback_used": chat_check.get("runtime_status_card_fallback_used"),
            "presented_as_live": chat_check.get("runtime_status_card_presented_as_live"),
            "learning_decision": chat_check.get("runtime_status_card_learning_decision"),
            "memory_lifecycle": {
                "schema": chat_check.get("runtime_status_card_memory_lifecycle_schema"),
                "status": chat_check.get("runtime_status_card_memory_lifecycle_status"),
                "selected_count": chat_check.get("runtime_status_card_memory_lifecycle_selected_count"),
                "quarantined_excluded": chat_check.get(
                    "runtime_status_card_memory_lifecycle_quarantined_excluded"
                ),
                "learning_decision": chat_check.get(
                    "runtime_status_card_memory_lifecycle_learning_decision"
                ),
            },
        },
        "agent_runtime_status_card": {
            "schema": agent_check.get("agent_runtime_status_card_schema"),
            "status": agent_check.get("agent_runtime_status_card_status"),
            "public_safe": agent_check.get("agent_runtime_status_card_public_safe"),
            "memory_decision": agent_check.get("agent_runtime_status_card_memory_decision"),
        },
        "agent_tool_artifacts": {
            "manifest_schema": agent_check.get("tool_artifact_manifest_schema"),
            "manifest_status": agent_check.get("tool_artifact_manifest_status"),
            "artifact_count": agent_check.get("tool_artifact_manifest_count"),
            "manifest_file": agent_check.get("tool_artifact_manifest_file"),
            "manifest_file_exists": agent_check.get("tool_artifact_manifest_file_exists"),
            "artifact_files_exist": agent_check.get("tool_artifact_files_exist"),
            "relative_paths_only": agent_check.get("tool_artifact_relative_paths_only"),
            "evidence_packet_materialized": agent_check.get("tool_artifact_evidence_packet_materialized"),
            "public_safe": agent_check.get("tool_artifact_public_safe"),
            "status_card_local_artifacts_materialized": agent_check.get(
                "tool_execution_status_card_local_artifacts_materialized"
            ),
        },
        "live_llm_agent_proof": {
            "schema": agent_proof.get("schema"),
            "status": agent_proof.get("status"),
            "passed": agent_proof.get("passed"),
            "proof_level": agent_proof.get("proof_level"),
            "provider_path": agent_proof.get("provider_path"),
            "live_client_generate_called": agent_proof.get("live_client_generate_called"),
            "client_override_used": agent_proof.get("client_override_used"),
            "built_in_provider_client_called": agent_proof.get("built_in_provider_client_called"),
        },
        "chat_memory_lifecycle_status_card": {
            "schema": chat_check.get("memory_lifecycle_status_card_schema"),
            "status": chat_check.get("memory_lifecycle_status_card_status"),
            "selected_count": chat_check.get("memory_lifecycle_status_card_selected_count"),
            "quarantined_excluded": chat_check.get("memory_lifecycle_status_card_quarantined_excluded"),
            "learning_decision": chat_check.get("memory_lifecycle_status_card_learning_decision"),
        },
        "public_safe": {
            "secret_values_exported": False,
            "raw_provider_payload_saved": False,
            "private_reasoning_trace": "do_not_store",
            "live_provider_call_requested": live_check,
            "live_provider_call_attempted": bool(live_check),
            "provider_client_generate_attempted": provider_client_generate_attempted,
            "provider_doctor_call_attempted": provider_doctor_call_attempted,
            "provider_doctor_network_call_made": provider_doctor_network_call_made,
            "provider_doctor_blocked_before_transport": provider_doctor_blocked_before_transport,
            "provider_doctor_block_reason": provider_check.get("network_call_block_reason"),
            "agent_live_client_generate_called": agent_live_client_generate_called,
            "built_in_provider_client_called": built_in_provider_client_called,
            "local_tool_artifacts_materialized": agent_check.get("tool_artifact_manifest_status") == "materialized",
            "tool_artifact_public_safe": agent_check.get("tool_artifact_public_safe"),
            "live_provider_call_attempted_only_when_requested": True,
            "provider_client_attempted_only_when_requested": not provider_client_generate_attempted or live_check,
        },
        "user_visible_summary": {
            "ko": (
                "선택한 LLM은 live 채팅과 에이전트 업무에 사용할 준비가 됐습니다."
                if status == "ready_for_live_agent_work"
                else "offline/no-network 검증은 통과했지만 live provider 호출은 아직 시도하지 않았습니다."
                if status == "offline_verified_live_not_attempted"
                else f"live 연결이 막혔습니다. 먼저 확인할 단계는 {blocking_step.get('id') if blocking_step else 'provider setup'}입니다."
            ),
            "en": (
                "The selected LLM is ready for live chat and agent work."
                if status == "ready_for_live_agent_work"
                else "Offline/no-network checks passed, but a live provider call has not been attempted."
                if status == "offline_verified_live_not_attempted"
                else f"Live connection is blocked; inspect {blocking_step.get('id') if blocking_step else 'provider setup'} first."
            ),
        },
        "next_actions": (
            ["Start live chat or hired-agent work with the generated artifacts."]
            if status == "ready_for_live_agent_work"
            else [
                "Run the explicit live-check sequence only when you intend to call the selected provider.",
                *required_before_live.values(),
            ]
            if status == "offline_verified_live_not_attempted"
            else [
                f"Inspect {blocking_step.get('id') if blocking_step else 'provider_doctor'} artifact first.",
                "Configure the required API key, model, localhost server, or model path.",
                "Re-run doctor-llm-live-readiness with --live-check after setup.",
            ]
        ),
    }


def run_llm_live_readiness_suite(
    *,
    engine: str,
    model: str | None = None,
    model_path: str | None = None,
    service: str | None = None,
    chat_surface: str | None = None,
    live_check: bool = False,
    output_dir: Path,
    task: str = "Run a Paideia live readiness suite for the selected LLM provider.",
) -> dict[str, Any]:
    """Run the selected provider through doctor, application smoke, and agent runtime smoke.

    The suite is intentionally explicit: without live_check it performs only the
    no-network posture and writes the exact commands needed for live execution.
    With live_check it uses the same live path as agent runtime smoke and fails
    closed if the provider key, model, local server, or path is missing.
    """

    output_dir.mkdir(parents=True, exist_ok=True)
    llm_mode = "live" if live_check else "offline"
    doctor = doctor_llm_provider(
        engine=engine,
        model=model,
        model_path=model_path,
        service=service,
        live_check=live_check,
    )
    application_smoke = run_llm_application_smoke(
        engine=engine,
        model=model,
        model_path=model_path,
        service=service,
        llm_mode=llm_mode,
        task=task,
    )
    agent_smoke = run_agent_runtime_smoke(
        engine=engine,
        model=model,
        model_path=model_path,
        service=service,
        llm_mode=llm_mode,
        task=task,
        artifact_dir=output_dir / "agent_runtime_tool_artifacts",
    )
    chat_smoke = run_chat_runtime_smoke(
        engine=engine,
        model=model,
        model_path=model_path,
        service=service,
        chat_surface=chat_surface,
        llm_mode=llm_mode,
        message="보스가 Paideia 채팅 readiness를 확인합니다.",
        artifact_dir=output_dir / "chat_runtime_smoke_artifacts",
    )
    summary_path = output_dir / "llm_live_readiness_suite.json"
    artifacts = {
        "summary": str(summary_path),
        "provider_doctor": _report_path(
            output_dir,
            "llm_provider_doctor.live.json" if live_check else "llm_provider_doctor.offline.json",
        ),
        "application_smoke": _report_path(
            output_dir,
            "llm_application_smoke.live.json" if live_check else "llm_application_smoke.offline.json",
        ),
        "agent_runtime_smoke": _report_path(
            output_dir,
            "agent_runtime_smoke.live.json" if live_check else "agent_runtime_smoke.offline.json",
        ),
        "chat_runtime_smoke": _report_path(
            output_dir,
            "chat_runtime_smoke.live.json" if live_check else "chat_runtime_smoke.offline.json",
        ),
    }
    _write_json(Path(artifacts["provider_doctor"]), doctor)
    _write_json(Path(artifacts["application_smoke"]), application_smoke)
    _write_json(Path(artifacts["agent_runtime_smoke"]), agent_smoke)
    _write_json(Path(artifacts["chat_runtime_smoke"]), chat_smoke)
    agent_proof = (
        agent_smoke.get("live_llm_agent_proof", {})
        if isinstance(agent_smoke.get("live_llm_agent_proof"), dict)
        else {}
    )
    required_before_live = {
        "provider_doctor": "doctor-llm-provider --live-check",
        "application_smoke": "run-llm-application-smoke --live-check",
        "agent_runtime_smoke": "run-agent-runtime-smoke --live-check",
        "chat_runtime_smoke": "run-chat-runtime-smoke --live-check",
    }
    checks = {
        "provider_doctor": {
            "schema": doctor.get("schema"),
            "status": _status(doctor),
            "passed": doctor.get("passed") is True,
            "live_check_requested": doctor.get("live_check_requested"),
            "smoke_contract_status": doctor.get("smoke_contract", {}).get("status")
            if isinstance(doctor.get("smoke_contract"), dict)
            else None,
            "provider_call_attempted": doctor.get("smoke_contract", {}).get("provider_call_attempted")
            if isinstance(doctor.get("smoke_contract"), dict)
            else None,
            "network_call_made_by_doctor": doctor.get("smoke_contract", {}).get("network_call_made_by_doctor")
            if isinstance(doctor.get("smoke_contract"), dict)
            else None,
            "network_call_blocked_before_transport": doctor.get("smoke_contract", {}).get(
                "network_call_blocked_before_transport"
            )
            if isinstance(doctor.get("smoke_contract"), dict)
            else None,
            "network_call_block_reason": doctor.get("smoke_contract", {}).get("network_call_block_reason")
            if isinstance(doctor.get("smoke_contract"), dict)
            else None,
            "network_call_delegated_to_client_override": doctor.get("smoke_contract", {}).get(
                "network_call_delegated_to_client_override"
            )
            if isinstance(doctor.get("smoke_contract"), dict)
            else None,
        },
        "application_smoke": {
            "schema": application_smoke.get("schema"),
            "status": _status(application_smoke),
            "passed": application_smoke.get("passed") is True,
            "runtime_status": application_smoke.get("runtime_result", {}).get("status")
            if isinstance(application_smoke.get("runtime_result"), dict)
            else None,
            "llm_client_contract_status": application_smoke.get("runtime_contract", {}).get(
                "llm_client_contract_status"
            )
            if isinstance(application_smoke.get("runtime_contract"), dict)
            else None,
        },
        "agent_runtime_smoke": {
            "schema": agent_smoke.get("schema"),
            "status": _status(agent_smoke),
            "passed": agent_smoke.get("passed") is True,
            "run_attempted": agent_smoke.get("details", {}).get("run_attempted")
            if isinstance(agent_smoke.get("details"), dict)
            else None,
            "failure_mode": agent_smoke.get("details", {}).get("failure_mode")
            if isinstance(agent_smoke.get("details"), dict)
            else None,
            "llm_client_contract_status": agent_smoke.get("details", {}).get("llm_client_contract_status")
            if isinstance(agent_smoke.get("details"), dict)
            else None,
            "live_llm_agent_proof": {
                "schema": agent_proof.get("schema"),
                "status": agent_proof.get("status"),
                "passed": agent_proof.get("passed"),
                "proof_level": agent_proof.get("proof_level"),
                "provider_path": agent_proof.get("provider_path"),
                "live_runtime_path_selected": agent_proof.get("live_runtime_path_selected"),
                "live_client_generate_called": agent_proof.get("live_client_generate_called"),
                "client_override_used": agent_proof.get("client_override_used"),
                "built_in_provider_client_called": agent_proof.get("built_in_provider_client_called"),
            },
            "agent_runtime_status_card_schema": agent_smoke.get("details", {}).get(
                "agent_runtime_status_card_schema"
            )
            if isinstance(agent_smoke.get("details"), dict)
            else None,
            "agent_runtime_status_card_status": agent_smoke.get("details", {}).get(
                "agent_runtime_status_card_status"
            )
            if isinstance(agent_smoke.get("details"), dict)
            else None,
            "agent_runtime_status_card_public_safe": agent_smoke.get("details", {}).get(
                "agent_runtime_status_card_public_safe"
            )
            if isinstance(agent_smoke.get("details"), dict)
            else None,
            "agent_runtime_status_card_memory_decision": agent_smoke.get("details", {}).get(
                "agent_runtime_status_card_memory_decision"
            )
            if isinstance(agent_smoke.get("details"), dict)
            else None,
            "tool_artifact_manifest_schema": agent_smoke.get("details", {}).get(
                "tool_artifact_manifest_schema"
            )
            if isinstance(agent_smoke.get("details"), dict)
            else None,
            "tool_artifact_manifest_status": agent_smoke.get("details", {}).get(
                "tool_artifact_manifest_status"
            )
            if isinstance(agent_smoke.get("details"), dict)
            else None,
            "tool_artifact_manifest_count": agent_smoke.get("details", {}).get(
                "tool_artifact_manifest_count"
            )
            if isinstance(agent_smoke.get("details"), dict)
            else None,
            "tool_artifact_manifest_file": agent_smoke.get("details", {}).get(
                "tool_artifact_manifest_file"
            )
            if isinstance(agent_smoke.get("details"), dict)
            else None,
            "tool_artifact_manifest_file_exists": agent_smoke.get("details", {}).get(
                "tool_artifact_manifest_file_exists"
            )
            if isinstance(agent_smoke.get("details"), dict)
            else None,
            "tool_artifact_files_exist": agent_smoke.get("details", {}).get("tool_artifact_files_exist")
            if isinstance(agent_smoke.get("details"), dict)
            else None,
            "tool_artifact_relative_paths_only": agent_smoke.get("details", {}).get(
                "tool_artifact_relative_paths_only"
            )
            if isinstance(agent_smoke.get("details"), dict)
            else None,
            "tool_artifact_evidence_packet_materialized": agent_smoke.get("details", {}).get(
                "tool_artifact_evidence_packet_materialized"
            )
            if isinstance(agent_smoke.get("details"), dict)
            else None,
            "tool_artifact_public_safe": agent_smoke.get("details", {}).get("tool_artifact_public_safe")
            if isinstance(agent_smoke.get("details"), dict)
            else None,
            "tool_execution_status_card_local_artifacts_materialized": agent_smoke.get("details", {}).get(
                "tool_execution_status_card_local_artifacts_materialized"
            )
            if isinstance(agent_smoke.get("details"), dict)
            else None,
        },
        "chat_runtime_smoke": {
            "schema": chat_smoke.get("schema"),
            "status": _status(chat_smoke),
            "passed": chat_smoke.get("passed") is True,
            "chat_status": chat_smoke.get("details", {}).get("chat_status")
            if isinstance(chat_smoke.get("details"), dict)
            else None,
            "reply_generation_mode": chat_smoke.get("details", {}).get("reply_generation_mode")
            if isinstance(chat_smoke.get("details"), dict)
            else None,
            "provider_not_ready": chat_smoke.get("details", {}).get("provider_not_ready")
            if isinstance(chat_smoke.get("details"), dict)
            else None,
            "runtime_status_card_schema": chat_smoke.get("details", {}).get("runtime_status_card_schema")
            if isinstance(chat_smoke.get("details"), dict)
            else None,
            "runtime_status_card_status": chat_smoke.get("details", {}).get("runtime_status_card_status")
            if isinstance(chat_smoke.get("details"), dict)
            else None,
            "runtime_status_card_fallback_used": chat_smoke.get("details", {}).get(
                "runtime_status_card_fallback_used"
            )
            if isinstance(chat_smoke.get("details"), dict)
            else None,
            "runtime_status_card_presented_as_live": chat_smoke.get("details", {}).get(
                "runtime_status_card_presented_as_live"
            )
            if isinstance(chat_smoke.get("details"), dict)
            else None,
            "runtime_status_card_learning_decision": chat_smoke.get("details", {}).get(
                "runtime_status_card_learning_decision"
            )
            if isinstance(chat_smoke.get("details"), dict)
            else None,
            "memory_lifecycle_status_card_schema": chat_smoke.get("details", {}).get(
                "memory_lifecycle_status_card_schema"
            )
            if isinstance(chat_smoke.get("details"), dict)
            else None,
            "memory_lifecycle_status_card_status": chat_smoke.get("details", {}).get(
                "memory_lifecycle_status_card_status"
            )
            if isinstance(chat_smoke.get("details"), dict)
            else None,
            "memory_lifecycle_status_card_selected_count": chat_smoke.get("details", {}).get(
                "memory_lifecycle_status_card_selected_count"
            )
            if isinstance(chat_smoke.get("details"), dict)
            else None,
            "memory_lifecycle_status_card_quarantined_excluded": chat_smoke.get("details", {}).get(
                "memory_lifecycle_status_card_quarantined_excluded"
            )
            if isinstance(chat_smoke.get("details"), dict)
            else None,
            "memory_lifecycle_status_card_learning_decision": chat_smoke.get("details", {}).get(
                "memory_lifecycle_status_card_learning_decision"
            )
            if isinstance(chat_smoke.get("details"), dict)
            else None,
            "runtime_status_card_memory_lifecycle_schema": chat_smoke.get("details", {}).get(
                "runtime_status_card_memory_lifecycle_schema"
            )
            if isinstance(chat_smoke.get("details"), dict)
            else None,
            "runtime_status_card_memory_lifecycle_status": chat_smoke.get("details", {}).get(
                "runtime_status_card_memory_lifecycle_status"
            )
            if isinstance(chat_smoke.get("details"), dict)
            else None,
            "runtime_status_card_memory_lifecycle_selected_count": chat_smoke.get("details", {}).get(
                "runtime_status_card_memory_lifecycle_selected_count"
            )
            if isinstance(chat_smoke.get("details"), dict)
            else None,
            "runtime_status_card_memory_lifecycle_quarantined_excluded": chat_smoke.get("details", {}).get(
                "runtime_status_card_memory_lifecycle_quarantined_excluded"
            )
            if isinstance(chat_smoke.get("details"), dict)
            else None,
            "runtime_status_card_memory_lifecycle_learning_decision": chat_smoke.get("details", {}).get(
                "runtime_status_card_memory_lifecycle_learning_decision"
            )
            if isinstance(chat_smoke.get("details"), dict)
            else None,
        },
    }
    passed = (
        checks["provider_doctor"]["passed"]
        and checks["application_smoke"]["passed"]
        and checks["agent_runtime_smoke"]["passed"]
        and checks["chat_runtime_smoke"]["passed"]
    )
    live_ready = bool(live_check and passed)
    live_connection_status_card = _build_live_connection_status_card(
        engine=engine,
        service=service,
        model=model,
        model_path=model_path,
        chat_surface=chat_surface,
        live_check=live_check,
        passed=passed,
        live_ready=live_ready,
        checks=checks,
        required_before_live=required_before_live,
    )
    suite = {
        "schema": LLM_LIVE_READINESS_SCHEMA,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "engine": engine,
        "service": service or engine,
        "model": model,
        "model_path_present": bool(model_path),
        "chat_surface": chat_surface,
        "summary_path": str(summary_path),
        "live_check_requested": live_check,
        "llm_mode": llm_mode,
        "status": "ready_for_live_agent_work" if live_ready else "needs_live_configuration_or_offline_review",
        "passed": passed,
        "live_ready": live_ready,
        "checks": checks,
        "artifacts": artifacts,
        "required_before_live": required_before_live,
        "live_connection_status_card": live_connection_status_card,
        "data_policy": {
            "secret_values_exported": False,
            "send_private_training_files": False,
            "send_full_session_replay": False,
            "raw_provider_payload_saved": False,
            "private_reasoning_trace": "do_not_store",
            "live_provider_call_requested": live_check,
            "live_provider_called_only_when_live_check_requested": live_check,
            "live_provider_call_attempted": bool(live_check),
            "provider_client_generate_attempted": live_connection_status_card["public_safe"][
                "provider_client_generate_attempted"
            ],
            "provider_doctor_network_call_made": live_connection_status_card["public_safe"][
                "provider_doctor_network_call_made"
            ],
            "provider_doctor_blocked_before_transport": live_connection_status_card["public_safe"][
                "provider_doctor_blocked_before_transport"
            ],
            "agent_tool_artifact_manifest_schema": live_connection_status_card["agent_tool_artifacts"][
                "manifest_schema"
            ],
            "agent_tool_artifact_manifest_status": live_connection_status_card["agent_tool_artifacts"][
                "manifest_status"
            ],
            "agent_tool_artifact_public_safe": live_connection_status_card["agent_tool_artifacts"][
                "public_safe"
            ],
            "agent_live_llm_proof_schema": agent_proof.get("schema"),
            "agent_live_llm_proof_status": agent_proof.get("status"),
            "agent_live_llm_proof_provider_path": agent_proof.get("provider_path"),
        },
        "next_actions": live_connection_status_card["next_actions"],
    }
    _write_json(summary_path, suite)
    return suite
