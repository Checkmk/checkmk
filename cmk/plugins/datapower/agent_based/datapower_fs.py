#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_value_store,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    StringTable,
)
from cmk.plugins.datapower.lib import DETECT
from cmk.plugins.lib.df import df_check_filesystem_list, FILESYSTEM_DEFAULT_PARAMS


def saveint(i: str) -> int:
    """Tries to cast a string to an integer and return it. In case this
    fails, it returns 0.

    Advice: Please don't use this function in new code. It is understood as
    bad style these days, because in case you get 0 back from this function,
    you can not know whether it is really 0 or something went wrong."""
    try:
        return int(i)
    except TypeError, ValueError:
        return 0


def discover_datapower_fs(section: StringTable) -> DiscoveryResult:
    if section:
        # only discover filesystems with a defined total size > 0
        if saveint(section[0][0]) != 0:
            yield Service(item="Encrypted")
        if saveint(section[0][2]) != 0:
            yield Service(item="Unencrypted")
        if saveint(section[0][4]) != 0:
            yield Service(item="Temporary")
        if saveint(section[0][6]) != 0:
            yield Service(item="Internal")


def check_datapower_fs(item: str, params: Mapping[str, Any], section: StringTable) -> CheckResult:
    if item == "Encrypted":
        i = 0
    elif item == "Unencrypted":
        i = 2
    elif item == "Temporary":
        i = 4
    elif item == "Internal":
        i = 6
    else:
        return

    avail_mb = float(section[0][i])
    size_mb = float(section[0][i + 1])
    fslist = [(item, size_mb, avail_mb, 0.0)]

    yield from df_check_filesystem_list(get_value_store(), item, params, fslist)


def parse_datapower_fs(string_table: StringTable) -> StringTable:
    return string_table


snmp_section_datapower_fs = SimpleSNMPSection(
    name="datapower_fs",
    parse_function=parse_datapower_fs,
    detect=DETECT,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.14685.3.1.29",
        oids=["1", "2", "3", "4", "5", "6", "7", "8"],
    ),
)


check_plugin_datapower_fs = CheckPlugin(
    name="datapower_fs",
    service_name="Filesystem %s",
    discovery_function=discover_datapower_fs,
    check_function=check_datapower_fs,
    check_ruleset_name="filesystem",
    check_default_parameters=FILESYSTEM_DEFAULT_PARAMS,
)
