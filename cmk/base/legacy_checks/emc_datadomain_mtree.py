#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import render, SNMPTree
from cmk.plugins.lib.emc import DETECT_DATADOMAIN

check_info = {}


def parse_emc_datadomain_mtree(string_table):
    return {
        line[0]: {"precompiled": int(float(line[1]) * 1024**3), "status_code": line[2]}
        for line in string_table
    }


def check_emc_datadomain_mtree(item, params, parsed):
    if not (mtree_data := parsed.get(item)):
        return
    state_table = {
        "0": "unknown",
        "1": "deleted",
        "2": "read-only",
        "3": "read-write",
        "4": "replication destination",
        "5": "retention lock enabled",
        "6": "retention lock disabled",
    }
    dev_state_str = state_table.get(
        mtree_data["status_code"], "invalid code %s" % mtree_data["status_code"]
    )
    yield (
        params.get(dev_state_str, 3),
        "Status: {}, Precompiled: {}".format(
            dev_state_str, render.bytes(mtree_data["precompiled"])
        ),
        [("precompiled", mtree_data["precompiled"])],
    )


def discover_emc_datadomain_mtree(section):
    yield from ((item, {}) for item in section)


check_info["emc_datadomain_mtree"] = LegacyCheckDefinition(
    name="emc_datadomain_mtree",
    detect=DETECT_DATADOMAIN,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.19746.1.15.2.1.1",
        oids=["2", "3", "4"],
    ),
    parse_function=parse_emc_datadomain_mtree,
    service_name="MTree %s",
    discovery_function=discover_emc_datadomain_mtree,
    check_function=check_emc_datadomain_mtree,
    check_ruleset_name="emc_datadomain_mtree",
    check_default_parameters={
        "deleted": 2,
        "read-only": 1,
        "read-write": 0,
        "replication destination": 0,
        "retention lock disabled": 0,
        "retention lock enabled": 0,
        "unknown": 3,
    },
)
