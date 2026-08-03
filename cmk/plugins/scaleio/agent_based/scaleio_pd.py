#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

from collections.abc import Mapping
from typing import Any

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
from cmk.plugins.scaleio.lib import (
    convert_scaleio_space_into_mb,
    KNOWN_CONVERSION_VALUES_INTO_MB,
    parse_scaleio,
    ScaleioSection,
)

# <<<scaleio_pd>>>
# PROTECTION_DOMAIN 91ebcf4500000000:
#        ID                                                 91ebcf4500000000
#        NAME                                               domain01
#        STATE                                              PROTECTION_DOMAIN_ACTIVE
#        MAX_CAPACITY_IN_KB                                 65.5 TB (67059 GB)
#        UNUSED_CAPACITY_IN_KB                              17.2 TB (17635 GB)


def parse_scaleio_pd(string_table: StringTable) -> ScaleioSection:
    return parse_scaleio(string_table, "PROTECTION_DOMAIN")


def discover_scaleio_pd(section: ScaleioSection) -> DiscoveryResult:
    yield from (Service(item=item) for item in section)


def check_scaleio_pd(item: str, params: Mapping[str, Any], section: ScaleioSection) -> CheckResult:
    if not (data := section.get(item)):
        return

    # How will the data be represented? It's magic and the only
    # indication is the unit. We need to handle this!
    unit = data["MAX_CAPACITY_IN_KB"][3].strip(")")
    if unit not in KNOWN_CONVERSION_VALUES_INTO_MB:
        yield Result(state=State.UNKNOWN, summary=f"Unknown unit: {unit}")
        return

    total = convert_scaleio_space_into_mb(unit, int(data["MAX_CAPACITY_IN_KB"][2].strip("(")))
    free = convert_scaleio_space_into_mb(unit, int(data["UNUSED_CAPACITY_IN_KB"][2].strip("(")))

    yield from df_check_filesystem_single(
        value_store=get_value_store(),
        mountpoint=item,
        filesystem_size=total,
        free_space=free,
        reserved_space=0.0,
        inodes_avail=None,
        inodes_total=None,
        params=params,
    )


agent_section_scaleio_pd = AgentSection(
    name="scaleio_pd",
    parse_function=parse_scaleio_pd,
)


check_plugin_scaleio_pd = CheckPlugin(
    name="scaleio_pd",
    service_name="ScaleIO PD capacity %s",
    discovery_function=discover_scaleio_pd,
    check_function=check_scaleio_pd,
    check_ruleset_name="filesystem",
    check_default_parameters=FILESYSTEM_DEFAULT_PARAMS,
)


def discover_scaleio_pd_status(section: ScaleioSection) -> DiscoveryResult:
    yield from (Service(item=item) for item in section)


def check_scaleio_pd_status(item: str, section: ScaleioSection) -> CheckResult:
    if not (data := section.get(item)):
        return

    status = data["STATE"][0].replace("PROTECTION_DOMAIN_", "")
    state = State.OK if status == "ACTIVE" else State.CRIT
    name = data["NAME"][0]

    yield Result(state=state, summary=f"Name: {name}, State: {status}")


check_plugin_scaleio_pd_status = CheckPlugin(
    name="scaleio_pd_status",
    service_name="ScaleIO PD status %s",
    sections=["scaleio_pd"],
    discovery_function=discover_scaleio_pd_status,
    check_function=check_scaleio_pd_status,
)
