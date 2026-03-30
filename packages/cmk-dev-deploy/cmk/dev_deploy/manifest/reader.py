# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Manifest reader: loads JSON manifest and constructs typed dataclass instances.

Does NOT import ``cmk.dev_deploy.output`` to avoid circular dependencies.
"""

from __future__ import annotations

import functools
import json
import os
from pathlib import Path
from typing import Any

from cmk.dev_deploy.types import (
    ConfigDeploySpec,
    ConfigFileEntry,
    DeployMethod,
    InstallSpec,
    PostInstallAction,
    Service,
    ServiceAction,
    ServiceSpec,
    WheelDeployMode,
    WheelDeploySpec,
)


def _manifest_dir() -> Path:
    """Return the manifest directory, using BUILD_WORKSPACE_DIRECTORY when under bazel run."""
    workspace = os.environ.get("BUILD_WORKSPACE_DIRECTORY")
    if workspace:
        return (
            Path(workspace)
            / "packages"
            / "cmk-dev-deploy"
            / "cmk"
            / "dev_deploy"
            / "manifest"
        )
    return Path(__file__).parent


def manifest_path() -> Path:
    """Return the path to the deploy manifest JSON file."""
    return _manifest_dir() / "deploy_manifest.json"


def hash_path() -> Path:
    """Return the path to the manifest hash file."""
    return _manifest_dir() / ".manifest_hash"


@functools.lru_cache(maxsize=1)
def _load_raw() -> dict[str, Any]:  # type: ignore[misc]
    """Load and cache the raw manifest dict."""
    with open(manifest_path()) as f:
        result: dict[str, Any] = json.load(f)
        return result


def clear_cache() -> None:
    """Clear the cached manifest (used after rebuild)."""
    _load_raw.cache_clear()


# --- Field mapping functions ---


def _parse_install_spec(raw: dict[str, Any]) -> InstallSpec:
    """Convert a manifest install_spec dict to an InstallSpec dataclass."""
    return InstallSpec(
        package=raw["source_prefix"].rstrip("/"),
        package_target=raw["package_target"],
        output_basename=raw["output_basename"],
        install_dest=raw["site_dest"],
        mode=raw["mode"],
        post_install=tuple(PostInstallAction(a) for a in raw["post_install"]),
        edition_constraint=frozenset(raw["editions"]) if raw["editions"] else None,
        needs_version_flag=raw["needs_version_flag"],
        needs_faked_artifacts=raw.get("needs_faked_artifacts", False),
        use_copytree=raw["use_copytree"],
        frontend_supervised=raw.get("frontend_supervised", False),
    )


def _parse_config_spec(raw: dict[str, Any]) -> ConfigDeploySpec:
    """Convert a manifest config_spec dict to a ConfigDeploySpec dataclass."""
    mode_raw = raw["mode"]
    files = tuple(
        ConfigFileEntry(src=f["src"], dest=f["dest"], mode=f["mode"])
        for f in raw.get("files", [])
    )
    services = tuple(_parse_service_pair(s) for s in raw.get("services", []))
    return ConfigDeploySpec(
        source_prefix=raw["source_prefix"],
        site_dest=raw["site_dest"],
        method=DeployMethod(raw["method"]),
        mode=mode_raw if mode_raw != -1 else None,
        includes=tuple(raw["includes"]),
        files=files,
        delete_extra=raw["delete_extra"],
        file_chmod=raw["file_chmod"] or None,
        services=services,
    )


def _parse_wheel_spec(raw: dict[str, Any]) -> WheelDeploySpec:
    """Convert a manifest wheel_spec dict to a WheelDeploySpec dataclass."""
    return WheelDeploySpec(
        package=raw["source_prefix"].rstrip("/"),
        wheel_targets=tuple(raw["wheel_targets"]),
        edition_constraint=frozenset(raw["editions"]) if raw["editions"] else None,
        deploy_mode=WheelDeployMode(raw.get("deploy_mode", "direct")),
        source_subdirs=tuple(raw.get("source_subdirs", [])),
        distribution_name=raw.get("distribution_name", ""),
        edition_filter=raw.get("edition_filter", False),
    )


def _parse_service_pair(s: str) -> tuple[Service, ServiceAction]:
    """Parse a "name:action" string into a (Service, ServiceAction) tuple."""
    name, action = s.split(":")
    return (Service(name), ServiceAction(action))


def _parse_service_spec(raw: dict[str, Any]) -> ServiceSpec:
    """Convert a manifest service_spec dict to a ServiceSpec dataclass."""
    return ServiceSpec(
        source_prefix=raw["source_prefix"],
        services=tuple(_parse_service_pair(s) for s in raw["services"]),
        edition_constraint=frozenset(raw["editions"]) if raw["editions"] else None,
    )


# --- Public getters ---


def get_install_specs() -> tuple[InstallSpec, ...]:
    """Return all install specs from the manifest as typed dataclasses."""
    data = _load_raw()
    return tuple(_parse_install_spec(s) for s in data["install_specs"])


def get_config_specs() -> tuple[ConfigDeploySpec, ...]:
    """Return all config deploy specs from the manifest as typed dataclasses."""
    data = _load_raw()
    return tuple(_parse_config_spec(s) for s in data["config_specs"])


def get_wheel_specs() -> tuple[WheelDeploySpec, ...]:
    """Return all wheel deploy specs from the manifest as typed dataclasses."""
    data = _load_raw()
    return tuple(_parse_wheel_spec(s) for s in data["wheel_specs"])


def get_service_specs() -> tuple[ServiceSpec, ...]:
    """Return all service specs from the manifest as typed dataclasses."""
    data = _load_raw()
    return tuple(_parse_service_spec(s) for s in data["service_specs"])


def get_frontend_supervised_prefixes() -> frozenset[str]:
    """Return path prefixes for frontend-supervised install specs."""
    return frozenset(
        spec.package + "/" for spec in get_install_specs() if spec.frontend_supervised
    )


def get_deploy_deps() -> dict[str, tuple[str, ...]]:
    """Return deploy dependency mapping from the manifest."""
    data = _load_raw()
    return {k: tuple(v) for k, v in data.get("deploy_deps", {}).items()}
