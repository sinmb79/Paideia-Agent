from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from time import monotonic
from typing import Any


WORKSPACE_SANDBOX_SCHEMA = "paideia-workspace-sandbox-policy/v1"
WORKSPACE_ROLLBACK_MANIFEST_SCHEMA = "paideia-workspace-rollback-manifest/v1"
DEFAULT_MAX_OUTPUT_FILE_BYTES = 2_000_000
DEFAULT_MAX_INPUT_FILE_BYTES = 1_000_000
DEFAULT_MAX_TOTAL_OUTPUT_BYTES = 10_000_000
DEFAULT_MAX_DECLARED_OUTPUTS = 64
DEFAULT_MAX_TRACE_EVENTS = 200
DEFAULT_MAX_RUNTIME_SECONDS = 300


class SandboxViolation(ValueError):
    """Raised when a workspace operation violates the local sandbox policy."""


def sandbox_kwargs_from_resource_limits(resource_limits: dict[str, Any] | None) -> dict[str, Any]:
    limits = resource_limits or {}

    def positive_int(key: str, default: int) -> int:
        try:
            value = int(limits.get(key, default))
        except (TypeError, ValueError):
            value = default
        return max(1, value)

    def string_list(key: str) -> list[str]:
        value = limits.get(key, [])
        if not isinstance(value, list):
            return []
        return [str(item) for item in value if str(item).strip()]

    return {
        "max_input_file_bytes": positive_int("max_input_file_bytes", DEFAULT_MAX_INPUT_FILE_BYTES),
        "max_output_file_bytes": positive_int("max_output_file_bytes", DEFAULT_MAX_OUTPUT_FILE_BYTES),
        "max_total_output_bytes": positive_int("max_total_output_bytes", DEFAULT_MAX_TOTAL_OUTPUT_BYTES),
        "max_declared_outputs": positive_int("max_declared_outputs", DEFAULT_MAX_DECLARED_OUTPUTS),
        "max_trace_events": positive_int("max_trace_events", DEFAULT_MAX_TRACE_EVENTS),
        "max_runtime_seconds": positive_int("max_runtime_seconds", DEFAULT_MAX_RUNTIME_SECONDS),
        "allowed_network_hosts": string_list("allowed_network_hosts"),
        "allowed_subprocess_commands": string_list("allowed_subprocess_commands"),
    }


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def workspace_sandbox_policy(
    workspace_root: Path,
    *,
    max_input_file_bytes: int = DEFAULT_MAX_INPUT_FILE_BYTES,
    max_output_file_bytes: int = DEFAULT_MAX_OUTPUT_FILE_BYTES,
    max_total_output_bytes: int = DEFAULT_MAX_TOTAL_OUTPUT_BYTES,
    max_declared_outputs: int = DEFAULT_MAX_DECLARED_OUTPUTS,
    max_trace_events: int = DEFAULT_MAX_TRACE_EVENTS,
    max_runtime_seconds: int = DEFAULT_MAX_RUNTIME_SECONDS,
    allowed_network_hosts: list[str] | None = None,
    allowed_subprocess_commands: list[str] | None = None,
) -> dict[str, Any]:
    root = workspace_root.resolve()
    network_allowlist = allowed_network_hosts or []
    subprocess_allowlist = allowed_subprocess_commands or []
    return {
        "schema": WORKSPACE_SANDBOX_SCHEMA,
        "workspace_root": str(root),
        "filesystem": {
            "mode": "allowlist",
            "allowed_roots": [str(root)],
            "path_traversal_guard": True,
            "reads_must_use_workspace_sandbox": True,
            "writes_must_use_workspace_sandbox": True,
        },
        "network": {
            "default": "blocked",
            "allowlist": network_allowlist,
            "external_upload": "blocked_without_boss_approval",
        },
        "subprocess": {
            "default": "blocked",
            "allowlist": subprocess_allowlist,
        },
        "resource_limits": {
            "max_input_file_bytes": max_input_file_bytes,
            "max_output_file_bytes": max_output_file_bytes,
            "max_total_output_bytes": max_total_output_bytes,
            "max_declared_outputs": max_declared_outputs,
            "max_trace_events": max_trace_events,
            "max_runtime_seconds": max_runtime_seconds,
        },
        "rollback": {
            "generated_files_are_declared_in_workspace_outputs": True,
            "manual_delete_safe_within_workspace_root": True,
            "rollback_manifest_required": True,
            "rollback_manifest_schema": WORKSPACE_ROLLBACK_MANIFEST_SCHEMA,
        },
        "audit": {
            "trace_required": True,
            "tool_execution_snapshot_required": True,
            "sandbox_enforcement_snapshot_required": True,
        },
        "enforcement": {
            "enabled": True,
            "write_api": "WorkspaceSandbox",
            "path_escape_raises": "SandboxViolation",
            "missing_input_raises": "SandboxViolation",
            "oversized_input_raises": "SandboxViolation",
            "oversized_output_raises": "SandboxViolation",
            "trace_limit_raises": "SandboxViolation",
            "total_output_budget_raises": "SandboxViolation",
            "declared_output_count_raises": "SandboxViolation",
            "runtime_budget_raises": "SandboxViolation",
            "network_and_subprocess_default": "deny",
        },
    }


class WorkspaceSandbox:
    def __init__(
        self,
        workspace_root: Path,
        *,
        max_input_file_bytes: int = DEFAULT_MAX_INPUT_FILE_BYTES,
        max_output_file_bytes: int = DEFAULT_MAX_OUTPUT_FILE_BYTES,
        max_total_output_bytes: int = DEFAULT_MAX_TOTAL_OUTPUT_BYTES,
        max_declared_outputs: int = DEFAULT_MAX_DECLARED_OUTPUTS,
        max_trace_events: int = DEFAULT_MAX_TRACE_EVENTS,
        max_runtime_seconds: int = DEFAULT_MAX_RUNTIME_SECONDS,
        allowed_network_hosts: list[str] | None = None,
        allowed_subprocess_commands: list[str] | None = None,
    ) -> None:
        self.root = workspace_root.resolve()
        self.max_input_file_bytes = max_input_file_bytes
        self.max_output_file_bytes = max_output_file_bytes
        self.max_total_output_bytes = max_total_output_bytes
        self.max_declared_outputs = max_declared_outputs
        self.max_trace_events = max_trace_events
        self.max_runtime_seconds = max_runtime_seconds
        self.allowed_network_hosts = allowed_network_hosts or []
        self.allowed_subprocess_commands = allowed_subprocess_commands or []
        self.started_monotonic = monotonic()
        self.audit_events: list[dict[str, Any]] = []
        self.declared_inputs: list[dict[str, Any]] = []
        self.declared_outputs: list[dict[str, Any]] = []
        self.total_input_bytes = 0
        self.total_output_bytes = 0

    def ensure_root(self) -> Path:
        self._enforce_runtime_budget("ensure_root")
        self.root.mkdir(parents=True, exist_ok=True)
        return self.root

    def safe_path(self, relative_path: str | Path) -> Path:
        self._enforce_runtime_budget("safe_path")
        candidate = Path(relative_path)
        if candidate.is_absolute():
            path = candidate.resolve()
        else:
            path = (self.root / candidate).resolve()
        if self.root not in path.parents and path != self.root:
            self._audit("path_escape_blocked", requested=str(relative_path), resolved=str(path))
            raise SandboxViolation("Workspace path escaped workspace directory")
        return path

    def read_text(self, relative_path: str | Path, *, purpose: str) -> str:
        self._enforce_runtime_budget("read_text")
        path = self.safe_path(relative_path)
        if not path.exists():
            self._audit(
                "input_file_missing",
                requested=self._safe_requested_path(relative_path),
                purpose=purpose,
            )
            raise SandboxViolation("Workspace input file is missing")
        if not path.is_file():
            self._audit(
                "input_file_not_regular",
                requested=self._safe_requested_path(relative_path),
                purpose=purpose,
            )
            raise SandboxViolation("Workspace input path is not a regular file")
        byte_count = path.stat().st_size
        if byte_count > self.max_input_file_bytes:
            self._audit(
                "input_size_blocked",
                requested=self._safe_requested_path(relative_path),
                byte_count=byte_count,
                max_input_file_bytes=self.max_input_file_bytes,
            )
            raise SandboxViolation("Workspace input exceeded max_input_file_bytes")
        try:
            data = path.read_bytes()
            text = data.decode("utf-8")
        except UnicodeDecodeError as exc:
            self._audit(
                "input_decode_blocked",
                requested=self._safe_requested_path(relative_path),
                encoding="utf-8",
                error_type=type(exc).__name__,
            )
            raise SandboxViolation("Workspace input must be valid UTF-8 text") from exc
        self._declare_input(path, purpose=purpose, bytes_read=len(data))
        return text

    def write_text(self, relative_path: str | Path, text: str, *, purpose: str) -> Path:
        data = text.encode("utf-8")
        self._enforce_runtime_budget("write_text")
        self._enforce_declared_output_count(relative_path)
        self._enforce_output_size(relative_path, len(data))
        self._enforce_total_output_size(relative_path, len(data))
        path = self.safe_path(relative_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        self._declare_output(path, purpose=purpose, bytes_written=len(data))
        return path

    def write_json(self, relative_path: str | Path, data: dict[str, Any], *, purpose: str) -> Path:
        text = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
        return self.write_text(relative_path, text, purpose=purpose)

    def write_jsonl(self, relative_path: str | Path, entries: list[dict[str, Any]], *, purpose: str) -> Path:
        self._enforce_trace_events(relative_path, len(entries))
        text = "".join(json.dumps(entry, ensure_ascii=False) + "\n" for entry in entries)
        return self.write_text(relative_path, text, purpose=purpose)

    def append_jsonl(self, relative_path: str | Path, entries: list[dict[str, Any]], *, purpose: str) -> Path:
        self._enforce_runtime_budget("append_jsonl")
        path = self.safe_path(relative_path)
        existing_count = 0
        if path.exists():
            existing_count = len(path.read_text(encoding="utf-8").splitlines())
        self._enforce_trace_events(relative_path, existing_count + len(entries))
        text = "".join(json.dumps(entry, ensure_ascii=False) + "\n" for entry in entries)
        data = text.encode("utf-8")
        self._enforce_output_size(relative_path, path.stat().st_size + len(data) if path.exists() else len(data))
        self._enforce_total_output_size(relative_path, len(data))
        if not path.exists():
            self._enforce_declared_output_count(relative_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as file:
            file.write(text)
        self._declare_output(path, purpose=purpose, bytes_written=len(data), append=True)
        return path

    def deny_network(self, reason: str = "network_blocked_by_workspace_sandbox") -> None:
        self._audit("network_access_blocked", reason=reason)
        raise SandboxViolation(reason)

    def request_network(self, host: str, *, reason: str = "network_request") -> dict[str, Any]:
        self._enforce_runtime_budget("request_network")
        if host not in self.allowed_network_hosts:
            self._audit("network_access_blocked", host=host, reason=reason)
            raise SandboxViolation("network host not allowed by workspace sandbox")
        grant = {
            "host": host,
            "reason": reason,
            "granted": True,
            "network_call_performed": False,
        }
        self._audit("network_access_granted_without_call", **grant)
        return grant

    def deny_subprocess(self, reason: str = "subprocess_blocked_by_workspace_sandbox") -> None:
        self._audit("subprocess_blocked", reason=reason)
        raise SandboxViolation(reason)

    def request_subprocess(self, command: str, *, reason: str = "subprocess_request") -> dict[str, Any]:
        self._enforce_runtime_budget("request_subprocess")
        if command not in self.allowed_subprocess_commands:
            self._audit("subprocess_blocked", command=command, reason=reason)
            raise SandboxViolation("subprocess command not allowed by workspace sandbox")
        grant = {
            "command": command,
            "reason": reason,
            "granted": True,
            "subprocess_executed": False,
        }
        self._audit("subprocess_granted_without_execution", **grant)
        return grant

    def policy(self) -> dict[str, Any]:
        return workspace_sandbox_policy(
            self.root,
            max_input_file_bytes=self.max_input_file_bytes,
            max_output_file_bytes=self.max_output_file_bytes,
            max_total_output_bytes=self.max_total_output_bytes,
            max_declared_outputs=self.max_declared_outputs,
            max_trace_events=self.max_trace_events,
            max_runtime_seconds=self.max_runtime_seconds,
            allowed_network_hosts=self.allowed_network_hosts,
            allowed_subprocess_commands=self.allowed_subprocess_commands,
        )

    def snapshot(self) -> dict[str, Any]:
        policy = self.policy()
        policy["declared_inputs"] = self.declared_inputs
        policy["declared_outputs"] = self.declared_outputs
        policy["audit_events"] = self.audit_events
        policy["resource_usage"] = self.resource_usage()
        return policy

    def resource_usage(self) -> dict[str, Any]:
        elapsed = monotonic() - self.started_monotonic
        return {
            "elapsed_seconds": round(elapsed, 6),
            "total_input_bytes": self.total_input_bytes,
            "total_output_bytes": self.total_output_bytes,
            "declared_input_count": len(self.declared_inputs),
            "declared_output_count": len(self.declared_outputs),
            "remaining_total_output_bytes": max(0, self.max_total_output_bytes - self.total_output_bytes),
            "remaining_declared_outputs": max(0, self.max_declared_outputs - len(self.declared_outputs)),
            "runtime_budget_exceeded": elapsed > self.max_runtime_seconds,
            "within_budget": (
                elapsed <= self.max_runtime_seconds
                and self.total_output_bytes <= self.max_total_output_bytes
                and len(self.declared_outputs) <= self.max_declared_outputs
            ),
        }

    def rollback_manifest(self, *, operation_id: str = "workspace_run") -> dict[str, Any]:
        delete_order = [
            {
                "relative_path": output["relative_path"],
                "path": output["path"],
                "purpose": output["purpose"],
                "action": "manual_review_append" if output.get("append") else "delete_file",
                "safe_to_delete_within_workspace_root": True,
            }
            for output in reversed(self.declared_outputs)
        ]
        return {
            "schema": WORKSPACE_ROLLBACK_MANIFEST_SCHEMA,
            "created_at_utc": _now(),
            "operation_id": operation_id,
            "workspace_root": str(self.root),
            "rollback_mode": "manual_reviewed_delete_declared_outputs_only",
            "delete_order": delete_order,
            "append_entries_require_review": any(output.get("append") for output in self.declared_outputs),
            "never_delete_outside_workspace_root": True,
            "audit_artifacts_to_keep": ["rollback_manifest.json", "workspace_sandbox.json"],
        }

    def write_rollback_manifest(
        self,
        relative_path: str | Path = "rollback_manifest.json",
        *,
        operation_id: str = "workspace_run",
    ) -> Path:
        return self.write_json(
            relative_path,
            self.rollback_manifest(operation_id=operation_id),
            purpose="rollback_manifest",
        )

    def _safe_requested_path(self, relative_path: str | Path) -> str:
        candidate = Path(relative_path)
        if candidate.is_absolute():
            return candidate.name
        return candidate.as_posix()

    def _enforce_output_size(self, relative_path: str | Path, byte_count: int) -> None:
        if byte_count > self.max_output_file_bytes:
            self._audit(
                "output_size_blocked",
                requested=str(relative_path),
                byte_count=byte_count,
                max_output_file_bytes=self.max_output_file_bytes,
            )
            raise SandboxViolation("Workspace output exceeded max_output_file_bytes")

    def _enforce_total_output_size(self, relative_path: str | Path, byte_count: int) -> None:
        if self.total_output_bytes + byte_count > self.max_total_output_bytes:
            self._audit(
                "total_output_budget_blocked",
                requested=str(relative_path),
                byte_count=byte_count,
                total_output_bytes=self.total_output_bytes,
                max_total_output_bytes=self.max_total_output_bytes,
            )
            raise SandboxViolation("Workspace outputs exceeded max_total_output_bytes")

    def _enforce_declared_output_count(self, relative_path: str | Path) -> None:
        if len(self.declared_outputs) + 1 > self.max_declared_outputs:
            self._audit(
                "declared_output_count_blocked",
                requested=str(relative_path),
                declared_output_count=len(self.declared_outputs),
                max_declared_outputs=self.max_declared_outputs,
            )
            raise SandboxViolation("Workspace outputs exceeded max_declared_outputs")

    def _enforce_trace_events(self, relative_path: str | Path, event_count: int) -> None:
        if event_count > self.max_trace_events:
            self._audit(
                "trace_event_limit_blocked",
                requested=str(relative_path),
                event_count=event_count,
                max_trace_events=self.max_trace_events,
            )
            raise SandboxViolation("Workspace trace exceeded max_trace_events")

    def _enforce_runtime_budget(self, operation: str) -> None:
        elapsed = monotonic() - self.started_monotonic
        if elapsed > self.max_runtime_seconds:
            self._audit(
                "runtime_budget_blocked",
                operation=operation,
                elapsed_seconds=round(elapsed, 6),
                max_runtime_seconds=self.max_runtime_seconds,
            )
            raise SandboxViolation("Workspace runtime exceeded max_runtime_seconds")

    def _declare_output(self, path: Path, *, purpose: str, bytes_written: int, append: bool = False) -> None:
        self._enforce_declared_output_count(path.relative_to(self.root).as_posix())
        entry = {
            "path": str(path),
            "relative_path": path.relative_to(self.root).as_posix(),
            "purpose": purpose,
            "bytes_written": bytes_written,
            "append": append,
        }
        self.declared_outputs.append(entry)
        self.total_output_bytes += bytes_written
        self._audit("sandbox_file_write", **entry)

    def _declare_input(self, path: Path, *, purpose: str, bytes_read: int) -> None:
        entry = {
            "path": str(path),
            "relative_path": path.relative_to(self.root).as_posix(),
            "purpose": purpose,
            "bytes_read": bytes_read,
        }
        self.declared_inputs.append(entry)
        self.total_input_bytes += bytes_read
        self._audit("sandbox_file_read", **entry)

    def _audit(self, event: str, **fields: Any) -> None:
        self.audit_events.append(
            {
                "recorded_at_utc": _now(),
                "event": event,
                **fields,
            }
        )
