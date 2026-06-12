from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import http.client
import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

from ai22b.config import STORAGE_ROOT, talent_foundry_storage_path
from ai22b.talent_foundry.memory_substrate import run_chat_turn_from_employment
from ai22b.talent_foundry.onboarding_choices import DEFAULT_CHATGPT_CODEX_MODEL, chatgpt_codex_model_ids


DEFAULT_MODEL = DEFAULT_CHATGPT_CODEX_MODEL
DEFAULT_LIVE_MAX_OUTPUT_TOKENS = 2400
MAX_TELEGRAM_MESSAGE = 3900


def _load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def _json_request(token: str, method: str, payload: dict[str, Any] | None = None, timeout: int = 60) -> dict[str, Any]:
    body = None
    headers = {}
    request_method = "GET"
    if payload is not None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
        request_method = "POST"

    connection = http.client.HTTPSConnection("api.telegram.org", timeout=timeout)
    try:
        connection.request(request_method, f"/bot{token}/{method}", body=body, headers=headers)
        response = connection.getresponse()
        response_text = response.read().decode("utf-8")
    finally:
        connection.close()
    if response.status >= 400:
        raise RuntimeError(f"Telegram HTTP error: {response.status} {response_text[:500]}")
    return json.loads(response_text)


class TelegramApi:
    def __init__(self, token: str) -> None:
        self._token = token

    def call(self, method: str, payload: dict[str, Any] | None = None, timeout: int = 60) -> dict[str, Any]:
        return _json_request(self._token, method, payload=payload, timeout=timeout)

    def send_message(self, chat_id: int | str, text: str, *, reply_to_message_id: int | None = None) -> None:
        chunks = _split_message(text)
        for index, chunk in enumerate(chunks):
            payload: dict[str, Any] = {
                "chat_id": chat_id,
                "text": chunk,
                "disable_web_page_preview": True,
            }
            if index == 0 and reply_to_message_id:
                payload["reply_parameters"] = {"message_id": reply_to_message_id}
            self.call("sendMessage", payload=payload, timeout=30)

    def send_chat_action(self, chat_id: int | str, action: str = "typing") -> None:
        try:
            self.call("sendChatAction", payload={"chat_id": chat_id, "action": action}, timeout=10)
        except Exception:
            return


def _split_message(text: str) -> list[str]:
    if not text:
        return ["(empty reply)"]
    chunks: list[str] = []
    remaining = text
    while len(remaining) > MAX_TELEGRAM_MESSAGE:
        cut = remaining.rfind("\n", 0, MAX_TELEGRAM_MESSAGE)
        if cut < 1000:
            cut = MAX_TELEGRAM_MESSAGE
        chunks.append(remaining[:cut].strip())
        remaining = remaining[cut:].strip()
    chunks.append(remaining)
    return chunks


def _parse_allowed_users(value: str) -> set[int]:
    users: set[int] = set()
    for item in value.replace(";", ",").split(","):
        item = item.strip()
        if not item:
            continue
        try:
            users.add(int(item))
        except ValueError:
            continue
    return users


def _telegram_command_name(text: str) -> str:
    first = text.strip().split(maxsplit=1)[0] if text.strip() else ""
    return first.split("@", 1)[0].lower()


def _model_choices_text(current_model: str) -> str:
    choices = chatgpt_codex_model_ids()
    rendered = "\n".join(
        f"- {model_id}{' (current)' if model_id == current_model else ''}"
        for model_id in choices
    )
    return (
        "Selectable ChatGPT/Codex models:\n"
        f"{rendered}\n\n"
        "Use /model <model-name> to switch. Custom model names are allowed and will be verified on the next live call."
    )


def _handle_model_command(text: str, current_model: str) -> tuple[str, str]:
    command = _telegram_command_name(text)
    parts = text.strip().split(maxsplit=1)
    if command == "/models" or len(parts) == 1:
        return current_model, _model_choices_text(current_model)
    requested = parts[1].strip()
    if not requested:
        return current_model, "Usage: /model <model-name>"
    known = set(chatgpt_codex_model_ids())
    note = "" if requested in known else "\nCustom model name accepted; it will be verified on the next live call."
    return requested, f"Paideia LLM model switched to {requested}.{note}"


def _discover_latest_employment_record(storage_root: Path) -> Path:
    search_roots = [
        storage_root / "talent-foundry" / "runs" / "console_onboarding",
        storage_root / "talent-foundry" / "runs",
    ]
    candidates: list[tuple[float, Path]] = []
    for root in search_roots:
        if not root.exists():
            continue
        for path in root.rglob("employment_record.json"):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                continue
            if data.get("schema") == "ai-talent-local-employment/v1" and data.get("status") == "active":
                candidates.append((path.stat().st_mtime, path))
    if not candidates:
        raise FileNotFoundError(f"No active employment_record.json found under {storage_root}")
    return sorted(candidates, reverse=True)[0][1]


def _read_agent_summary(employment_record: Path) -> dict[str, Any]:
    data = json.loads(employment_record.read_text(encoding="utf-8"))
    return {
        "name": (data.get("agent") or {}).get("name") or "Paideia Agent",
        "role": (data.get("agent") or {}).get("role") or "local agent",
        "engine": (data.get("llm_runtime") or {}).get("engine") or "unknown",
        "status": data.get("status"),
    }


def _decode_json_string_fragment(fragment: str) -> str:
    candidate = fragment
    trailing_slashes = re.search(r"\\+$", candidate)
    if trailing_slashes and len(trailing_slashes.group(0)) % 2 == 1:
        candidate = candidate[:-1]
    try:
        return json.loads(f'"{candidate}"')
    except json.JSONDecodeError:
        return (
            candidate.replace(r"\n", "\n")
            .replace(r"\r", "\r")
            .replace(r"\t", "\t")
            .replace(r"\/", "/")
            .replace(r"\"", '"')
            .replace(r"\\", "\\")
        )


def _extract_json_wrapped_answer(text: str) -> tuple[str, bool]:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped, flags=re.IGNORECASE)
        stripped = re.sub(r"\s*```$", "", stripped)
    try:
        parsed = json.loads(stripped)
    except json.JSONDecodeError:
        parsed = None
    if isinstance(parsed, dict):
        value = parsed.get("assistant_answer") or parsed.get("assistant_reply")
        if value:
            return str(value).strip(), False

    for key in ("assistant_answer", "assistant_reply"):
        match = re.search(rf'["\']{key}["\']\s*:\s*"', stripped)
        if not match:
            continue
        start = match.end()
        escaped = False
        end = None
        for index, char in enumerate(stripped[start:], start=start):
            if escaped:
                escaped = False
                continue
            if char == "\\":
                escaped = True
                continue
            if char == '"':
                end = index
                break
        fragment = stripped[start:end] if end is not None else stripped[start:]
        return _decode_json_string_fragment(fragment).strip(), end is None
    return text.strip(), False


def _normalize_answer_text(raw_answer: str) -> str:
    answer, possibly_truncated = _extract_json_wrapped_answer(raw_answer)
    noise_markers = [
        "\n\nReviewable reasoning summary:\n- LLM output: The model did not return strict JSON",
    ]
    for marker in noise_markers:
        if marker in answer:
            answer = answer.split(marker, 1)[0]
    answer = answer.strip()
    if possibly_truncated:
        answer = answer.rstrip(",;: ")
        answer += "\n\n(Response may have been truncated. Send 'continue' to keep going.)"
    return answer


def _run_paideia_chat(
    *,
    employment_record: Path,
    message: str,
    output_dir: Path,
    llm_mode: str,
    llm_model: str,
    learn_from_chat: bool,
    live_max_output_tokens: int,
    chat_backend: str,
    hermes_agent_root: str | None,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_path = output_dir / f"telegram_chat_{stamp}.json"

    previous_backend = os.environ.get("PAIDEIA_CHAT_BACKEND")
    previous_tokens = os.environ.get("PAIDEIA_LIVE_MAX_OUTPUT_TOKENS")
    previous_hermes = os.environ.get("PAIDEIA_HERMES_AGENT_ROOT")
    os.environ["PAIDEIA_CHAT_BACKEND"] = chat_backend
    os.environ["PAIDEIA_LIVE_MAX_OUTPUT_TOKENS"] = str(live_max_output_tokens)
    if hermes_agent_root:
        os.environ["PAIDEIA_HERMES_AGENT_ROOT"] = hermes_agent_root
    try:
        data = run_chat_turn_from_employment(
            employment_record,
            message=message,
            output_path=output_path,
            llm_mode=llm_mode,
            llm_model=llm_model,
            learn_from_chat=learn_from_chat,
        )
    except Exception as exc:
        return {
            "ok": False,
            "error": "paideia_chat_failed",
            "detail": f"{type(exc).__name__}: {exc}",
            "output_path": str(output_path),
        }
    finally:
        if previous_backend is None:
            os.environ.pop("PAIDEIA_CHAT_BACKEND", None)
        else:
            os.environ["PAIDEIA_CHAT_BACKEND"] = previous_backend
        if previous_tokens is None:
            os.environ.pop("PAIDEIA_LIVE_MAX_OUTPUT_TOKENS", None)
        else:
            os.environ["PAIDEIA_LIVE_MAX_OUTPUT_TOKENS"] = previous_tokens
        if previous_hermes is None:
            os.environ.pop("PAIDEIA_HERMES_AGENT_ROOT", None)
        else:
            os.environ["PAIDEIA_HERMES_AGENT_ROOT"] = previous_hermes

    raw_answer = str(
        data.get("assistant_answer")
        or data.get("assistant_reply")
        or (data.get("llm_runtime_result") or {}).get("assistant_reply")
        or ""
    ).strip()
    answer = _normalize_answer_text(raw_answer)
    mode = data.get("reply_generation_mode") or data.get("llm_mode") or llm_mode
    return {
        "ok": True,
        "answer": answer or "(Paideia returned an empty answer.)",
        "mode": mode,
        "output_path": str(output_path),
        "learning": data.get("chat_learning_update", {}),
    }


def _same_path(left: Path, right: Path) -> bool:
    try:
        return left.resolve() == right.resolve()
    except OSError:
        return str(left).lower() == str(right).lower()


def _specialist_prompt(*, objective: str, team_name: str, role: str) -> str:
    return (
        f"Boss asked the investment office team lead to handle this objective:\n{objective}\n\n"
        f"You are a specialist member of {team_name}.\n"
        f"Your assigned role is: {role}\n\n"
        "Return a concise Korean specialist memo for the CIO/team lead. Use these sections:\n"
        "1. Signal\n"
        "2. Evidence or live verification needed\n"
        "3. US equity implication\n"
        "4. Downside or invalidation\n"
        "5. Recommended action for CIO\n\n"
        "Guardrails: do not execute trades, do not request brokerage credentials, do not claim unverified live data as fact, "
        "and mark uncertainty clearly."
    )


def _leader_synthesis_prompt(*, objective: str, team_name: str, reports: list[dict[str, Any]]) -> str:
    report_text = []
    for item in reports:
        status = "ok" if item.get("ok") else "failed"
        report_text.append(
            f"[{item.get('role', 'unknown role')}] status={status}\n"
            f"{item.get('answer') or item.get('error') or '(no report)'}"
        )
    return (
        f"Boss asked via Telegram:\n{objective}\n\n"
        f"You are the CIO and Telegram-facing team lead of {team_name}. "
        "Specialist agents worked under your directive and returned these memos:\n\n"
        + "\n\n".join(report_text)
        + "\n\nSynthesize a Korean Boss-facing briefing. Keep it practical and structured:\n"
        "1. Executive view\n"
        "2. Team consensus and disagreements\n"
        "3. Market, macro/rates, geopolitics, commodities/FX, equity, and risk implications\n"
        "4. Approval-gated action list\n"
        "5. Missing data and verification needs\n\n"
        "Do not execute or imply executed trades. Separate facts, assumptions, and proposals."
    )


def _run_team_directive(
    *,
    team_path: Path,
    leader_record: Path,
    objective: str,
    output_dir: Path,
    llm_mode: str,
    llm_model: str,
    learn_from_chat: bool,
    live_max_output_tokens: int,
    chat_backend: str,
    hermes_agent_root: str | None,
    team_max_workers: int,
) -> dict[str, Any]:
    if not team_path.exists():
        return {"ok": False, "error": f"Team file not found: {team_path}"}
    try:
        team = json.loads(team_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"ok": False, "error": f"Team file could not be read: {type(exc).__name__}: {exc}"}

    team_name = (team.get("team") or {}).get("name") or "Investment Office"
    members = team.get("members") or []
    specialists = [
        member
        for member in members
        if not _same_path(Path(member.get("employment_record_path", "")), leader_record)
    ]
    if not specialists:
        return {"ok": False, "error": "No specialist members were available for team dispatch."}

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = output_dir / f"team_directive_{stamp}"
    run_dir.mkdir(parents=True, exist_ok=True)

    def call_member(member: dict[str, Any]) -> dict[str, Any]:
        member_id = str(member.get("member_id") or "member")
        role = str(member.get("coordination_role") or (member.get("agent") or {}).get("role") or member_id)
        record_path = Path(member["employment_record_path"])
        result = _run_paideia_chat(
            employment_record=record_path,
            message=_specialist_prompt(objective=objective, team_name=team_name, role=role),
            output_dir=run_dir / member_id,
            llm_mode=llm_mode,
            llm_model=llm_model,
            learn_from_chat=False,
            live_max_output_tokens=live_max_output_tokens,
            chat_backend=chat_backend,
            hermes_agent_root=hermes_agent_root,
        )
        return {
            "member_id": member_id,
            "role": role,
            "employment_record": str(record_path),
            "ok": bool(result.get("ok")),
            "answer": result.get("answer"),
            "error": result.get("detail") or result.get("error"),
            "mode": result.get("mode"),
            "output_path": result.get("output_path"),
        }

    reports: list[dict[str, Any]] = []
    max_workers = max(1, int(team_max_workers or 1))
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(call_member, member) for member in specialists]
        for future in as_completed(futures):
            reports.append(future.result())
    reports.sort(key=lambda item: item.get("member_id", ""))

    leader_result = _run_paideia_chat(
        employment_record=leader_record,
        message=_leader_synthesis_prompt(objective=objective, team_name=team_name, reports=reports),
        output_dir=run_dir / "cio_team_lead",
        llm_mode=llm_mode,
        llm_model=llm_model,
        learn_from_chat=learn_from_chat,
        live_max_output_tokens=live_max_output_tokens,
        chat_backend=chat_backend,
        hermes_agent_root=hermes_agent_root,
    )

    artifact = {
        "schema": "22b-investment-office-telegram-team-directive/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "team_path": str(team_path),
        "team_name": team_name,
        "leader_record": str(leader_record),
        "objective": objective,
        "llm_mode": llm_mode,
        "llm_model": llm_model,
        "chat_backend": chat_backend,
        "specialist_reports": reports,
        "leader_synthesis": leader_result,
    }
    artifact_path = run_dir / "team_directive.json"
    artifact_path.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")

    ok_reports = sum(1 for item in reports if item.get("ok"))
    if leader_result.get("ok"):
        answer = leader_result["answer"]
    else:
        answer = (
            "Team dispatch completed, but CIO synthesis failed.\n"
            f"Reason: {leader_result.get('error')}\n"
            f"Detail: {leader_result.get('detail')}"
        )
    return {
        "ok": bool(leader_result.get("ok")),
        "answer": f"{answer}\n\nTeam dispatch: {ok_reports}/{len(reports)} specialist reports\nArtifact: {artifact_path}",
        "artifact_path": str(artifact_path),
        "reports_ok": ok_reports,
        "reports_total": len(reports),
    }


def _status_text(
    *,
    agent: dict[str, Any],
    employment_record: Path,
    llm_mode: str,
    llm_model: str,
    chat_backend: str,
    team_path: Path | None = None,
) -> str:
    return (
        "Paideia Telegram bridge is running.\n"
        f"Agent: {agent['name']} ({agent['role']})\n"
        f"Runtime engine: {agent['engine']}\n"
        f"Chat backend: {chat_backend}\n"
        f"Telegram chat mode: {llm_mode}\n"
        f"Model: {llm_model or '(Paideia default)'}\n"
        f"Web search: {os.environ.get('PAIDEIA_ENABLE_WEB_SEARCH', '1')}\n"
        f"Employment record: {employment_record}\n"
        f"Team file: {team_path or '(not configured)'}"
    )


def run_bridge(args: argparse.Namespace) -> int:
    env_file = Path(args.env_file) if args.env_file else Path.cwd() / "paideia-telegram.env"
    _load_env_file(env_file)

    token = (
        os.environ.get("PAIDEIA_TELEGRAM_BOT_TOKEN")
        or os.environ.get("HERMES_TELEGRAM_BOT_TOKEN")
        or os.environ.get("TELEGRAM_BOT_TOKEN")
    )
    if not token:
        raise SystemExit("Missing PAIDEIA_TELEGRAM_BOT_TOKEN or HERMES_TELEGRAM_BOT_TOKEN.")

    allowed_users = _parse_allowed_users(
        os.environ.get("PAIDEIA_TELEGRAM_ALLOWED_USERS")
        or os.environ.get("HERMES_TELEGRAM_ALLOWED_USERS")
        or ""
    )
    if not allowed_users:
        raise SystemExit("Missing PAIDEIA_TELEGRAM_ALLOWED_USERS or HERMES_TELEGRAM_ALLOWED_USERS.")

    storage_root = Path(args.storage_root) if args.storage_root else STORAGE_ROOT
    employment_record_arg = args.employment_record or os.environ.get("PAIDEIA_TELEGRAM_EMPLOYMENT_RECORD")
    team_arg = args.team or os.environ.get("PAIDEIA_INVESTMENT_TEAM_FILE")
    employment_record = (
        Path(employment_record_arg)
        if employment_record_arg
        else _discover_latest_employment_record(storage_root)
    )
    team_path = Path(team_arg) if team_arg else None
    output_dir = Path(args.output_dir)
    llm_mode = args.llm_mode
    llm_model = args.llm_model
    chat_backend = args.chat_backend
    learn_from_chat = not args.no_learn_from_chat
    agent = _read_agent_summary(employment_record)

    api = TelegramApi(token)
    bot_info = api.call("getMe", timeout=20).get("result", {})
    print(f"Paideia Telegram bridge started for @{bot_info.get('username', 'unknown_bot')}", flush=True)
    print(
        _status_text(
            agent=agent,
            employment_record=employment_record,
            llm_mode=llm_mode,
            llm_model=llm_model,
            chat_backend=chat_backend,
            team_path=team_path,
        ),
        flush=True,
    )

    offset: int | None = None
    while True:
        try:
            payload: dict[str, Any] = {"timeout": 30, "allowed_updates": ["message"]}
            if offset is not None:
                payload["offset"] = offset
            updates = api.call("getUpdates", payload=payload, timeout=45).get("result", [])
        except Exception as exc:
            print(f"Telegram polling error: {type(exc).__name__}: {exc}", flush=True)
            time.sleep(5)
            continue

        for update in updates:
            offset = int(update["update_id"]) + 1
            message = update.get("message") or {}
            chat = message.get("chat") or {}
            sender = message.get("from") or {}
            chat_id = chat.get("id")
            user_id = sender.get("id")
            text = str(message.get("text") or "").strip()
            if not chat_id or not text:
                continue
            if int(user_id or 0) not in allowed_users:
                api.send_message(chat_id, "This Paideia bridge is private and this Telegram user is not allowed.")
                continue
            message_id = message.get("message_id")
            command = _telegram_command_name(text)
            if command in {"/start", "/status"}:
                api.send_message(
                    chat_id,
                    _status_text(
                        agent=agent,
                        employment_record=employment_record,
                        llm_mode=llm_mode,
                        llm_model=llm_model,
                        chat_backend=chat_backend,
                        team_path=team_path,
                    ),
                    reply_to_message_id=message_id,
                )
                continue
            if command == "/offline":
                llm_mode = "offline"
                api.send_message(chat_id, "Paideia chat mode switched to offline.", reply_to_message_id=message_id)
                continue
            if command == "/auto":
                llm_mode = "auto"
                api.send_message(chat_id, "Paideia chat mode switched to auto.", reply_to_message_id=message_id)
                continue
            if command == "/live":
                llm_mode = "live"
                api.send_message(chat_id, f"Paideia chat mode switched to live ({llm_model}).", reply_to_message_id=message_id)
                continue
            if command == "/codex":
                chat_backend = "codex_oauth"
                api.send_message(chat_id, "Paideia chat backend switched to ChatGPT/Codex OAuth.", reply_to_message_id=message_id)
                continue
            if command == "/api":
                chat_backend = "openai_api"
                api.send_message(chat_id, "Paideia chat backend switched to OpenAI API key Responses path.", reply_to_message_id=message_id)
                continue
            if command == "/backend":
                parts = text.split(maxsplit=1)
                if len(parts) == 2 and parts[1].strip() in {"codex_oauth", "openai_api", "auto"}:
                    chat_backend = parts[1].strip()
                    api.send_message(chat_id, f"Paideia chat backend switched to {chat_backend}.", reply_to_message_id=message_id)
                else:
                    api.send_message(chat_id, "Usage: /backend codex_oauth | openai_api | auto", reply_to_message_id=message_id)
                continue
            if command in {"/model", "/models"}:
                llm_model, reply = _handle_model_command(text, llm_model)
                api.send_message(chat_id, reply, reply_to_message_id=message_id)
                continue
            if command == "/help":
                api.send_message(
                    chat_id,
                    "/status - bridge status\n/live - live Paideia chat\n/auto - live when available, fallback locally\n/offline - deterministic local fallback\n/codex - use ChatGPT/Codex OAuth backend\n/api - use OpenAI API key backend\n/backend auto - try Codex OAuth, then API fallback\n/models - show selectable ChatGPT/Codex models\n/model <name> - switch model for later chat turns\n/team <objective> - dispatch objective to the investment specialist team and synthesize through CIO\n\nSend any other message to chat with the hired Paideia agent.",
                    reply_to_message_id=message_id,
                )
                continue
            if command == "/team":
                objective = text.split(maxsplit=1)[1].strip() if len(text.split(maxsplit=1)) == 2 else ""
                if not objective:
                    api.send_message(chat_id, "Usage: /team <investment research objective>", reply_to_message_id=message_id)
                    continue
                if team_path is None:
                    api.send_message(chat_id, "No investment team file is configured.", reply_to_message_id=message_id)
                    continue
                api.send_message(
                    chat_id,
                    "Dispatching the objective to the investment specialist team. I will send the CIO synthesis when it is ready.",
                    reply_to_message_id=message_id,
                )
                api.send_chat_action(chat_id)
                result = _run_team_directive(
                    team_path=team_path,
                    leader_record=employment_record,
                    objective=objective,
                    output_dir=output_dir,
                    llm_mode=llm_mode,
                    llm_model=llm_model,
                    learn_from_chat=learn_from_chat,
                    live_max_output_tokens=args.live_max_output_tokens,
                    chat_backend=chat_backend,
                    hermes_agent_root=args.hermes_agent_root,
                    team_max_workers=args.team_max_workers,
                )
                reply = result.get("answer") if result.get("ok") else f"Team dispatch failed.\nReason: {result.get('error')}"
                api.send_message(chat_id, str(reply), reply_to_message_id=message_id)
                continue

            api.send_chat_action(chat_id)
            result = _run_paideia_chat(
                employment_record=employment_record,
                message=text,
                output_dir=output_dir,
                llm_mode=llm_mode,
                llm_model=llm_model,
                learn_from_chat=learn_from_chat,
                live_max_output_tokens=args.live_max_output_tokens,
                chat_backend=chat_backend,
                hermes_agent_root=args.hermes_agent_root,
            )
            if result["ok"]:
                reply = result["answer"]
                if args.show_mode_footer:
                    reply = f"{reply}\n\n[{result['mode']}]"
            else:
                reply = (
                    "Paideia chat failed.\n"
                    f"Reason: {result.get('error')}\n"
                    f"Detail: {result.get('detail')}"
                )
            api.send_message(chat_id, reply, reply_to_message_id=message_id)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Telegram bridge for a locally hired Paideia Agent.")
    parser.add_argument("--env-file", help="Optional env file with Telegram bot and allowlist settings.")
    parser.add_argument("--storage-root", help="Root containing talent-foundry runtime storage.")
    parser.add_argument("--employment-record")
    parser.add_argument("--team")
    parser.add_argument("--output-dir", default=str(talent_foundry_storage_path("telegram-bridge", "runs")))
    parser.add_argument("--llm-mode", choices=["offline", "auto", "live"], default=os.environ.get("PAIDEIA_LLM_MODE", "live"))
    parser.add_argument(
        "--llm-model",
        default=os.environ.get("PAIDEIA_LLM_MODEL")
        or os.environ.get("AI22B_OPENAI_MODEL")
        or os.environ.get("OPENAI_MODEL")
        or DEFAULT_MODEL,
    )
    parser.add_argument(
        "--chat-backend",
        choices=["codex_oauth", "openai_api", "auto"],
        default=os.environ.get("PAIDEIA_CHAT_BACKEND", "codex_oauth"),
    )
    parser.add_argument("--hermes-agent-root", default=os.environ.get("PAIDEIA_HERMES_AGENT_ROOT"))
    parser.add_argument("--no-learn-from-chat", action="store_true")
    parser.add_argument("--team-max-workers", type=int, default=int(os.environ.get("PAIDEIA_TEAM_MAX_WORKERS", "1")))
    parser.add_argument(
        "--live-max-output-tokens",
        type=int,
        default=int(os.environ.get("PAIDEIA_LIVE_MAX_OUTPUT_TOKENS", DEFAULT_LIVE_MAX_OUTPUT_TOKENS)),
    )
    parser.add_argument(
        "--show-mode-footer",
        action="store_true",
        default=os.environ.get("PAIDEIA_TELEGRAM_SHOW_MODE_FOOTER") == "1",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    run_bridge(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
