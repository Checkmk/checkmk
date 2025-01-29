#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Mapping
from typing import Any

import pydantic

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_value_store,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.plugins.lib.df import df_check_filesystem_single, FILESYSTEM_DEFAULT_PARAMS
from cmk.plugins.lib.threepar import parse_3par


class SpaceUsage(pydantic.BaseModel):
    totalMiB: float
    usedMiB: float

    @property
    def freeMiB(self):
        return self.totalMiB - self.usedMiB


class ThreeparCPG(pydantic.BaseModel):
    name: str
    state: int
    num_fpvvs: int = pydantic.Field(alias="numFPVVs")  # number of Fully Provisioned Virtual Volumes
    num_tdvvs: int = pydantic.Field(alias="numTDVVs")  # number of Thinly Deduped Virtual Volumes
    num_tpvvs: int = pydantic.Field(
        alias="numTPVVs"
    )  # number of Thinly Provisioned Virtual Volumes
    sa_usage: SpaceUsage = pydantic.Field(alias="SAUsage")  # Snapshot administration usage
    sd_usage: SpaceUsage = pydantic.Field(alias="SDUsage")  # Snapshot data space usage
    usr_usage: SpaceUsage = pydantic.Field(alias="UsrUsage")  # User data space usage


ThreeparCPGSection = Mapping[str, ThreeparCPG]

_STATES = {
    1: (State.OK, "Normal"),
    2: (State.WARN, "Degraded"),
    3: (State.CRIT, "Failed"),
}


def parse_threepar_cpgs(string_table: StringTable) -> ThreeparCPGSection:
    if (raw_members := parse_3par(string_table).get("members")) is None:
        return {}

    return {cpgs.get("name"): ThreeparCPG.model_validate(cpgs) for cpgs in raw_members}


def count_threepar_vvs(cpg: ThreeparCPG) -> int:
    return cpg.num_fpvvs + cpg.num_tdvvs + cpg.num_tpvvs


agent_section_3par_cpgs = AgentSection(
    name="3par_cpgs",
    parse_function=parse_threepar_cpgs,
)


def discover_threepar_cpgs(section: ThreeparCPGSection) -> DiscoveryResult:
    for cpg in section.values():
        if cpg.name and count_threepar_vvs(cpg) > 0:
            yield Service(item=cpg.name)


def check_threepar_cpgs(item: str, section: ThreeparCPGSection) -> CheckResult:
    if (cpg := section.get(item)) is None:
        return

    state, state_readable = _STATES[cpg.state]
    yield Result(state=state, summary=f"{state_readable}, {count_threepar_vvs(cpg)} VVs")


check_plugin_3par_cpgs = CheckPlugin(
    name="3par_cpgs",
    discovery_function=discover_threepar_cpgs,
    check_function=check_threepar_cpgs,
    service_name="CPG %s",
)


def discover_threepar_cpgs_usage(section: ThreeparCPGSection) -> DiscoveryResult:
    for cpg in section.values():
        if count_threepar_vvs(cpg) > 0:
            for fs in [
                "SAUsage",
                "SDUsage",
                "UsrUsage",
            ]:
                yield Service(item=f"{cpg.name} {fs}")


def check_threepar_cpgs_usage(
    item: str, params: Mapping[str, Any], section: ThreeparCPGSection
) -> CheckResult:
    for cpg in section.values():
        if f"{cpg.name} SAUsage" == item:
            yield from df_check_filesystem_single(
                value_store=get_value_store(),
                mountpoint=item,
                filesystem_size=cpg.sa_usage.totalMiB,
                free_space=cpg.sa_usage.freeMiB,
                reserved_space=0.0,
                inodes_avail=None,
                inodes_total=None,
                params=params,
            )
        if f"{cpg.name} SDUsage" == item:
            yield from df_check_filesystem_single(
                value_store=get_value_store(),
                mountpoint=item,
                filesystem_size=cpg.sd_usage.totalMiB,
                free_space=cpg.sd_usage.freeMiB,
                reserved_space=0.0,
                inodes_avail=None,
                inodes_total=None,
                params=params,
            )
        if f"{cpg.name} UsrUsage" == item:
            yield from df_check_filesystem_single(
                value_store=get_value_store(),
                mountpoint=item,
                filesystem_size=cpg.usr_usage.totalMiB,
                free_space=cpg.usr_usage.freeMiB,
                reserved_space=0.0,
                inodes_avail=None,
                inodes_total=None,
                params=params,
            )


check_plugin_3par_cpgs_usage = CheckPlugin(
    name="3par_cpgs_usage",
    discovery_function=discover_threepar_cpgs_usage,
    check_function=check_threepar_cpgs_usage,
    service_name="CPG %s",
    check_ruleset_name="threepar_cpgs",
    check_default_parameters=FILESYSTEM_DEFAULT_PARAMS,
    sections=["3par_cpgs"],
)
