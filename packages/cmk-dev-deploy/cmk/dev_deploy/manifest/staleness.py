# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Manifest staleness detection and rebuild orchestration.

Separated from ``reader.py`` to break the circular import with ``output``.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

from cmk.dev_deploy.core import output
from cmk.dev_deploy.core.subprocess_utils import run_checked
from cmk.dev_deploy.errors import ManifestBuildError
from cmk.dev_deploy.manifest.reader import (
    clear_cache,
    hash_path,
    manifest_path,
)

# Directories to skip when scanning for BUILD / .bzl files.
# These are bazel output symlinks, caches, and non-source directories.
_IGNORED_PREFIXES = ("bazel-", ".git", "node_modules", ".bazel")


def _discover_build_files(repo_root: Path) -> list[str]:
    """Find all BUILD and .bzl files (plus deploy_specs.toml) in the repo."""
    result = _discover_build_files_git(repo_root)
    if result is not None:
        return result
    return _discover_build_files_walk(repo_root)


def _discover_build_files_git(repo_root: Path) -> list[str] | None:
    """Fast discovery via ``git ls-files``; returns None on failure."""
    try:
        proc = subprocess.run(
            [
                "git",
                "ls-files",
                "-z",
                "--",
                "**/BUILD",
                "BUILD",
                "**/*.bzl",
                "*.bzl",
                "packages/cmk-dev-deploy/cmk/dev_deploy/manifest/deploy_specs.toml",
            ],
            capture_output=True,
            check=False,
            cwd=str(repo_root),
            timeout=5,
        )
    except (subprocess.TimeoutExpired, OSError):
        return None

    if proc.returncode != 0:
        return None

    # -z uses NUL separators; decode as utf-8 (paths are repo-relative)
    raw = proc.stdout.decode("utf-8", errors="replace")
    files = [f for f in raw.split("\0") if f]
    return sorted(set(files))


def _discover_build_files_walk(repo_root: Path) -> list[str]:
    """Fallback discovery via os.walk when git is unavailable."""
    result: list[str] = []

    specs_rel = "packages/cmk-dev-deploy/cmk/dev_deploy/manifest/deploy_specs.toml"
    if (repo_root / specs_rel).is_file():
        result.append(specs_rel)

    for dirpath, dirnames, filenames in os.walk(repo_root, followlinks=False):
        dirnames[:] = [
            d
            for d in dirnames
            if not any(d.startswith(prefix) for prefix in _IGNORED_PREFIXES)
        ]

        rel_dir = os.path.relpath(dirpath, repo_root)
        for fname in filenames:
            if fname == "BUILD" or fname.endswith(".bzl"):
                if rel_dir == ".":
                    result.append(fname)
                else:
                    result.append(os.path.join(rel_dir, fname))

    return sorted(set(result))


def _compute_file_hashes(repo_root: Path) -> dict[str, str]:
    """Compute per-file SHA256 hashes for all build-related files."""
    t0 = time.monotonic()
    files = _discover_build_files(repo_root)
    t_discover = time.monotonic()
    hashes: dict[str, str] = {}
    for rel_path in files:
        filepath = repo_root / rel_path
        if filepath.is_file():
            hashes[rel_path] = hashlib.sha256(filepath.read_bytes()).hexdigest()
    elapsed = time.monotonic() - t0
    output.verbose(
        f"Manifest: hashed {len(hashes)} build files in {elapsed:.2f}s "
        f"(discover: {t_discover - t0:.2f}s, hash: {elapsed - (t_discover - t0):.2f}s)"
    )
    return hashes


def _load_stored_hashes() -> dict[str, str] | None:
    """Load stored per-file hashes from .manifest_hash, or None."""
    if not hash_path().is_file():
        return None
    try:
        data = json.loads(hash_path().read_text())
        if isinstance(data, dict) and "files" in data:
            files: dict[str, str] = data["files"]
            return files
    except (json.JSONDecodeError, KeyError):
        pass
    return None


def _diff_hashes(
    stored: dict[str, str],
    current: dict[str, str],
) -> tuple[list[str], list[str], list[str]]:
    """Return (added, removed, modified) file path lists."""
    stored_set = set(stored)
    current_set = set(current)
    added = sorted(current_set - stored_set)
    removed = sorted(stored_set - current_set)
    modified = sorted(p for p in stored_set & current_set if stored[p] != current[p])
    return added, removed, modified


def save_manifest_hashes(repo_root: Path) -> None:
    """Compute and save per-file hashes to .manifest_hash."""
    t0 = time.monotonic()
    current = _compute_file_hashes(repo_root)
    hash_path().write_text(json.dumps({"files": current}, indent=2) + "\n")
    output.verbose(
        f"Manifest: saved {len(current)} file hashes in {time.monotonic() - t0:.2f}s"
    )


def is_manifest_stale(repo_root: Path) -> bool:
    """Return True if build files have changed since manifest generation."""
    if not manifest_path().is_file():
        output.info("Manifest: not found, will generate")
        return True

    stored = _load_stored_hashes()
    if stored is None:
        # Hash file missing (e.g. after rebase or fresh checkout) but
        # manifest exists.  Regenerate hashes from current BUILD files
        # instead of triggering a full expensive rebuild.
        output.info("Manifest: rebuilding hash cache (manifest exists)")
        save_manifest_hashes(repo_root)
        return False

    current = _compute_file_hashes(repo_root)
    added, removed, modified = _diff_hashes(stored, current)

    if not added and not removed and not modified:
        return False

    total = len(added) + len(removed) + len(modified)
    output.info(f"Manifest: {total} build file(s) changed, regenerating...")
    for f in modified:
        output.verbose(f"  ~ {f}")
    for f in added:
        output.verbose(f"  + {f}")
    for f in removed:
        output.verbose(f"  - {f}")

    return True


# --- Rebuild orchestration ---


def _rebuild_manifest(repo_root: Path) -> None:
    """Invoke update_manifest.py and update the hash file."""
    t0 = time.monotonic()
    script = (
        repo_root
        / "packages"
        / "cmk-dev-deploy"
        / "cmk"
        / "dev_deploy"
        / "manifest"
        / "update.py"
    )
    run_checked(
        [sys.executable, str(script)],
        cwd=repo_root,
        timeout=600,
        error_cls=ManifestBuildError,
        description="Manifest rebuild",
        recovery="This usually means Bazel is stuck. Try:\n"
        "  1. bazel clean --expunge\n"
        "  2. cmk-dev-deploy --rebuild-manifest",
    )
    # update.py already saves hashes via save_manifest_hashes(), but save
    # again here to capture the state as seen by the parent process.
    save_manifest_hashes(repo_root)
    clear_cache()
    elapsed = time.monotonic() - t0
    output.info(f"Manifest: rebuilt in {elapsed:.1f}s")


def ensure_manifest(
    repo_root: Path,
    *,
    force_rebuild: bool = False,
) -> None:
    """Ensure the manifest exists and is fresh, rebuilding if needed."""
    t0 = time.monotonic()
    if force_rebuild:
        output.info("Manifest: forced rebuild requested")
        _rebuild_manifest(repo_root)
        return
    if not manifest_path().is_file():
        output.info("Manifest: not found, generating...")
        _rebuild_manifest(repo_root)
        return
    if is_manifest_stale(repo_root):
        _rebuild_manifest(repo_root)
        return
    elapsed = time.monotonic() - t0
    output.info(f"Manifest: reusing cached manifest (staleness check: {elapsed:.2f}s)")
