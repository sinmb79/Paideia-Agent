from __future__ import annotations

import json
from datetime import datetime, timezone
from html import escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from ai22b.talent_foundry.channel_gateway import run_openclaw_channel_message


WEBCHAT_SERVER_SCHEMA = "ai22b-openclaw-webchat-server/v1"
WEBCHAT_RESPONSE_SCHEMA = "ai22b-openclaw-webchat-response/v1"
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


def _webchat_html(agent_name: str) -> str:
    escaped_agent_name = escape(agent_name)
    return f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Paideia WebChat - {escaped_agent_name}</title>
  <style>
    :root {{ color-scheme: light dark; font-family: system-ui, -apple-system, Segoe UI, sans-serif; }}
    body {{ margin: 0; background: #101418; color: #eef4f7; }}
    main {{ max-width: 880px; margin: 0 auto; padding: 24px; min-height: 100vh; box-sizing: border-box; display: flex; flex-direction: column; gap: 16px; }}
    header {{ display: flex; justify-content: space-between; align-items: baseline; gap: 16px; border-bottom: 1px solid #28343d; padding-bottom: 12px; }}
    h1 {{ font-size: 20px; margin: 0; }}
    #status {{ color: #9ab0bd; font-size: 13px; }}
    #chat {{ flex: 1; display: flex; flex-direction: column; gap: 12px; overflow-y: auto; padding: 4px 0; }}
    .msg {{ border: 1px solid #2b3a44; border-radius: 8px; padding: 12px; line-height: 1.55; white-space: pre-wrap; }}
    .user {{ align-self: flex-end; background: #17324a; max-width: 78%; }}
    .assistant {{ align-self: flex-start; background: #182420; max-width: 86%; }}
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
    const conversationId = "webchat-" + Math.random().toString(16).slice(2);
    function addMessage(kind, text) {{
      const div = document.createElement("div");
      div.className = "msg " + kind;
      div.textContent = text;
      chat.appendChild(div);
      div.scrollIntoView({{ block: "end" }});
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
          body: JSON.stringify({{ message: text, conversation_id: conversationId, sender_id: "webchat-user" }})
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
  </script>
</body>
</html>
"""


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
            if path in {"/", "/webchat"}:
                _write_text_response(
                    self,
                    200,
                    _webchat_html(employment["agent"]["name"]),
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
                    llm_mode=llm_mode,
                    llm_model=llm_model,
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
                    "security": {
                        "external_send_performed_by_core": False,
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
