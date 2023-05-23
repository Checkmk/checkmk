#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import discover, get_bytes_human_readable, LegacyCheckDefinition
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree
from cmk.base.plugins.agent_based.utils.emc import DETECT_DATADOMAIN


def parse_emc_datadomain_mtree(info):
    return {
        line[0]: {"precompiled": int(float(line[1]) * 1024**3), "status_code": line[2]}
        for line in info
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
        "Status: %s, Precompiled: %s"
        % (dev_state_str, get_bytes_human_readable(mtree_data["precompiled"])),
        [("precompiled", mtree_data["precompiled"])],
    )


check_info["emc_datadomain_mtree"] = LegacyCheckDefinition(
    detect=DETECT_DATADOMAIN,
    parse_function=parse_emc_datadomain_mtree,
    check_function=check_emc_datadomain_mtree,
    discovery_function=discover(),
    service_name="MTree %s",
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.19746.1.15.2.1.1",
        oids=["2", "3", "4"],
    ),
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
