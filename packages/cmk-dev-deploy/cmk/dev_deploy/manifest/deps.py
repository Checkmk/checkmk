# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Deploy-time transitive dependency expansion.

Functions for expanding changed directories to include cross-deployer
dependencies, using deploy_deps data from the JSON manifest (generated
by Bazel from BUILD file declarations).
"""

from __future__ import annotations


def expand_dependencies(changed_dirs: set[str]) -> set[str]:
    """Expand a set of changed directories to include transitive deploy dependencies.

    Uses a worklist algorithm with a visited set to handle cycles safely.
    Deploy dependency data is loaded from the manifest via manifest_reader.

    Args:
        changed_dirs: Set of source directory prefixes that have changes.

    Returns:
        Expanded set including the original directories plus all transitive
        deploy dependencies.
    """
    from cmk.dev_deploy.manifest.reader import get_deploy_deps

    deploy_deps = get_deploy_deps()

    expanded: set[str] = set(changed_dirs)
    visited: set[str] = set()
    worklist: list[str] = list(changed_dirs)

    while worklist:
        current = worklist.pop()
        if current in visited:
            continue
        visited.add(current)

        deps = deploy_deps.get(current)
        if deps is None:
            continue

        for dep in deps:
            if dep not in expanded:
                expanded.add(dep)
                worklist.append(dep)

    return expanded


def extract_changed_dirs(files: tuple[str, ...]) -> set[str]:
    """Extract unique directory prefixes from a list of changed files.

    For each file, finds the longest matching deploy_deps key (from manifest).
    Files that do not match any key are silently ignored (they are handled by
    other deployers that don't need dependency expansion).

    Args:
        files: Tuple of changed file paths relative to the repository root.

    Returns:
        Set of directory prefixes (keys from manifest deploy_deps) that
        contain at least one changed file.
    """
    from cmk.dev_deploy.manifest.reader import get_deploy_deps

    deploy_deps = get_deploy_deps()

    matched: set[str] = set()
    # Pre-sort keys by length (longest first) for longest-prefix matching
    sorted_keys = sorted(deploy_deps.keys(), key=len, reverse=True)

    for filepath in files:
        for key in sorted_keys:
            if filepath.startswith(key):
                matched.add(key)
                break  # First (longest) match wins

    return matched
