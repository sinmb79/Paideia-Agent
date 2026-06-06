from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ai22b.talent_foundry.learning_loop import build_reasoning_kernel, create_learning_ledger
from ai22b.talent_foundry.llm_runtime import build_llm_runtime_config
from ai22b.talent_foundry.memory_substrate import run_chat_turn_from_employment
from ai22b.talent_foundry.onboarding_choices import DEFAULT_CHAT_SURFACE_ID, resolve_chat_surface


CHAT_RUNTIME_SMOKE_SCHEMA = "paideia-chat-runtime-smoke/v1"


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _fixture_agent_manifest() -> dict[str, Any]:
    return {
        "schema": "ai-talent-agent-manifest/v1",
        "agent": {
            "name": "paideia-chat-smoke-agent",
            "role": "public-safe chat readiness fixture",
            "major_goal": "Verify selected LLM and chat surface can produce a bounded Paideia chat turn.",
            "birth": {
                "datetime": "doctor-fixture",
                "place": "local-public-safe-fixture",
            },
        },
        "identity_source": {
            "role_model_inspiration": {
                "role_model_id": "graham_value_investing",
                "boundary": "learning_path_only_not_impersonation",
            }
        },
        "memory_profile": {
            "procedural_principles": [
                "Use local records as identity.",
                "Treat the selected LLM as an application language engine.",
                "Do not promote chat learning without review.",
            ],
            "semantic_themes": ["chat readiness", "provider preflight", "local identity boundary"],
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


def _write_chat_fixture(
    *,
    artifact_dir: Path,
    engine: str,
    model: str | None,
    model_path: str | None,
    service: str | None,
    chat_surface: str | None,
) -> tuple[Path, dict[str, Any]]:
    fixture_root = artifact_dir / "fixture"
    fixture_root.mkdir(parents=True, exist_ok=True)
    agent_manifest = _fixture_agent_manifest()
    ledger = create_learning_ledger(owner=agent_manifest["agent"]["name"])
    ledger["reasoning_kernel"] = build_reasoning_kernel(ledger)
    runtime_config = build_llm_runtime_config(
        engine=engine,
        model=model,
        model_path=model_path,
        service=service,
    )
    selected_chat_surface = resolve_chat_surface(chat_surface or DEFAULT_CHAT_SURFACE_ID)
    employment_record = {
        "schema": "ai-talent-local-employment/v1",
        "employment_id": "chat-runtime-smoke-employment",
        "hired_at_utc": _now(),
        "employer": "Boss",
        "relationship": "installed_ai_talent_hired_as_local_agent",
        "install_id": "chat-runtime-smoke-install",
        "agent": {
            "name": agent_manifest["agent"]["name"],
            "role": "chat readiness fixture",
            "major_goal": agent_manifest["agent"]["major_goal"],
        },
        "source": {
            "installed_manifest": "chat_runtime_smoke_fixture",
            "agent_manifest": "agent_manifest.json",
            "source_archive": "chat_runtime_smoke_fixture",
            "source_sha256": "chat_runtime_smoke_fixture",
        },
        "entrypoints": {
            "agent_manifest": "agent_manifest.json",
            "learning_ledger": "learning_ledger.json",
            "memory_substrate": "memory_substrate.json",
            "chat_log": "employment_chat_log.jsonl",
            "last_chat": "last_hired_agent_chat.json",
        },
        "guardrails": agent_manifest["tool_policy"]["blocked_tools"],
        "llm_service": {
            "service_id": service or engine,
            "engine": engine,
            "selected_model": model,
            "selected_model_path": model_path,
        },
        "chat_surface": selected_chat_surface,
        "llm_runtime": runtime_config,
        "growth_after_hire": {
            "continues": True,
            "principle": "Chat is a runtime interaction; learning remains review-gated.",
            "record_policy": "Smoke chat turns do not auto-promote learning.",
        },
        "llm_policy": agent_manifest["llm_policy"],
        "status": "active",
    }
    _write_json(fixture_root / "agent_manifest.json", agent_manifest)
    _write_json(fixture_root / "learning_ledger.json", ledger)
    employment_record_path = fixture_root / "employment_record.json"
    _write_json(employment_record_path, employment_record)
    return employment_record_path, selected_chat_surface


def run_chat_runtime_smoke(
    *,
    engine: str,
    model: str | None = None,
    model_path: str | None = None,
    service: str | None = None,
    chat_surface: str | None = None,
    llm_mode: str = "offline",
    message: str = "보스가 설치 직후 채팅 readiness를 확인합니다.",
    artifact_dir: Path,
) -> dict[str, Any]:
    """Run a public-safe hired-chat smoke against the selected LLM/chat surface."""

    if llm_mode not in {"offline", "auto", "live"}:
        raise ValueError("llm_mode must be one of: offline, auto, live")
    artifact_dir.mkdir(parents=True, exist_ok=True)
    employment_record_path, selected_chat_surface = _write_chat_fixture(
        artifact_dir=artifact_dir,
        engine=engine,
        model=model,
        model_path=model_path,
        service=service,
        chat_surface=chat_surface,
    )
    chat_output_path = artifact_dir / ("chat_turn.live.json" if llm_mode == "live" else "chat_turn.offline.json")
    chat = run_chat_turn_from_employment(
        employment_record_path,
        message=message,
        output_path=chat_output_path,
        llm_mode=llm_mode,
        llm_model=model,
        learn_from_chat=False,
    )
    preflight = chat.get("llm_provider_preflight", {}) if isinstance(chat.get("llm_provider_preflight"), dict) else {}
    llm_result = chat.get("llm_runtime_result", {}) if isinstance(chat.get("llm_runtime_result"), dict) else {}
    status_card = (
        chat.get("chat_runtime_status_card", {})
        if isinstance(chat.get("chat_runtime_status_card"), dict)
        else {}
    )
    trace = chat.get("chat_execution_trace", []) if isinstance(chat.get("chat_execution_trace"), list) else []
    selected_nodes = (
        chat.get("chat_context", {})
        .get("active_memory_route", {})
        .get("selected_nodes", [])
        if isinstance(chat.get("chat_context"), dict)
        else []
    )
    provider_not_ready = chat.get("chat_status") == "needs_configuration"
    passed = chat.get("chat_status") == "completed" and chat.get("stored_private_reasoning_trace") is False
    if llm_mode == "live" and provider_not_ready:
        passed = False
    report = {
        "schema": CHAT_RUNTIME_SMOKE_SCHEMA,
        "created_at_utc": _now(),
        "status": "passed" if passed else chat.get("chat_status", "failed"),
        "passed": passed,
        "engine": engine,
        "service": service or engine,
        "model": model,
        "model_path_present": bool(model_path),
        "chat_surface": _fixture_chat_surface_summary(chat, selected_chat_surface),
        "llm_mode": llm_mode,
        "details": {
            "chat_status": chat.get("chat_status"),
            "reply_generation_mode": chat.get("reply_generation_mode"),
            "conversation_intent": chat.get("conversation_intent"),
            "llm_status": llm_result.get("status"),
            "llm_reason": llm_result.get("reason"),
            "preflight_status": preflight.get("status"),
            "preflight_live_path_selected": preflight.get("live_path_selected"),
            "preflight_network_call_made": preflight.get("network_call_made_by_preflight"),
            "selected_memory_count": len(selected_nodes),
            "trace_steps": [item.get("step") for item in trace if isinstance(item, dict)],
            "stored_private_reasoning_trace": chat.get("stored_private_reasoning_trace"),
            "learning_update_performed": bool(chat.get("chat_learning_update")),
            "provider_not_ready": provider_not_ready,
            "runtime_status_card_schema": status_card.get("schema"),
            "runtime_status_card_status": status_card.get("status"),
            "runtime_status_card_fallback_used": status_card.get("fallback", {}).get("used")
            if isinstance(status_card.get("fallback"), dict)
            else None,
            "runtime_status_card_presented_as_live": status_card.get("fallback", {}).get("presented_as_live")
            if isinstance(status_card.get("fallback"), dict)
            else None,
            "runtime_status_card_learning_decision": status_card.get("learning", {}).get("decision")
            if isinstance(status_card.get("learning"), dict)
            else None,
            "runtime_status_card_user_summary_ko": status_card.get("user_visible_summary", {}).get("ko")
            if isinstance(status_card.get("user_visible_summary"), dict)
            else None,
        },
        "artifacts": {
            "employment_record": str(employment_record_path),
            "chat_turn": str(chat_output_path),
        },
        "data_policy": {
            "secret_values_exported": False,
            "send_private_training_files": False,
            "send_full_session_replay": False,
            "raw_provider_payload_saved": False,
            "private_reasoning_trace": "do_not_store",
            "learning_auto_promotion_performed": False,
        },
    }
    return report


def _fixture_chat_surface_summary(chat: dict[str, Any], selected_chat_surface: dict[str, Any]) -> dict[str, Any]:
    # The concrete selected surface is stored in the employment fixture, while
    # chat output exposes only the bounded employment context.
    return {
        "id": selected_chat_surface.get("id"),
        "name": selected_chat_surface.get("name"),
        "selected_surface_recorded": True,
        "runtime": "hired_chat_path",
        "chat_context_schema": chat.get("chat_context", {}).get("schema")
        if isinstance(chat.get("chat_context"), dict)
        else None,
    }
