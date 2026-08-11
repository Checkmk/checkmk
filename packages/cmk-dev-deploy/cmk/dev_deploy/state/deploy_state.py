# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Persistent deploy state tracking for incremental deployment."""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from cmk.dev_deploy.core.git import query_untracked_files
from cmk.dev_deploy.core.timeouts import GIT_QUICK

STATE_FILE_NAME = "deploy_state.json"
STATE_SCHEMA_VERSION = 2


@dataclass
class DeployerState:
    """State of a single deployer's last successful deployment."""

    deployer: str
    git_commit: str
    dirty_file_hashes: dict[str, str]
    deployed_at: float


@dataclass
class DeployState:
    """Complete deploy state for one site."""

    schema_version: int = STATE_SCHEMA_VERSION
    branch: str = ""
    deployers: dict[str, DeployerState] = field(default_factory=dict)
    created_at: float = 0.0
    diff_base_commit: str = ""
    """Set to HEAD after each deploy cycle; used as the diff base on next run."""
    backend: str = ""
    """Site preparation backend that prepared the site ("overlay" or "clone")."""
    uncovered_files: dict[str, str] = field(default_factory=dict)
    """Changed files no deploy spec covers (path -> content hash at detection).

    Kept so the "will NOT be deployed" warning persists across runs even
    though the diff base advances past these files."""


# /var/tmp survives reboots (unlike /tmp, which may be tmpfs).
STATE_BASE = Path("/var") / "tmp" / "cmk-dev-deploy"


def state_file_path(site_root: Path, base_dir: Path = STATE_BASE) -> Path:
    """Return the canonical state file path for a site."""
    return base_dir / site_root.name / STATE_FILE_NAME


def load_state(site_root: Path, base_dir: Path = STATE_BASE) -> DeployState | None:
    """Load and validate state from disk, or return None."""
    path = state_file_path(site_root, base_dir)
    if not path.is_file():
        return None
    try:
        raw = json.loads(path.read_text())
        # Validate schema version
        if raw.get("schema_version") != STATE_SCHEMA_VERSION:
            return None
        # Reconstruct typed state
        deployers: dict[str, DeployerState] = {}
        for key, val in raw.get("deployers", {}).items():
            deployers[key] = DeployerState(
                deployer=val["deployer"],
                git_commit=val["git_commit"],
                dirty_file_hashes=val.get("dirty_file_hashes", {}),
                deployed_at=val.get("deployed_at", 0.0),
            )
        return DeployState(
            schema_version=raw["schema_version"],
            branch=raw.get("branch", ""),
            deployers=deployers,
            created_at=raw.get("created_at", 0.0),
            diff_base_commit=raw.get("diff_base_commit", ""),
            backend=raw.get("backend", ""),
            uncovered_files=raw.get("uncovered_files", {}),
        )
    except (json.JSONDecodeError, KeyError, TypeError, ValueError):
        return None


def save_state(state: DeployState, site_root: Path, base_dir: Path = STATE_BASE) -> None:
    """Atomically write state to disk (temp file + rename)."""
    path = state_file_path(site_root, base_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    # Serialize manually (not using dataclasses.asdict to keep control)
    data = {
        "schema_version": state.schema_version,
        "branch": state.branch,
        "created_at": state.created_at,
        "diff_base_commit": state.diff_base_commit,
        "backend": state.backend,
        "uncovered_files": state.uncovered_files,
        "deployers": {
            key: {
                "deployer": ds.deployer,
                "git_commit": ds.git_commit,
                "dirty_file_hashes": ds.dirty_file_hashes,
                "deployed_at": ds.deployed_at,
            }
            for key, ds in state.deployers.items()
        },
    }
    # Atomic write: write to temp file in same directory, then rename
    fd, tmp_path = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp", prefix=".deploy_state_")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(data, f, indent=2, sort_keys=True)
            f.write("\n")
        os.rename(tmp_path, str(path))
    except BaseException:
        # Clean up temp file on any failure
        with contextlib.suppress(OSError):
            os.unlink(tmp_path)
        raise


def delete_state(site_root: Path, base_dir: Path = STATE_BASE) -> None:
    """Delete the state file, silently ignoring missing files."""
    path = state_file_path(site_root, base_dir)
    with contextlib.suppress(OSError):
        path.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Git helpers
# ---------------------------------------------------------------------------


@dataclass
class _GitCache:
    """Memo of the git queries a deploy cycle repeats.

    ``git diff --name-only HEAD`` alone used to run seven times per cycle
    (change filtering, two skip checks, three per-deployer snapshots, the
    state save) with an identical result every time, and each caller then
    re-hashed the files it matched.  Answering all of them from one query
    also gives the cycle a single consistent view of the working tree, the
    same guarantee the per-deployer snapshots were already reaching for by
    running before the deployers rather than after them.
    """

    repo_root: Path | None = None
    branch: str | None = None
    head: str | None = None
    dirty_files: tuple[str, ...] | None = None
    untracked: tuple[str, ...] | None = None
    file_hashes: dict[str, str] = field(default_factory=dict)


_git_cache = _GitCache()


def reset_git_cache() -> None:
    """Discard the memoized git state; called once per deploy cycle."""
    global _git_cache
    _git_cache = _GitCache()


def _cache_for(repo_root: Path) -> _GitCache:
    """Return the memo, discarding it when it belongs to another repository."""
    global _git_cache
    if _git_cache.repo_root != repo_root:
        _git_cache = _GitCache(repo_root=repo_root)
    return _git_cache


def _git_stdout(args: list[str], repo_root: Path) -> str | None:
    """Return stripped stdout of a git command, or None when it fails."""
    try:
        result = subprocess.run(
            ["git", *args],
            capture_output=True,
            text=True,
            check=False,
            cwd=str(repo_root),
            timeout=GIT_QUICK,
        )
    except (subprocess.TimeoutExpired, OSError):
        return None
    return result.stdout.strip() if result.returncode == 0 else None


def get_current_branch(repo_root: Path) -> str:
    """Return the current git branch name, or '' if detached HEAD or on error."""
    cache = _cache_for(repo_root)
    if cache.branch is None:
        branch = _git_stdout(["rev-parse", "--abbrev-ref", "HEAD"], repo_root)
        cache.branch = "" if branch in (None, "HEAD") else branch
    return cache.branch


def get_head_commit(repo_root: Path) -> str:
    """Return the current HEAD commit hash (40-char SHA), or '' on error."""
    cache = _cache_for(repo_root)
    if cache.head is None:
        cache.head = _git_stdout(["rev-parse", "HEAD"], repo_root) or ""
    return cache.head


def get_untracked_files(repo_root: Path) -> list[str]:
    """Return untracked, non-ignored files; memoized for the deploy cycle.

    The watch loop calls the unmemoized :func:`query_untracked_files`
    instead: it polls between cycles, when the memo is stale by design.
    """
    cache = _cache_for(repo_root)
    if cache.untracked is None:
        cache.untracked = tuple(query_untracked_files(repo_root))
    return list(cache.untracked)


def get_dirty_files(repo_root: Path) -> list[str]:
    """Return paths of files differing from HEAD in the working tree.

    Covers unstaged and staged modifications plus untracked files.  The
    latter are invisible to ``git diff`` and would otherwise never be
    recorded as deployed, so a deployer whose only changes are new files
    would skip itself forever (and, once deployed, redeploy forever).
    """
    cache = _cache_for(repo_root)
    if cache.dirty_files is None:
        out = _git_stdout(["diff", "--name-only", "HEAD"], repo_root)
        tracked = {line for line in (out or "").splitlines() if line}
        cache.dirty_files = tuple(sorted(tracked | set(get_untracked_files(repo_root))))
    return list(cache.dirty_files)


def compute_file_hash(filepath: Path) -> str:
    """Compute SHA256 of a file's contents using 8KB chunk reads."""
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def compute_dirty_hashes(
    repo_root: Path,
    path_prefixes: tuple[str, ...] | None = None,
) -> dict[str, str]:
    """Compute SHA256 hashes for dirty files, optionally filtered by prefix.

    Hashes are memoized per cycle: the deployers' prefix filters overlap,
    so a file that several of them own would otherwise be read once per
    deployer.
    """
    dirty = get_dirty_files(repo_root)
    if path_prefixes is not None:
        dirty = [f for f in dirty if f.startswith(path_prefixes)]
    cache = _cache_for(repo_root)
    result: dict[str, str] = {}
    for relpath in dirty:
        if (cached := cache.file_hashes.get(relpath)) is not None:
            result[relpath] = cached
        elif (abs_path := repo_root / relpath).is_file():
            result[relpath] = cache.file_hashes[relpath] = compute_file_hash(abs_path)
    return result


# ---------------------------------------------------------------------------
# State assembly helpers (extracted from __main__.py)
# ---------------------------------------------------------------------------


def prune_stale_dirty(ds: DeployerState, current_dirty: set[str]) -> DeployerState:
    """Remove dirty-file entries for files that are no longer dirty.

    Prevents stale entries from causing perpetual "dirty files reverted"
    false positives when carrying forward state for skipped deployers.
    """
    pruned = {f: h for f, h in ds.dirty_file_hashes.items() if f in current_dirty}
    if len(pruned) == len(ds.dirty_file_hashes):
        return ds  # nothing changed
    return DeployerState(
        deployer=ds.deployer,
        git_commit=ds.git_commit,
        dirty_file_hashes=pruned,
        deployed_at=ds.deployed_at,
    )


def build_and_save_state(  # noqa: PLR0917
    repo_root: Path,
    site_root: Path,
    branch: str,
    successful_deployers: set[str],
    previous_state: DeployState | None,
    run_diff_base: str | None = None,
    deployer_dirty_hashes: dict[str, dict[str, str]] | None = None,
    all_succeeded: bool = True,
    backend: str = "",
    uncovered_files: dict[str, str] | None = None,
    base_dir: Path = STATE_BASE,
) -> None:
    """Assemble and persist deploy state with partial-failure support.

    Builds a new ``DeployState`` from the current HEAD, merging fresh
    deployer states for successful deployers with carried-forward (and
    pruned) states for skipped/failed deployers.

    When *all_succeeded* is False (partial failure), the ``diff_base_commit``
    is kept at *run_diff_base* -- the base this run detected changes against
    -- so that the next run re-detects the changes that the failed
    deployer(s) missed.  This matters most on a first deploy (no previous
    state, diff base = site build commit): advancing to HEAD there would
    silently drop the failed deployer's changes forever.
    """
    import time as _time

    head = get_head_commit(repo_root)
    if not head:
        return  # Can't record state without a commit

    # Lazy global fallback: only compute if needed
    _global_dirty: dict[str, str] | None = None
    # Current dirty files for pruning stale entries from carried-forward state
    current_dirty = set(get_dirty_files(repo_root))
    now = _time.time()

    # On partial failure, keep the diff base this run detected changes
    # against so failed deployers re-detect their changes on the next run.
    # Advancing to HEAD here would silently drop those changes.
    if all_succeeded:
        diff_base = head
    elif run_diff_base:
        diff_base = run_diff_base
    elif previous_state and previous_state.diff_base_commit:
        diff_base = previous_state.diff_base_commit
    else:
        diff_base = head

    new_state = DeployState(
        branch=branch,
        created_at=now,
        diff_base_commit=diff_base,
        backend=backend or (previous_state.backend if previous_state else ""),
        uncovered_files=(
            dict(uncovered_files)
            if uncovered_files is not None
            else (dict(previous_state.uncovered_files) if previous_state else {})
        ),
    )

    all_deployer_names = ["install_spec", "config_spec", "wheel_spec"]
    for name in all_deployer_names:
        if name in successful_deployers:
            # Use per-deployer dirty hashes if available, else global fallback
            if deployer_dirty_hashes is not None and name in deployer_dirty_hashes:
                hashes = deployer_dirty_hashes[name]
            else:
                if _global_dirty is None:
                    _global_dirty = compute_dirty_hashes(repo_root)
                hashes = _global_dirty
            # Fresh state for successfully deployed
            new_state.deployers[name] = DeployerState(
                deployer=name,
                git_commit=head,
                dirty_file_hashes=dict(hashes),
                deployed_at=now,
            )
        elif previous_state is not None and name in previous_state.deployers:
            new_state.deployers[name] = prune_stale_dirty(
                previous_state.deployers[name], current_dirty
            )
        # else: no entry (first deploy, deployer didn't run)

    try:
        save_state(new_state, site_root, base_dir)
    except OSError:
        import sys

        print(  # noqa: T201 -- intentional fallback; output module not importable here
            "[warn] Failed to save deploy state (will retry on next deploy)",
            file=sys.stderr,
        )
