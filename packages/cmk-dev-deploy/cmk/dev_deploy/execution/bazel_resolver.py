# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Bazel target resolution module for cmk-dev-deploy.

Maps changed files to owning Bazel build targets by matching file paths
against the manifest's source-prefix-to-target mapping.  This is instant
compared to the old ``bazel query rdeps()`` approach which had to load
the entire workspace.

Only files in categories requiring Bazel builds (CPP, RUST, VUE, FRONTEND)
are resolved. Python fast-path files are excluded -- they are handled by
:mod:`cmk.dev_deploy.deployers.wheel_deployer` without Bazel.
"""

from __future__ import annotations

import time

from cmk.dev_deploy.manifest.reader import (
    get_frontend_supervised_prefixes,
    get_install_specs,
)
from cmk.dev_deploy.types import (
    BazelTarget,
    BazelTargetKind,
    BazelTargetSet,
    ChangeCategory,
    ChangeSet,
)

# Categories that need Bazel target resolution.
# Python (fast path), CONFIG, DATA, TEST, OTHER, BUILD are excluded.
_BAZEL_CATEGORIES = frozenset(
    {
        ChangeCategory.CPP,
        ChangeCategory.RUST,
        ChangeCategory.VUE,
        ChangeCategory.FRONTEND,
    }
)


def resolve_bazel_targets(
    changes: ChangeSet,
    _repo_root: object,
    *,
    frontend_supervised: bool = False,
) -> BazelTargetSet:
    """Resolve changed files to owning Bazel build targets.

    Filters the changeset to Bazel-buildable categories and matches files
    against the manifest's install spec source prefixes.  BUILD file changes
    are handled separately: global build files (MODULE.bazel, bazel/) trigger
    a conservative ``//...`` target, while specific BUILD files produce
    per-package targets.

    Args:
        changes: The categorized changeset from :func:`detect_changes`.
        repo_root: Absolute path to the git repository root (unused, kept
            for API compatibility).
        frontend_supervised: When True, exclude files under frontend-supervised
            package prefixes from resolution (handled by Vite HMR instead).

    Returns:
        A :class:`BazelTargetSet` with resolved targets and metadata.
    """
    queryable_files = _get_bazel_queryable_files(changes, frontend_supervised=frontend_supervised)
    build_packages = _get_build_file_packages(changes)

    if not queryable_files and not build_packages:
        return BazelTargetSet(
            targets=(),
            files_queried=0,
            files_resolved=0,
            from_cache=False,
            query_time_ms=0,
        )

    all_targets: list[tuple[str, str]] = []
    query_time_ms = 0

    if queryable_files:
        # Match files against the manifest's install spec source prefixes.
        # The manifest already maps source directories to deploy targets,
        # so no bazel query is needed.
        start = time.monotonic()
        matched = _resolve_via_manifest(queryable_files)
        elapsed = time.monotonic() - start
        query_time_ms = int(elapsed * 1000)
        all_targets.extend(matched)

    # Add BUILD file package-level targets
    for pkg_pattern in build_packages:
        all_targets.append(("other", pkg_pattern))

    # Deduplicate by label
    seen: set[str] = set()
    unique_targets: list[BazelTarget] = []
    for kind_str, label in all_targets:
        if label not in seen:
            seen.add(label)
            unique_targets.append(_parse_target(kind_str, label))

    # Sort by label for deterministic output
    unique_targets.sort(key=lambda t: t.label)

    return BazelTargetSet(
        targets=tuple(unique_targets),
        files_queried=len(queryable_files),
        files_resolved=len(queryable_files) if all_targets else 0,
        from_cache=False,
        query_time_ms=query_time_ms,
    )


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _get_bazel_queryable_files(
    changes: ChangeSet,
    *,
    frontend_supervised: bool = False,
) -> list[str]:
    """Extract files that need Bazel target resolution.

    Only files in categories that require Bazel builds (CPP, RUST, VUE,
    FRONTEND) are included. Python fast-path, config, data, test, and
    other files are excluded.

    When *frontend_supervised* is True, files under frontend-supervised
    package prefixes (from :func:`~cmk.dev_deploy.manifest.reader.get_frontend_supervised_prefixes`)
    are excluded -- those are handled by Vite HMR instead of Bazel.

    Returns:
        Sorted list of file paths relative to repo root.
    """
    files: list[str] = []
    for cat in _BAZEL_CATEGORIES:
        files.extend(changes.categories.get(cat, ()))
    if frontend_supervised:
        prefixes = get_frontend_supervised_prefixes()
        files = [f for f in files if not any(f.startswith(p) for p in prefixes)]
    return sorted(files)


def _resolve_via_manifest(files: list[str]) -> list[tuple[str, str]]:
    """Match changed files against install spec source prefixes.

    Uses the manifest's existing source-prefix-to-target mapping (enriched
    at manifest build time via bazel cquery) to resolve files to packages
    without running any bazel query at deploy time.

    Returns:
        List of ``(kind_str, package_label)`` tuples matching the format
        expected by :func:`_parse_target`.
    """
    specs = get_install_specs()
    matched_packages: set[str] = set()

    for f in files:
        for spec in specs:
            if f.startswith(spec.package + "/"):
                matched_packages.add(spec.package)
                break  # file matched, no need to check more specs

    # Return synthetic targets using the package path (the label format
    # doesn't matter for downstream — only the package is extracted)
    return [("other", f"//{pkg}:all") for pkg in sorted(matched_packages)]


def _get_build_file_packages(changes: ChangeSet) -> list[str]:
    """Extract Bazel package patterns from changed BUILD files.

    Returns:
        List of package patterns like ``'//packages/check-cert/...'``,
        or ``['//...']`` for global build file changes (MODULE.bazel, bazel/).
    """
    build_files = changes.categories.get(ChangeCategory.BUILD, ())
    if not build_files:
        return []

    packages: set[str] = set()
    for f in build_files:
        if f == "MODULE.bazel" or f.startswith("bazel/"):
            # Global build files changed -- conservative full rebuild
            return ["//..."]
        if f.endswith("/BUILD") or f.endswith("/BUILD.bazel"):
            # Package-specific BUILD file
            dirname = f.rsplit("/", 1)[0]
            packages.add(f"//{dirname}/...")
    return sorted(packages)


def _parse_target(kind_str: str, label: str) -> BazelTarget:
    """Parse a ``(kind_str, label)`` pair into a :class:`BazelTarget`.

    Extracts the package from the label by stripping the leading ``//``
    and splitting on ``:``.
    """
    kind = BazelTargetKind.from_query_kind(kind_str)
    # Strip leading "//" and split on ":" to get the package path
    package = label.lstrip("/").split(":")[0].rstrip("/.")
    return BazelTarget(label=label, kind=kind, package=package)
