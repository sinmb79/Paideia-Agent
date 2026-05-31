from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ONBOARDING_NEXT_STEPS_SCHEMA = "ai22b-paideia-onboarding-next-steps/v1"


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _quote(value: str | Path) -> str:
    text = str(value)
    if not text:
        return '""'
    escaped = text.replace("`", "``").replace('"', '`"')
    return f'"{escaped}"'


def _command(command: str, *, live: bool = False, external_network: bool = False) -> dict[str, Any]:
    return {
        "command": command,
        "live": live,
        "external_network_when_operator_runs": external_network,
    }


def build_onboarding_next_steps(
    *,
    employment_record_path: Path,
    selected_llm_service: dict[str, Any],
    selected_chat_surface: dict[str, Any],
    llm_health: dict[str, Any],
    live_smoke_plan_path: Path | None = None,
    output_path: Path | None = None,
    markdown_output_path: Path | None = None,
) -> dict[str, Any]:
    employment_record_path = employment_record_path.expanduser().resolve()
    installed_dir = employment_record_path.parent
    openclaw_model = (
        selected_llm_service.get("openclaw_model")
        or selected_llm_service.get("selected_model")
        or selected_llm_service.get("default_model")
        or ""
    )
    webchat_url = "http://127.0.0.1:8722/"
    commands = {
        "inspect_runtime": _command(
            "ai22b-talent-foundry doctor-openclaw-employment-runtime "
            f"--employment-record {_quote(employment_record_path)} "
            f"--output {_quote(installed_dir / 'openclaw_employment_runtime_doctor.json')}"
        ),
        "start_webchat_offline": _command(
            "ai22b-talent-foundry run-openclaw-webchat-server "
            f"--employment-record {_quote(employment_record_path)} "
            "--port 8722 --llm-mode offline "
            f"--output-dir {_quote(installed_dir / 'openclaw_webchat_runs')}"
        ),
        "start_webchat_live": _command(
            "ai22b-talent-foundry run-openclaw-webchat-server "
            f"--employment-record {_quote(employment_record_path)} "
            "--port 8722 --llm-mode live "
            f"--output-dir {_quote(installed_dir / 'openclaw_webchat_runs')}",
            live=True,
            external_network=True,
        ),
        "chat_offline": _command(
            "ai22b-talent-foundry chat-hired-agent "
            f"--employment-record {_quote(employment_record_path)} "
            "--message \"안녕, 지금 선택된 LLM/채팅 설정을 요약해줘.\" "
            "--llm-mode offline "
            f"--output {_quote(installed_dir / 'chat_offline_first_turn.json')}"
        ),
        "chat_live": _command(
            "ai22b-talent-foundry chat-hired-agent "
            f"--employment-record {_quote(employment_record_path)} "
            "--message \"안녕, OpenClaw live runtime으로 답해줘.\" "
            "--llm-mode live "
            + (f"--llm-model {_quote(str(openclaw_model))} " if openclaw_model else "")
            + f"--output {_quote(installed_dir / 'chat_live_first_turn.json')}",
            live=True,
            external_network=True,
        ),
        "build_live_smoke_plan": _command(
            "ai22b-talent-foundry build-openclaw-live-smoke-plan "
            f"--employment-record {_quote(employment_record_path)} "
            f"--output {_quote(live_smoke_plan_path or (installed_dir / 'openclaw_live_smoke_plan.json'))} "
            f"--markdown-output {_quote(installed_dir / 'OPENCLAW_LIVE_SMOKE_PLAN.md')}"
        ),
        "run_installed_smoke_offline": _command(
            f"powershell -ExecutionPolicy Bypass -File {_quote(installed_dir / 'run_openclaw_smoke_sequence.ps1')} "
            "-Channel webchat"
        ),
        "run_installed_smoke_live": _command(
            f"powershell -ExecutionPolicy Bypass -File {_quote(installed_dir / 'run_openclaw_smoke_sequence.ps1')} "
            "-Channel webchat -IncludeLive",
            live=True,
            external_network=True,
        ),
    }
    steps = [
        {
            "id": "inspect_runtime",
            "title": "Inspect the selected OpenClaw-compatible runtime",
            "command_id": "inspect_runtime",
            "why": "Confirm the hired talent's provider/model, chat surface, and no-secret runtime policy.",
        },
        {
            "id": "start_webchat",
            "title": "Open local WebChat",
            "command_id": "start_webchat_offline",
            "url": webchat_url,
            "why": "Use the browser chat to switch each turn between offline, auto, and live mode.",
        },
        {
            "id": "offline_first_turn",
            "title": "Run a safe offline first chat turn",
            "command_id": "chat_offline",
            "why": "Verify local Paideia memory and chat routing without external network use.",
        },
        {
            "id": "live_first_turn",
            "title": "Run a live OpenClaw LLM turn only after auth is ready",
            "command_id": "chat_live",
            "why": "Verify that the selected OpenClaw provider/model can act as the live language engine.",
        },
        {
            "id": "smoke_sequence",
            "title": "Run OpenClaw smoke checks",
            "command_id": "run_installed_smoke_offline",
            "live_command_id": "run_installed_smoke_live",
            "why": "Validate offline context, runtime preflight, and optional live CLI/Gateway/channel probes.",
        },
    ]
    next_steps = {
        "schema": ONBOARDING_NEXT_STEPS_SCHEMA,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "employment_record": str(employment_record_path),
        "selection": {
            "llm_service_id": selected_llm_service.get("service_id"),
            "llm_engine": selected_llm_service.get("engine"),
            "api_protocol": selected_llm_service.get("api_protocol"),
            "openclaw_provider_id": selected_llm_service.get("openclaw_provider_id"),
            "openclaw_model": openclaw_model,
            "chat_surface_id": selected_chat_surface.get("id"),
            "chat_channel": selected_chat_surface.get("openclaw_channel_id") or "webchat",
            "llm_health_status": llm_health.get("status"),
        },
        "commands": commands,
        "steps": steps,
        "webchat": {
            "url": webchat_url,
            "runtime_endpoint": f"{webchat_url.rstrip('/')}/api/runtime",
            "smoke_plan_endpoint": f"{webchat_url.rstrip('/')}/api/smoke-plan",
            "per_turn_modes": ["offline", "auto", "live"],
            "supports_provider_model_override": True,
        },
        "policy": {
            "secret_values_stored": False,
            "external_network_by_default": False,
            "live_steps_require_operator_opt_in": True,
            "llm_identity_policy": "application_engine_not_identity",
        },
    }
    if output_path:
        _write_json(output_path, next_steps)
    if markdown_output_path:
        render_onboarding_next_steps_markdown(next_steps, output_path=markdown_output_path)
    return next_steps


def render_onboarding_next_steps_markdown(
    next_steps: dict[str, Any],
    *,
    output_path: Path | None = None,
) -> str:
    selection = next_steps.get("selection", {})
    commands = next_steps.get("commands", {})
    lines = [
        "# Paideia Agent Next Steps",
        "",
        f"- LLM service: `{selection.get('llm_service_id')}`",
        f"- Runtime engine: `{selection.get('llm_engine')}`",
        f"- Provider/model: `{selection.get('openclaw_model') or 'not selected'}`",
        f"- Chat surface: `{selection.get('chat_surface_id')}`",
        f"- LLM health: `{selection.get('llm_health_status')}`",
        "",
        "## Recommended Flow",
        "",
    ]
    for step in next_steps.get("steps", []):
        command = commands.get(step.get("command_id"), {})
        lines.extend(
            [
                f"### {step.get('title')}",
                "",
                str(step.get("why") or ""),
                "",
                "```powershell",
                str(command.get("command") or ""),
                "```",
                "",
            ]
        )
        live_command = commands.get(step.get("live_command_id"), {})
        if live_command:
            lines.extend(["Live option:", "", "```powershell", str(live_command.get("command") or ""), "```", ""])
        if step.get("url"):
            lines.extend([f"Open: {step['url']}", ""])
    lines.extend(
        [
            "## Safety Boundary",
            "",
            "- Offline steps are the default.",
            "- Live steps may contact the selected provider or OpenClaw runtime only when the operator chooses them.",
            "- Provider keys, bot tokens, OAuth refresh tokens, QR sessions, and private training files are not stored in this guide.",
            "",
        ]
    )
    markdown = "\n".join(lines).rstrip() + "\n"
    if output_path:
        _write_text(output_path, markdown)
    return markdown
