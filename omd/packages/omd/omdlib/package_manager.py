#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from typing import Literal


def _get_raw_version(omd_version: str) -> str:
    return omd_version[:-4]


def select_matching_packages(version: str, installed_packages: Sequence[str]) -> list[str]:
    raw_version = _get_raw_version(version)
    target_package_name = f"{get_edition(version)}-{raw_version}"
    with_version_str = [package for package in installed_packages if target_package_name in package]
    if "p" in raw_version:
        return with_version_str
    if "-" in raw_version:
        return with_version_str
    return [
        package
        for package in with_version_str
        if f"{raw_version}p" not in package and f"{raw_version}-" not in package
    ]


def get_edition(
    omd_version: str,
) -> Literal["raw", "enterprise", "managed", "free", "cloud", "saas", "unknown"]:
    """Returns the long Checkmk Edition name or "unknown" of the given OMD version"""
    parts = omd_version.split(".")
    if parts[-1] == "demo":
        edition_short = parts[-2]
    else:
        edition_short = parts[-1]

    if edition_short == "cre":
        return "raw"
    if edition_short == "cee":
        return "enterprise"
    if edition_short == "cme":
        return "managed"
    if edition_short == "cfe":
        return "free"
    if edition_short == "cce":
        return "cloud"
    if edition_short == "cse":
        return "saas"
    return "unknown"
