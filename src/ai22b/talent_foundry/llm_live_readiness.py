from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ai22b.talent_foundry.agent_runtime_smoke import run_agent_runtime_smoke
from ai22b.talent_foundry.chat_runtime_smoke import run_chat_runtime_smoke
from ai22b.talent_foundry.llm_runtime import doctor_llm_provider, run_llm_application_smoke


LLM_LIVE_READINESS_SCHEMA = "paideia-llm-live-readiness-suite/v1"


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _status(value: dict[str, Any]) -> str:
    if value.get("passed") is True:
        return "passed"
    return str(value.get("status") or "failed")


def _report_path(output_dir: Path, filename: str) -> str:
    return str(output_dir / filename)


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
        },
    }
    passed = (
        checks["provider_doctor"]["passed"]
        and checks["application_smoke"]["passed"]
        and checks["agent_runtime_smoke"]["passed"]
        and checks["chat_runtime_smoke"]["passed"]
    )
    live_ready = bool(live_check and passed)
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
        "data_policy": {
            "secret_values_exported": False,
            "send_private_training_files": False,
            "send_full_session_replay": False,
            "raw_provider_payload_saved": False,
            "private_reasoning_trace": "do_not_store",
            "live_provider_called_only_when_live_check_requested": live_check,
            "live_provider_call_attempted": bool(live_check),
        },
        "next_actions": (
            ["Use the generated live-ready reports before chat or hired-agent work."]
            if live_ready
            else [
                "Review provider_doctor, application_smoke, and agent_runtime_smoke artifacts.",
                "Configure the required API key, model, local server, or local model path.",
                "Re-run this suite with --live-check only when you intentionally want a real provider call.",
            ]
        ),
    }
    _write_json(summary_path, suite)
    return suite
