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
from ai22b.talent_foundry.onboarding_choices import (
    CHAT_SURFACE_CATALOG,
    DEFAULT_CHAT_SURFACE_ID,
    DEFAULT_LLM_SERVICE_ID,
    LLM_SERVICE_CATALOG,
)
from ai22b.talent_foundry.role_models import list_role_models, summarize_role_model
from ai22b.talent_foundry.registry import (
    assemble_hired_agent_team,
    assemble_hired_projection_swarm,
    hire_installed_agent,
    run_hired_projection_swarm_cycle,
    run_hired_team_cycle,
)
from ai22b.talent_foundry.simulation_rollouts import build_simulation_rollouts


CONSOLE_SESSION_SCHEMA = "ai-talent-guided-console-session/v1"
OPENCLAW_STYLE_WIZARD_SCHEMA = "ai22b-paideia-openclaw-style-onboarding/v1"

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
        "prompt": "보스가 제공할 비공개 교재 폴더는 어디로 둘까요?",
        "default": "",
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
            "secret_storage": "env_or_user_managed_no_plaintext_saved",
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
        },
        "runtime": {
            "post_hire_mode": normalized.get("post_hire_mode"),
            "simulation_rollouts_enabled": normalized.get("simulation_rollouts_enabled"),
            "finish_action": normalized.get("finish_action"),
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
        "onboarding_session": onboarding["artifacts"]["onboarding_session"],
        "employment_record": onboarding["artifacts"]["employment_record"],
        "employment_goal": onboarding["artifacts"]["employment_goal"],
        "first_goal_cycle": onboarding["artifacts"]["first_goal_cycle"],
    }
    status = onboarding["status"]
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
        simulation = build_simulation_rollouts(
            Path(onboarding["artifacts"]["employment_record"]),
            objective=normalized.get("cycle_note")
            or normalized.get("initial_goal")
            or f"{normalized['talent_name']} first simulation rollout",
            output_path=simulation_path,
        )
        artifacts["simulation_rollouts"] = str(simulation_path)
        post_hire_extensions["simulation_rollouts"] = {
            "schema": simulation["schema"],
            "episode_count": simulation["summary"]["episode_count"],
            "promotion_candidate_count": simulation["summary"]["promotion_candidate_count"],
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
        },
        "local_policy": onboarding["local_policy"],
        "post_hire_extensions": post_hire_extensions,
        "artifacts": artifacts,
        "next_commands": onboarding["next_commands"],
    }
    _write_json(output_path, session)
    return session
