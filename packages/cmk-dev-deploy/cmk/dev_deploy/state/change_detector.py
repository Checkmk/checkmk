# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Change detection and categorization via git diff."""

from __future__ import annotations

import json
import logging
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

from cmk.dev_deploy.core.timeouts import GIT_QUICK
from cmk.dev_deploy.errors import ChangeDetectionError
from cmk.dev_deploy.manifest.reader import get_categorization_rules
from cmk.dev_deploy.types import CategorizationRule, ChangeCategory, ChangeSet

if TYPE_CHECKING:
    from cmk.dev_deploy.state.deploy_state import DeployState

logger = logging.getLogger(__name__)

# Structural rules: not derivable from manifest, always present.
# These match disjoint path prefixes (tests/, MODULE.bazel, bazel/)
# that do not overlap with any manifest-derived prefix.
#
# Note: "MODULE.bazel" as a prefix also matches "MODULE.bazel.lock" via
# startswith(). This is a pre-existing false positive inherited from the
# original hardcoded rules. Both files are build-system files, so the
# miscategorization is harmless in practice.
_STRUCTURAL_RULES: tuple[CategorizationRule, ...] = (
    CategorizationRule("tests/", None, ChangeCategory.TEST),
    CategorizationRule("MODULE.bazel", None, ChangeCategory.BUILD),
    CategorizationRule("bazel/", None, ChangeCategory.BUILD),
)

# Cached combined rules: computed once on first call, reset by reset_categorization_cache().
_cached_rules: tuple[CategorizationRule, ...] | None = None


def _load_rules() -> tuple[CategorizationRule, ...]:
    """Load categorization rules: structural rules + manifest-derived rules.

    The combined result is cached in the module-level _cached_rules variable
    to avoid repeated tuple concatenation on every categorize_file() call.

    Structural rules have unconditional priority (applied first). They match
    disjoint path prefixes (tests/, MODULE.bazel, bazel/) that never overlap
    with manifest-derived prefixes (packages/, cmk/, agents/, etc.), so the
    ordering between the two groups does not affect correctness.

    Within manifest-derived rules, ordering is longest-prefix-first.
    """
    global _cached_rules
    if _cached_rules is not None:
        return _cached_rules

    try:
        manifest_rules = get_categorization_rules()
    except (FileNotFoundError, json.JSONDecodeError, KeyError):
        logger.warning(
            "Manifest unavailable or missing categorization_rules -- "
            "using structural-only fallback (all files categorize as OTHER). "
            "Run with --rebuild-manifest to regenerate."
        )
        _cached_rules = _STRUCTURAL_RULES
        return _cached_rules

    _cached_rules = _STRUCTURAL_RULES + manifest_rules
    return _cached_rules


def reset_categorization_cache() -> None:
    """Reset the cached combined rules (called after manifest rebuild).

    This is a public function (no underscore prefix) because it is called
    from staleness.py after a manifest rebuild.  Naming it without an
    underscore avoids the convention violation of importing a private name
    across module boundaries.
    """
    global _cached_rules
    _cached_rules = None


def categorize_file(path: str) -> ChangeCategory:
    """Categorize a file path using first-match-wins against ordered rules."""
    for rule in _load_rules():
        if path.startswith(rule.prefix):
            if rule.extensions is None:
                return rule.category
            suffix = "." + path.rsplit(".", 1)[-1] if "." in path else ""
            if suffix in rule.extensions:
                return rule.category
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
    changed_files = _git_diff_files(build_commit, repo_root, target_commit=target_commit)
    deleted_files = _git_diff_deleted(build_commit, repo_root, target_commit=target_commit)

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
    frozen_categories = {cat: tuple(sorted(paths)) for cat, paths in categorized.items()}

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
    """Return changed (non-deleted) file paths between build_commit and a target.

    Excludes deleted files (--diff-filter=d) since those are tracked separately
    by _git_diff_deleted().  Without this filter, deleted files appear in
    ChangeSet.files and the wheel deployer crashes trying to copy them.
    """
    cmd = ["git", "diff", "--name-only", "--no-renames", "--diff-filter=d", build_commit]
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
