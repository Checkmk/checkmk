#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_value_store,
    Metric,
    render,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.plugins.ibm.lib_svc import parse_ibm_svc_with_header
from cmk.plugins.lib.df import df_check_filesystem_single, FILESYSTEM_DEFAULT_PARAMS

# Example output from agent:
# <<<ibm_svc_mdiskgrp:sep(58)>>>
# 0:Quorum_2:online:1:0:704.00MB:64:704.00MB:0.00MB:0.00MB:0.00MB:0:0:auto:inactive:no:0.00MB:0.00MB:0.00MB
# 1:stp5_450G_03:online:18:6:29.43TB:256:21.68TB:8.78TB:7.73TB:7.75TB:29:80:auto:inactive:no:0.00MB:0.00MB:0.00MB
# 4:stp5_450G_02:online:15:14:24.53TB:256:277.00GB:24.26TB:24.26TB:24.26TB:98:80:auto:inactive:no:0.00MB:0.00MB:0.00MB
# 9:stp6_450G_03:online:18:6:29.43TB:256:21.68TB:8.78TB:7.73TB:7.75TB:29:80:auto:inactive:no:0.00MB:0.00MB:0.00MB
# 10:stp6_450G_02:online:15:14:24.53TB:256:277.00GB:24.26TB:24.26TB:24.26TB:98:80:auto:inactive:no:0.00MB:0.00MB:0.00MB
# 15:stp6_300G_01:online:15:23:16.34TB:256:472.50GB:15.88TB:15.88TB:15.88TB:97:80:auto:inactive:no:0.00MB:0.00MB:0.00MB
# 16:stp5_300G_01:online:15:23:16:34TB:256:472.50GB:15.88TB:15.88TB:15.88TB:97:80:auto:inactive:no:0.00MB:0.00MB:0.00MB
# 17:Quorum_1:online:1:0:512.00MB:256:512.00MB:0.00MB:0.00MB:0.00MB:0:80:auto:inactive:no:0.00MB:0.00MB:0.00MB
# 18:Quorum_0:online:1:0:512.00MB:256:512.00MB:0.00MB:0.00MB:0.00MB:0:80:auto:inactive:no:0.00MB:0.00MB:0.00MB
# 21:stp5_450G_01:online:12:31:19.62TB:256:320.00GB:19.31TB:19.31TB:19.31TB:98:0:auto:inactive:no:0.00MB:0.00MB:0.00MB
# 22:stp6_450G_01:online:12:31:19.62TB:256:320.00GB:19.31TB:19.31TB:19.31TB:98:0:auto:inactive:no:0.00MB:0.00MB:0.00MB
# 23:stp5_600G_01:online:3:2:6.54TB:256:512.00MB:6.54TB:6.54TB:6.54TB:99:80:auto:inactive:no:0.00MB:0.00MB:0.00MB
# 24:stp6_600G_01:online:3:2:6.54TB:256:512.00MB:6.54TB:6.54TB:6.54TB:99:80:auto:inactive:no:0.00MB:0.00MB:0.00MB


Section = Mapping[str, Mapping[str, str]]


def ibm_svc_mdiskgrp_to_mb(size: str) -> float:
    if size.endswith("MB"):
        return float(size.replace("MB", ""))
    if size.endswith("GB"):
        return float(size.replace("GB", "")) * 1024
    if size.endswith("TB"):
        return float(size.replace("TB", "")) * 1024 * 1024
    if size.endswith("PB"):
        return float(size.replace("PB", "")) * 1024 * 1024 * 1024
    if size.endswith("EB"):
        return float(size.replace("EB", "")) * 1024 * 1024 * 1024 * 1024
    return float(size)


def parse_ibm_svc_mdiskgrp(string_table: StringTable) -> Section:
    dflt_header = [
        "id",
        "name",
        "status",
        "mdisk_count",
        "vdisk_count",
        "capacity",
        "extent_size",
        "free_capacity",
        "virtual_capacity",
        "used_capacity",
        "real_capacity",
        "overallocation",
        "warning",
        "easy_tier",
        "easy_tier_status",
        "compression_active",
        "compression_virtual_capacity",
        "compression_compressed_capacity",
        "compression_uncompressed_capacity",
        "parent_mdisk_grp_id",
        "parent_mdisk_grp_name",
        "child_mdisk_grp_count",
        "child_mdisk_grp_capacity",
        "type",
        "encrypt",
        "owner_type",
        "site_id",
        "site_name",
    ]
    parsed: dict[str, Mapping[str, str]] = {}
    for rows in parse_ibm_svc_with_header(string_table, dflt_header).values():
        try:
            data = rows[0]
        except IndexError:
            continue
        parsed.setdefault(data["name"], data)
    return parsed


def discover_ibm_svc_mdiskgrp(section: Section) -> DiscoveryResult:
    yield from (Service(item=mdisk_name) for mdisk_name in section)


def check_ibm_svc_mdiskgrp(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:
    if not (data := section.get(item)):
        return
    mgrp_status = data["status"]

    if mgrp_status != "online":
        yield Result(state=State.CRIT, summary=f"Status: {mgrp_status}")
        return

    # Names of the fields are a bit confusing and not what you would
    # expect.

    # 1. Physical size of the pool
    capacity = ibm_svc_mdiskgrp_to_mb(data["capacity"])

    # 2. Part of that that is physically in use
    real_capacity = ibm_svc_mdiskgrp_to_mb(data["real_capacity"])

    # 3. Provisioned space - can be more than physical size
    virtual_capacity = ibm_svc_mdiskgrp_to_mb(data["virtual_capacity"])

    # Compute available (do not use free_capacity, it's something different)
    avail_mb = capacity - real_capacity

    yield from df_check_filesystem_single(
        value_store=get_value_store(),
        mountpoint=item,
        filesystem_size=capacity,
        free_space=avail_mb,
        reserved_space=0,
        inodes_total=None,
        inodes_avail=None,
        params=params,
    )

    mb = 1024 * 1024

    # Compute provisioning
    if not capacity:
        return  # provisioning does not make sense when capacity is 0

    provisioning = 100.0 * virtual_capacity / capacity
    infotext = f"Provisioning: {render.percent(provisioning)}"
    state = State.OK
    warn_mb: float | None = None
    crit_mb: float | None = None
    if "provisioning_levels" in params:
        warn, crit = params["provisioning_levels"]
        if provisioning >= crit:
            state = State.CRIT
        elif provisioning >= warn:
            state = State.WARN
        if state is not State.OK:
            infotext += f" (warn/crit at {render.percent(warn)}/{render.percent(crit)})"
        warn_mb = capacity * mb * warn / 100
        crit_mb = capacity * mb * crit / 100

    yield Result(state=state, summary=infotext)
    # Note: Performance data is now (with new metric system) normed to
    # canonical units - i.e. 1 byte in this case.
    yield Metric(
        "fs_provisioning",
        virtual_capacity * mb,
        levels=(warn_mb, crit_mb) if warn_mb is not None and crit_mb is not None else None,
        boundaries=(0, capacity * mb),
    )


agent_section_ibm_svc_mdiskgrp = AgentSection(
    name="ibm_svc_mdiskgrp",
    parse_function=parse_ibm_svc_mdiskgrp,
)


check_plugin_ibm_svc_mdiskgrp = CheckPlugin(
    name="ibm_svc_mdiskgrp",
    service_name="Pool Capacity %s",
    discovery_function=discover_ibm_svc_mdiskgrp,
    check_function=check_ibm_svc_mdiskgrp,
    check_ruleset_name="ibm_svc_mdiskgrp",
    check_default_parameters=FILESYSTEM_DEFAULT_PARAMS,
)
