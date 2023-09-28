#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from .agent_based_api.v1 import register, SNMPTree
from .agent_based_api.v1.type_defs import StringTable
from .utils.diskstat import Section
from .utils.emc import DETECT_VPLEX


def parse_emc_vplex_volumes(string_table: StringTable) -> Section:
    volumes: dict[str, dict[str, float]] = {}

    # Each volume is listed twice, because they are connected to both directors
    for name, _uuid, ops, read, write, read_wait_raw, write_wait_raw in string_table:
        read_wait = float(read_wait_raw) / 1000000
        write_wait = float(write_wait_raw) / 1000000

        if name in volumes:
            volumes[name]["read_throughput"] += float(read)
            volumes[name]["write_throughput"] += float(write)
            volumes[name]["ios"] += float(ops)
            volumes[name]["average_read_wait"] = max(volumes[name]["average_read_wait"], read_wait)
            volumes[name]["average_write_wait"] = max(
                volumes[name]["average_write_wait"], write_wait
            )
        else:
            volumes[name] = {
                "average_read_wait": read_wait,
                "average_write_wait": write_wait,
                "read_throughput": float(read),
                "write_throughput": float(write),
                "ios": float(ops),
            }

    return volumes


register.snmp_section(
    name="emc_vplex_volumes",
    parse_function=parse_emc_vplex_volumes,
    parsed_section_name="diskstat_io_volumes",
    detect=DETECT_VPLEX,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.1139.21.2.2.8.1",
        oids=[
            "1",  # vplexDirectorVirtualVolumeName
            "2",  # vplexDirectorVirtualVolumeUuid
            "3",  # vplexDirectorVirtualVolumeOps
            "4",  # vplexDirectorVirtualVolumeRead
            "5",  # vplexDirectorVirtualVolumeWrite
            "6",  # vplexDirectorVirtualVolumeReadAvgLatency
            "7",  # vplexDirectorVirtualVolumeWriteAvgLatency
        ],
    ),
)
