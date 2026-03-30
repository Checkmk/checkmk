# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Path-aware skip logic for per-deployer deployment decisions.

Each deployer is only redeployed when its own source files have changed.
"""

from __future__ import annotations

from pathlib import Path

from cmk.dev_deploy.core.subprocess_utils import run_checked
from cmk.dev_deploy.core.timeouts import GIT_DIFF_PATHS, GIT_QUICK
from cmk.dev_deploy.site.site_resolver import read_build_commit
from cmk.dev_deploy.state.deploy_state import compute_dirty_hashes, DeployState
from cmk.dev_deploy.types import SkipResult


def _format_short_paths(paths: tuple[str, ...]) -> str:
    """Format path prefixes into a compact display string."""
    path_names = [p.rstrip("/") for p in paths]
    if len(path_names) > 3:
        return ", ".join(path_names[:3]) + f" (+{len(path_names) - 3} more)"
    return ", ".join(path_names)


def _git_diff_paths(
    old_commit: str,
    new_commit: str,
    paths: tuple[str, ...],
    repo_root: Path,
) -> list[str]:
    """Return file paths changed between two commits, filtered by path prefixes."""
    cmd = ["git", "diff", "--name-only", f"{old_commit}..{new_commit}", "--", *paths]
    result = run_checked(
        cmd,
        cwd=repo_root,
        timeout=GIT_DIFF_PATHS,
        error_cls=RuntimeError,
        description="git diff",
    )
    return [line for line in result.stdout.strip().splitlines() if line]


def _validate_commit_exists(commit: str, repo_root: Path) -> None:
    """Validate that a commit exists in the repository."""
    run_checked(
        ["git", "cat-file", "-e", commit],
        cwd=repo_root,
        timeout=GIT_QUICK,
        error_cls=RuntimeError,
        description=f"git cat-file for {commit[:12]}",
    )


def check_skip(
    deployer_name: str,
    repo_root: Path,
    site_root: Path,
    state: DeployState | None,
    head_commit: str,
) -> SkipResult:
    """Decide whether a deployer can be skipped based on path-filtered git diff."""
    # Lazy import to avoid circular imports (consistent with source_paths.py pattern)
    from cmk.dev_deploy.execution.source_paths import resolve_source_paths

    # Step 1: Resolve source paths
    paths = resolve_source_paths(deployer_name, repo_root)

    if paths is None:
        # HEAD fallback mode: no source path metadata
        return _check_skip_head_fallback(deployer_name, state, head_commit, repo_root)

    if len(paths) == 0:
        # Empty source paths: always skip (no source files = nothing to deploy)
        return SkipResult(
            should_skip=True,
            reason="no source files",
            deployer=deployer_name,
            paths_checked=paths,
            changed_files=(),
        )

    # Step 2b: Path-aware skip
    return _check_skip_path_aware(deployer_name, paths, repo_root, site_root, state, head_commit)


def _check_skip_head_fallback(
    deployer_name: str,
    state: DeployState | None,
    head_commit: str,
    repo_root: Path,
) -> SkipResult:
    """HEAD fallback skip logic for deployers without source path metadata."""
    if state is None or deployer_name not in state.deployers:
        return SkipResult(
            should_skip=False,
            reason="no previous state (HEAD fallback)",
            deployer=deployer_name,
            paths_checked=(),
            changed_files=(),
        )

    ds = state.deployers[deployer_name]

    if ds.git_commit != head_commit:
        return SkipResult(
            should_skip=False,
            reason="HEAD changed (no source paths, HEAD fallback)",
            deployer=deployer_name,
            paths_checked=(),
            changed_files=(),
        )

    # Compare global dirty hashes (no path_prefixes filter)
    current_dirty = compute_dirty_hashes(repo_root)
    if current_dirty != ds.dirty_file_hashes:
        return SkipResult(
            should_skip=False,
            reason="dirty files changed (HEAD fallback)",
            deployer=deployer_name,
            paths_checked=(),
            changed_files=(),
        )

    return SkipResult(
        should_skip=True,
        reason="no changes (HEAD fallback)",
        deployer=deployer_name,
        paths_checked=(),
        changed_files=(),
    )


def _diff_and_dirty(
    old_commit: str,
    head_commit: str,
    paths: tuple[str, ...],
    repo_root: Path,
) -> tuple[list[str], dict[str, str]]:
    """Compute committed changes and current dirty hashes for given paths.

    Returns ``(changed_files, current_dirty_hashes)``.
    """
    changed_files = _git_diff_paths(old_commit, head_commit, paths, repo_root)
    current_dirty = compute_dirty_hashes(repo_root, path_prefixes=paths)
    return changed_files, current_dirty


def _combine_changed(changed_files: list[str], current_dirty: dict[str, str]) -> tuple[str, ...]:
    """Merge committed changes and dirty files into a single list."""
    all_changed: list[str] = list(changed_files)
    for dirty_file in current_dirty:
        if dirty_file not in all_changed:
            all_changed.append(dirty_file)
    return tuple(all_changed)


def _check_skip_path_aware(
    deployer_name: str,
    paths: tuple[str, ...],
    repo_root: Path,
    site_root: Path,
    state: DeployState | None,
    head_commit: str,
) -> SkipResult:
    """Path-aware skip logic for deployers with known source paths."""
    if state is None or deployer_name not in state.deployers:
        # First deploy: determine baseline from site build commit
        return _check_skip_first_deploy(deployer_name, paths, repo_root, site_root, head_commit)

    # Deployer has previous state
    ds = state.deployers[deployer_name]
    old_commit = ds.git_commit

    # Validate the old commit still exists
    _validate_commit_exists(old_commit, repo_root)

    changed_files, current_dirty = _diff_and_dirty(old_commit, head_commit, paths, repo_root)
    dirty_changed = current_dirty != ds.dirty_file_hashes

    if not changed_files and not dirty_changed:
        # No committed changes AND dirty hashes match: skip
        return SkipResult(
            should_skip=True,
            reason=f"no changes in {_format_short_paths(paths)}",
            deployer=deployer_name,
            paths_checked=paths,
            changed_files=(),
        )

    if changed_files:
        reason = f"{len(changed_files)} file(s) changed"
    else:
        reason = f"dirty files changed in {_format_short_paths(paths)}"

    all_changed = (
        _combine_changed(changed_files, current_dirty) if dirty_changed else tuple(changed_files)
    )

    return SkipResult(
        should_skip=False,
        reason=reason,
        deployer=deployer_name,
        paths_checked=paths,
        changed_files=all_changed,
    )


def _check_skip_first_deploy(
    deployer_name: str,
    paths: tuple[str, ...],
    repo_root: Path,
    site_root: Path,
    head_commit: str,
) -> SkipResult:
    """Handle first-deploy case using site build commit as baseline."""
    old_commit = read_build_commit(site_root)

    if old_commit is None:
        # No baseline at all: must deploy
        return SkipResult(
            should_skip=False,
            reason="first deploy (no baseline)",
            deployer=deployer_name,
            paths_checked=paths,
            changed_files=(),
        )

    changed_files, current_dirty = _diff_and_dirty(old_commit, head_commit, paths, repo_root)

    return SkipResult(
        should_skip=False,
        reason=f"first deploy from build commit {old_commit[:12]}",
        deployer=deployer_name,
        paths_checked=paths,
        changed_files=_combine_changed(changed_files, current_dirty),
    )
