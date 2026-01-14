#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.base.check_legacy_includes.cisco_ucs import DETECT, MAP_OPERABILITY, MAP_PRESENCE

check_info = {}

# comNET GmbH, Fabian Binder - 2018-05-08

# .1.3.6.1.4.1.9.9.719.1.41.9.1.3  cucsProcessorUnitRn
# .1.3.6.1.4.1.9.9.719.1.41.9.1.13 cucsProcessorUnitPresence
# .1.3.6.1.4.1.9.9.719.1.41.9.1.15 cucsProcessorUnitSerial
# .1.3.6.1.4.1.9.9.719.1.41.9.1.8  cucsProcessorUnitModel
# .1.3.6.1.4.1.9.9.719.1.41.9.1.10 cucsProcessorUnitOperability


def discover_cisco_ucs_cpu(info):
    for name, presence, _serial, _model, _status in info:
        if presence != "11":  # do not discover missing units
            yield name, None


def check_cisco_ucs_cpu(item, _no_params, info):
    for name, presence, serial, model, status in info:
        if name == item:
            state, state_readable = MAP_OPERABILITY.get(
                status, (3, "Unknown, status code %s" % status)
            )
            presence_state, presence_readable = MAP_PRESENCE.get(
                presence, (3, "Unknown, status code %s" % presence)
            )
            yield state, "Status: %s" % state_readable
            yield presence_state, "Presence: %s" % presence_readable
            yield 0, f"Model: {model}, SN: {serial}"


def parse_cisco_ucs_cpu(string_table: StringTable) -> StringTable:
    return string_table


check_info["cisco_ucs_cpu"] = LegacyCheckDefinition(
    name="cisco_ucs_cpu",
    parse_function=parse_cisco_ucs_cpu,
    detect=DETECT,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.9.9.719.1.41.9.1",
        oids=["3", "13", "15", "8", "10"],
    ),
    service_name="CPU %s",
    discovery_function=discover_cisco_ucs_cpu,
    check_function=check_cisco_ucs_cpu,
)
