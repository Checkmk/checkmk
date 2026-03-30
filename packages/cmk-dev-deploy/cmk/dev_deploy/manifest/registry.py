# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Registry helpers for deploy directory coverage checks.

Provides:
- :func:`uncovered_changed_dirs` -- Given changed file paths, find source
  directories that have changes but no registry entry (for pipeline warnings).
"""

from __future__ import annotations

from cmk.dev_deploy.manifest.reader import (
    get_config_specs,
    get_install_specs,
    get_wheel_specs,
)


def _all_registered_source_dirs() -> frozenset[str]:
    """Build set of ALL registered source directories from the manifest.

    Combines source prefixes from install specs, config specs, and wheel specs.

    Returns:
        A frozenset of source directory strings with trailing slashes.
    """
    install_dirs = frozenset(spec.package + "/" for spec in get_install_specs())
    config_dirs = frozenset(spec.source_prefix for spec in get_config_specs())
    wheel_dirs = frozenset(spec.package + "/" for spec in get_wheel_specs())

    return install_dirs | config_dirs | wheel_dirs


def uncovered_changed_files(changed_files: tuple[str, ...]) -> list[str]:
    """Find changed files not covered by any deploy registry entry.

    For each changed file, checks whether any registered directory is a
    prefix of the file's path (longest-prefix matching).  Returns the
    actual file paths that have no matching registry entry.

    Files in the repo root (no directory prefix) are skipped.

    Args:
        changed_files: Changed file paths relative to repo root.

    Returns:
        Sorted list of unregistered file paths.
    """
    registered = _all_registered_source_dirs()
    # Sort registered dirs by length (longest first) for longest-prefix matching
    sorted_registered = sorted(registered, key=len, reverse=True)

    unregistered: list[str] = []

    for filepath in changed_files:
        # Skip files in repo root (no directory component)
        if "/" not in filepath:
            continue

        # Try longest-prefix matching against registered dirs
        if not any(filepath.startswith(reg_dir) for reg_dir in sorted_registered):
            unregistered.append(filepath)

    return sorted(unregistered)
