from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


WORKSPACE_SANDBOX_SCHEMA = "paideia-workspace-sandbox-policy/v1"
WORKSPACE_ROLLBACK_MANIFEST_SCHEMA = "paideia-workspace-rollback-manifest/v1"
DEFAULT_MAX_OUTPUT_FILE_BYTES = 2_000_000
DEFAULT_MAX_TRACE_EVENTS = 200


class SandboxViolation(ValueError):
    """Raised when a workspace operation violates the local sandbox policy."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def workspace_sandbox_policy(
    workspace_root: Path,
    *,
    max_output_file_bytes: int = DEFAULT_MAX_OUTPUT_FILE_BYTES,
    max_trace_events: int = DEFAULT_MAX_TRACE_EVENTS,
) -> dict[str, Any]:
    root = workspace_root.resolve()
    return {
        "schema": WORKSPACE_SANDBOX_SCHEMA,
        "workspace_root": str(root),
        "filesystem": {
            "mode": "allowlist",
            "allowed_roots": [str(root)],
            "path_traversal_guard": True,
            "writes_must_use_workspace_sandbox": True,
        },
        "network": {
            "default": "blocked",
            "external_upload": "blocked_without_boss_approval",
        },
        "subprocess": {
            "default": "blocked",
            "allowlist": [],
        },
        "resource_limits": {
            "max_output_file_bytes": max_output_file_bytes,
            "max_trace_events": max_trace_events,
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
            "oversized_output_raises": "SandboxViolation",
            "trace_limit_raises": "SandboxViolation",
            "network_and_subprocess_default": "deny",
        },
    }


class WorkspaceSandbox:
    def __init__(
        self,
        workspace_root: Path,
        *,
        max_output_file_bytes: int = DEFAULT_MAX_OUTPUT_FILE_BYTES,
        max_trace_events: int = DEFAULT_MAX_TRACE_EVENTS,
    ) -> None:
        self.root = workspace_root.resolve()
        self.max_output_file_bytes = max_output_file_bytes
        self.max_trace_events = max_trace_events
        self.audit_events: list[dict[str, Any]] = []
        self.declared_outputs: list[dict[str, Any]] = []

    def ensure_root(self) -> Path:
        self.root.mkdir(parents=True, exist_ok=True)
        return self.root

    def safe_path(self, relative_path: str | Path) -> Path:
        candidate = Path(relative_path)
        if candidate.is_absolute():
            path = candidate.resolve()
        else:
            path = (self.root / candidate).resolve()
        if self.root not in path.parents and path != self.root:
            self._audit("path_escape_blocked", requested=str(relative_path), resolved=str(path))
            raise SandboxViolation("Workspace output escaped workspace directory")
        return path

    def write_text(self, relative_path: str | Path, text: str, *, purpose: str) -> Path:
        data = text.encode("utf-8")
        self._enforce_output_size(relative_path, len(data))
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
        path = self.safe_path(relative_path)
        existing_count = 0
        if path.exists():
            existing_count = len(path.read_text(encoding="utf-8").splitlines())
        self._enforce_trace_events(relative_path, existing_count + len(entries))
        text = "".join(json.dumps(entry, ensure_ascii=False) + "\n" for entry in entries)
        data = text.encode("utf-8")
        self._enforce_output_size(relative_path, path.stat().st_size + len(data) if path.exists() else len(data))
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as file:
            file.write(text)
        self._declare_output(path, purpose=purpose, bytes_written=len(data), append=True)
        return path

    def deny_network(self, reason: str = "network_blocked_by_workspace_sandbox") -> None:
        self._audit("network_access_blocked", reason=reason)
        raise SandboxViolation(reason)

    def deny_subprocess(self, reason: str = "subprocess_blocked_by_workspace_sandbox") -> None:
        self._audit("subprocess_blocked", reason=reason)
        raise SandboxViolation(reason)

    def policy(self) -> dict[str, Any]:
        return workspace_sandbox_policy(
            self.root,
            max_output_file_bytes=self.max_output_file_bytes,
            max_trace_events=self.max_trace_events,
        )

    def snapshot(self) -> dict[str, Any]:
        policy = self.policy()
        policy["declared_outputs"] = self.declared_outputs
        policy["audit_events"] = self.audit_events
        return policy

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

    def _enforce_output_size(self, relative_path: str | Path, byte_count: int) -> None:
        if byte_count > self.max_output_file_bytes:
            self._audit(
                "output_size_blocked",
                requested=str(relative_path),
                byte_count=byte_count,
                max_output_file_bytes=self.max_output_file_bytes,
            )
            raise SandboxViolation("Workspace output exceeded max_output_file_bytes")

    def _enforce_trace_events(self, relative_path: str | Path, event_count: int) -> None:
        if event_count > self.max_trace_events:
            self._audit(
                "trace_event_limit_blocked",
                requested=str(relative_path),
                event_count=event_count,
                max_trace_events=self.max_trace_events,
            )
            raise SandboxViolation("Workspace trace exceeded max_trace_events")

    def _declare_output(self, path: Path, *, purpose: str, bytes_written: int, append: bool = False) -> None:
        entry = {
            "path": str(path),
            "relative_path": path.relative_to(self.root).as_posix(),
            "purpose": purpose,
            "bytes_written": bytes_written,
            "append": append,
        }
        self.declared_outputs.append(entry)
        self._audit("sandbox_file_write", **entry)

    def _audit(self, event: str, **fields: Any) -> None:
        self.audit_events.append(
            {
                "recorded_at_utc": _now(),
                "event": event,
                **fields,
            }
        )
