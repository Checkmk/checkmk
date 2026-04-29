# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Registry helpers for deploy directory coverage checks.

Provides:
- :func:`uncovered_changed_files` -- Given changed file paths, find source
  files that have changes but no registry entry (for pipeline warnings).
"""

from __future__ import annotations

from cmk.dev_deploy.manifest.reader import (
    get_config_specs,
    get_install_specs,
    get_wheel_specs,
)


def _registered_coverage() -> tuple[frozenset[str], frozenset[str]]:
    """Build registry coverage signal as (covered_dirs, covered_files).

    - ``covered_dirs`` are source-tree prefixes (with trailing ``/``).  Used
      for install and wheel specs which deploy entire packages, and as a
      fallback for config specs whose enriched ``files`` list is empty.
    - ``covered_files`` are exact source paths.  Populated from each config
      spec's enumerated ``files`` list.

    Coverage is checked file-first, then dir-prefix.  Using the explicit
    file list avoids false negatives for over-broad ``source_prefix``
    values: ``commonpath()`` can collapse a few sibling files at different
    depths into a top-level prefix (e.g. ``omd/``), which would otherwise
    silently mask any sibling file as "covered" even when no spec actually
    deploys it.
    """
    install_dirs = frozenset(spec.package + "/" for spec in get_install_specs())
    wheel_dirs = frozenset(spec.package + "/" for spec in get_wheel_specs())

    config_dirs: set[str] = set()
    config_files: set[str] = set()
    for spec in get_config_specs():
        if spec.files:
            config_files.update(entry.src for entry in spec.files)
        else:
            config_dirs.add(spec.source_prefix)

    return (install_dirs | wheel_dirs | frozenset(config_dirs), frozenset(config_files))


def uncovered_changed_files(changed_files: tuple[str, ...]) -> list[str]:
    """Find changed files not covered by any deploy registry entry.

    Coverage matches a changed file when either:

    - The file's exact path appears in some config spec's ``files`` list, or
    - A registered package prefix (install/wheel/config-without-files) is
      a prefix of the file's path (longest-prefix matching).

    Files in the repo root (no directory prefix) are skipped.

    Args:
        changed_files: Changed file paths relative to repo root.

    Returns:
        Sorted list of unregistered file paths.
    """
    covered_dirs, covered_files = _registered_coverage()
    sorted_dirs = sorted(covered_dirs, key=len, reverse=True)

    unregistered: list[str] = []

    for filepath in changed_files:
        if "/" not in filepath:
            continue
        if filepath in covered_files:
            continue
        if any(filepath.startswith(reg_dir) for reg_dir in sorted_dirs):
            continue
        unregistered.append(filepath)

    return sorted(unregistered)
