# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Branch and edition mismatch detection for deploy safety warnings.

Provides two checks that warn (but never block) when a deployment might be
going to an unexpected site:

* **Branch mismatch** -- the working branch differs from the branch the site
  was built from.
* **Edition mismatch** -- changed files belong to a higher Checkmk edition
  than the target site, so they will be filtered out during deployment.

Both functions return ``None`` when everything is fine, or a human-readable
warning string when a mismatch is detected.  Neither function raises
exceptions -- warnings must never block a deployment.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType

from cmk.dev_deploy.site.edition_filter import EDITION_CONFIG
from cmk.dev_deploy.types import ChangeSet, SiteInfo


@dataclass(frozen=True)
class _WarningConfig:
    # Path substrings that indicate a file requires a specific minimum edition.
    # Ordered from most-specific to least-specific so the first match wins.
    edition_patterns: MappingProxyType[str, str] = field(
        default_factory=lambda: MappingProxyType(
            {
                "nonfree/ultimatemt/": "ultimatemt",
                "nonfree/ultimate/": "ultimate",
                "nonfree/cloud/": "cloud",
                "nonfree/pro/": "pro",
                "non-free/": "pro",
            }
        )
    )


WARNING_CONFIG = _WarningConfig()

_SUBPROCESS_TIMEOUT_SHORT: int = 5
_SUBPROCESS_TIMEOUT_LONG: int = 10


def check_branch_mismatch(build_commit: str | None, repo_root: Path) -> str | None:
    """Check whether the current git branch matches the site's build branch.

    Args:
        build_commit: The 40-char git SHA from the site's ``COMMIT`` file,
            or ``None`` if the file is missing.
        repo_root: Path to the repository root (used as ``cwd`` for git).

    Returns:
        A warning string if the branches differ, or ``None`` if they match
        (or if detection is not possible).
    """
    if build_commit is None:
        return None

    try:
        current_branch = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
            timeout=_SUBPROCESS_TIMEOUT_SHORT,
            cwd=repo_root,
        )
    except (subprocess.TimeoutExpired, OSError):
        return None

    if current_branch.returncode != 0:
        return None

    branch_name = current_branch.stdout.strip()
    if not branch_name or branch_name == "HEAD":
        # Detached HEAD -- cannot determine branch
        return None

    # Check if build_commit is an ancestor of the current branch
    try:
        ancestor_check = subprocess.run(
            ["git", "merge-base", "--is-ancestor", build_commit, branch_name],
            capture_output=True,
            text=True,
            check=False,
            timeout=_SUBPROCESS_TIMEOUT_SHORT,
            cwd=repo_root,
        )
    except (subprocess.TimeoutExpired, OSError):
        return None

    if ancestor_check.returncode == 0:
        # Build commit is an ancestor of current branch -- match
        return None

    # Branches differ -- try to find the build branch name
    build_branch = _find_branch_for_commit(build_commit, repo_root)
    if build_branch:
        source = f"'{build_branch}'"
    else:
        source = f"commit {build_commit[:12]}"

    return (
        f"Branch mismatch: you are on '{branch_name}' but site was built from {source}\n"
        f"Deploy will proceed. Use Ctrl-C to abort."
    )


def _find_branch_for_commit(commit: str, repo_root: Path) -> str | None:
    """Try to find a branch name that contains the given commit.

    Returns the first branch name found, or ``None`` if detection fails.
    """
    try:
        result = subprocess.run(
            ["git", "branch", "--contains", commit, "--format=%(refname:short)"],
            capture_output=True,
            text=True,
            check=False,
            timeout=_SUBPROCESS_TIMEOUT_LONG,
            cwd=repo_root,
        )
    except (subprocess.TimeoutExpired, OSError):
        return None

    if result.returncode != 0 or not result.stdout.strip():
        return None

    # Return the first branch name
    return result.stdout.strip().splitlines()[0].strip()


def check_edition_mismatch(changes: ChangeSet | None, site: SiteInfo | None) -> str | None:
    """Check whether changed files require a higher edition than the target site.

    Args:
        changes: The detected change set, or ``None`` if unavailable.
        site: The resolved site info, or ``None`` if unavailable.

    Returns:
        A warning string listing mismatched files, or ``None`` if all files
        are compatible with the site edition.
    """
    if changes is None or site is None:
        return None
    if changes.is_empty:
        return None

    site_edition = site.edition
    site_includes = EDITION_CONFIG.includes.get(site_edition, frozenset())

    mismatched: list[str] = []
    for filepath in changes.files:
        required_edition = _required_edition_for_file(filepath)
        if required_edition is None:
            continue
        # File requires this edition -- check if the site includes it
        if required_edition == site_edition.value:
            continue
        if required_edition in site_includes:
            continue
        mismatched.append(filepath)

    if not mismatched:
        return None

    lines = [
        f"Edition mismatch: {len(mismatched)} changed file(s) require a higher edition "
        f"than site '{site.name}' ({site_edition.value})",
        "These files will be filtered out during deployment:",
    ]
    display_limit = 10
    for filepath in mismatched[:display_limit]:
        lines.append(f"  {filepath}")
    if len(mismatched) > display_limit:
        lines.append(f"  ... and {len(mismatched) - display_limit} more")

    return "\n".join(lines)


def _required_edition_for_file(filepath: str) -> str | None:
    """Return the minimum edition required for a file, or ``None`` if no restriction."""
    for pattern, edition in WARNING_CONFIG.edition_patterns.items():
        if pattern in filepath:
            return edition
    return None
