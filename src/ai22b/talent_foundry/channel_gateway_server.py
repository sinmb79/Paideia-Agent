from __future__ import annotations

import json
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from ai22b.talent_foundry.channel_gateway import (
    OPENCLAW_CHANNEL_MESSAGE_SCHEMA,
    OPENCLAW_GATEWAY_CONFIG_SCHEMA,
    build_openclaw_gateway_config,
    run_openclaw_channel_message,
)
from ai22b.talent_foundry.channel_ingress import translate_openclaw_platform_event
from ai22b.talent_foundry.openclaw_compat import find_openclaw_channel


OPENCLAW_CHANNEL_GATEWAY_SERVER_SCHEMA = "ai22b-openclaw-channel-gateway-server/v1"
OPENCLAW_CHANNEL_GATEWAY_RESPONSE_SCHEMA = "ai22b-openclaw-channel-gateway-response/v1"
MAX_CHANNEL_MESSAGE_BYTES = 1_000_000


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


def _extract_channel_payload(payload: dict[str, Any]) -> dict[str, Any]:
    channel_payload = payload.get("channel") if isinstance(payload.get("channel"), dict) else {}
    message_payload = payload.get("message") if isinstance(payload.get("message"), dict) else {}
    sender_payload = payload.get("sender") if isinstance(payload.get("sender"), dict) else {}
    channel_id = (
        channel_payload.get("channel_id")
        or channel_payload.get("id")
        or payload.get("channel_id")
        or payload.get("channel")
    )
    message = message_payload.get("text") or payload.get("text") or payload.get("message_text") or payload.get("message")
    sender_id = sender_payload.get("sender_id") or payload.get("sender_id") or payload.get("from") or "channel-user"
    conversation_id = (
        payload.get("conversation_id")
        or payload.get("thread_id")
        or payload.get("session_key")
        or payload.get("chat_id")
        or "channel-conversation"
    )
    metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
    metadata = {
        **metadata,
        "external_platform_event": bool(
            payload.get("schema") == OPENCLAW_CHANNEL_MESSAGE_SCHEMA
            or payload.get("external_platform_event")
            or metadata.get("external_platform_event")
        ),
        "gateway_http_request": True,
        "source_schema": payload.get("schema"),
    }
    return {
        "channel_id": str(channel_id or "").strip(),
        "message": str(message or "").strip(),
        "sender_id": str(sender_id or "channel-user"),
        "conversation_id": str(conversation_id or "channel-conversation"),
        "metadata": metadata,
    }


def make_openclaw_channel_gateway_server(
    employment_record_path: Path,
    *,
    channels: list[str] | None = None,
    access_config_path: Path | None = None,
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
    output_dir = output_dir or employment_record_path.parent / "openclaw_channel_gateway_runs"
    output_dir.mkdir(parents=True, exist_ok=True)
    config = build_openclaw_gateway_config(
        employment_record_path,
        channels=channels or ["telegram", "discord", "slack", "webchat"],
        bind_host=bind_host,
        port=port,
    )
    allowed_channels = {item["channel_id"] for item in config["allowed_channels"]}
    access_config = _read_json(access_config_path) if access_config_path else None

    class PaideiaOpenClawGatewayHandler(BaseHTTPRequestHandler):
        server_version = "PaideiaOpenClawChannelGateway/0.1"

        def log_message(self, format: str, *args: Any) -> None:
            return

        def do_GET(self) -> None:
            path = urlparse(self.path).path
            if path == "/health":
                _write_json_response(
                    self,
                    200,
                    {
                        "schema": OPENCLAW_CHANNEL_GATEWAY_SERVER_SCHEMA,
                        "status": "ok",
                        "created_at_utc": datetime.now(timezone.utc).isoformat(),
                        "gateway_config_schema": OPENCLAW_GATEWAY_CONFIG_SCHEMA,
                        "employment": config["employment"],
                        "allowed_channels": config["allowed_channels"],
                        "paths": config["gateway"]["http_paths"],
                        "security": {
                            "bind_host": bind_host,
                            "platform_event_access_config_loaded": bool(access_config),
                            "external_send_performed_by_core": False,
                            "private_training_files_sent_to_channel": False,
                            "raw_external_payload_saved": False,
                        },
                    },
                )
                return
            if path == "/openclaw/gateway-config":
                _write_json_response(self, 200, config)
                return
            _write_json_response(self, 404, {"error": "not_found"})

        def do_OPTIONS(self) -> None:
            self.send_response(204)
            self.send_header("Allow", "GET, POST, OPTIONS")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()

        def do_POST(self) -> None:
            path = urlparse(self.path).path
            if path == "/openclaw/channel-message":
                self._handle_channel_message()
                return
            if path.startswith("/openclaw/platform-event"):
                self._handle_platform_event(path)
                return
            _write_json_response(self, 404, {"error": "not_found"})

        def _read_payload(self) -> dict[str, Any] | None:
            try:
                size = int(self.headers.get("Content-Length", "0"))
                if size > MAX_CHANNEL_MESSAGE_BYTES:
                    _write_json_response(self, 413, {"error": "request_too_large"})
                    return None
                return json.loads(self.rfile.read(size).decode("utf-8")) if size else {}
            except Exception as exc:
                _write_json_response(self, 400, {"error": "invalid_json", "detail": str(exc)[:240]})
                return None

        def _handle_channel_message(self) -> None:
            payload = self._read_payload()
            if payload is None:
                return
            response = self._run_normalized_payload(payload)
            _write_json_response(self, response["status_code"], response["body"])

        def _handle_platform_event(self, path: str) -> None:
            payload = self._read_payload()
            if payload is None:
                return
            path_parts = [part for part in path.split("/") if part]
            channel_id = ""
            if len(path_parts) >= 3:
                channel_id = path_parts[2]
            channel_id = str(payload.get("channel_id") or payload.get("platform") or channel_id or "").strip()
            try:
                translation = translate_openclaw_platform_event(
                    channel_id=channel_id,
                    payload=payload,
                    access_config=access_config,
                )
            except Exception as exc:
                _write_json_response(self, 400, {"error": "platform_event_translation_failed", "detail": str(exc)[:500]})
                return
            if not translation["access"]["allowed"]:
                _write_json_response(self, 403, translation)
                return
            response = self._run_normalized_payload(translation["channel_message"])
            body = {
                "schema": OPENCLAW_CHANNEL_GATEWAY_RESPONSE_SCHEMA,
                "status": response["body"].get("status"),
                "platform_event_translation": translation,
                **response["body"],
            }
            _write_json_response(self, response["status_code"], body)

        def _run_normalized_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
            normalized = _extract_channel_payload(payload)
            channel = find_openclaw_channel(normalized["channel_id"])
            if channel is None:
                return {
                    "status_code": 400,
                    "body": {"error": "unsupported_channel", "channel_id": normalized["channel_id"]},
                }
            if channel["channel_id"] not in allowed_channels:
                return {
                    "status_code": 403,
                    "body": {"error": "channel_not_allowed", "channel_id": channel["channel_id"]},
                }
            if not normalized["message"]:
                return {"status_code": 400, "body": {"error": "message_required"}}
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
            run_path = output_dir / f"{channel['channel_id']}_{timestamp}.json"
            try:
                run = run_openclaw_channel_message(
                    employment_record_path,
                    channel_id=channel["channel_id"],
                    message=normalized["message"],
                    sender_id=normalized["sender_id"],
                    conversation_id=normalized["conversation_id"],
                    output_path=run_path,
                    llm_mode=llm_mode,
                    llm_model=llm_model,
                    learn_from_chat=learn_from_chat,
                    metadata=normalized["metadata"],
                )
            except Exception as exc:
                return {
                    "status_code": 500,
                    "body": {"error": "channel_run_failed", "detail": str(exc)[:500]},
                }
            return {
                "status_code": 200,
                "body": {
                    "schema": OPENCLAW_CHANNEL_GATEWAY_RESPONSE_SCHEMA,
                    "status": run["status"],
                    "channel_run": run,
                    "channel_run_path": str(run_path),
                    "outbound": run["outbound"],
                    "security": run["security"],
                },
            }

    server = ThreadingHTTPServer((bind_host, port), PaideiaOpenClawGatewayHandler)
    server.paideia_openclaw_channel_gateway = {  # type: ignore[attr-defined]
        "schema": OPENCLAW_CHANNEL_GATEWAY_SERVER_SCHEMA,
        "employment_record": str(employment_record_path),
        "output_dir": str(output_dir),
        "channels": sorted(allowed_channels),
        "llm_mode": llm_mode,
        "llm_model": llm_model,
        "learn_from_chat": learn_from_chat,
    }
    return server


def run_openclaw_channel_gateway_server(
    employment_record_path: Path,
    *,
    channels: list[str] | None = None,
    access_config_path: Path | None = None,
    bind_host: str = "127.0.0.1",
    port: int = 8722,
    llm_mode: str = "offline",
    llm_model: str | None = None,
    learn_from_chat: bool = False,
    output_dir: Path | None = None,
) -> None:
    server = make_openclaw_channel_gateway_server(
        employment_record_path,
        channels=channels,
        access_config_path=access_config_path,
        bind_host=bind_host,
        port=port,
        llm_mode=llm_mode,
        llm_model=llm_model,
        learn_from_chat=learn_from_chat,
        output_dir=output_dir,
    )
    actual_host, actual_port = server.server_address
    print(f"Paideia OpenClaw channel gateway: http://{actual_host}:{actual_port}/")
    print("POST OpenClaw-style messages to /openclaw/channel-message.")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
