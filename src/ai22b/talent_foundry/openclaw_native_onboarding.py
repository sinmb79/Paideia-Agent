from __future__ import annotations

import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


OPENCLAW_NATIVE_ONBOARDING_RUNBOOK_SCHEMA = "ai22b-openclaw-native-onboarding-runbook/v1"


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _ps_quote(value: str | Path) -> str:
    text = str(value)
    escaped = text.replace("`", "``").replace('"', '`"')
    return f'"{escaped}"'


def _safe_agent_id(bundle: dict[str, Any]) -> str:
    handoff = bundle.get("openclaw_native_handoff", {})
    agent_id = str(handoff.get("paideia_agent", {}).get("agent_id") or "").strip()
    if agent_id:
        return agent_id
    name = str(bundle.get("employment", {}).get("agent", {}).get("name") or "paideia-agent")
    normalized = re.sub(r"[^a-zA-Z0-9_-]+", "-", name).strip("-").casefold()
    return normalized or "paideia-agent"


def _channels(bundle: dict[str, Any]) -> list[str]:
    values = [str(item).strip() for item in bundle.get("selection", {}).get("channels", [])]
    return [item for item in values if item] or ["webchat"]


def _channel_bind_args(channels: list[str]) -> str:
    return " ".join(f"--bind {channel}:*" for channel in channels)


def _channel_help_commands(channels: list[str]) -> list[str]:
    return [f"openclaw channels add --channel {channel} --help" for channel in channels if channel != "webchat"]


def _step(
    step_id: str,
    title: str,
    purpose: str,
    commands: list[str],
    *,
    artifacts: list[str] | None = None,
    owner_review_required: bool = True,
) -> dict[str, Any]:
    safe_artifacts = [
        str(item)
        for item in artifacts or []
        if item is not None and str(item).strip() and str(item) != "None"
    ]
    return {
        "id": step_id,
        "title": title,
        "purpose": purpose,
        "commands": commands,
        "artifacts": safe_artifacts,
        "owner_review_required": owner_review_required,
        "secret_values_stored": False,
    }


def build_openclaw_native_onboarding_runbook_from_bundle(
    bundle: dict[str, Any],
    *,
    runtime_bundle_path: Path,
    output_path: Path | None = None,
    markdown_output_path: Path | None = None,
) -> dict[str, Any]:
    if bundle.get("schema") != "ai22b-openclaw-runtime-bundle/v1":
        raise ValueError("Unsupported OpenClaw runtime bundle schema")

    runtime_bundle_path = runtime_bundle_path.expanduser().resolve()
    selection = bundle.get("selection", {})
    employment = bundle.get("employment", {})
    artifacts = bundle.get("artifacts", {})
    native_handoff = bundle.get("openclaw_native_handoff", {})
    agent = employment.get("agent", {})
    provider_id = str(selection.get("provider_id") or "")
    model = str(selection.get("model") or "<provider/model>")
    channels = _channels(bundle)
    bind_host = str(selection.get("bind_host") or "127.0.0.1")
    port = int(selection.get("port") or 8722)
    employment_record = Path(str(employment.get("employment_record") or runtime_bundle_path.parent / "employment_record.json"))
    workspace = Path(str(native_handoff.get("paideia_agent", {}).get("workspace") or employment_record.parent))
    agent_id = _safe_agent_id(bundle)
    openclaw_binary = shutil.which("openclaw")
    gateway_url = f"http://{bind_host}:{port}/openclaw/channel-message"
    webchat_url = f"http://{bind_host}:{port}/"
    native_patch = artifacts.get("openclaw_config_patch")
    existing_review = artifacts.get("existing_openclaw_config_review")
    live_smoke_plan_path = runtime_bundle_path.parent / "openclaw_live_smoke_plan.json"
    live_smoke_plan_markdown_path = runtime_bundle_path.parent / "OPENCLAW_LIVE_SMOKE_PLAN.md"
    preflight_path = runtime_bundle_path.parent / "openclaw_runtime_preflight.json"

    interactive_onboard = "openclaw onboard"
    noninteractive_onboard = (
        "openclaw onboard --non-interactive --mode local --auth-choice skip "
        "--gateway-auth token --gateway-token-ref-env OPENCLAW_GATEWAY_TOKEN "
        "--skip-skills --json"
    )
    add_agent_command = (
        f"openclaw agents add {agent_id} "
        f"--workspace {_ps_quote(workspace)} "
        f"--model {model} "
        f"{_channel_bind_args(channels)} "
        "--non-interactive --json"
    )

    steps = [
        _step(
            "detect_existing_config",
            "Detect existing OpenClaw config",
            "Match OpenClaw's first-run behavior: keep, review/update, or reset only after owner review.",
            [
                "ai22b-talent-foundry doctor-openclaw-installed-runtime --output openclaw_installed_runtime_doctor.json",
                "openclaw doctor",
                "openclaw status --deep",
                f"Review Paideia config review artifact: {_ps_quote(existing_review or '<existing_config_review.json>')}",
            ],
            artifacts=[str(existing_review)] if existing_review else [],
        ),
        _step(
            "run_openclaw_onboard",
            "Run OpenClaw onboarding",
            "Let OpenClaw own native provider auth, OAuth, Gateway token, channel plugin setup, and health checks.",
            [
                interactive_onboard,
                noninteractive_onboard,
            ],
        ),
        _step(
            "model_auth",
            "Configure provider/model",
            "Use OpenClaw's provider/model selector while keeping Paideia identity in local education artifacts.",
            [
                "openclaw models auth list",
                "openclaw config --section model",
                f"Set or confirm agents.defaults.model.primary = {model}",
            ],
        ),
        _step(
            "workspace",
            "Prepare workspace",
            "Mount this hired Paideia talent as an OpenClaw workspace-scoped agent.",
            [
                f"openclaw setup --workspace {_ps_quote(workspace)}",
                add_agent_command,
            ],
        ),
        _step(
            "gateway",
            "Start Gateway and Paideia loopback",
            "Run OpenClaw Gateway for native channels and Paideia's loopback gateway for memory-backed replies.",
            [
                "openclaw gateway run",
                "openclaw health",
                (
                    "ai22b-talent-foundry run-openclaw-channel-gateway-server "
                    f"--employment-record {_ps_quote(employment_record)} "
                    + " ".join(f"--channel {channel}" for channel in channels)
                    + f" --bind-host {bind_host} --port {port}"
                ),
            ],
            artifacts=[str(artifacts.get("gateway_config")), str(artifacts.get("channel_access_config"))],
        ),
        _step(
            "channels",
            "Pair channels",
            "Use OpenClaw channel plugins, QR flows, tokens, and allowlists before enabling external delivery.",
            [
                "openclaw channels list --all",
                *_channel_help_commands(channels),
                "openclaw channels status --probe --json",
                "openclaw pairing list",
                "openclaw pairing approve <channel> <code>",
            ],
            artifacts=[
                str(artifacts.get("channel_pairing_doctor")),
                str(artifacts.get("bridge_channel_plugin_plan")),
                str(artifacts.get("bridge_channel_access_config")),
            ],
        ),
        _step(
            "merge_review",
            "Review config patch",
            "Apply only owner-reviewed config changes; Paideia never overwrites OpenClaw config during runbook creation.",
            [
                f"Review {_ps_quote(native_patch or '<openclaw_config_patch.json>')}",
                (
                    "ai22b-talent-foundry prepare-openclaw-native-config "
                    f"--handoff {_ps_quote(artifacts.get('openclaw_native_handoff') or '<openclaw_native_handoff.json>')} "
                    "--mode plan "
                    f"--output {_ps_quote(runtime_bundle_path.parent / 'openclaw_native_config_merge.plan.json')}"
                ),
            ],
            artifacts=[str(native_patch)] if native_patch else [],
        ),
        _step(
            "preflight",
            "Run runtime preflight",
            "Check provider auth, channel pairing, native handoff, Gateway LLM, and offline channel flow.",
            [
                (
                    "ai22b-talent-foundry doctor-openclaw-runtime-preflight "
                    f"--runtime-bundle {_ps_quote(runtime_bundle_path)} "
                    "--run-channel-flow "
                    f"--output {_ps_quote(preflight_path)}"
                )
            ],
        ),
        _step(
            "smoke_test",
            "Run smoke tests",
            "Start offline, then explicitly opt in to Gateway/live LLM/live channel probes.",
            [
                (
                    "ai22b-talent-foundry build-openclaw-live-smoke-plan "
                    f"--employment-record {_ps_quote(employment_record)} "
                    f"--runtime-bundle {_ps_quote(runtime_bundle_path)} "
                    f"--output {_ps_quote(live_smoke_plan_path)} "
                    f"--markdown-output {_ps_quote(live_smoke_plan_markdown_path)}"
                ),
                "powershell -ExecutionPolicy Bypass -File .\\run_openclaw_smoke_sequence.ps1 -Channel webchat",
                "powershell -ExecutionPolicy Bypass -File .\\run_openclaw_smoke_sequence.ps1 -Channel webchat -IncludeLive",
            ],
        ),
        _step(
            "finish",
            "Open chat",
            "Choose local WebChat, terminal chat, or the paired OpenClaw channel after smoke tests pass.",
            [
                (
                    "ai22b-talent-foundry run-openclaw-webchat-server "
                    f"--employment-record {_ps_quote(employment_record)} --bind-host {bind_host} --port {port}"
                ),
                f"Open {webchat_url}",
            ],
            owner_review_required=False,
        ),
    ]

    runbook = {
        "schema": OPENCLAW_NATIVE_ONBOARDING_RUNBOOK_SCHEMA,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "ready_for_owner_review",
        "runtime_bundle": str(runtime_bundle_path),
        "openclaw_cli": {
            "binary": openclaw_binary or "openclaw",
            "detected_on_path": bool(openclaw_binary),
            "native_setup_required_if_missing": not bool(openclaw_binary),
        },
        "selection": {
            "agent_id": agent_id,
            "agent_name": agent.get("name"),
            "provider_id": provider_id,
            "model": model,
            "channels": channels,
            "workspace": str(workspace),
            "gateway_url": gateway_url,
            "webchat_url": webchat_url,
        },
        "openclaw_flow_mirroring": [
            "existing_config_detection",
            "model_auth",
            "workspace",
            "gateway",
            "channels",
            "skills_are_reviewed_separately",
            "health_check",
            "finish_terminal_webchat_or_channel",
        ],
        "steps": steps,
        "policy": {
            "secret_values_stored": False,
            "private_training_files_exported": False,
            "openclaw_config_written": False,
            "external_network_call_performed": False,
            "native_provider_auth_owned_by_openclaw": True,
            "native_channel_pairing_owned_by_openclaw": True,
        },
        "source_docs_checked": [
            "https://docs.openclaw.ai/reference/wizard",
            "https://docs.openclaw.ai/providers",
            "https://docs.openclaw.ai/channels",
            "https://docs.openclaw.ai/channels/channel-routing",
        ],
    }
    if output_path is not None:
        _write_json(output_path, runbook)
    if markdown_output_path is not None:
        render_openclaw_native_onboarding_runbook_markdown(runbook, output_path=markdown_output_path)
    return runbook


def build_openclaw_native_onboarding_runbook(
    runtime_bundle_path: Path,
    *,
    output_path: Path | None = None,
    markdown_output_path: Path | None = None,
) -> dict[str, Any]:
    runtime_bundle_path = runtime_bundle_path.expanduser().resolve()
    bundle = _read_json(runtime_bundle_path)
    return build_openclaw_native_onboarding_runbook_from_bundle(
        bundle,
        runtime_bundle_path=runtime_bundle_path,
        output_path=output_path,
        markdown_output_path=markdown_output_path,
    )


def render_openclaw_native_onboarding_runbook_markdown(
    runbook: dict[str, Any],
    *,
    output_path: Path | None = None,
) -> str:
    selection = runbook.get("selection", {})
    lines = [
        "# OpenClaw Native Onboarding Runbook",
        "",
        f"- Status: `{runbook.get('status')}`",
        f"- Agent: `{selection.get('agent_name')}` (`{selection.get('agent_id')}`)",
        f"- Provider/model: `{selection.get('model')}`",
        f"- Channels: `{', '.join(selection.get('channels') or [])}`",
        f"- Workspace: `{selection.get('workspace')}`",
        f"- OpenClaw CLI detected: `{runbook.get('openclaw_cli', {}).get('detected_on_path')}`",
        "",
        "This runbook mirrors the OpenClaw onboarding order while preserving Paideia's boundary: OpenClaw owns native provider auth, channel plugins, QR/session state, and final delivery; Paideia owns the local education records, memory substrate, and Reasoning Ledger.",
        "",
        "## Steps",
        "",
    ]
    for index, step in enumerate(runbook.get("steps", []), start=1):
        lines.extend(
            [
                f"### {index}. {step.get('title')}",
                "",
                str(step.get("purpose") or ""),
                "",
            ]
        )
        for command in step.get("commands", []):
            lines.extend(["```powershell", str(command), "```", ""])
        if step.get("artifacts"):
            artifacts = [str(item) for item in step["artifacts"] if str(item) and str(item) != "None"]
            if artifacts:
                lines.append("Artifacts:")
                for artifact in artifacts:
                    lines.append(f"- `{artifact}`")
                lines.append("")
    lines.extend(
        [
            "## Safety Boundary",
            "",
            "- Runbook generation performs no network call.",
            "- No provider key, bot token, OAuth refresh token, QR session, or private training file is stored.",
            "- OpenClaw config merge remains review-first and owner-approved.",
            "",
        ]
    )
    markdown = "\n".join(lines).rstrip() + "\n"
    if output_path is not None:
        _write_text(output_path, markdown)
    return markdown
