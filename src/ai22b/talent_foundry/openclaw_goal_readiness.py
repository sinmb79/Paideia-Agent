from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ai22b.talent_foundry.onboarding_choices import build_llm_service_health
from ai22b.talent_foundry.onboarding_next_steps import build_onboarding_next_steps
from ai22b.talent_foundry.openclaw_employment_runtime import build_openclaw_employment_runtime_doctor
from ai22b.talent_foundry.openclaw_installed_runtime import doctor_openclaw_installed_runtime
from ai22b.talent_foundry.openclaw_live_smoke_plan import build_openclaw_live_smoke_plan
from ai22b.talent_foundry.openclaw_support_matrix import build_openclaw_support_matrix


OPENCLAW_GOAL_READINESS_AUDIT_SCHEMA = "ai22b-paideia-openclaw-goal-readiness-audit/v1"
OPENCLAW_NATIVE_ENGINES = {
    "openclaw_cli_local",
    "openclaw_gateway_http",
    "openclaw_openai_compatible",
    "openclaw_anthropic_compatible",
    "openclaw_manifest_only",
}


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _check(
    check_id: str,
    passed: bool,
    *,
    evidence: dict[str, Any] | None = None,
    required: bool = True,
    next_action: str | None = None,
) -> dict[str, Any]:
    return {
        "id": check_id,
        "passed": passed,
        "required": required,
        "evidence": evidence or {},
        "next_action": next_action,
    }


def _support_matrix_catalog_ready(support_matrix: dict[str, Any]) -> bool:
    coverage = support_matrix.get("coverage", {})
    providers = coverage.get("providers", {}) if isinstance(coverage.get("providers"), dict) else {}
    channels = coverage.get("channels", {}) if isinstance(coverage.get("channels"), dict) else {}
    return (
        support_matrix.get("status") == "pass"
        and providers.get("parity_missing_count") == 0
        and channels.get("parity_missing_count") == 0
    )


def _selected_model(llm: dict[str, Any]) -> str:
    return str(llm.get("openclaw_model") or llm.get("selected_model") or llm.get("openclaw_agent_target") or "")


def _selected_llm_is_openclaw_compatible(llm: dict[str, Any]) -> bool:
    engine = str(llm.get("engine") or "")
    api_protocol = str(llm.get("api_protocol") or "")
    return (
        bool(llm.get("openclaw_provider_id"))
        or engine in OPENCLAW_NATIVE_ENGINES
        or api_protocol.startswith("openclaw_")
    )


def _selected_chat_is_openclaw_compatible(chat: dict[str, Any]) -> bool:
    surface_id = str(chat.get("surface_id") or "")
    channels = chat.get("openclaw_channels") or []
    return bool(channels) or surface_id.startswith("openclaw-channel-") or surface_id == "openclaw-style-gateway"


def _webchat_controls_ready(next_steps: dict[str, Any]) -> bool:
    webchat = next_steps.get("webchat", {})
    modes = set(webchat.get("per_turn_modes") or [])
    return {"offline", "auto", "live"}.issubset(modes) and bool(webchat.get("supports_provider_model_override"))


def _smoke_plan_ready(smoke_plan: dict[str, Any]) -> bool:
    sequence = set(smoke_plan.get("operator_sequence") or [])
    commands = smoke_plan.get("commands", {})
    required_steps = {
        "offline_context_smoke",
        "openclaw_cli_live_probe",
        "gateway_live_probe",
        "live_llm_chat_smoke",
        "live_channel_message_smoke",
    }
    return (
        required_steps.issubset(sequence)
        and bool(commands.get("openclaw_cli_live_probe"))
        and bool(commands.get("gateway_live_probe"))
        and smoke_plan.get("policy", {}).get("external_network_call_performed_by_plan") is False
    )


def _installed_runtime_ready(installed_runtime: dict[str, Any] | None, selected_engine: str) -> bool:
    if installed_runtime is None:
        return selected_engine not in {"openclaw_cli_local", "openclaw_gateway_http"}
    status = str(installed_runtime.get("status") or "")
    return status != "openclaw_cli_not_found"


def _secret_policy_ready(*artifacts: dict[str, Any]) -> bool:
    for artifact in artifacts:
        policy = artifact.get("policy", {})
        if (
            isinstance(policy, dict)
            and "secret_values_stored" in policy
            and policy.get("secret_values_stored") is not False
        ):
            return False
        claim_boundary = artifact.get("claim_boundary", {})
        if (
            isinstance(claim_boundary, dict)
            and "secret_values_stored" in claim_boundary
            and claim_boundary.get("secret_values_stored") is not False
        ):
            return False
    return True


def _overall_status(checks: list[dict[str, Any]], installed_runtime: dict[str, Any] | None) -> str:
    failed_required = [check for check in checks if check.get("required") and not check.get("passed")]
    if failed_required:
        return "needs_attention"
    installed_status = str((installed_runtime or {}).get("status") or "")
    if installed_status in {"ready_with_openclaw_gateway", "ready_for_gateway_start", "ready_for_openclaw_probe"}:
        return "ready_for_live_operator_validation"
    return "ready_for_openclaw_style_runtime_without_live_probe"


def audit_openclaw_goal_readiness(
    employment_record_path: Path,
    *,
    channels: list[str] | None = None,
    output_path: Path | None = None,
    summary_output_path: Path | None = None,
    refresh_docs: bool = False,
    docs_timeout: int = 15,
    timeout_seconds: int = 20,
    probe_installed_runtime: bool = True,
) -> dict[str, Any]:
    """Audit the end-to-end OpenClaw-style LLM/chat readiness for one hired talent.

    This is a no-secret, no-live-network audit. It may run read-only OpenClaw CLI
    status commands, but it does not invoke provider auth probes or chat probes.
    """

    employment_record_path = employment_record_path.expanduser().resolve()
    employment = _read_json(employment_record_path)
    if employment.get("schema") != "ai-talent-local-employment/v1":
        raise ValueError("Unsupported local employment record schema")
    if employment.get("status") != "active":
        raise ValueError("Local employment record is not active")

    runtime_doctor = build_openclaw_employment_runtime_doctor(
        employment_record_path,
        channels=channels,
        refresh_docs=refresh_docs,
        docs_timeout=docs_timeout,
    )
    smoke_plan = build_openclaw_live_smoke_plan(
        employment_record_path,
        channels=channels,
        refresh_docs=refresh_docs,
        docs_timeout=docs_timeout,
    )
    llm_health = build_llm_service_health(employment.get("llm_service", {}) or {})
    next_steps = build_onboarding_next_steps(
        employment_record_path=employment_record_path,
        selected_llm_service=employment.get("llm_service", {}) or {},
        selected_chat_surface=employment.get("chat_surface", {}) or {},
        llm_health=llm_health,
        live_smoke_plan_path=employment_record_path.parent / "openclaw_live_smoke_plan.json",
    )
    support_matrix = build_openclaw_support_matrix(refresh_docs=refresh_docs, docs_timeout=docs_timeout)
    installed_runtime = (
        doctor_openclaw_installed_runtime(timeout_seconds=timeout_seconds, probe_gateway=False)
        if probe_installed_runtime
        else None
    )

    selection = runtime_doctor.get("runtime_selection", {})
    llm = selection.get("llm", {})
    chat = selection.get("chat", {})
    selected_engine = str(llm.get("engine") or "")
    selected_model = _selected_model(llm)
    channel_ids = [item.get("channel_id") for item in chat.get("openclaw_channels", []) if item.get("channel_id")]

    checks = [
        _check(
            "openclaw_provider_channel_catalog_parity",
            _support_matrix_catalog_ready(support_matrix),
            evidence={
                "support_matrix_status": support_matrix.get("status"),
                "provider_missing_count": support_matrix.get("coverage", {}).get("providers", {}).get("parity_missing_count"),
                "channel_missing_count": support_matrix.get("coverage", {}).get("channels", {}).get("parity_missing_count"),
            },
            next_action="Run audit-openclaw-parity --refresh-docs if this fails.",
        ),
        _check(
            "selected_llm_is_openclaw_compatible",
            _selected_llm_is_openclaw_compatible(llm),
            evidence={
                "service_id": llm.get("service_id"),
                "engine": selected_engine,
                "api_protocol": llm.get("api_protocol"),
                "openclaw_provider_id": llm.get("openclaw_provider_id"),
            },
            next_action="Select openclaw_cli_local, openclaw_gateway_http, or an OpenClaw provider/model selector.",
        ),
        _check(
            "provider_model_selector_preserved",
            bool(selected_model),
            evidence={
                "openclaw_model": llm.get("openclaw_model"),
                "selected_model": llm.get("selected_model"),
                "openclaw_agent_target": llm.get("openclaw_agent_target"),
            },
            next_action="Provide --llm-model provider/model or let OpenClaw Gateway use openclaw/default.",
        ),
        _check(
            "selected_chat_is_openclaw_compatible",
            _selected_chat_is_openclaw_compatible(chat),
            evidence={
                "surface_id": chat.get("surface_id"),
                "channel_ids": channel_ids,
                "entrypoint": chat.get("entrypoint"),
            },
            next_action="Select openclaw-channel-webchat, openclaw-channel-telegram, or another OpenClaw channel.",
        ),
        _check(
            "webchat_per_turn_runtime_controls",
            _webchat_controls_ready(next_steps),
            evidence=next_steps.get("webchat", {}),
            next_action="Regenerate onboarding next steps or run a newer Paideia WebChat server.",
        ),
        _check(
            "live_smoke_plan_includes_cli_gateway_and_channel_probes",
            _smoke_plan_ready(smoke_plan),
            evidence={
                "status": smoke_plan.get("status"),
                "operator_sequence": smoke_plan.get("operator_sequence"),
                "external_network_call_performed_by_plan": smoke_plan.get("policy", {}).get("external_network_call_performed_by_plan"),
            },
            next_action="Regenerate build-openclaw-live-smoke-plan before attempting live tests.",
        ),
        _check(
            "installed_openclaw_runtime_detected",
            _installed_runtime_ready(installed_runtime, selected_engine),
            evidence={
                "selected_engine": selected_engine,
                "installed_runtime_status": (installed_runtime or {}).get("status"),
                "cli_detected_on_path": (installed_runtime or {}).get("openclaw_cli", {}).get("detected_on_path"),
            },
            next_action="Install/configure OpenClaw CLI or choose a direct local/provider adapter for non-OpenClaw runs.",
        ),
        _check(
            "secret_and_live_network_policy",
            _secret_policy_ready(runtime_doctor, smoke_plan, next_steps, installed_runtime or {}),
            evidence={
                "runtime_doctor_secrets": runtime_doctor.get("claim_boundary", {}).get("secret_values_stored"),
                "smoke_plan_secrets": smoke_plan.get("policy", {}).get("secret_values_stored"),
                "next_steps_secrets": next_steps.get("policy", {}).get("secret_values_stored"),
                "installed_runtime_secrets": (installed_runtime or {}).get("policy", {}).get("secret_values_stored"),
                "live_network_by_default": next_steps.get("policy", {}).get("external_network_by_default"),
            },
            next_action="Remove secret values from generated artifacts and keep live probes opt-in.",
        ),
    ]

    audit = {
        "schema": OPENCLAW_GOAL_READINESS_AUDIT_SCHEMA,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": _overall_status(checks, installed_runtime),
        "employment_record": str(employment_record_path),
        "selection": {
            "agent": selection.get("agent", {}),
            "llm_service_id": llm.get("service_id"),
            "llm_engine": selected_engine,
            "api_protocol": llm.get("api_protocol"),
            "openclaw_provider_id": llm.get("openclaw_provider_id"),
            "openclaw_model": selected_model,
            "chat_surface_id": chat.get("surface_id"),
            "openclaw_channel_ids": channel_ids,
            "webchat_url": next_steps.get("webchat", {}).get("url"),
        },
        "checks": checks,
        "runtime_doctor": {
            "schema": runtime_doctor.get("schema"),
            "status": runtime_doctor.get("status"),
            "llm_service_health_status": runtime_doctor.get("llm_service_health", {}).get("status"),
            "provider_support_level": (runtime_doctor.get("openclaw_support", {}).get("provider") or {}).get("support_level"),
            "channel_support_levels": [
                {
                    "channel_id": item.get("channel_id"),
                    "support_level": (item.get("support") or {}).get("support_level"),
                }
                for item in runtime_doctor.get("openclaw_support", {}).get("channels", [])
            ],
        },
        "installed_runtime": {
            "schema": (installed_runtime or {}).get("schema"),
            "status": (installed_runtime or {}).get("status") if installed_runtime is not None else "not_probed",
            "summary": (installed_runtime or {}).get("summary", {}),
            "openclaw_cli": (installed_runtime or {}).get("openclaw_cli", {}),
            "policy": (installed_runtime or {}).get("policy", {}),
        },
        "webchat": next_steps.get("webchat", {}),
        "live_smoke_plan": {
            "schema": smoke_plan.get("schema"),
            "status": smoke_plan.get("status"),
            "operator_sequence": smoke_plan.get("operator_sequence"),
            "selection": smoke_plan.get("selection"),
            "policy": smoke_plan.get("policy"),
        },
        "next_commands": {
            "inspect_runtime": next_steps.get("commands", {}).get("inspect_runtime", {}).get("command"),
            "start_webchat_offline": next_steps.get("commands", {}).get("start_webchat_offline", {}).get("command"),
            "chat_live": next_steps.get("commands", {}).get("chat_live", {}).get("command"),
            "build_live_smoke_plan": next_steps.get("commands", {}).get("build_live_smoke_plan", {}).get("command"),
            "doctor_installed_openclaw": (
                "ai22b-talent-foundry doctor-openclaw-installed-runtime "
                "--output openclaw_installed_runtime_doctor.json"
            ),
        },
        "claim_boundary": {
            "what_this_proves": (
                "The hired Paideia talent has an OpenClaw-compatible provider/model route, "
                "OpenClaw-style chat route, WebChat runtime controls, no-secret next steps, "
                "and a live smoke plan that keeps real network probes opt-in."
            ),
            "what_this_does_not_prove": (
                "It does not perform paid provider calls, OAuth pairing, QR login, bot-token delivery, "
                "or live OpenClaw Gateway chat unless the operator later runs the generated live commands."
            ),
            "secret_values_stored": False,
            "external_network_call_performed": False,
        },
    }
    if output_path:
        _write_json(output_path, audit)
    if summary_output_path:
        render_openclaw_goal_readiness_summary(audit, output_path=summary_output_path)
    return audit


def render_openclaw_goal_readiness_summary(
    audit: dict[str, Any],
    *,
    output_path: Path | None = None,
) -> str:
    selection = audit.get("selection", {})
    lines = [
        "# Paideia OpenClaw Goal Readiness",
        "",
        f"- Status: `{audit.get('status')}`",
        f"- Agent: `{selection.get('agent', {}).get('name')}`",
        f"- LLM engine: `{selection.get('llm_engine')}`",
        f"- Provider/model: `{selection.get('openclaw_model')}`",
        f"- Chat surface: `{selection.get('chat_surface_id')}`",
        f"- Channels: `{', '.join(selection.get('openclaw_channel_ids') or []) or 'none'}`",
        f"- WebChat: `{selection.get('webchat_url')}`",
        "",
        "## Checks",
        "",
    ]
    for check in audit.get("checks", []):
        lines.append(f"- `{check.get('id')}`: `{check.get('passed')}`")
        if not check.get("passed") and check.get("next_action"):
            lines.append(f"  Next: {check.get('next_action')}")
    lines.extend(["", "## Next Commands", ""])
    for key, command in (audit.get("next_commands") or {}).items():
        if not command:
            continue
        lines.extend([f"### {key}", "", "```powershell", str(command), "```", ""])
    lines.extend(
        [
            "## Boundary",
            "",
            "- This audit is read-only and stores no provider keys, bot tokens, OAuth sessions, or QR material.",
            "- Live provider, Gateway, and external channel probes remain explicit operator actions.",
            "",
        ]
    )
    markdown = "\n".join(lines).rstrip() + "\n"
    if output_path:
        _write_text(output_path, markdown)
    return markdown
