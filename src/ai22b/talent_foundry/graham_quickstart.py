from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ai22b.config import PROJECT_ROOT, talent_foundry_storage_path
from ai22b.talent_foundry.console import run_console_session
from ai22b.talent_foundry.memory_substrate import run_chat_turn_from_employment
from ai22b.talent_foundry.openclaw_channel_flow import doctor_openclaw_channel_flow


GRAHAM_JUNIOR_QUICKSTART_SCHEMA = "ai22b-graham-junior-quickstart/v1"
DEFAULT_GRAHAM_ANSWERS_PATH = PROJECT_ROOT / "examples" / "graham_junior_onboarding.answers.json"
DEFAULT_GRAHAM_QUICKSTART_OUTPUT_DIR = talent_foundry_storage_path("runs", "graham_junior_quickstart")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _apply_override(answers: dict[str, Any], key: str, value: str | None) -> None:
    if value is not None:
        answers[key] = value


def _exists(path_text: str | None) -> bool:
    return bool(path_text) and Path(path_text).exists()


def run_graham_junior_quickstart(
    *,
    output_dir: Path = DEFAULT_GRAHAM_QUICKSTART_OUTPUT_DIR,
    answers_path: Path = DEFAULT_GRAHAM_ANSWERS_PATH,
    output_path: Path | None = None,
    llm_service: str | None = None,
    llm_model: str | None = None,
    llm_model_path: str | None = None,
    chat_surface: str | None = None,
    channels: list[str] | None = None,
    message: str = "Graham Junior quickstart: summarize your training record and how I can chat with you.",
    llm_mode: str = "offline",
    learn_from_chat: bool = False,
) -> dict[str, Any]:
    if llm_mode not in {"offline", "auto", "live"}:
        raise ValueError("llm_mode must be offline, auto, or live")
    answers_path = answers_path.expanduser().resolve()
    output_dir = output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = (output_path or output_dir / "graham_junior_quickstart.json").expanduser().resolve()

    answers = _read_json(answers_path)
    _apply_override(answers, "llm_service", llm_service)
    _apply_override(answers, "llm_model", llm_model)
    _apply_override(answers, "llm_model_path", llm_model_path)
    _apply_override(answers, "chat_surface", chat_surface)

    console_session_path = output_dir / "console_session.json"
    console_session = run_console_session(
        answers=answers,
        output_dir=output_dir,
        output_path=console_session_path,
    )
    employment_record_path = Path(console_session["artifacts"]["employment_record"])
    first_chat_path = output_dir / "first_chat.json"
    first_chat = run_chat_turn_from_employment(
        employment_record_path,
        message=message,
        output_path=first_chat_path,
        llm_mode=llm_mode,
        learn_from_chat=learn_from_chat,
    )
    channel_flow_path = output_dir / "openclaw_channel_flow_doctor.json"
    channel_flow = doctor_openclaw_channel_flow(
        employment_record_path,
        channels=channels,
        message=message,
        output_path=channel_flow_path,
        output_dir=output_dir / "openclaw_channel_flow_artifacts",
        llm_mode=llm_mode,
        learn_from_chat=learn_from_chat,
    )

    onboarding = _read_json(Path(console_session["artifacts"]["onboarding_session"]))
    release_bundle_path = Path(onboarding["artifacts"]["release_bundle"])
    hiring_dossier_path = release_bundle_path / "hiring_dossier.json"
    hiring_dossier_markdown_path = release_bundle_path / "HIRING_DOSSIER.ko.md"
    assessment_transcript_path = Path(onboarding["artifacts"]["assessment_transcript"])
    runtime_bundle_path = Path(console_session["artifacts"]["openclaw_runtime_bundle"])
    support_matrix_path = Path(onboarding["artifacts"]["openclaw_support_matrix"])
    support_matrix = _read_json(support_matrix_path)
    selected_support = onboarding.get("openclaw_runtime", {}).get("selected_support", {})
    gateway_llm_doctor_path = console_session["artifacts"].get("openclaw_gateway_llm_doctor")

    checks = [
        {"id": "console_session_created", "passed": console_session_path.exists(), "path": str(console_session_path)},
        {
            "id": "employment_record_created",
            "passed": employment_record_path.exists(),
            "path": str(employment_record_path),
        },
        {
            "id": "assessment_transcript_created",
            "passed": assessment_transcript_path.exists(),
            "path": str(assessment_transcript_path),
        },
        {
            "id": "hiring_dossier_created",
            "passed": hiring_dossier_path.exists() and hiring_dossier_markdown_path.exists(),
            "json": str(hiring_dossier_path),
            "markdown": str(hiring_dossier_markdown_path),
        },
        {
            "id": "first_chat_created",
            "passed": first_chat_path.exists() and len(str(first_chat.get("assistant_answer") or "")) > 5,
            "path": str(first_chat_path),
            "reply_generation_mode": first_chat.get("reply_generation_mode"),
        },
        {
            "id": "openclaw_runtime_bundle_created",
            "passed": runtime_bundle_path.exists(),
            "path": str(runtime_bundle_path),
        },
        {
            "id": "openclaw_support_matrix_passed",
            "passed": support_matrix_path.exists() and support_matrix.get("status") == "pass",
            "path": str(support_matrix_path),
            "provider_id": selected_support.get("provider_id"),
        },
        {
            "id": "openclaw_channel_flow_passed",
            "passed": channel_flow.get("status") == "pass",
            "path": str(channel_flow_path),
        },
        {
            "id": "openclaw_gateway_llm_doctor_created_when_selected",
            "passed": True if not gateway_llm_doctor_path else _exists(str(gateway_llm_doctor_path)),
            "path": gateway_llm_doctor_path,
        },
    ]
    status = "pass" if all(check["passed"] for check in checks) else "needs_attention"
    report = {
        "schema": GRAHAM_JUNIOR_QUICKSTART_SCHEMA,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "answers_path": str(answers_path),
        "selected_llm_service": console_session.get("answers", {}).get("llm_service"),
        "selected_chat_surface": console_session.get("answers", {}).get("chat_surface"),
        "identity": onboarding.get("identity"),
        "track": onboarding.get("track"),
        "artifacts": {
            "quickstart_report": str(output_path),
            "console_session": str(console_session_path),
            "onboarding_session": console_session["artifacts"]["onboarding_session"],
            "employment_record": str(employment_record_path),
            "assessment_transcript": str(assessment_transcript_path),
            "hiring_dossier": str(hiring_dossier_path),
            "hiring_dossier_markdown": str(hiring_dossier_markdown_path),
            "first_chat": str(first_chat_path),
            "openclaw_runtime_bundle": str(runtime_bundle_path),
            "openclaw_support_matrix": str(support_matrix_path),
            "openclaw_channel_flow_doctor": str(channel_flow_path),
            "openclaw_gateway_llm_doctor": gateway_llm_doctor_path,
        },
        "first_chat": {
            "reply_generation_mode": first_chat.get("reply_generation_mode"),
            "conversation_intent": first_chat.get("conversation_intent"),
            "assistant_answer_preview": str(first_chat.get("assistant_answer") or "")[:600],
            "stored_private_reasoning_trace": first_chat.get("stored_private_reasoning_trace"),
        },
        "openclaw_channel_flow": {
            "status": channel_flow.get("status"),
            "summary": channel_flow.get("summary"),
            "external_network_call_performed": channel_flow.get("mode", {}).get("external_network_call_performed"),
        },
        "openclaw_support": {
            "matrix_status": support_matrix.get("status"),
            "coverage": support_matrix.get("coverage"),
            "selected_support": selected_support,
        },
        "checks": checks,
        "next_commands": {
            "chat_again": (
                f"ai22b-talent-foundry chat-hired-agent --employment-record {employment_record_path} "
                '--message "안녕, 네가 배운 과정과 지금 할 수 있는 일을 소개해줘" --output next_chat.json'
            ),
            "doctor_channel_flow": (
                f"ai22b-talent-foundry doctor-openclaw-channel-flow --employment-record {employment_record_path} "
                f"--output {channel_flow_path}"
            ),
            "view_hiring_dossier": str(hiring_dossier_markdown_path),
            "view_assessment_transcript": str(assessment_transcript_path),
        },
        "security": {
            "secret_values_stored": False,
            "private_training_files_exported": False,
            "external_network_delivery_performed": False,
        },
    }
    _write_json(output_path, report)
    return report
