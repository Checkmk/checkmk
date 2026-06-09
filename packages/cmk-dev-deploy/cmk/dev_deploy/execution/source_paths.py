# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Source path resolution for per-deployer skip logic.

Resolves repo-relative source paths for any deployer from manifest metadata.
Used by path-aware skip logic to filter git diffs per-deployer instead of
globally.

Public API:
    resolve_source_paths(deployer_name) -> tuple[str, ...] | None
"""

from __future__ import annotations


def resolve_source_paths(deployer_name: str) -> tuple[str, ...] | None:
    """Resolve repo-relative source path prefixes for a deployer.

    Returns a tuple of repo-relative path prefixes (strings ending with ``/``
    for directories), or ``None`` if no source path metadata is available
    (caller should treat as "always deploy").

    Args:
        deployer_name: Deployer key, e.g. ``'config_spec'`` or
            ``'install_spec'``.

    Returns:
        Tuple of repo-relative path prefixes, or ``None`` for unknown deployers.
    """
    if deployer_name == "config_spec":
        return _resolve_config_paths()

    if deployer_name == "install_spec":
        return _resolve_install_paths()

    if deployer_name == "wheel_spec":
        return _resolve_wheel_paths()

    # Unknown deployer: return None (fallback = always deploy)
    return None


# ---------------------------------------------------------------------------
# Config spec resolution
# ---------------------------------------------------------------------------


def _resolve_config_paths() -> tuple[str, ...]:
    """Return source_prefix from every config spec in the manifest."""
    from cmk.dev_deploy.manifest.reader import get_config_specs

    return tuple(spec.source_prefix for spec in get_config_specs())


# ---------------------------------------------------------------------------
# Install spec resolution (with transitive dependency expansion)
# ---------------------------------------------------------------------------


def _resolve_install_paths() -> tuple[str, ...]:
    """Return package + '/' from every install spec, plus transitive deps."""
    from cmk.dev_deploy.manifest.reader import get_install_specs

    paths: list[str] = []
    for spec in get_install_specs():
        prefix = spec.package + "/" if not spec.package.endswith("/") else spec.package
        if prefix not in paths:
            paths.append(prefix)

    # Expand transitive dependencies for install specs (non-Python deployer)
    from cmk.dev_deploy.manifest.deps import expand_dependencies

    expanded = expand_dependencies(set(paths))
    for dep_path in sorted(expanded):
        if dep_path not in paths:
            paths.append(dep_path)

    return tuple(paths)


# ---------------------------------------------------------------------------
# Wheel resolution
# ---------------------------------------------------------------------------


def _resolve_wheel_paths() -> tuple[str, ...]:
    """Return the source-tree prefixes covered by wheel deployment.

    Used to record path-filtered dirty hashes in the deploy state so the
    dirty/revert detection in change_detector covers Python files.
    """
    from cmk.dev_deploy.deployers.wheel_deployer import wheel_prefixes

    return wheel_prefixes()
