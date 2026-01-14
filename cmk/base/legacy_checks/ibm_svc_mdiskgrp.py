#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="var-annotated"

from collections.abc import Iterable, Mapping, Sequence
from typing import Any

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import render
from cmk.base.check_legacy_includes.df import df_check_filesystem_list, FILESYSTEM_DEFAULT_PARAMS
from cmk.base.check_legacy_includes.ibm_svc import parse_ibm_svc_with_header

check_info = {}

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


def ibm_svc_mdiskgrp_to_mb(size: str) -> float:
    if size.endswith("MB"):
        size_mb = float(size.replace("MB", ""))
    elif size.endswith("GB"):
        size_mb = float(size.replace("GB", "")) * 1024
    elif size.endswith("TB"):
        size_mb = float(size.replace("TB", "")) * 1024 * 1024
    elif size.endswith("PB"):
        size_mb = float(size.replace("PB", "")) * 1024 * 1024 * 1024
    elif size.endswith("EB"):
        size_mb = float(size.replace("EB", "")) * 1024 * 1024 * 1024 * 1024
    else:
        size_mb = float(size)
    return size_mb


def parse_ibm_svc_mdiskgrp(
    string_table: Sequence[Sequence[str]],
) -> Mapping[str, Mapping[str, str]]:
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
    parsed = {}
    for rows in parse_ibm_svc_with_header(string_table, dflt_header).values():
        try:
            data = rows[0]
        except IndexError:
            continue
        parsed.setdefault(data["name"], data)
    return parsed


def discover_ibm_svc_mdiskgrp(
    parsed: Mapping[str, Mapping[str, str]],
) -> Iterable[tuple[str, dict[str, object]]]:
    for mdisk_name in parsed:
        yield mdisk_name, {}


def check_ibm_svc_mdiskgrp(
    item: str, params: Mapping[str, Any], parsed: Mapping[str, Mapping[str, str]]
) -> Iterable[tuple[int, str] | tuple[int, str, list[Any]]]:
    if not (data := parsed.get(item)):
        return
    mgrp_status = data["status"]

    if mgrp_status != "online":
        yield 2, "Status: %s" % mgrp_status
        return

    fslist = []

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

    fslist.append((item, capacity, avail_mb, 0))
    status, message, perfdata = df_check_filesystem_list(item, params, fslist)
    yield status, message, perfdata

    mb = 1024 * 1024

    # Compute provisioning
    if not capacity:
        return  # provisioning does not make sense when capacity is 0

    provisioning = 100.0 * virtual_capacity / capacity
    infotext = "Provisioning: %s" % render.percent(provisioning)
    state = 0
    if "provisioning_levels" in params:
        warn, crit = params["provisioning_levels"]
        if provisioning >= crit:
            state = 2
        elif provisioning >= warn:
            state = 1
        if state:
            infotext += f" (warn/crit at {render.percent(warn)}/{render.percent(crit)})"
        warn_mb = capacity * mb * warn / 100
        crit_mb = capacity * mb * crit / 100
    else:
        warn_mb = None
        crit_mb = None

    # Note: Performance data is now (with new metric system) normed to
    # canonical units - i.e. 1 byte in this case.
    yield (
        state,
        infotext,
        [("fs_provisioning", virtual_capacity * mb, warn_mb, crit_mb, 0, capacity * mb)],
    )


check_info["ibm_svc_mdiskgrp"] = LegacyCheckDefinition(
    name="ibm_svc_mdiskgrp",
    parse_function=parse_ibm_svc_mdiskgrp,
    service_name="Pool Capacity %s",
    discovery_function=discover_ibm_svc_mdiskgrp,
    check_function=check_ibm_svc_mdiskgrp,
    check_ruleset_name="ibm_svc_mdiskgrp",
    check_default_parameters=FILESYSTEM_DEFAULT_PARAMS,
)
