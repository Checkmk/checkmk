#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.base.check_legacy_includes.cisco_ucs import DETECT, MAP_OPERABILITY

check_info = {}

# comNET GmbH, Fabian Binder - 2018-05-07

# .1.3.6.1.4.1.9.9.719.1.9.35.1.32 cucsComputeRackUnitModel
# .1.3.6.1.4.1.9.9.719.1.9.35.1.47 cucsComputeRackUnitSerial
# .1.3.6.1.4.1.9.9.719.1.9.35.1.43 cucsComputeRackUnitOperability


def discover_cisco_ucs_system(info):
    return [(None, None)]


def check_cisco_ucs_system(_no_item, _no_params, info):
    model, serial, status = info[0]
    state, state_readable = MAP_OPERABILITY.get(status, (3, "Unknown, status code %s" % status))
    return state, f"Status: {state_readable}, Model: {model}, SN: {serial}"


def parse_cisco_ucs_system(string_table: StringTable) -> StringTable | None:
    return string_table or None


check_info["cisco_ucs_system"] = LegacyCheckDefinition(
    name="cisco_ucs_system",
    parse_function=parse_cisco_ucs_system,
    detect=DETECT,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.9.9.719.1.9.35.1",
        oids=["32", "47", "43"],
    ),
    service_name="System health",
    discovery_function=discover_cisco_ucs_system,
    check_function=check_cisco_ucs_system,
)
