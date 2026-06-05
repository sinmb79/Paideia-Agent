from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


OWNER_SELF_EXTENSION_INTAKE_SCHEMA = "paideia-owner-self-extension-intake/v1"
ALLOWED_COPYRIGHT_ATTESTATIONS = {
    "owner_provided_or_authorized_for_local_use",
    "public_or_open_license_metadata_only",
    "metadata_only_pending_review",
}


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _size_bucket(size: int) -> str:
    if size < 1_000:
        return "lt_1kb"
    if size < 100_000:
        return "lt_100kb"
    if size < 1_000_000:
        return "lt_1mb"
    if size < 10_000_000:
        return "lt_10mb"
    return "gte_10mb"


def _source_location_policy(source_dir: Path, repo_root: Path | None) -> dict[str, Any]:
    resolved_source = source_dir.resolve()
    policy = {
        "source_dir_exists": source_dir.exists(),
        "source_dir_is_directory": source_dir.is_dir(),
        "source_root_fingerprint_sha256": _sha256_text(str(resolved_source).casefold()),
        "raw_source_path_exported": False,
        "allowed_private_locations": [
            "data/private/**",
            "AI22B_STORAGE_ROOT/talent-foundry/private/**",
            "owner-managed local private folder outside public repo",
        ],
        "inside_repo": False,
        "inside_repo_private_area": False,
        "issue": None,
    }
    if repo_root is not None and repo_root.exists():
        resolved_repo = repo_root.resolve()
        policy["repo_root_fingerprint_sha256"] = _sha256_text(str(resolved_repo).casefold())
        policy["inside_repo"] = _is_relative_to(resolved_source, resolved_repo)
        private_root = resolved_repo / "data" / "private"
        policy["inside_repo_private_area"] = _is_relative_to(resolved_source, private_root) if private_root.exists() else False
        if policy["inside_repo"] and not policy["inside_repo_private_area"]:
            policy["issue"] = "source_dir_inside_public_repo_outside_data_private"
    return policy


def build_owner_self_extension_intake(
    *,
    source_dir: Path,
    owner: str,
    output_path: Path | None = None,
    owner_consent: bool = False,
    copyright_attestation: str = "metadata_only_pending_review",
    repo_root: Path | None = None,
    max_files: int = 200,
) -> dict[str, Any]:
    """Build a local-only owner self-extension intake manifest.

    The intake intentionally does not ingest file contents and does not export
    raw filenames or absolute paths. It records only reviewable metadata so the
    owner can decide what to promote into a private curriculum later.
    """

    source_policy = _source_location_policy(source_dir, repo_root)
    file_summaries: list[dict[str, Any]] = []
    extension_counts: dict[str, int] = {}
    size_buckets: dict[str, int] = {}
    total_bytes = 0
    truncated = False
    if source_dir.exists() and source_dir.is_dir():
        for index, path in enumerate(sorted(item for item in source_dir.rglob("*") if item.is_file())):
            if index >= max_files:
                truncated = True
                break
            try:
                stat = path.stat()
            except OSError:
                continue
            relative = path.relative_to(source_dir).as_posix()
            extension = path.suffix.casefold() or "[no_extension]"
            bucket = _size_bucket(stat.st_size)
            total_bytes += stat.st_size
            extension_counts[extension] = extension_counts.get(extension, 0) + 1
            size_buckets[bucket] = size_buckets.get(bucket, 0) + 1
            file_summaries.append(
                {
                    "relative_path_fingerprint_sha256": _sha256_text(relative),
                    "extension": extension,
                    "size_bucket": bucket,
                    "raw_filename_exported": False,
                    "content_read": False,
                }
            )
    issues: list[dict[str, Any]] = []
    if not owner_consent:
        issues.append(
            {
                "id": "owner_consent_missing",
                "severity": "error",
                "message": "Owner self-extension intake requires explicit owner consent.",
            }
        )
    if copyright_attestation not in ALLOWED_COPYRIGHT_ATTESTATIONS:
        issues.append(
            {
                "id": "unsupported_copyright_attestation",
                "severity": "error",
                "message": "Copyright attestation must be one of the allowed local-use policies.",
            }
        )
    if not source_policy["source_dir_exists"] or not source_policy["source_dir_is_directory"]:
        issues.append(
            {
                "id": "source_dir_unavailable",
                "severity": "error",
                "message": "Source directory must exist before private owner intake can be prepared.",
            }
        )
    if source_policy.get("issue"):
        issues.append(
            {
                "id": source_policy["issue"],
                "severity": "error",
                "message": "Private owner materials must not be sourced from a public repo path outside data/private.",
            }
        )
    valid = not any(issue["severity"] == "error" for issue in issues)
    intake = {
        "schema": OWNER_SELF_EXTENSION_INTAKE_SCHEMA,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "ready_for_private_curriculum_review" if valid else "blocked",
        "valid": valid,
        "owner_label": owner,
        "track_id": "owner_self_extension",
        "network_action_performed": False,
        "content_ingestion_performed": False,
        "privacy": {
            "raw_absolute_paths_exported": False,
            "raw_filenames_exported": False,
            "file_contents_exported": False,
            "private_data_upload": "forbidden",
        },
        "consent": {
            "owner_consent": owner_consent,
            "copyright_attestation": copyright_attestation,
            "allowed_attestations": sorted(ALLOWED_COPYRIGHT_ATTESTATIONS),
        },
        "source_policy": source_policy,
        "scan_summary": {
            "max_files": max_files,
            "scanned_file_count": len(file_summaries),
            "truncated": truncated,
            "total_size_bytes": total_bytes,
            "extension_counts": dict(sorted(extension_counts.items())),
            "size_buckets": dict(sorted(size_buckets.items())),
        },
        "files": file_summaries,
        "promotion_policy": {
            "default": "metadata_only_pending_boss_review",
            "allowed_next_step": "convert_selected_private_materials_to_local_private_curriculum",
            "public_release": "never_include_private_materials_or_full_copyrighted_text",
            "reasoning_ledger": "do_not_promote_without_reviewed_learning_result",
        },
        "issues": issues,
        "next_actions": (
            [
                "Review extension counts and size buckets before selecting private materials.",
                "Create a private curriculum inside data/private/** or AI22B_STORAGE_ROOT only after review.",
            ]
            if valid
            else [
                "Provide explicit owner consent and a valid local-use copyright attestation.",
                "Move source files into data/private/** or an owner-managed folder outside the public repo.",
            ]
        ),
    }
    if output_path is not None:
        _write_json(output_path, intake)
    return intake

