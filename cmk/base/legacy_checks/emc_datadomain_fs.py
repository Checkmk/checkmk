#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.base.check_legacy_includes.df import df_check_filesystem_list, FILESYSTEM_DEFAULT_PARAMS
from cmk.plugins.lib.df import EXCLUDED_MOUNTPOINTS
from cmk.plugins.lib.emc import DETECT_DATADOMAIN

check_info = {}


def inventory_emc_datadomain_fs(info):
    mplist = []
    for line in info:
        if line[1] in EXCLUDED_MOUNTPOINTS:
            continue
        mplist.append((line[1], None))
    return mplist


def check_emc_datadomain_fs(item, params, info):
    fslist = []
    for line in info:
        if item == line[1] or "patterns" in params:
            size_mb = float(line[2]) * 1024.0
            avail_mb = float(line[4]) * 1024.0
            fslist.append((item, size_mb, avail_mb, 0))
    return df_check_filesystem_list(item, params, fslist)


def parse_emc_datadomain_fs(string_table: StringTable) -> StringTable:
    return string_table


check_info["emc_datadomain_fs"] = LegacyCheckDefinition(
    name="emc_datadomain_fs",
    parse_function=parse_emc_datadomain_fs,
    detect=DETECT_DATADOMAIN,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.19746.1.3.2.1.1",
        oids=["1", "3", "4", "5", "6", "7", "8"],
    ),
    service_name="DD-Filesystem %s",
    discovery_function=inventory_emc_datadomain_fs,
    check_function=check_emc_datadomain_fs,
    check_ruleset_name="filesystem",
    check_default_parameters=FILESYSTEM_DEFAULT_PARAMS,
)
