#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable
from dataclasses import dataclass
from typing import get_args, Literal

from cmk.werks.flavor.cmk import CmkFlavor
from cmk.werks.flavor.cmk.version import read_current_version as read_cmk_version
from cmk.werks.flavor.cmk.version import version_from_defines_make

from .flavor import Flavor, read_repo_file, RepoFiles


@dataclass(frozen=True)
class _LegacyFlavor:
    """A flavor that still uses the Checkmk werk model"""

    name: str
    branch_regex: str
    read_current_version: Callable[[RepoFiles], str | None]

    def cleanup_branch_name(self, branch_name: str) -> str:
        return branch_name

    def adapt_werk_string(self, werk_string: str, werk_id: int) -> str:  # noqa: ARG002
        return werk_string


def _read_cma_version(repo: RepoFiles) -> str | None:
    if (content := read_repo_file(repo, "cma-defines")) is None:
        return None
    return version_from_defines_make(content)


def _read_kube_version(repo: RepoFiles) -> str | None:
    if (content := read_repo_file(repo, ".werks/config")) is None:
        return None
    first_line = content.decode("utf-8").split("\n", 1)[0]
    if not first_line.startswith('current_version = "'):
        return None
    return first_line.split("=", 1)[1].strip('" ')


FlavorName = Literal["cmk", "cma", "checkmk_kube_agent", "cloudmk"]
FLAVOR_NAMES = sorted(get_args(FlavorName))


def get_flavor(name: str) -> Flavor:
    match name:
        case "cmk":
            return CmkFlavor()
        case "cma":
            return _LegacyFlavor("cma", r"^(master$|\d+\.\d+$)", _read_cma_version)
        case "checkmk_kube_agent":
            return _LegacyFlavor(
                "checkmk_kube_agent", r"^(main$|\d+\.\d+\.\d+)", _read_kube_version
            )
        case "cloudmk":
            return _LegacyFlavor("cloudmk", r"^main$", read_cmk_version)
        case _:
            raise ValueError(f"Unknown flavor {name!r}, expected one of {', '.join(FLAVOR_NAMES)}")
