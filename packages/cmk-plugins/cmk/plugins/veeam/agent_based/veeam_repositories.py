#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

import json
from collections.abc import Mapping
from contextlib import suppress
from dataclasses import dataclass
from typing import Any

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_value_store,
    GetRateError,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.plugins.lib.df import df_check_filesystem_single, FILESYSTEM_DEFAULT_PARAMS

_GB = 1024.0


@dataclass(frozen=True, kw_only=True)
class VeeamRepository:
    """Mirrors the VBR REST API's RepositoryStateModel
    (GET /api/v1/backupInfrastructure/repositories/states)."""

    type: str
    description: str
    capacity_gb: float
    free_gb: float
    is_online: bool
    is_out_of_date: bool
    host_name: str | None
    path: str | None
    extent_type: str | None


Section = Mapping[str, VeeamRepository]


def parse_veeam_repositories(string_table: StringTable) -> Section:
    section: dict[str, VeeamRepository] = {}
    # TODO: this assumes the endpoint returns plain repositories and scale-out
    # extents, but not the scale-out repository itself. The API reference does not
    # say, and nothing here filters it out. If it were returned, it would become a
    # service of its own, most likely with a size of 0. We need to confirm this with
    # real data.

    for line in string_table:
        repo_dict = json.loads(line[0])
        scaleout_details = repo_dict.get("scaleOutRepositoryDetails")
        extent_type = scaleout_details["extentType"] if scaleout_details is not None else None
        # TODO: `type` is a raw ERepositoryType enum identifier and extentType a raw
        # EExtentType enum identifier; we show them as-is rather than maintaining a
        # translation table for the dozens of possible values. Double-check once we
        # can verify against real data whether a translation is worth adding.
        category = f"{extent_type} Extent" if extent_type is not None else repo_dict["type"]
        item = f"{category} - {repo_dict['name']}"
        section[item] = VeeamRepository(
            type=repo_dict["type"],
            description=repo_dict["description"],
            capacity_gb=repo_dict["capacityGB"],
            free_gb=repo_dict["freeGB"],
            is_online=repo_dict["isOnline"],
            is_out_of_date=repo_dict["isOutOfDate"],
            host_name=repo_dict.get("hostName"),
            path=repo_dict.get("path"),
            extent_type=extent_type,
        )
    return section


def discovery_veeam_repositories(section: Section) -> DiscoveryResult:
    yield from (Service(item=item) for item in section)


def check_veeam_repositories(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:
    if (repository := section.get(item)) is None:
        return

    if not repository.is_online:
        yield Result(state=State.CRIT, summary="Offline")
        return

    if repository.is_out_of_date:
        yield Result(state=State.WARN, summary="Out of date")

    with suppress(GetRateError):
        yield from df_check_filesystem_single(
            get_value_store(),
            item,
            repository.capacity_gb * _GB,
            repository.free_gb * _GB,
            0,
            None,
            None,
            params,
        )

    if repository.host_name is not None:
        yield Result(state=State.OK, notice=f"Host: {repository.host_name}")
    if repository.path is not None:
        yield Result(state=State.OK, notice=f"Path: {repository.path}")
    if repository.description:
        yield Result(state=State.OK, notice=f"Description: {repository.description}")


agent_section_veeam_repositories = AgentSection(
    name="veeam_repositories",
    parse_function=parse_veeam_repositories,
)

check_plugin_veeam_repositories = CheckPlugin(
    name="veeam_repositories",
    service_name="Backup repository %s",
    discovery_function=discovery_veeam_repositories,
    check_function=check_veeam_repositories,
    check_ruleset_name="filesystem",
    check_default_parameters=FILESYSTEM_DEFAULT_PARAMS,
)
