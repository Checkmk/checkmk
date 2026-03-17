# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Distribution info resolution for wheel deployment.

Maps WheelDeploySpec metadata to concrete source-to-target deployment
instructions (DistributionInfo, PackageInfo).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from cmk.dev_deploy.types import WheelDeployMode, WheelDeploySpec


@dataclass(frozen=True)
class DistributionInfo:
    """Source-to-target mapping for a single installable distribution."""

    distribution_name: str
    source_subdirs: tuple[str, ...]
    top_level_packages: tuple[str, ...]
    deploy_mode: WheelDeployMode
    bazel_target: str = ""


@dataclass(frozen=True)
class PackageInfo:
    """Complete deployment info for one WheelDeploySpec package."""

    distributions: tuple[DistributionInfo, ...]


def derive_top_level_packages(source_subdirs: tuple[str, ...]) -> tuple[str, ...]:
    """Derive top-level package names from the first path component of each subdir."""
    top_levels: set[str] = set()
    for subdir in source_subdirs:
        if "/" in subdir.rstrip("/"):
            # e.g. 'cmk/ccc/' -> 'cmk'
            top_levels.add(subdir.split("/")[0])
        elif subdir.endswith(".py"):
            # e.g. 'cmk_update_agent.py' -> 'cmk_update_agent'
            top_levels.add(subdir.removesuffix(".py"))
        else:
            # e.g. 'livestatus/' -> 'livestatus'
            top_levels.add(subdir.rstrip("/"))
    return tuple(sorted(top_levels))


def build_package_info_from_spec(
    spec: WheelDeploySpec,
    repo_root: Path,
) -> PackageInfo | None:
    """Build PackageInfo from WheelDeploySpec metadata, or None if source is missing."""
    if spec.deploy_mode == WheelDeployMode.GENERATED:
        dist_name = spec.distribution_name or spec.package.rsplit("/", 1)[-1]
        bazel_target = spec.wheel_targets[0] if spec.wheel_targets else ":wheel"
        return PackageInfo(
            distributions=(
                DistributionInfo(
                    distribution_name=dist_name,
                    source_subdirs=(),
                    top_level_packages=(
                        "cmk",
                    ),  # All generated packages are under cmk/
                    deploy_mode=WheelDeployMode.GENERATED,
                    bazel_target=bazel_target,
                ),
            ),
        )

    # direct mode: use Bazel-derived source_subdirs from manifest
    package_dir = repo_root / spec.package
    if not package_dir.is_dir():
        return None

    source_subdirs = spec.source_subdirs
    if not source_subdirs:
        return None

    dist_name = spec.distribution_name or spec.package.rsplit("/", 1)[-1]
    top_level = derive_top_level_packages(source_subdirs)

    has_dirs = any(s.endswith("/") for s in source_subdirs)
    mode = WheelDeployMode.DIRECT if has_dirs else WheelDeployMode.FLAT

    return PackageInfo(
        distributions=(
            DistributionInfo(
                distribution_name=dist_name,
                source_subdirs=source_subdirs,
                top_level_packages=top_level,
                deploy_mode=mode,
            ),
        ),
    )
