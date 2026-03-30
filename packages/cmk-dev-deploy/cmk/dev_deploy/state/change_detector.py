# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Change detection and categorization via git diff."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

from cmk.dev_deploy.core.timeouts import GIT_QUICK
from cmk.dev_deploy.errors import ChangeDetectionError
from cmk.dev_deploy.types import ChangeCategory, ChangeSet

if TYPE_CHECKING:
    from cmk.dev_deploy.state.deploy_state import DeployState

# Categorization rules: ordered tuple of (prefix, extension_filter, category).
# First match wins. Extension filter is None for "match any file in this prefix".
# Derived from .f12 script analysis and repository directory structure.
_CATEGORIZATION_RULES: tuple[tuple[str, frozenset[str] | None, ChangeCategory], ...] = (
    # Python fast path: .py files under cmk/ (main source tree)
    ("cmk/", frozenset({".py"}), ChangeCategory.PYTHON),
    # C++ sources
    ("packages/livestatus/", frozenset({".cc", ".h", ".hpp"}), ChangeCategory.CPP),
    ("packages/neb/", frozenset({".cc", ".h", ".hpp"}), ChangeCategory.CPP),
    ("packages/unixcat/", frozenset({".cc", ".h"}), ChangeCategory.CPP),
    (
        "non-free/packages/cmc/",
        frozenset({".cc", ".h", ".hpp", ".proto"}),
        ChangeCategory.CPP,
    ),
    # Rust sources
    ("packages/check-cert/", frozenset({".rs"}), ChangeCategory.RUST),
    ("packages/check-http/", frozenset({".rs"}), ChangeCategory.RUST),
    ("packages/cmk-agent-ctl/", frozenset({".rs"}), ChangeCategory.RUST),
    ("packages/mk-oracle/", frozenset({".rs"}), ChangeCategory.RUST),
    ("packages/mk-sql/", frozenset({".rs"}), ChangeCategory.RUST),
    # Vue/Frontend
    (
        "packages/cmk-frontend-vue/",
        frozenset({".vue", ".ts", ".tsx", ".js"}),
        ChangeCategory.VUE,
    ),
    ("packages/cmk-shared-typing/", frozenset({".ts"}), ChangeCategory.VUE),
    (
        "packages/cmk-frontend/",
        frozenset({".js", ".css", ".scss"}),
        ChangeCategory.FRONTEND,
    ),
    # Python packages (after specific C++/Rust/Vue rules so those match first)
    ("packages/", frozenset({".py"}), ChangeCategory.PYTHON),
    ("non-free/packages/", frozenset({".py"}), ChangeCategory.PYTHON),
    # Config/Data (no extension filter -- deploy all files in these dirs)
    ("agents/", None, ChangeCategory.CONFIG),
    ("notifications/", None, ChangeCategory.CONFIG),
    ("active_checks/", None, ChangeCategory.CONFIG),
    ("locale/", None, ChangeCategory.DATA),
    ("doc/", None, ChangeCategory.DATA),
    ("omd/", None, ChangeCategory.CONFIG),
    # Build system files
    ("MODULE.bazel", None, ChangeCategory.BUILD),
    ("bazel/", None, ChangeCategory.BUILD),
    # Tests
    ("tests/", None, ChangeCategory.TEST),
)


def categorize_file(path: str) -> ChangeCategory:
    """Categorize a file path using first-match-wins against ordered rules."""
    for prefix, ext_filter, category in _CATEGORIZATION_RULES:
        if path.startswith(prefix):
            if ext_filter is None:
                return category
            suffix = "." + path.rsplit(".", 1)[-1] if "." in path else ""
            if suffix in ext_filter:
                return category
    return ChangeCategory.OTHER


def detect_changes(
    build_commit: str | None,
    repo_root: Path,
    *,
    target_commit: str | None = None,
) -> ChangeSet | None:
    """Detect and categorize changed files between build_commit and a target.

    Returns None if build_commit is None. When target_commit is None, diffs
    against the working tree; otherwise diffs committed changes only.
    """
    if build_commit is None:
        return None

    _validate_commit(build_commit, repo_root)
    if target_commit is not None:
        _validate_commit(target_commit, repo_root)
    changed_files = _git_diff_files(
        build_commit, repo_root, target_commit=target_commit
    )
    deleted_files = _git_diff_deleted(
        build_commit, repo_root, target_commit=target_commit
    )

    if not changed_files and not deleted_files:
        return ChangeSet(
            build_commit=build_commit,
            files=(),
            deleted_files=(),
            categories={},
        )

    # Categorize all files
    categorized: dict[ChangeCategory, list[str]] = {}
    for file_path in changed_files:
        cat = categorize_file(file_path)
        categorized.setdefault(cat, []).append(file_path)

    # Convert to frozen structure
    frozen_categories = {
        cat: tuple(sorted(paths)) for cat, paths in categorized.items()
    }

    return ChangeSet(
        build_commit=build_commit,
        files=tuple(sorted(changed_files)),
        deleted_files=tuple(sorted(deleted_files)),
        categories=frozen_categories,
    )


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _validate_commit(commit: str, repo_root: Path) -> None:
    """Verify that a commit hash exists in the local repository."""
    result = subprocess.run(
        ["git", "cat-file", "-t", commit],
        capture_output=True,
        text=True,
        check=False,
        cwd=str(repo_root),
        timeout=GIT_QUICK,
    )
    if result.returncode != 0 or result.stdout.strip() != "commit":
        raise ChangeDetectionError(
            f"Build commit {commit[:12]} not found in this repository.",
            recovery=(
                "The site was built from a commit not in your local repo.\n"
                "Try: git fetch origin\n"
                "Or deploy without change detection: cmk-dev-deploy --full"
            ),
        )


def _git_diff_files(
    build_commit: str,
    repo_root: Path,
    *,
    target_commit: str | None = None,
) -> list[str]:
    """Return changed file paths between build_commit and a target."""
    cmd = ["git", "diff", "--name-only", "--no-renames", build_commit]
    if target_commit is not None:
        cmd.append(target_commit)
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=False,
        cwd=str(repo_root),
        timeout=GIT_QUICK,
    )
    if result.returncode != 0:
        raise ChangeDetectionError(
            f"git diff failed (exit {result.returncode}): {result.stderr.strip()}",
            recovery="Ensure the site build commit is reachable in this repo.",
        )
    return [line for line in result.stdout.strip().splitlines() if line]


def _git_diff_deleted(
    build_commit: str,
    repo_root: Path,
    *,
    target_commit: str | None = None,
) -> list[str]:
    """Return file paths deleted between build_commit and a target."""
    cmd = [
        "git",
        "diff",
        "--name-only",
        "--no-renames",
        "--diff-filter=D",
        build_commit,
    ]
    if target_commit is not None:
        cmd.append(target_commit)
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=False,
        cwd=str(repo_root),
        timeout=GIT_QUICK,
    )
    if result.returncode != 0:
        return []  # Non-fatal: deletions are best-effort
    return [line for line in result.stdout.strip().splitlines() if line]


# ---------------------------------------------------------------------------
# Change filtering helpers (extracted from __main__.py)
# ---------------------------------------------------------------------------


def state_has_dirty_files(state: DeployState | None) -> bool:
    """Return True if any deployer in *state* has dirty file hashes."""
    if state is None:
        return False
    return any(ds.dirty_file_hashes for ds in state.deployers.values())


def has_reverted_dirty_files(state: DeployState, repo_root: Path) -> bool:
    """Return True if previously-dirty files are no longer dirty.

    Detects the case where a user modified files, deployed, then reverted.
    The clean version needs to be redeployed.
    """
    from cmk.dev_deploy.state.deploy_state import get_dirty_files

    previously_dirty: set[str] = set()
    for ds in state.deployers.values():
        previously_dirty.update(ds.dirty_file_hashes.keys())
    if not previously_dirty:
        return False
    currently_dirty = set(get_dirty_files(repo_root))
    return bool(previously_dirty - currently_dirty)


def filter_stale_dirty(
    changes: ChangeSet,
    state: DeployState,
    repo_root: Path,
) -> ChangeSet:
    """Remove already-deployed dirty files from a changeset.

    Dirty files that appear in ``git diff`` every run but have the same
    content hash as the last deploy are filtered out.
    """
    from cmk.dev_deploy.state.deploy_state import compute_file_hash, get_dirty_files

    # Reconstruct known dirty hashes from all deployers' state
    known_dirty: dict[str, str] = {}
    for ds in state.deployers.values():
        known_dirty.update(ds.dirty_file_hashes)

    if not known_dirty:
        return changes

    # Identify currently dirty files (staged + unstaged vs HEAD)
    current_dirty = set(get_dirty_files(repo_root))

    # Find stale dirty files: dirty AND hash matches saved state
    stale: set[str] = set()
    for f in changes.files:
        if f not in current_dirty:
            continue  # committed change, keep it
        known_hash = known_dirty.get(f)
        if known_hash is None:
            continue  # new dirty file, keep it
        abs_path = repo_root / f
        if not abs_path.is_file():
            continue  # deleted file, keep it
        if compute_file_hash(abs_path) == known_hash:
            stale.add(f)

    if not stale:
        return changes

    # Build filtered changeset
    filtered_files = tuple(f for f in changes.files if f not in stale)
    filtered_categories: dict[ChangeCategory, tuple[str, ...]] = {}
    for cat, cat_files in changes.categories.items():
        kept = tuple(f for f in cat_files if f not in stale)
        if kept:
            filtered_categories[cat] = kept

    return ChangeSet(
        build_commit=changes.build_commit,
        files=filtered_files,
        categories=filtered_categories,
    )
