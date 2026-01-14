#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.plugins.juniper.lib import DETECT_JUNIPER_TRPZ

check_info = {}


def discover_juniper_trpz_info(info):
    return [(None, None)]


def check_juniper_trpz_info(_no_item, _no_params, info):
    serial, version = info[0]
    message = f"S/N: {serial}, FW Version: {version}"
    return 0, message


def parse_juniper_trpz_info(string_table: StringTable) -> StringTable | None:
    return string_table or None


check_info["juniper_trpz_info"] = LegacyCheckDefinition(
    name="juniper_trpz_info",
    parse_function=parse_juniper_trpz_info,
    detect=DETECT_JUNIPER_TRPZ,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.14525.4.2.1",
        oids=["1", "4"],
    ),
    service_name="Info",
    discovery_function=discover_juniper_trpz_info,
    check_function=check_juniper_trpz_info,
)
