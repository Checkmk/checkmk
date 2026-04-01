# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Persistent deploy state tracking for incremental deployment."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

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


def state_file_path(site_root: Path) -> Path:
    """Return the canonical state file path for a site."""
    return Path("/var/tmp/cmk-dev-deploy") / site_root.name / STATE_FILE_NAME  # nosec B108


def load_state(site_root: Path) -> DeployState | None:
    """Load and validate state from disk, or return None."""
    path = state_file_path(site_root)
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
        )
    except (json.JSONDecodeError, KeyError, TypeError, ValueError):
        return None


def save_state(state: DeployState, site_root: Path) -> None:
    """Atomically write state to disk (temp file + rename)."""
    path = state_file_path(site_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    # Serialize manually (not using dataclasses.asdict to keep control)
    data = {
        "schema_version": state.schema_version,
        "branch": state.branch,
        "created_at": state.created_at,
        "diff_base_commit": state.diff_base_commit,
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
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def delete_state(site_root: Path) -> None:
    """Delete the state file, silently ignoring missing files."""
    path = state_file_path(site_root)
    try:
        path.unlink(missing_ok=True)
    except OSError:
        pass


# ---------------------------------------------------------------------------
# Git helpers
# ---------------------------------------------------------------------------


def get_current_branch(repo_root: Path) -> str:
    """Return the current git branch name, or '' if detached HEAD or on error."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
            cwd=str(repo_root),
            timeout=GIT_QUICK,
        )
    except (subprocess.TimeoutExpired, OSError):
        return ""
    if result.returncode != 0:
        return ""
    branch = result.stdout.strip()
    return "" if branch == "HEAD" else branch


def get_head_commit(repo_root: Path) -> str:
    """Return the current HEAD commit hash (40-char SHA), or '' on error."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
            cwd=str(repo_root),
            timeout=GIT_QUICK,
        )
    except (subprocess.TimeoutExpired, OSError):
        return ""
    if result.returncode != 0:
        return ""
    return result.stdout.strip()


def get_dirty_files(repo_root: Path) -> list[str]:
    """Return paths of files with unstaged or staged changes relative to HEAD."""
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
            cwd=str(repo_root),
            timeout=GIT_QUICK,
        )
    except (subprocess.TimeoutExpired, OSError):
        return []
    if result.returncode != 0:
        return []
    return [line for line in result.stdout.strip().splitlines() if line]


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
    """Compute SHA256 hashes for dirty files, optionally filtered by prefix."""
    dirty = get_dirty_files(repo_root)
    if path_prefixes is not None:
        dirty = [f for f in dirty if any(f.startswith(p) for p in path_prefixes)]
    result: dict[str, str] = {}
    for relpath in dirty:
        abs_path = repo_root / relpath
        if abs_path.is_file():
            result[relpath] = compute_file_hash(abs_path)
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


def build_and_save_state(
    repo_root: Path,
    site_root: Path,
    branch: str,
    successful_deployers: set[str],
    previous_state: DeployState | None,
    wheel_per_pkg_states: dict[str, DeployerState] | None = None,
    deployer_dirty_hashes: dict[str, dict[str, str]] | None = None,
    all_succeeded: bool = True,
) -> None:
    """Assemble and persist deploy state with partial-failure support.

    Builds a new ``DeployState`` from the current HEAD, merging fresh
    deployer states for successful deployers with carried-forward (and
    pruned) states for skipped/failed deployers.

    When *all_succeeded* is False (partial failure), the ``diff_base_commit``
    is preserved from the previous state so that the next run re-detects the
    changes that the failed deployer(s) missed.
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

    # On partial failure, preserve the previous diff base so failed deployers
    # re-detect their changes on the next run.
    if all_succeeded:
        diff_base = head
    elif previous_state and previous_state.diff_base_commit:
        diff_base = previous_state.diff_base_commit
    else:
        diff_base = head

    new_state = DeployState(
        branch=branch,
        created_at=now,
        diff_base_commit=diff_base,
    )

    all_deployer_names = ["install_spec", "config_spec"]
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

    # Per-package wheel states (from wheel_deployer)
    if wheel_per_pkg_states:
        for key, pkg_state in wheel_per_pkg_states.items():
            new_state.deployers[key] = pkg_state

    # Carry forward previous per-package wheel states not in new deploy
    if previous_state is not None:
        for key, prev_ds in previous_state.deployers.items():
            if key.startswith("wheel:") and key not in new_state.deployers:
                new_state.deployers[key] = prune_stale_dirty(prev_ds, current_dirty)

    try:
        save_state(new_state, site_root)
    except OSError:
        import sys

        print(  # noqa: T201 -- intentional fallback; output module not importable here
            "[warn] Failed to save deploy state (will retry on next deploy)",
            file=sys.stderr,
        )
