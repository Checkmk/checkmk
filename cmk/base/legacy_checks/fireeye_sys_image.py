#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.plugins.fireeye.lib import DETECT

check_info = {}

# .1.3.6.1.4.1.25597.11.5.1.1.0 eMPS (eMPS) 7.6.5.442663 --> FE-FIREEYE-MIB::feInstalledSystemImage.0
# .1.3.6.1.4.1.25597.11.5.1.2.0 7.6.5 --> FE-FIREEYE-MIB::feSystemImageVersionCurrent.0
# .1.3.6.1.4.1.25597.11.5.1.3.0 7.6.5 --> FE-FIREEYE-MIB::feSystemImageVersionLatest.0
# .1.3.6.1.4.1.25597.11.5.1.4.0 1 --> FE-FIREEYE-MIB::feIsSystemImageLatest.0


def check_fireeye_sys_image(_no_item, _no_params, info):
    installed, version, latest_version, is_latest = info[0]
    state = 0
    infotext = f"Image: {installed}, Version: {version}"

    if is_latest != "1":
        state = 1
        infotext += ", Latest version: %s" % latest_version

    return state, infotext


def parse_fireeye_sys_image(string_table: StringTable) -> StringTable:
    return string_table


def discover_fireeye_sys_image(info):
    yield from [(None, None)] if info else []


check_info["fireeye_sys_image"] = LegacyCheckDefinition(
    name="fireeye_sys_image",
    parse_function=parse_fireeye_sys_image,
    detect=DETECT,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.25597.11.5.1",
        oids=["1", "2", "3", "4"],
    ),
    service_name="System image",
    discovery_function=discover_fireeye_sys_image,
    check_function=check_fireeye_sys_image,
)
