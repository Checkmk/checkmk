#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import get_bytes_human_readable, LegacyCheckDefinition
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import any_of, contains, SNMPTree, startswith


def inventory_dell_eql_storage(info):
    for line in info:
        yield line[0], {}


def check_dell_eql_storage(item, _no_params, info):
    for (
        name,
        desc,
        health_state,
        raid_state,
        total_storage,
        repl_storage,
        snap_storage,
        used_storage,
    ) in info:
        if name == item:
            if desc:
                yield 0, desc

            # Health Status:
            health_states = {
                "0": "Unknown",
                "1": "Normal",
                "2": "Warning",
                "3": "Critical",
            }
            if health_state == "1":
                state = 0
            elif health_state in ["2", "0"]:
                state = 1
            else:
                state = 2
            yield state, "Health State: %s" % health_states[health_state]

            # Raid Status
            raid_states = {
                "1": "Ok",
                "2": "Degraded",
                "3": "Verifying",
                "4": "Reconstructing",
                "5": "Failed",
                "6": "CatastrophicLoss",
                "7": "Expanding",
                "8": "Mirroring",
            }

            if raid_state == "1":
                state = 0
            elif raid_state in ["3", "4", "7", "8"]:
                state = 1
            else:
                state = 2
            yield state, "Raid State: %s" % raid_states[raid_state]

            # Storage
            total_bytes = int(total_storage) * 1048576
            used_bytes = int(used_storage) * 1048576
            repl_bytes = int(repl_storage) * 1048576
            snap_bytes = int(snap_storage) * 1048576
            perfdata = [
                ("fs_used", used_bytes),
                ("fs_size", total_bytes),
                ("fs_free", total_bytes - used_bytes),
            ]
            yield 0, "Used: %s/%s (Snapshots: %s, Replication: %s)" % (
                get_bytes_human_readable(used_bytes),
                get_bytes_human_readable(total_bytes),
                get_bytes_human_readable(snap_bytes),
                get_bytes_human_readable(repl_bytes),
            ), perfdata


check_info["dell_eql_storage"] = LegacyCheckDefinition(
    detect=any_of(
        contains(".1.3.6.1.2.1.1.1.0", "EQL-SUP"),
        startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.12740.17"),
    ),
    check_function=check_dell_eql_storage,
    discovery_function=inventory_dell_eql_storage,
    service_name="Storage %s",
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.12740.2.1",
        oids=[
            "1.1.9.1",
            "1.1.7.1",
            "5.1.1.1",
            "13.1.1.1",
            "10.1.1.1",
            "10.1.4.1",
            "10.1.3.1",
            "10.1.2.1",
        ],
    ),
)
