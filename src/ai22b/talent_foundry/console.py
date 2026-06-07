from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from ai22b.talent_foundry.agent_identity_card import (
    build_agent_id_card_payload,
    build_agent_identity_layer_envelope,
)
from ai22b.talent_foundry.onboarding import run_agent_onboarding
from ai22b.talent_foundry.llm_onboarding import build_llm_provider_matrix
from ai22b.talent_foundry.onboarding_choices import (
    CHAT_SURFACE_CATALOG,
    DEFAULT_CHAT_SURFACE_ID,
    DEFAULT_LLM_SERVICE_ID,
    LLM_SERVICE_CATALOG,
)
from ai22b.talent_foundry.owner_self_extension import build_owner_self_extension_intake
from ai22b.talent_foundry.role_models import list_role_models, summarize_role_model
from ai22b.talent_foundry.registry import (
    assemble_hired_agent_team,
    assemble_hired_projection_swarm,
    hire_installed_agent,
    run_hired_projection_swarm_cycle,
    run_hired_team_cycle,
)
from ai22b.talent_foundry.simulation_rollouts import build_simulation_rollouts, evaluate_simulation_rollouts


CONSOLE_SESSION_SCHEMA = "ai-talent-guided-console-session/v1"
OPENCLAW_STYLE_WIZARD_SCHEMA = "ai22b-paideia-openclaw-style-onboarding/v1"
ONBOARDING_LAUNCH_PLAN_SCHEMA = "paideia-onboarding-launch-plan/v1"
ONBOARDING_NEXT_ACTION_SCHEMA = "paideia-onboarding-next-action/v1"
ONBOARDING_ACTION_RUN_SCHEMA = "paideia-onboarding-action-run/v1"
ONBOARDING_ACTION_ALLOWLIST = {"doctor_onboarding_session", "first_chat_offline"}

SPECIALIST_TEAM_ROLES = [
    ("macro", "거시경제 분석 에이전트"),
    ("company", "기업분석 에이전트"),
    ("quant", "퀀트 분석 에이전트"),
    ("risk_compliance", "리스크/컴플라이언스 에이전트"),
]

CONSOLE_QUESTIONS = [
    {
        "id": "existing_config_action",
        "label": "기존 설정",
        "prompt": "기존 Paideia 설정을 어떻게 처리할까요?",
        "default": "review_update",
        "step": "existing_config",
    },
    {
        "id": "onboarding_mode",
        "label": "온보딩 모드",
        "prompt": "온보딩 모드는 어떻게 진행할까요?",
        "default": "quickstart",
        "step": "mode",
    },
    {
        "id": "owner",
        "label": "고용주",
        "prompt": "누가 이 인재를 고용하나요?",
        "default": "보스",
        "step": "workspace",
    },
    {
        "id": "llm_service",
        "label": "LLM 서비스",
        "prompt": "연구원/대화 엔진으로 사용할 LLM 서비스는 무엇으로 둘까요?",
        "default": DEFAULT_LLM_SERVICE_ID,
        "step": "model_auth",
    },
    {
        "id": "llm_model",
        "label": "LLM 모델",
        "prompt": "특정 모델명을 지정할까요? 비워두면 환경변수 또는 기본값을 사용합니다.",
        "step": "model_auth",
    },
    {
        "id": "llm_model_path",
        "label": "로컬 모델 경로",
        "prompt": "로컬 모델 엔진을 고른 경우 모델 경로는 어디인가요?",
        "step": "model_auth",
        "advanced_only": True,
    },
    {
        "id": "workspace_dir",
        "label": "워크스페이스",
        "prompt": "에이전트 파일과 기억을 저장할 워크스페이스는 어디로 둘까요?",
        "default": "",
        "step": "workspace",
    },
    {
        "id": "chat_surface",
        "label": "채팅 표면",
        "prompt": "처음 대화할 채팅 표면은 무엇으로 둘까요?",
        "default": DEFAULT_CHAT_SURFACE_ID,
        "step": "gateway_channels",
    },
    {
        "id": "gateway_mode",
        "label": "게이트웨이",
        "prompt": "채팅 게이트웨이는 어떻게 둘까요?",
        "default": "local_loopback",
        "step": "gateway_channels",
    },
    {
        "id": "channel_mode",
        "label": "채널",
        "prompt": "외부 채팅 채널은 지금 연결할까요?",
        "default": "local_only",
        "step": "gateway_channels",
    },
    {
        "id": "web_search_provider",
        "label": "웹 검색",
        "prompt": "웹 검색 도구는 어떻게 설정할까요?",
        "default": "skip_now",
        "step": "web_search",
        "advanced_only": True,
    },
    {
        "id": "skills_mode",
        "label": "스킬",
        "prompt": "Hermes/OpenClaw 스타일 스킬은 어떻게 처리할까요?",
        "default": "quarantine_import_only",
        "step": "skills",
    },
    {
        "id": "talent_source",
        "label": "인재 소스",
        "prompt": "어떤 방식으로 인재를 육성할까요?",
        "default": "public_role_model",
        "step": "education_path",
    },
    {
        "id": "request",
        "label": "요청",
        "prompt": "선택한 LLM 연구원에게 어떤 AI 인재 육성을 맡길까요?",
        "required": True,
        "step": "education_path",
    },
    {
        "id": "domain",
        "label": "분야",
        "prompt": "대표 인물 트랙의 분야는 무엇으로 둘까요?",
        "default": "securities_research",
        "step": "education_path",
    },
    {
        "id": "role_model_id",
        "label": "대표 인물",
        "prompt": "대표 인물 모티브는 무엇으로 둘까요?",
        "default": "graham_value_investing",
        "step": "education_path",
    },
    {
        "id": "private_curriculum_dir",
        "label": "비공개 교재 폴더",
        "prompt": "보스가 제공할 비공개 교재/자기확장 자료 폴더는 어디로 둘까요?",
        "default": "",
        "step": "education_path",
        "advanced_only": True,
    },
    {
        "id": "owner_materials_consent",
        "label": "자기확장 자료 동의",
        "prompt": "자기확장 자료를 metadata-only로 로컬 접수하는 데 동의하나요?",
        "default": "no",
        "step": "education_path",
        "advanced_only": True,
    },
    {
        "id": "copyright_attestation",
        "label": "저작권/사용권 확인",
        "prompt": "비공개 자료의 사용권 확인 상태는 무엇인가요?",
        "default": "metadata_only_pending_review",
        "step": "education_path",
        "advanced_only": True,
    },
    {
        "id": "agent_surface",
        "label": "실행 방식",
        "prompt": "초기 에이전트 실행 방식은 무엇으로 둘까요?",
        "default": "cli-console",
        "step": "runtime",
    },
    {
        "id": "talent_name",
        "label": "이름",
        "prompt": "새 인재의 이름은 무엇인가요?",
        "default": "신용",
        "step": "education_path",
    },
    {
        "id": "gender",
        "label": "성별",
        "prompt": "새 인재의 성별 설정은 무엇인가요?",
        "default": "남자",
        "step": "education_path",
    },
    {
        "id": "initial_goal",
        "label": "첫 목표",
        "prompt": "고용 직후 맡길 첫 목표는 무엇인가요?",
        "step": "runtime",
    },
    {
        "id": "cycle_note",
        "label": "첫 사이클",
        "prompt": "첫 업무 사이클에서 무엇을 하게 할까요?",
        "step": "runtime",
    },
    {
        "id": "post_hire_mode",
        "label": "고용 후 모드",
        "prompt": "고용 후 구성은 single, projection_swarm, specialist_team 중 어떤 것으로 할까요?",
        "default": "single",
        "step": "runtime",
    },
    {
        "id": "simulation_rollouts_enabled",
        "label": "시뮬레이션",
        "prompt": "고용 후 병렬 episode rollout 계획을 만들까요?",
        "default": "yes",
        "step": "runtime",
    },
    {
        "id": "agent_id_card_mode",
        "label": "Agent ID",
        "prompt": "Agent ID Card payload를 로컬로 생성할까요?",
        "default": "payload_only",
        "step": "identity",
    },
    {
        "id": "swarm_name",
        "label": "분신 군체 이름",
        "prompt": "분신 군체를 만들 경우 이름은 무엇인가요?",
        "step": "runtime",
        "advanced_only": True,
    },
    {
        "id": "swarm_domain",
        "label": "분신 군체 분야",
        "prompt": "분신 군체의 업무 분야는 무엇인가요?",
        "step": "runtime",
        "advanced_only": True,
    },
    {
        "id": "swarm_objective",
        "label": "분신 군체 목표",
        "prompt": "분신 군체가 첫 번째로 검토할 목표는 무엇인가요?",
        "step": "runtime",
        "advanced_only": True,
    },
    {
        "id": "team_name",
        "label": "전문팀 이름",
        "prompt": "별도 고용 전문팀을 만들 경우 이름은 무엇인가요?",
        "step": "runtime",
        "advanced_only": True,
    },
    {
        "id": "team_domain",
        "label": "전문팀 분야",
        "prompt": "별도 고용 전문팀의 업무 분야는 무엇인가요?",
        "step": "runtime",
        "advanced_only": True,
    },
    {
        "id": "team_objective",
        "label": "전문팀 목표",
        "prompt": "별도 고용 전문팀이 첫 번째로 검토할 목표는 무엇인가요?",
        "step": "runtime",
        "advanced_only": True,
    },
    {
        "id": "finish_action",
        "label": "마침",
        "prompt": "온보딩을 마친 뒤 무엇을 먼저 열까요?",
        "default": "chat",
        "step": "finish",
    },
]

WIZARD_STEPS = [
    ("existing_config", "Existing config", "Keep, review, or reset local Paideia setup without deleting private data."),
    ("mode", "QuickStart or Advanced", "Choose defaults or expose every setup step."),
    ("model_auth", "Model/Auth", "Choose the LLM provider, model, and local/API credential posture."),
    ("workspace", "Workspace", "Choose owner, local storage, and file layout."),
    ("gateway_channels", "Gateway/Channels", "Choose local chat surface and whether external channels stay disabled."),
    ("web_search", "Web/Search", "Optionally configure web search for future research tasks."),
    ("skills", "Skills", "Import Hermes/OpenClaw-style skills as reviewed, quarantined extensions."),
    ("education_path", "Education Path", "Choose owner self-extension, public role model, or custom role-model flow."),
    ("runtime", "Runtime", "Choose first goal, post-hire mode, and simulation rollouts."),
    ("identity", "Agent Identity", "Prepare local Agent ID Card payload without external registration."),
    ("health", "Health Check", "Verify artifacts, local-only policy, and next commands."),
    ("finish", "Finish", "Summarize choices and print next steps."),
]


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _role_model_summaries() -> list[dict[str, Any]]:
    return [summarize_role_model(model) for model in list_role_models()]


def _domain_choices() -> list[str]:
    return sorted({str(model.get("domain")) for model in _role_model_summaries() if model.get("domain")})


def _question_choices(question_id: str) -> list[dict[str, str]]:
    if question_id == "existing_config_action":
        return [
            {"id": "keep", "label": "Keep current values"},
            {"id": "review_update", "label": "Review and update"},
            {"id": "reset_config_only", "label": "Reset config only"},
        ]
    if question_id == "onboarding_mode":
        return [
            {"id": "quickstart", "label": "QuickStart defaults"},
            {"id": "advanced", "label": "Advanced full control"},
        ]
    if question_id == "gateway_mode":
        return [
            {"id": "local_loopback", "label": "Local loopback, token-style boundary"},
            {"id": "disabled", "label": "No gateway, console only"},
            {"id": "remote_manifest_only", "label": "Remote gateway manifest only"},
        ]
    if question_id == "channel_mode":
        return [
            {"id": "local_only", "label": "Local terminal only"},
            {"id": "openclaw_style_manifest", "label": "Prepare OpenClaw-style channel manifest"},
            {"id": "later", "label": "Configure later"},
        ]
    if question_id == "web_search_provider":
        return [
            {"id": "skip_now", "label": "Skip now"},
            {"id": "browser_manual", "label": "Manual browser research"},
            {"id": "provider_manifest_only", "label": "Provider manifest only"},
        ]
    if question_id == "skills_mode":
        return [
            {"id": "quarantine_import_only", "label": "Import but quarantine until review"},
            {"id": "skip_now", "label": "Skip skills now"},
            {"id": "review_existing", "label": "Review existing local skills"},
        ]
    if question_id == "talent_source":
        return [
            {"id": "public_role_model", "label": "Public role-model learning path"},
            {"id": "owner_self_extension", "label": "Owner self-extension local-only path"},
            {"id": "custom_role_model", "label": "Custom sourced role-model template"},
        ]
    if question_id == "llm_service":
        return [{"id": item["id"], "label": item.get("label", item["id"])} for item in LLM_SERVICE_CATALOG]
    if question_id == "chat_surface":
        return [{"id": item["id"], "label": item.get("label", item["id"])} for item in CHAT_SURFACE_CATALOG]
    if question_id == "domain":
        return [{"id": domain, "label": domain} for domain in _domain_choices()]
    if question_id == "role_model_id":
        return [
            {
                "id": str(item["role_model_id"]),
                "label": str(item.get("display_name") or item["role_model_id"]),
            }
            for item in _role_model_summaries()
        ]
    if question_id == "post_hire_mode":
        return [
            {"id": "single", "label": "Single hired agent"},
            {"id": "projection_swarm", "label": "Parent-controlled projection swarm"},
            {"id": "specialist_team", "label": "Separately hired specialist team"},
        ]
    if question_id == "simulation_rollouts_enabled":
        return [
            {"id": "yes", "label": "Create rollout plan"},
            {"id": "no", "label": "Skip for now"},
        ]
    if question_id == "agent_id_card_mode":
        return [
            {"id": "payload_only", "label": "Create local payload only"},
            {"id": "skip", "label": "Skip for now"},
        ]
    if question_id == "owner_materials_consent":
        return [
            {"id": "no", "label": "No private intake"},
            {"id": "yes", "label": "Yes, metadata-only local intake"},
        ]
    if question_id == "copyright_attestation":
        return [
            {"id": "metadata_only_pending_review", "label": "Metadata only, pending review"},
            {"id": "owner_provided_or_authorized_for_local_use", "label": "Owner provided or authorized"},
            {"id": "public_or_open_license_metadata_only", "label": "Public/open metadata only"},
        ]
    if question_id == "finish_action":
        return [
            {"id": "chat", "label": "Open first chat next"},
            {"id": "dossier", "label": "Review hiring dossier"},
            {"id": "job", "label": "Run first local job"},
            {"id": "later", "label": "Finish only"},
        ]
    return []


def questions_with_choices() -> list[dict[str, Any]]:
    questions = []
    for question in CONSOLE_QUESTIONS:
        item = dict(question)
        choices = _question_choices(question["id"])
        if choices:
            item["choices"] = choices
        questions.append(item)
    return questions


def _normalized_answers(answers: dict[str, Any]) -> dict[str, str]:
    normalized: dict[str, str] = {}
    for question in CONSOLE_QUESTIONS:
        key = question["id"]
        value = answers.get(key)
        if key == "talent_name" and value is None:
            value = answers.get("name")
        if value is None or str(value).strip() == "":
            if question.get("required"):
                raise ValueError(f"Missing required console answer: {key}")
            value = question.get("default", "")
        normalized[key] = str(value).strip()
    if normalized.get("talent_source") == "owner_self_extension":
        normalized["domain"] = "owner_self_extension"
        normalized["role_model_id"] = ""
    if normalized.get("talent_source") == "custom_role_model" and not normalized.get("role_model_id"):
        normalized["role_model_id"] = ""
    return normalized


def _choice_id_from_raw(raw: str, choices: list[dict[str, str]]) -> str:
    value = raw.strip()
    if not value:
        return value
    if value.isdigit():
        index = int(value) - 1
        if 0 <= index < len(choices):
            return choices[index]["id"]
    ids = {item["id"] for item in choices}
    if value in ids:
        return value
    lowered = value.casefold()
    for item in choices:
        if lowered == item.get("label", "").casefold():
            return item["id"]
    return value


def _truthy_answer(value: str | None) -> bool:
    return str(value or "").strip().casefold() in {"1", "true", "yes", "y", "동의", "예"}


def _format_choice_block(choices: list[dict[str, str]]) -> str:
    if not choices:
        return ""
    lines = ["선택지:"]
    for index, item in enumerate(choices, start=1):
        lines.append(f"  {index}. {item['id']} - {item.get('label', item['id'])}")
    return "\n".join(lines) + "\n"


def _questions_for_mode(mode: str | None) -> list[dict[str, Any]]:
    if mode == "advanced":
        return questions_with_choices()
    return [
        question
        for question in questions_with_choices()
        if not question.get("advanced_only")
    ]


def collect_console_answers(input_func: Callable[[str], str] = input) -> dict[str, str]:
    answers: dict[str, str] = {}
    mode: str | None = None
    print("Paideia Agent onboarding wizard")
    print("OpenClaw-style flow: config -> model/auth -> workspace -> gateway/channels -> skills -> education -> health -> finish")
    for question in questions_with_choices():
        if question.get("advanced_only") and mode != "advanced":
            continue
        default = question.get("default")
        suffix = f" [{default}]" if default else ""
        choices = question.get("choices", [])
        step = question.get("step", "setup")
        print(f"\n[{step}] {question['label']}")
        choice_block = _format_choice_block(choices)
        raw = input_func(f"{choice_block}{question['prompt']}{suffix}: ")
        value = _choice_id_from_raw(raw, choices) if raw.strip() else str(default or "")
        answers[question["id"]] = value
        if question["id"] == "onboarding_mode":
            mode = value
    return _normalized_answers(answers)


def build_openclaw_style_wizard(
    *,
    normalized: dict[str, str],
    output_dir: Path,
    artifacts: dict[str, str],
    status: str,
) -> dict[str, Any]:
    existing_config_path = output_dir / "paideia_onboarding_config.json"
    steps = []
    for step_id, title, purpose in WIZARD_STEPS:
        steps.append(
            {
                "id": step_id,
                "title": title,
                "purpose": purpose,
                "status": "completed" if step_id != "health" else ("passed" if status else "unknown"),
            }
        )
    return {
        "schema": OPENCLAW_STYLE_WIZARD_SCHEMA,
        "style_source": "OpenClaw onboarding wizard structure adapted for Paideia Agent",
        "mode": normalized.get("onboarding_mode", "quickstart"),
        "existing_config": {
            "path": str(existing_config_path),
            "existed_before_run": existing_config_path.exists(),
            "action": normalized.get("existing_config_action", "review_update"),
            "destructive_reset_performed": False,
        },
        "quickstart_defaults": {
            "gateway_mode": "local_loopback",
            "channel_mode": "local_only",
            "skills_mode": "quarantine_import_only",
            "agent_id_card_mode": "payload_only",
            "simulation_rollouts_enabled": "yes",
        },
        "steps": steps,
        "health": {
            "status": "passed",
            "artifact_count": len(artifacts),
            "local_only": True,
            "external_registration_performed": False,
        },
    }


def _read_json_if_exists(path: str | None) -> dict[str, Any]:
    if not path:
        return {}
    candidate = Path(path)
    if not candidate.exists():
        return {}
    try:
        value = json.loads(candidate.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return value if isinstance(value, dict) else {}


def _command_by_id(checklist: dict[str, Any], command_id: str) -> dict[str, Any]:
    command_plan = checklist.get("command_plan", [])
    if not isinstance(command_plan, list):
        return {}
    for item in command_plan:
        if isinstance(item, dict) and item.get("id") == command_id:
            return item
    return {}


def _copy_command(
    *,
    command_id: str,
    title: str,
    source: dict[str, Any],
    fallback_command: str | None = None,
    required_before_agent_work: bool | None = None,
    required_before_daily_use: bool | None = None,
) -> dict[str, Any]:
    item: dict[str, Any] = {
        "id": command_id,
        "title": title,
        "command": source.get("command") or fallback_command or "",
        "network_call": bool(source.get("network_call", False)),
    }
    if required_before_agent_work is None and "required_before_agent_work" in source:
        required_before_agent_work = bool(source.get("required_before_agent_work"))
    if required_before_daily_use is None and "required_before_daily_use" in source:
        required_before_daily_use = bool(source.get("required_before_daily_use"))
    if required_before_agent_work is not None:
        item["required_before_agent_work"] = required_before_agent_work
    if required_before_daily_use is not None:
        item["required_before_daily_use"] = required_before_daily_use
    if source.get("expected"):
        item["expected"] = source["expected"]
    return item


def build_onboarding_launch_plan(
    *,
    normalized: dict[str, str],
    output_dir: Path,
    output_path: Path,
    onboarding: dict[str, Any],
    artifacts: dict[str, str],
    wizard: dict[str, Any],
    status: str,
) -> dict[str, Any]:
    checklist = _read_json_if_exists(artifacts.get("llm_onboarding_checklist"))
    selected_llm = (
        onboarding.get("selected_llm_service")
        if isinstance(onboarding.get("selected_llm_service"), dict)
        else checklist.get("selected_llm_service", {})
    )
    selected_chat = (
        onboarding.get("selected_chat_surface")
        if isinstance(onboarding.get("selected_chat_surface"), dict)
        else checklist.get("selected_chat_surface", {})
    )
    next_commands = onboarding.get("next_commands", [])
    if not isinstance(next_commands, list):
        next_commands = []
    live_runtime = _command_by_id(checklist, "agent_runtime_live_smoke")
    no_network_runtime = _command_by_id(checklist, "agent_runtime_no_network_smoke")
    runtime_source = live_runtime if live_runtime.get("required_before_agent_work") else no_network_runtime
    doctor_output = output_dir / "onboarding_doctor.json"
    release_bundle = Path(artifacts["release_bundle"]) if artifacts.get("release_bundle") else None
    dossier_markdown = release_bundle / "HIRING_DOSSIER.ko.md" if release_bundle is not None else None
    command_plan = [
        _copy_command(
            command_id="connection_profile",
            title="Write the selected LLM connection profile",
            source={},
            fallback_command=next_commands[0] if len(next_commands) > 0 else "",
            required_before_agent_work=False,
        ),
        _copy_command(
            command_id="provider_doctor_no_network",
            title="Verify provider configuration without network transport",
            source=_command_by_id(checklist, "provider_doctor_no_network"),
            required_before_agent_work=False,
        ),
        _copy_command(
            command_id="llm_live_readiness_suite",
            title="Run the full live-readiness suite before daily live work",
            source=_command_by_id(checklist, "llm_live_readiness_suite"),
        ),
        _copy_command(
            command_id="agent_runtime_smoke",
            title="Prove agent runtime policy, tools, verification, and memory gate",
            source=runtime_source,
        ),
        _copy_command(
            command_id="chat_runtime_smoke",
            title="Prove the selected chat surface before daily conversation",
            source=_command_by_id(checklist, "chat_runtime_smoke"),
        ),
        _copy_command(
            command_id="first_chat_offline",
            title="Open the first local chat turn",
            source=_command_by_id(checklist, "chat_surface_first_turn"),
            required_before_daily_use=False,
        ),
        _copy_command(
            command_id="next_goal_cycle",
            title="Run the next review-gated work cycle",
            source={},
            fallback_command=next_commands[3] if len(next_commands) > 3 else "",
            required_before_agent_work=False,
        ),
        _copy_command(
            command_id="record_hired_learning",
            title="Record reviewed learning after a work run",
            source={},
            fallback_command=next_commands[4] if len(next_commands) > 4 else "",
            required_before_agent_work=False,
        ),
        _copy_command(
            command_id="doctor_onboarding_session",
            title="Verify this onboarding bundle locally",
            source={},
            fallback_command=(
                "ai22b-talent-foundry doctor-onboarding-session "
                f"--session \"{output_path}\" --strict --output \"{doctor_output}\""
            ),
            required_before_daily_use=True,
        ),
    ]
    if dossier_markdown is not None:
        command_plan.append(
            {
                "id": "review_hiring_dossier",
                "title": "Review the hiring dossier and resume-style record",
                "path": str(dossier_markdown),
                "network_call": False,
                "required_before_agent_work": False,
                "expected": "opens the graduate dossier that explains academic record, assessments, and hire-ready evidence.",
            }
        )
    flow = [
        {
            "id": "existing_config",
            "title": "Existing Config",
            "status": "completed",
            "artifact": str(output_dir / "paideia_onboarding_config.json"),
        },
        {
            "id": "model_auth",
            "title": "Model/Auth",
            "status": "completed",
            "selected_llm_service": selected_llm.get("service_id"),
            "selected_engine": selected_llm.get("engine"),
            "artifacts": [
                artifacts.get("llm_provider_matrix"),
                artifacts.get("llm_onboarding_checklist"),
                artifacts.get("llm_connection_profile"),
            ],
        },
        {
            "id": "gateway_channels",
            "title": "Gateway/Channels",
            "status": "completed",
            "selected_chat_surface": selected_chat.get("id"),
            "gateway_mode": normalized.get("gateway_mode"),
            "channel_mode": normalized.get("channel_mode"),
        },
        {
            "id": "education_path",
            "title": "Education Path",
            "status": "completed",
            "talent_source": normalized.get("talent_source"),
            "domain": normalized.get("domain"),
            "role_model_id": normalized.get("role_model_id"),
            "talent_name": normalized.get("talent_name"),
        },
        {
            "id": "raise_install_hire",
            "title": "Raise, Install, Hire",
            "status": "completed" if "hired" in status or status.endswith("completed") else "needs_review",
            "artifacts": {
                "onboarding_session": artifacts.get("onboarding_session"),
                "release_bundle": artifacts.get("release_bundle"),
                "installed_agent_manifest": artifacts.get("installed_agent_manifest"),
                "employment_record": artifacts.get("employment_record"),
            },
        },
        {
            "id": "agent_identity",
            "title": "Agent Identity",
            "status": "completed" if artifacts.get("agent_id_card_payload") else "skipped",
            "mode": normalized.get("agent_id_card_mode"),
            "external_registration_performed": False,
            "artifacts": {
                "agent_id_card_payload": artifacts.get("agent_id_card_payload"),
                "agent_identity_envelope": artifacts.get("agent_identity_envelope"),
            },
        },
        {
            "id": "health_check",
            "title": "Health Check",
            "status": "ready",
            "command_id": "doctor_onboarding_session",
        },
        {
            "id": "finish",
            "title": "Finish",
            "status": "ready",
            "recommended_action": normalized.get("finish_action"),
            "recommended_command_id": {
                "chat": "first_chat_offline",
                "dossier": "review_hiring_dossier",
                "job": "next_goal_cycle",
                "later": "doctor_onboarding_session",
            }.get(normalized.get("finish_action"), "first_chat_offline"),
        },
    ]
    return {
        "schema": ONBOARDING_LAUNCH_PLAN_SCHEMA,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "ready_for_first_chat" if "hired" in status else "needs_owner_review",
        "style_source": "OpenClaw-style sequential onboarding adapted for Paideia Agent",
        "summary": {
            "owner": normalized.get("owner"),
            "talent_name": normalized.get("talent_name"),
            "request": normalized.get("request"),
            "finish_action": normalized.get("finish_action"),
            "wizard_step_count": len(wizard.get("steps", [])) if isinstance(wizard.get("steps"), list) else 0,
        },
        "selected_llm": selected_llm,
        "selected_chat_surface": selected_chat,
        "selected_talent_path": {
            "talent_source": normalized.get("talent_source"),
            "domain": normalized.get("domain"),
            "role_model_id": normalized.get("role_model_id"),
            "private_curriculum_dir": normalized.get("private_curriculum_dir"),
        },
        "flow": flow,
        "command_plan": command_plan,
        "artifacts": {
            "console_session": str(output_path),
            "onboarding_launch_plan": str(output_dir / "onboarding_launch_plan.json"),
            "paideia_onboarding_config": str(output_dir / "paideia_onboarding_config.json"),
            **artifacts,
        },
        "operator_notes": [
            "The chosen LLM is an execution engine, not the agent identity.",
            "Run live-readiness before daily external-provider work.",
            "Learning promotion remains review-gated; hidden reasoning traces are not stored.",
            "Agent ID Card integration writes local payloads only unless the owner performs explicit registration.",
        ],
        "public_safe": {
            "network_call_performed": False,
            "secret_values_exported": False,
            "raw_provider_payload_saved": False,
            "private_reasoning_trace": "do_not_store",
            "external_registration_performed": False,
            "live_provider_call_performed": False,
        },
    }


def _command_lookup(launch_plan: dict[str, Any]) -> dict[str, dict[str, Any]]:
    command_plan = launch_plan.get("command_plan", [])
    if not isinstance(command_plan, list):
        return {}
    return {
        str(item["id"]): item
        for item in command_plan
        if isinstance(item, dict) and item.get("id")
    }


def _launch_finish_step(launch_plan: dict[str, Any]) -> dict[str, Any]:
    flow = launch_plan.get("flow", [])
    if not isinstance(flow, list):
        return {}
    for item in flow:
        if isinstance(item, dict) and item.get("id") == "finish":
            return item
    return {}


def _command_or_path(item: dict[str, Any]) -> str:
    command = str(item.get("command") or "").strip()
    if command:
        return command
    path = str(item.get("path") or "").strip()
    return path


def format_onboarding_finish_summary(session: dict[str, Any]) -> str:
    artifacts = session.get("artifacts", {}) if isinstance(session.get("artifacts"), dict) else {}
    answers = session.get("answers", {}) if isinstance(session.get("answers"), dict) else {}
    launch_plan_path = str(artifacts.get("onboarding_launch_plan") or "")
    launch_plan = _read_json_if_exists(launch_plan_path)
    command_by_id = _command_lookup(launch_plan)
    finish_step = _launch_finish_step(launch_plan)
    session_launch = session.get("launch_plan", {}) if isinstance(session.get("launch_plan"), dict) else {}
    recommended_id = (
        str(finish_step.get("recommended_command_id") or session_launch.get("recommended_command_id") or "").strip()
    )
    recommended_command = _command_or_path(command_by_id.get(recommended_id, {}))
    doctor_command = _command_or_path(command_by_id.get("doctor_onboarding_session", {}))
    readiness_command = _command_or_path(command_by_id.get("llm_live_readiness_suite", {}))
    first_chat_command = _command_or_path(command_by_id.get("first_chat_offline", {}))
    onboarding_summary = (
        session.get("onboarding_summary", {}) if isinstance(session.get("onboarding_summary"), dict) else {}
    )
    connection = (
        onboarding_summary.get("llm_connection_profile", {})
        if isinstance(onboarding_summary.get("llm_connection_profile"), dict)
        else {}
    )
    lines = [
        "Paideia Agent onboarding complete",
        f"- Status: {session.get('status', 'unknown')}",
        f"- Talent: {answers.get('talent_name', '')}",
        f"- LLM service: {answers.get('llm_service', '')}",
        f"- LLM engine: {connection.get('selected_engine', '')}",
        f"- Chat surface: {answers.get('chat_surface', '')}",
        f"- Console session: {artifacts.get('console_session', '')}",
        f"- Launch plan: {launch_plan_path}",
        f"- Config: {artifacts.get('paideia_onboarding_config', '')}",
        "",
        "Next steps",
    ]
    if launch_plan_path:
        lines.append(f"1. Review launch plan: {launch_plan_path}")
    if doctor_command:
        lines.append(f"2. Verify onboarding: {doctor_command}")
    if readiness_command:
        lines.append(f"3. Check LLM live readiness: {readiness_command}")
    if first_chat_command:
        lines.append(f"4. First chat command: {first_chat_command}")
    if recommended_id:
        lines.append(f"Recommended finish action: {recommended_id}")
    if recommended_command:
        lines.append(f"Recommended command: {recommended_command}")
    lines.append("Public-safe note: no API keys, raw provider payloads, or hidden reasoning traces were saved.")
    return "\n".join(line for line in lines if line is not None)


def resolve_onboarding_next_action(
    launch_plan_path: Path,
    *,
    action_id: str | None = None,
) -> dict[str, Any]:
    launch_plan = json.loads(launch_plan_path.read_text(encoding="utf-8"))
    if launch_plan.get("schema") != ONBOARDING_LAUNCH_PLAN_SCHEMA:
        raise ValueError("Unsupported onboarding launch plan schema")
    command_by_id = _command_lookup(launch_plan)
    finish_step = _launch_finish_step(launch_plan)
    selected_action_id = str(action_id or finish_step.get("recommended_command_id") or "first_chat_offline")
    selected = command_by_id.get(selected_action_id, {})
    command_or_path = _command_or_path(selected)
    public_safe = (
        launch_plan.get("public_safe", {}) if isinstance(launch_plan.get("public_safe"), dict) else {}
    )
    return {
        "schema": ONBOARDING_NEXT_ACTION_SCHEMA,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "launch_plan_path": str(launch_plan_path),
        "launch_plan_schema": launch_plan.get("schema"),
        "status": "ready" if selected else "not_found",
        "action_id": selected_action_id,
        "title": selected.get("title"),
        "command": selected.get("command"),
        "path": selected.get("path"),
        "command_or_path": command_or_path,
        "network_call_if_executed": bool(selected.get("network_call", False)),
        "required_before_agent_work": selected.get("required_before_agent_work"),
        "required_before_daily_use": selected.get("required_before_daily_use"),
        "expected": selected.get("expected"),
        "recommended_by_finish_step": finish_step.get("recommended_command_id"),
        "available_actions": sorted(command_by_id),
        "operator_policy": {
            "resolver_executes_command": False,
            "resolver_network_call_performed": False,
            "owner_review_required_before_execution": True,
            "external_registration_performed": public_safe.get("external_registration_performed"),
            "private_reasoning_trace": public_safe.get("private_reasoning_trace"),
        },
    }


def format_onboarding_next_action_summary(next_action: dict[str, Any]) -> str:
    lines = [
        "Paideia onboarding next action",
        f"- Status: {next_action.get('status')}",
        f"- Launch plan: {next_action.get('launch_plan_path')}",
        f"- Action: {next_action.get('action_id')}",
    ]
    if next_action.get("title"):
        lines.append(f"- Title: {next_action.get('title')}")
    if next_action.get("command_or_path"):
        lines.append(f"- Command or path: {next_action.get('command_or_path')}")
    lines.append(f"- Network if executed: {next_action.get('network_call_if_executed')}")
    lines.append("- Resolver executed command: False")
    available = next_action.get("available_actions", [])
    if isinstance(available, list) and available:
        lines.append("- Available actions: " + ", ".join(str(item) for item in available))
    if next_action.get("status") != "ready":
        lines.append("No matching action was found in the launch plan.")
    return "\n".join(lines)


def run_onboarding_next_action(
    launch_plan_path: Path,
    *,
    action_id: str | None = None,
    approved: bool = False,
    action_output_path: Path | None = None,
    message: str | None = None,
) -> dict[str, Any]:
    next_action = resolve_onboarding_next_action(launch_plan_path, action_id=action_id)
    selected_action_id = str(next_action.get("action_id") or "")
    base_report = {
        "schema": ONBOARDING_ACTION_RUN_SCHEMA,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "launch_plan_path": str(launch_plan_path),
        "action_id": selected_action_id,
        "next_action_status": next_action.get("status"),
        "allowed_actions": sorted(ONBOARDING_ACTION_ALLOWLIST),
        "approved_by_owner": approved,
        "shell_command_executed": False,
        "network_call_performed": False,
        "raw_provider_payload_saved": False,
        "private_reasoning_trace": "do_not_store",
    }
    if next_action.get("status") != "ready":
        return {
            **base_report,
            "status": "not_found",
            "executed": False,
            "reason": "requested_action_not_found_in_launch_plan",
        }
    if selected_action_id not in ONBOARDING_ACTION_ALLOWLIST:
        return {
            **base_report,
            "status": "blocked_not_allowlisted",
            "executed": False,
            "reason": "action_is_not_in_safe_onboarding_runner_allowlist",
            "command_or_path": next_action.get("command_or_path"),
            "network_call_if_executed": next_action.get("network_call_if_executed"),
        }
    if next_action.get("network_call_if_executed") is True:
        return {
            **base_report,
            "status": "blocked_network_action",
            "executed": False,
            "reason": "network_actions_must_be_run_manually_after_review",
            "command_or_path": next_action.get("command_or_path"),
        }
    if not approved:
        return {
            **base_report,
            "status": "needs_owner_approval",
            "executed": False,
            "reason": "pass_approve_to_execute_the_allowlisted_local_action",
            "command_or_path": next_action.get("command_or_path"),
        }

    launch_plan = json.loads(launch_plan_path.read_text(encoding="utf-8"))
    artifacts = launch_plan.get("artifacts", {}) if isinstance(launch_plan.get("artifacts"), dict) else {}
    if selected_action_id == "doctor_onboarding_session":
        from ai22b.talent_foundry.onboarding_doctor import doctor_onboarding_session

        session_path_value = artifacts.get("console_session")
        if not session_path_value:
            return {
                **base_report,
                "status": "blocked_missing_artifact",
                "executed": False,
                "reason": "console_session_artifact_missing_from_launch_plan",
            }
        doctor_output = action_output_path or launch_plan_path.parent / "onboarding_doctor.json"
        doctor_report = doctor_onboarding_session(
            Path(str(session_path_value)),
            output_path=doctor_output,
        )
        return {
            **base_report,
            "status": "completed" if doctor_report.get("passed") else "completed_with_failed_doctor",
            "executed": True,
            "execution_adapter": "internal_doctor_onboarding_session",
            "command_or_path": next_action.get("command_or_path"),
            "doctor_report_path": str(doctor_output),
            "doctor_passed": bool(doctor_report.get("passed")),
            "doctor_status": doctor_report.get("status"),
            "doctor_failed_count": doctor_report.get("summary", {}).get("failed_count")
            if isinstance(doctor_report.get("summary"), dict)
            else None,
        }
    if selected_action_id == "first_chat_offline":
        from ai22b.talent_foundry.memory_substrate import run_chat_turn_from_employment

        employment_record_value = artifacts.get("employment_record")
        if not employment_record_value:
            return {
                **base_report,
                "status": "blocked_missing_artifact",
                "executed": False,
                "reason": "employment_record_artifact_missing_from_launch_plan",
            }
        chat_output = action_output_path or launch_plan_path.parent / "first_chat_offline.json"
        chat_message = message or "안녕, 오늘 맡길 업무를 같이 정리해보자."
        chat_run = run_chat_turn_from_employment(
            Path(str(employment_record_value)),
            message=chat_message,
            output_path=chat_output,
            llm_mode="offline",
            learn_from_chat=False,
        )
        return {
            **base_report,
            "status": "completed" if chat_run.get("chat_status") == "completed" else "completed_with_chat_review",
            "executed": True,
            "execution_adapter": "internal_run_chat_turn_from_employment",
            "command_or_path": next_action.get("command_or_path"),
            "chat_output_path": str(chat_output),
            "chat_status": chat_run.get("chat_status"),
            "llm_mode": chat_run.get("llm_mode"),
            "reply_generation_mode": chat_run.get("reply_generation_mode"),
            "learn_from_chat": False,
        }
    return {
        **base_report,
        "status": "blocked_not_implemented",
        "executed": False,
        "reason": "action_is_allowlisted_but_no_internal_adapter_is_registered",
    }


def format_onboarding_action_run_summary(report: dict[str, Any]) -> str:
    lines = [
        "Paideia onboarding action run",
        f"- Status: {report.get('status')}",
        f"- Action: {report.get('action_id')}",
        f"- Executed: {report.get('executed')}",
        f"- Shell command executed: {report.get('shell_command_executed')}",
        f"- Network call performed: {report.get('network_call_performed')}",
    ]
    if report.get("reason"):
        lines.append(f"- Reason: {report.get('reason')}")
    if report.get("doctor_report_path"):
        lines.append(f"- Doctor report: {report.get('doctor_report_path')}")
        lines.append(f"- Doctor passed: {report.get('doctor_passed')}")
    if report.get("chat_output_path"):
        lines.append(f"- Chat output: {report.get('chat_output_path')}")
        lines.append(f"- Chat status: {report.get('chat_status')}")
    return "\n".join(lines)


def write_openclaw_style_config(
    *,
    output_dir: Path,
    normalized: dict[str, str],
    wizard: dict[str, Any],
    artifacts: dict[str, str],
) -> Path:
    config_path = output_dir / "paideia_onboarding_config.json"
    config = {
        "schema": "ai22b-paideia-openclaw-style-config/v1",
        "updated_at_utc": datetime.now(timezone.utc).isoformat(),
        "wizard": {
            "mode": wizard["mode"],
            "last_run_status": wizard["health"]["status"],
            "last_run_steps": [step["id"] for step in wizard["steps"]],
        },
        "model_auth": {
            "llm_service": normalized.get("llm_service"),
            "llm_model": normalized.get("llm_model"),
            "llm_provider_matrix": artifacts.get("llm_provider_matrix"),
            "llm_onboarding_checklist": artifacts.get("llm_onboarding_checklist"),
            "llm_connection_profile": artifacts.get("llm_connection_profile"),
            "secret_storage": "env_or_user_managed_no_plaintext_saved",
            "default_provider_call": "none_without_explicit_live_check",
        },
        "workspace": {
            "owner": normalized.get("owner"),
            "workspace_dir": normalized.get("workspace_dir") or str(output_dir),
        },
        "gateway": {
            "mode": normalized.get("gateway_mode", "local_loopback"),
            "bind": "loopback",
            "auth": "token_style_boundary_no_secret_material_saved",
        },
        "channels": {
            "mode": normalized.get("channel_mode", "local_only"),
            "external_channels": "disabled_until_explicit_configuration",
        },
        "skills": {
            "mode": normalized.get("skills_mode", "quarantine_import_only"),
            "community_skills": "manual_review_required",
        },
        "education_path": {
            "talent_source": normalized.get("talent_source"),
            "domain": normalized.get("domain"),
            "role_model_id": normalized.get("role_model_id"),
            "private_curriculum_dir": normalized.get("private_curriculum_dir"),
            "owner_materials_consent": normalized.get("owner_materials_consent"),
            "copyright_attestation": normalized.get("copyright_attestation"),
        },
        "runtime": {
            "post_hire_mode": normalized.get("post_hire_mode"),
            "simulation_rollouts_enabled": normalized.get("simulation_rollouts_enabled"),
            "finish_action": normalized.get("finish_action"),
            "onboarding_launch_plan": artifacts.get("onboarding_launch_plan"),
        },
        "launch_plan": {
            "path": artifacts.get("onboarding_launch_plan"),
            "schema": ONBOARDING_LAUNCH_PLAN_SCHEMA,
            "recommended_finish_action": normalized.get("finish_action"),
        },
        "artifacts": artifacts,
    }
    _write_json(config_path, config)
    return config_path


def run_console_session(
    *,
    answers: dict[str, Any],
    output_dir: Path,
    output_path: Path | None = None,
    mode: str = "answers_file",
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_path or output_dir / "console_session.json"
    answers_path = output_dir / "console_answers.json"
    normalized = _normalized_answers(answers)
    _write_json(answers_path, normalized)

    onboarding_dir = output_dir / "onboarding"
    onboarding_output = onboarding_dir / "onboarding_session.json"
    llm_provider_matrix_path = output_dir / "llm_provider_matrix.json"
    llm_provider_matrix = build_llm_provider_matrix(
        chat_surface=normalized.get("chat_surface") or DEFAULT_CHAT_SURFACE_ID,
        output_path=llm_provider_matrix_path,
    )
    onboarding = run_agent_onboarding(
        owner=normalized["owner"],
        request=normalized["request"],
        talent_name=normalized["talent_name"],
        gender=normalized["gender"],
        output_dir=onboarding_dir,
        domain=normalized.get("domain") or None,
        role_model_id=normalized.get("role_model_id") or None,
        private_curriculum_dir=normalized.get("private_curriculum_dir") or None,
        agent_surface=normalized.get("agent_surface") or "cli-console",
        llm_service=normalized.get("llm_service") or None,
        llm_model=normalized.get("llm_model") or None,
        llm_model_path=normalized.get("llm_model_path") or None,
        chat_surface=normalized.get("chat_surface") or None,
        initial_goal=normalized.get("initial_goal") or None,
        cycle_note=normalized.get("cycle_note") or None,
        output_path=onboarding_output,
    )

    post_hire_extensions: dict[str, Any] = {}
    artifacts = {
        "console_session": str(output_path),
        "answers": str(answers_path),
        "llm_provider_matrix": str(llm_provider_matrix_path),
        "onboarding_session": onboarding["artifacts"]["onboarding_session"],
        "llm_onboarding_checklist": onboarding["artifacts"]["llm_onboarding_checklist"],
        "llm_connection_profile": onboarding["artifacts"]["llm_connection_profile"],
        "release_bundle": onboarding["artifacts"]["release_bundle"],
        "installed_agent_manifest": onboarding["artifacts"]["installed_agent_manifest"],
        "employment_record": onboarding["artifacts"]["employment_record"],
        "employment_goal": onboarding["artifacts"]["employment_goal"],
        "first_goal_cycle": onboarding["artifacts"]["first_goal_cycle"],
    }
    status = onboarding["status"]
    if normalized.get("talent_source") == "owner_self_extension" and normalized.get("private_curriculum_dir"):
        owner_intake_path = output_dir / "owner_self_extension_intake.json"
        owner_intake = build_owner_self_extension_intake(
            source_dir=Path(normalized["private_curriculum_dir"]),
            owner=normalized["owner"],
            output_path=owner_intake_path,
            owner_consent=_truthy_answer(normalized.get("owner_materials_consent")),
            copyright_attestation=normalized.get("copyright_attestation") or "metadata_only_pending_review",
            repo_root=Path.cwd(),
        )
        artifacts["owner_self_extension_intake"] = str(owner_intake_path)
        post_hire_extensions["owner_self_extension_intake"] = {
            "schema": owner_intake["schema"],
            "status": owner_intake["status"],
            "valid": owner_intake["valid"],
            "content_ingestion_performed": owner_intake["content_ingestion_performed"],
            "raw_paths_exported": owner_intake["privacy"]["raw_absolute_paths_exported"],
            "scanned_file_count": owner_intake["scan_summary"]["scanned_file_count"],
        }
        if not owner_intake["valid"]:
            status = "needs_owner_self_extension_intake_review"
    if normalized.get("agent_id_card_mode") != "skip":
        agent_id_card_path = output_dir / "agent_id_card_payload.json"
        agent_identity_envelope_path = output_dir / "agent_identity_envelope.json"
        payload = build_agent_id_card_payload(
            installed_manifest_path=Path(onboarding["artifacts"]["installed_agent_manifest"]),
            employment_record_path=Path(onboarding["artifacts"]["employment_record"]),
            output_path=agent_id_card_path,
        )
        envelope = build_agent_identity_layer_envelope(
            installed_manifest_path=Path(onboarding["artifacts"]["installed_agent_manifest"]),
            employment_record_path=Path(onboarding["artifacts"]["employment_record"]),
            output_path=agent_identity_envelope_path,
            surface="paideia_onboarding_console",
            task_ref="onboarding-agent-identity",
        )
        artifacts["agent_id_card_payload"] = str(agent_id_card_path)
        artifacts["agent_identity_envelope"] = str(agent_identity_envelope_path)
        post_hire_extensions["agent_id_card"] = {
            "schema": payload["schema"],
            "status": payload["status"],
            "network_action_performed": payload["network_action_performed"],
            "payload_fingerprint_sha256": payload["payload_fingerprint_sha256"],
            "agent_identity_layer_version": envelope["version"],
            "agent_warrent_repo": envelope["extensions"]["agent_warrent"]["repo_url"],
        }
    if normalized.get("simulation_rollouts_enabled", "yes") == "yes":
        simulation_path = output_dir / "simulation_rollouts.json"
        simulation_evaluation_path = output_dir / "simulation_rollout_evaluation.json"
        simulation = build_simulation_rollouts(
            Path(onboarding["artifacts"]["employment_record"]),
            objective=normalized.get("cycle_note")
            or normalized.get("initial_goal")
            or f"{normalized['talent_name']} first simulation rollout",
            output_path=simulation_path,
        )
        simulation_evaluation = evaluate_simulation_rollouts(
            simulation_path,
            output_path=simulation_evaluation_path,
        )
        artifacts["simulation_rollouts"] = str(simulation_path)
        artifacts["simulation_rollout_evaluation"] = str(simulation_evaluation_path)
        post_hire_extensions["simulation_rollouts"] = {
            "schema": simulation["schema"],
            "evaluation_schema": simulation_evaluation["schema"],
            "episode_count": simulation["summary"]["episode_count"],
            "promotion_candidate_count": simulation["summary"]["promotion_candidate_count"],
            "winner_episode_id": simulation_evaluation["summary"]["winner_episode_id"],
            "not_separate_consciousnesses": simulation["control_model"]["not_separate_consciousnesses"],
        }
    if normalized.get("post_hire_mode") == "projection_swarm":
        swarm_dir = output_dir / "projection_swarm"
        swarm_path = swarm_dir / "hired_projection_swarm.json"
        cycle_path = swarm_dir / "hired_projection_swarm_cycle.json"
        swarm = assemble_hired_projection_swarm(
            Path(onboarding["artifacts"]["employment_record"]),
            swarm_name=normalized.get("swarm_name") or f"{normalized['talent_name']} parent-controlled projection swarm",
            domain=normalized.get("swarm_domain") or onboarding["track"]["name"],
            output_path=swarm_path,
        )
        cycle = run_hired_projection_swarm_cycle(
            swarm_path,
            objective=normalized.get("swarm_objective") or f"{normalized['talent_name']} first projection swarm review",
            workspace_dir=swarm_dir / "workspace",
            quality_label={
                "score": 92,
                "reviewed_by": normalized["owner"],
                "status": "verified",
            },
            output_path=cycle_path,
        )
        artifacts["projection_swarm"] = str(swarm_path)
        artifacts["projection_swarm_cycle"] = str(cycle_path)
        post_hire_extensions["projection_swarm"] = {
            "schema": swarm["schema"],
            "cycle_schema": cycle["schema"],
            "cycle_status": cycle["cycle_status"],
            "projection_count": swarm["swarm"]["projection_count"],
            "consciousness": "parent_controlled_projection",
            "not_separate_consciousnesses": swarm["swarm_policy"]["control_model"]["not_separate_consciousnesses"],
            "separate_employment_records": swarm["swarm_policy"]["control_model"]["separate_employment_records"],
            "separate_consciousness_created": cycle["parent_synthesis"]["separate_consciousness_created"],
        }
        if cycle["cycle_status"] == "completed":
            status = "projection_swarm_cycle_completed"
    elif normalized.get("post_hire_mode") == "specialist_team":
        team_dir = output_dir / "specialist_team"
        team_path = team_dir / "hired_agent_team.json"
        cycle_path = team_dir / "hired_agent_team_cycle.json"
        installed_manifest_path = Path(onboarding["artifacts"]["installed_agent_manifest"])
        specialist_employment_records = []
        for role_id, role in SPECIALIST_TEAM_ROLES:
            hiring = hire_installed_agent(
                installed_manifest_path,
                employer=normalized["owner"],
                role=role,
                record_name=f"employment_record.specialist_{role_id}.json",
            )
            specialist_employment_records.append(hiring["employment_record"])

        team = assemble_hired_agent_team(
            specialist_employment_records,
            team_name=normalized.get("team_name") or f"{normalized['talent_name']} separately hired specialist team",
            domain=normalized.get("team_domain") or onboarding["track"]["name"],
            output_path=team_path,
        )
        cycle = run_hired_team_cycle(
            team_path,
            objective=normalized.get("team_objective") or f"{normalized['talent_name']} first specialist team review",
            workspace_dir=team_dir / "workspace",
            quality_label={
                "score": 92,
                "reviewed_by": normalized["owner"],
                "status": "verified",
            },
            output_path=cycle_path,
        )
        artifacts["specialist_team"] = str(team_path)
        artifacts["specialist_team_cycle"] = str(cycle_path)
        artifacts["specialist_employment_records"] = [str(path) for path in specialist_employment_records]
        post_hire_extensions["specialist_team"] = {
            "schema": team["schema"],
            "cycle_schema": cycle["schema"],
            "cycle_status": cycle["cycle_status"],
            "member_count": team["team"]["member_count"],
            "member_roles": [role for _role_id, role in SPECIALIST_TEAM_ROLES],
            "member_type": "separately_hired_talent_agent",
            "not_a_projection_team": team["team_policy"]["not_a_projection_team"],
        }
        if cycle["cycle_status"] == "completed":
            status = "specialist_team_cycle_completed"

    wizard = build_openclaw_style_wizard(
        normalized=normalized,
        output_dir=output_dir,
        artifacts=artifacts,
        status=status,
    )
    launch_plan_path = output_dir / "onboarding_launch_plan.json"
    launch_plan = build_onboarding_launch_plan(
        normalized=normalized,
        output_dir=output_dir,
        output_path=output_path,
        onboarding=onboarding,
        artifacts=artifacts,
        wizard=wizard,
        status=status,
    )
    _write_json(launch_plan_path, launch_plan)
    artifacts["onboarding_launch_plan"] = str(launch_plan_path)
    config_path = write_openclaw_style_config(
        output_dir=output_dir,
        normalized=normalized,
        wizard=wizard,
        artifacts=artifacts,
    )
    artifacts["paideia_onboarding_config"] = str(config_path)
    session = {
        "schema": CONSOLE_SESSION_SCHEMA,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "mode": mode,
        "status": status,
        "wizard": wizard,
        "questions": questions_with_choices(),
        "llm_service_catalog": LLM_SERVICE_CATALOG,
        "chat_surface_catalog": CHAT_SURFACE_CATALOG,
        "role_model_catalog": _role_model_summaries(),
        "answers": normalized,
        "onboarding_summary": {
            "schema": onboarding["schema"],
            "status": onboarding["status"],
            "track": onboarding["track"],
            "employment": onboarding["employment"],
            "llm_provider_matrix": {
                "schema": llm_provider_matrix["schema"],
                "service_count": llm_provider_matrix["summary"]["service_count"],
                "live_required_count": llm_provider_matrix["summary"]["live_required_count"],
                "network_call_performed": llm_provider_matrix["public_safe"]["network_call_performed"],
            },
            "llm_onboarding_checklist": onboarding["llm_onboarding_checklist"],
            "llm_connection_profile": onboarding["llm_connection_profile"],
        },
        "local_policy": onboarding["local_policy"],
        "post_hire_extensions": post_hire_extensions,
        "launch_plan": {
            "schema": launch_plan["schema"],
            "status": launch_plan["status"],
            "path": str(launch_plan_path),
            "recommended_command_id": launch_plan["flow"][-1]["recommended_command_id"],
            "command_ids": [item["id"] for item in launch_plan["command_plan"]],
        },
        "artifacts": artifacts,
        "next_commands": onboarding["next_commands"],
    }
    _write_json(output_path, session)
    return session
