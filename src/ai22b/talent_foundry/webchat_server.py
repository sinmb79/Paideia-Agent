from __future__ import annotations

import json
from datetime import datetime, timezone
from html import escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from ai22b.talent_foundry.channel_gateway import run_openclaw_channel_message
from ai22b.talent_foundry.openclaw_employment_runtime import build_runtime_selection_snapshot
from ai22b.talent_foundry.openclaw_live_smoke_plan import build_openclaw_live_smoke_plan


WEBCHAT_SERVER_SCHEMA = "ai22b-openclaw-webchat-server/v1"
WEBCHAT_RESPONSE_SCHEMA = "ai22b-openclaw-webchat-response/v1"
WEBCHAT_RUNTIME_SCHEMA = "ai22b-openclaw-webchat-runtime/v1"
MAX_MESSAGE_BYTES = 1_000_000


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json_response(handler: BaseHTTPRequestHandler, status: int, payload: dict[str, Any]) -> None:
    body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Cache-Control", "no-store")
    handler.end_headers()
    handler.wfile.write(body)


def _write_text_response(handler: BaseHTTPRequestHandler, status: int, text: str, content_type: str) -> None:
    body = text.encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", content_type)
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Cache-Control", "no-store")
    handler.end_headers()
    handler.wfile.write(body)


def _webchat_html(agent_name: str, *, default_llm_mode: str, default_llm_model: str | None) -> str:
    escaped_agent_name = escape(agent_name)
    escaped_default_llm_mode = escape(default_llm_mode)
    escaped_default_llm_model = escape(default_llm_model or "")
    return f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Paideia WebChat - {escaped_agent_name}</title>
  <style>
    :root {{ color-scheme: light dark; font-family: system-ui, -apple-system, Segoe UI, sans-serif; }}
    body {{ margin: 0; background: #101418; color: #eef4f7; }}
    main {{ max-width: 980px; margin: 0 auto; padding: 24px; min-height: 100vh; box-sizing: border-box; display: flex; flex-direction: column; gap: 16px; }}
    header {{ display: flex; justify-content: space-between; align-items: baseline; gap: 16px; border-bottom: 1px solid #28343d; padding-bottom: 12px; }}
    h1 {{ font-size: 20px; margin: 0; }}
    #status {{ color: #9ab0bd; font-size: 13px; }}
    #runtime {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 8px; }}
    .metric {{ border: 1px solid #2b3a44; border-radius: 8px; padding: 10px; background: #111a22; min-height: 54px; }}
    .metric span {{ display: block; color: #9ab0bd; font-size: 12px; margin-bottom: 4px; }}
    .metric strong {{ font-size: 13px; overflow-wrap: anywhere; }}
    details {{ border: 1px solid #2b3a44; border-radius: 8px; padding: 10px 12px; background: #0d1318; }}
    summary {{ cursor: pointer; font-weight: 700; }}
    #smoke {{ margin: 10px 0 0; padding-left: 20px; color: #c8d7df; }}
    #smoke li {{ margin: 4px 0; }}
    #chat {{ flex: 1; display: flex; flex-direction: column; gap: 12px; overflow-y: auto; padding: 4px 0; }}
    .msg {{ border: 1px solid #2b3a44; border-radius: 8px; padding: 12px; line-height: 1.55; white-space: pre-wrap; }}
    .user {{ align-self: flex-end; background: #17324a; max-width: 78%; }}
    .assistant {{ align-self: flex-start; background: #182420; max-width: 86%; }}
    #controls {{ display: grid; grid-template-columns: 140px minmax(0, 1fr); gap: 8px; align-items: center; }}
    label {{ color: #b7c7d0; font-size: 12px; display: flex; flex-direction: column; gap: 4px; }}
    select, input {{ border-radius: 8px; border: 1px solid #2b3a44; background: #0d1115; color: inherit; padding: 9px; }}
    form {{ display: flex; gap: 8px; }}
    textarea {{ flex: 1; resize: vertical; min-height: 48px; max-height: 160px; border-radius: 8px; border: 1px solid #2b3a44; background: #0d1115; color: inherit; padding: 10px; }}
    button {{ border-radius: 8px; border: 1px solid #567; background: #e7f2ff; color: #101418; padding: 0 18px; font-weight: 700; }}
    button:disabled {{ opacity: 0.55; }}
  </style>
</head>
<body>
  <main>
    <header>
      <h1>{escaped_agent_name} WebChat</h1>
      <span id="status">local loopback gateway</span>
    </header>
    <section id="runtime" aria-label="OpenClaw runtime"></section>
    <details open>
      <summary>OpenClaw smoke plan</summary>
      <ol id="smoke"></ol>
    </details>
    <section id="controls" aria-label="LLM runtime controls">
      <label>Mode
        <select id="llm-mode">
          <option value="offline">offline</option>
          <option value="auto">auto</option>
          <option value="live">live</option>
        </select>
      </label>
      <label>Model override
        <input id="llm-model" value="{escaped_default_llm_model}" placeholder="provider/model" />
      </label>
    </section>
    <section id="chat" aria-live="polite"></section>
    <form id="form">
      <textarea id="message" placeholder="Type a message for the local Paideia agent"></textarea>
      <button id="send" type="submit">Send</button>
    </form>
  </main>
  <script>
    const chat = document.querySelector("#chat");
    const form = document.querySelector("#form");
    const textarea = document.querySelector("#message");
    const send = document.querySelector("#send");
    const llmMode = document.querySelector("#llm-mode");
    const llmModel = document.querySelector("#llm-model");
    const runtime = document.querySelector("#runtime");
    const smoke = document.querySelector("#smoke");
    const conversationId = "webchat-" + Math.random().toString(16).slice(2);
    llmMode.value = "{escaped_default_llm_mode}";
    function addMessage(kind, text) {{
      const div = document.createElement("div");
      div.className = "msg " + kind;
      div.textContent = text;
      chat.appendChild(div);
      div.scrollIntoView({{ block: "end" }});
    }}
    function metric(label, value) {{
      const div = document.createElement("div");
      div.className = "metric";
      div.innerHTML = "<span></span><strong></strong>";
      div.querySelector("span").textContent = label;
      div.querySelector("strong").textContent = value || "not selected";
      runtime.appendChild(div);
    }}
    async function loadRuntime() {{
      try {{
        const response = await fetch("/api/runtime");
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || "runtime request failed");
        const llm = data.runtime_selection.llm;
        const chatRuntime = data.runtime_selection.chat;
        metric("Provider", llm.openclaw_provider_id || llm.service_id);
        metric("Model", llm.openclaw_model || llm.selected_model);
        metric("Runtime path", data.live_smoke_plan.selection.live_runtime_path);
        metric("Chat surface", chatRuntime.surface_id);
        metric("Chat channel", data.webchat_controls.selected_chat_channel);
        metric("Network", llm.network_access);
        metric("Plan status", data.live_smoke_plan.status);
        metric("Secrets", data.security.secret_values_stored ? "stored" : "not stored");
        llmMode.value = data.webchat_controls.default_llm_mode || llmMode.value;
        if (!llmModel.value && data.webchat_controls.default_llm_model_override) {{
          llmModel.value = data.webchat_controls.default_llm_model_override;
        }}
        for (const step of data.live_smoke_plan.operator_sequence) {{
          const li = document.createElement("li");
          li.textContent = step;
          smoke.appendChild(li);
        }}
      }} catch (error) {{
        metric("Runtime", "unavailable: " + error.message);
      }}
    }}
    form.addEventListener("submit", async (event) => {{
      event.preventDefault();
      const text = textarea.value.trim();
      if (!text) return;
      addMessage("user", text);
      textarea.value = "";
      send.disabled = true;
      try {{
        const response = await fetch("/api/message", {{
          method: "POST",
          headers: {{ "Content-Type": "application/json" }},
          body: JSON.stringify({{
            message: text,
            conversation_id: conversationId,
            sender_id: "webchat-user",
            llm_mode: llmMode.value,
            llm_model: llmModel.value.trim()
          }})
        }});
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || "request failed");
        addMessage("assistant", data.reply_text || "");
      }} catch (error) {{
        addMessage("assistant", "WebChat gateway error: " + error.message);
      }} finally {{
        send.disabled = false;
        textarea.focus();
      }}
    }});
    loadRuntime();
  </script>
</body>
</html>
"""


def _runtime_payload(
    employment_record_path: Path,
    employment: dict[str, Any],
    *,
    llm_mode: str,
    llm_model: str | None,
) -> dict[str, Any]:
    runtime_selection = build_runtime_selection_snapshot(employment, channels=["webchat"])
    live_smoke_plan = _smoke_plan_payload(employment_record_path)
    return {
        "schema": WEBCHAT_RUNTIME_SCHEMA,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "runtime_selection": runtime_selection,
        "live_smoke_plan": {
            "schema": live_smoke_plan["schema"],
            "status": live_smoke_plan["status"],
            "operator_sequence": live_smoke_plan["operator_sequence"],
            "commands": live_smoke_plan["commands"],
            "policy": live_smoke_plan["policy"],
            "selection": live_smoke_plan["selection"],
        },
        "webchat_controls": {
            "available_llm_modes": ["offline", "auto", "live"],
            "default_llm_mode": llm_mode,
            "default_llm_model_override": llm_model,
            "selected_chat_channel": "webchat",
            "message_endpoint": "/api/message",
            "live_requires_operator_opt_in": True,
        },
        "security": {
            "secret_values_stored": False,
            "external_network_call_performed": False,
            "private_training_files_sent_to_channel": False,
        },
    }


def _smoke_plan_payload(employment_record_path: Path) -> dict[str, Any]:
    return build_openclaw_live_smoke_plan(
        employment_record_path,
        channels=["webchat"],
    )


def make_openclaw_webchat_server(
    employment_record_path: Path,
    *,
    bind_host: str = "127.0.0.1",
    port: int = 8722,
    llm_mode: str = "offline",
    llm_model: str | None = None,
    learn_from_chat: bool = False,
    output_dir: Path | None = None,
) -> ThreadingHTTPServer:
    employment_record_path = employment_record_path.resolve()
    employment = _read_json(employment_record_path)
    if employment.get("schema") != "ai-talent-local-employment/v1":
        raise ValueError("Unsupported local employment record schema")
    if employment.get("status") != "active":
        raise ValueError("Local employment record is not active")
    output_dir = output_dir or employment_record_path.parent / "openclaw_webchat_runs"
    output_dir.mkdir(parents=True, exist_ok=True)

    class PaideiaWebChatHandler(BaseHTTPRequestHandler):
        server_version = "PaideiaOpenClawWebChat/0.1"

        def log_message(self, format: str, *args: Any) -> None:
            return

        def do_GET(self) -> None:
            path = urlparse(self.path).path
            if path == "/health":
                _write_json_response(
                    self,
                    200,
                    {
                        "schema": WEBCHAT_SERVER_SCHEMA,
                        "status": "ok",
                        "created_at_utc": datetime.now(timezone.utc).isoformat(),
                        "channel_id": "webchat",
                        "agent": employment["agent"],
                        "paths": {
                            "webchat": "/webchat",
                            "runtime": "/api/runtime",
                            "smoke_plan": "/api/smoke-plan",
                            "message": "/api/message",
                        },
                        "security": {
                            "bind_host": bind_host,
                            "external_send_performed_by_core": False,
                            "private_training_files_sent_to_channel": False,
                        },
                    },
                )
                return
            if path == "/api/runtime":
                _write_json_response(
                    self,
                    200,
                    _runtime_payload(
                        employment_record_path,
                        employment,
                        llm_mode=llm_mode,
                        llm_model=llm_model,
                    ),
                )
                return
            if path == "/api/smoke-plan":
                _write_json_response(self, 200, _smoke_plan_payload(employment_record_path))
                return
            if path in {"/", "/webchat"}:
                _write_text_response(
                    self,
                    200,
                    _webchat_html(
                        employment["agent"]["name"],
                        default_llm_mode=llm_mode,
                        default_llm_model=llm_model,
                    ),
                    "text/html; charset=utf-8",
                )
                return
            _write_json_response(self, 404, {"error": "not_found"})

        def do_OPTIONS(self) -> None:
            self.send_response(204)
            self.send_header("Allow", "GET, POST, OPTIONS")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()

        def do_POST(self) -> None:
            path = urlparse(self.path).path
            if path != "/api/message":
                _write_json_response(self, 404, {"error": "not_found"})
                return
            try:
                size = int(self.headers.get("Content-Length", "0"))
                if size > MAX_MESSAGE_BYTES:
                    _write_json_response(self, 413, {"error": "request_too_large"})
                    return
                payload = json.loads(self.rfile.read(size).decode("utf-8")) if size else {}
            except Exception as exc:
                _write_json_response(self, 400, {"error": "invalid_json", "detail": str(exc)[:240]})
                return
            message = str(payload.get("message", "")).strip()
            if not message:
                _write_json_response(self, 400, {"error": "message_required"})
                return
            requested_llm_mode = str(payload.get("llm_mode") or llm_mode).strip().casefold()
            if requested_llm_mode not in {"offline", "auto", "live"}:
                _write_json_response(
                    self,
                    400,
                    {"error": "invalid_llm_mode", "allowed": ["offline", "auto", "live"]},
                )
                return
            requested_llm_model = str(payload.get("llm_model") or llm_model or "").strip() or None
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
            run_path = output_dir / f"webchat_{timestamp}.json"
            try:
                run = run_openclaw_channel_message(
                    employment_record_path,
                    channel_id="webchat",
                    message=message,
                    sender_id=str(payload.get("sender_id") or "webchat-user"),
                    conversation_id=str(payload.get("conversation_id") or "webchat"),
                    output_path=run_path,
                    llm_mode=requested_llm_mode,
                    llm_model=requested_llm_model,
                    learn_from_chat=learn_from_chat,
                    metadata={"external_platform_event": False, "webchat_request": True},
                )
            except Exception as exc:
                _write_json_response(self, 500, {"error": "channel_run_failed", "detail": str(exc)[:500]})
                return
            _write_json_response(
                self,
                200,
                {
                    "schema": WEBCHAT_RESPONSE_SCHEMA,
                    "status": run["status"],
                    "reply_text": run["outbound"]["text"],
                    "channel_run": run,
                    "channel_run_path": str(run_path),
                    "runtime_request": {
                        "llm_mode": requested_llm_mode,
                        "llm_model_override": requested_llm_model,
                        "chat_channel": "webchat",
                    },
                    "security": {
                        "external_send_performed_by_core": False,
                        "live_llm_network_requested": requested_llm_mode in {"auto", "live"},
                        "private_training_files_sent_to_channel": False,
                    },
                },
            )

    server = ThreadingHTTPServer((bind_host, port), PaideiaWebChatHandler)
    server.paideia_webchat = {  # type: ignore[attr-defined]
        "schema": WEBCHAT_SERVER_SCHEMA,
        "employment_record": str(employment_record_path),
        "output_dir": str(output_dir),
        "llm_mode": llm_mode,
        "llm_model": llm_model,
        "learn_from_chat": learn_from_chat,
    }
    return server


def run_openclaw_webchat_server(
    employment_record_path: Path,
    *,
    bind_host: str = "127.0.0.1",
    port: int = 8722,
    llm_mode: str = "offline",
    llm_model: str | None = None,
    learn_from_chat: bool = False,
    output_dir: Path | None = None,
) -> None:
    server = make_openclaw_webchat_server(
        employment_record_path,
        bind_host=bind_host,
        port=port,
        llm_mode=llm_mode,
        llm_model=llm_model,
        learn_from_chat=learn_from_chat,
        output_dir=output_dir,
    )
    actual_host, actual_port = server.server_address
    print(f"Paideia OpenClaw WebChat gateway: http://{actual_host}:{actual_port}/")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
