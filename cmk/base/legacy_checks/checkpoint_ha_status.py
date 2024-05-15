#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.config import check_info

from cmk.agent_based.v2 import DiscoveryResult, Service, SNMPTree, StringTable
from cmk.plugins.lib.checkpoint import DETECT

# .1.3.6.1.4.1.2620.1.5.2.0 1
# .1.3.6.1.4.1.2620.1.5.3.0 6
# .1.3.6.1.4.1.2620.1.5.4.0 0
# .1.3.6.1.4.1.2620.1.5.5.0 yes
# .1.3.6.1.4.1.2620.1.5.6.0 active
# .1.3.6.1.4.1.2620.1.5.7.0 OK
# .1.3.6.1.4.1.2620.1.5.101.0 0
# .1.3.6.1.4.1.2620.1.5.103.0


def discover_checkpoint_ha_status(section: StringTable) -> DiscoveryResult:
    if not section:
        return
    installed, _major, _minor, _started, _state, _block_state, _stat_code, _stat_long = section[0]
    if installed != "0":
        yield Service()


def check_checkpoint_ha_status(_no_item, _no_params, info):
    installed, major, minor, started, state, block_state, stat_code, stat_long = info[0]

    # Some devices have a trailing "\n" in the state field. Drop it.
    state = state.rstrip()

    if installed == "0":
        yield 2, "Not installed"
    else:
        yield 0, f"Installed: v{major}.{minor}"

        for val, infotext, ok_vals, warn_vals in [
            (started, "Started", ["yes"], None),
            (state, "Status", ["active", "standby"], None),
            (block_state, "Blocking", ["ok"], ["initializing"]),
        ]:
            if ok_vals is None or val.lower() in ok_vals:
                status = 0
            elif warn_vals is not None and val.lower() in warn_vals:
                status = 1
            else:
                status = 2

            yield status, f"{infotext}: {val}"

        if stat_code != "0":
            yield 2, "Problem: %s" % stat_long


def parse_checkpoint_ha_status(string_table: StringTable) -> StringTable:
    return string_table


check_info["checkpoint_ha_status"] = LegacyCheckDefinition(
    parse_function=parse_checkpoint_ha_status,
    detect=DETECT,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.2620.1.5",
        oids=["2", "3", "4", "5", "6", "7", "101", "103"],
    ),
    service_name="HA Status",
    discovery_function=discover_checkpoint_ha_status,
    check_function=check_checkpoint_ha_status,
)
