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

# example output
# <<<scaleio_sds>>>
# SDS 3c7af8db00000000:
#        ID                                                 3c7af8db00000000
#        NAME                                               sds03
#        PROTECTION_DOMAIN_ID                               91ebcf4500000000
#        STATE                                              REMOVE_STATE_NORMAL
#        MEMBERSHIP_STATE                                   JOINED
#        MDM_CONNECTION_STATE                               MDM_CONNECTED
#        MAINTENANCE_MODE_STATE                             NO_MAINTENANCE
#        MAX_CAPACITY_IN_KB                                 21.8 TB (22353 GB)
#        UNUSED_CAPACITY_IN_KB                              13.2 TB (13471 GB)


def parse_scaleio_sds(string_table: StringTable) -> ScaleioSection:
    return parse_scaleio(string_table, "SDS")


def discover_scaleio_sds(section: ScaleioSection) -> DiscoveryResult:
    yield from (Service(item=item) for item in section)


def check_scaleio_sds(item: str, params: Mapping[str, Any], section: ScaleioSection) -> CheckResult:
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


agent_section_scaleio_sds = AgentSection(
    name="scaleio_sds",
    parse_function=parse_scaleio_sds,
)


check_plugin_scaleio_sds = CheckPlugin(
    name="scaleio_sds",
    service_name="ScaleIO SDS capacity %s",
    discovery_function=discover_scaleio_sds,
    check_function=check_scaleio_sds,
    check_ruleset_name="filesystem",
    check_default_parameters=FILESYSTEM_DEFAULT_PARAMS,
)


def discover_scaleio_sds_status(section: ScaleioSection) -> DiscoveryResult:
    yield from (Service(item=item) for item in section)


def check_scaleio_sds_status(item: str, section: ScaleioSection) -> CheckResult:
    if not (data := section.get(item)):
        return

    name, pd_id = data["NAME"][0], data["PROTECTION_DOMAIN_ID"][0]
    yield Result(state=State.OK, summary=f"Name: {name}, PD: {pd_id}")

    status = data["STATE"][0]
    if "normal" not in status.lower():
        yield Result(state=State.CRIT, summary="State: %s" % status)

    status_maint = data["MAINTENANCE_MODE_STATE"][0]
    if "no_maintenance" not in status_maint.lower():
        yield Result(state=State.WARN, summary="Maintenance: %s" % status_maint)

    status_conn = data["MDM_CONNECTION_STATE"][0]
    if "connected" not in status_conn.lower():
        yield Result(state=State.CRIT, summary="Connection state: %s" % status_conn)

    status_member = data["MEMBERSHIP_STATE"][0]
    if "joined" not in status_member.lower():
        yield Result(state=State.CRIT, summary="Membership state: %s" % status_member)


check_plugin_scaleio_sds_status = CheckPlugin(
    name="scaleio_sds_status",
    service_name="ScaleIO SDS status %s",
    sections=["scaleio_sds"],
    discovery_function=discover_scaleio_sds_status,
    check_function=check_scaleio_sds_status,
)
