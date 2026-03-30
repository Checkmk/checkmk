# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Source path resolution for per-deployer skip logic.

Resolves repo-relative source paths for any deployer from manifest metadata.
Used by path-aware skip logic to filter git diffs per-deployer instead of
globally.

Public API:
    resolve_source_paths(deployer_name, repo_root) -> tuple[str, ...] | None
"""

from __future__ import annotations

from pathlib import Path

from cmk.dev_deploy.types import WheelDeploySpec


def resolve_source_paths(
    deployer_name: str,
    repo_root: Path,
) -> tuple[str, ...] | None:
    """Resolve repo-relative source path prefixes for a deployer.

    Returns a tuple of repo-relative path prefixes (strings ending with ``/``
    for directories), or ``None`` if no source path metadata is available
    (caller should treat as "always deploy").

    Args:
        deployer_name: Deployer key, e.g. ``'config_spec'``,
            ``'install_spec'``, or ``'wheel:packages/cmk-ccc'``.
        repo_root: Absolute path to the git repository root.

    Returns:
        Tuple of repo-relative path prefixes, or ``None`` for unknown deployers.
    """
    if deployer_name == "config_spec":
        return _resolve_config_paths()

    if deployer_name == "install_spec":
        return _resolve_install_paths()

    if deployer_name.startswith("wheel:"):
        return _resolve_wheel_paths(deployer_name, repo_root)

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


def _find_wheel_spec(package_path: str) -> WheelDeploySpec | None:
    """Find a WheelDeploySpec by package path."""
    from cmk.dev_deploy.manifest.reader import get_wheel_specs

    for spec in get_wheel_specs():
        if spec.package == package_path:
            return spec
    return None


def _resolve_wheel_paths(
    deployer_name: str,
    _repo_root: Path,
) -> tuple[str, ...] | None:
    """Resolve source paths for a wheel deployer key.

    Each deploy_wheel is now a single distribution (multi-dist packages were
    split into separate entries).  Uses Bazel-derived ``source_subdirs`` from
    the manifest instead of auto-discovering from disk.
    """
    # Parse deployer_name: "wheel:{package}"
    remainder = deployer_name[len("wheel:") :]
    package_path = remainder.split(":", 1)[0]

    spec = _find_wheel_spec(package_path)
    if spec is None:
        return None

    return _resolve_package_level(spec)


def _resolve_package_level(
    spec: WheelDeploySpec,
) -> tuple[str, ...]:
    """Resolve paths for a wheel deployer key using Bazel-derived source_subdirs."""
    if spec.source_subdirs:
        return tuple(spec.package + "/" + subdir for subdir in spec.source_subdirs)

    # Fallback: the whole package dir
    return (spec.package + "/",)
