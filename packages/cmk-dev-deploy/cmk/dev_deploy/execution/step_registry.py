# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Deployment step registry — single source of truth for step/deployer/display name mappings."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DeployerInfo:
    """Metadata for one deployment step."""

    step_name: str  # e.g. "config_deploy"
    deployer_name: str  # e.g. "config_spec"
    display_name: str  # e.g. "config"


_REGISTRY: tuple[DeployerInfo, ...] = (
    DeployerInfo(
        step_name="config_deploy", deployer_name="config_spec", display_name="config"
    ),
    DeployerInfo(
        step_name="bazel_build", deployer_name="install_spec", display_name="bazel"
    ),
    DeployerInfo(
        step_name="wheel_deploy", deployer_name="wheel_spec", display_name="wheels"
    ),
)

# Pre-built lookup dicts (immutable after module load)
STEP_TO_DEPLOYER: dict[str, str] = {
    info.step_name: info.deployer_name
    for info in _REGISTRY
    if info.deployer_name != "wheel_spec"  # wheel uses per-package state keys
}

DEPLOYER_DISPLAY_NAMES: dict[str, str] = {
    info.deployer_name: info.display_name for info in _REGISTRY
}

STEP_DISPLAY_NAMES: dict[str, str] = {
    info.step_name: info.display_name for info in _REGISTRY
}


def step_display_name(step_name: str) -> str:
    """Return the human-readable display name for a step, or the step name itself."""
    return STEP_DISPLAY_NAMES.get(step_name, step_name)
