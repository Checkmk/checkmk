#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.v2 import AgentSection, StringTable
from cmk.plugins.lib.diskstat import Section

# <<<hpux_lunstats>>>
# WWID:  0x600508b1001cf7f0d25c51941cf5e2d7
#         STATISTICS FOR LUN :/dev/rdisk/disk11
# Bytes read                                       : 841717976279
# Bytes written                                    : 430393024512
# Total I/Os processed                             : 206684834
# I/O failures                                     : 0
# Retried I/O failures                             : 0
# I/O failures due to invalid IO size              : 0
# IO failures due to misallignment or boundary      : 0
# WWID:  0x60a98000572d44745634645076556357
#         STATISTICS FOR LUN :/dev/rdisk/disk5
# Bytes read                                       : 1035897815087
# Bytes written                                    : 113475461120
# Total I/Os processed                             : 23920189
# I/O failures                                     : 24
# Retried I/O failures                             : 0
# I/O failures due to invalid IO size              : 0
# IO failures due to misallignment or boundary      : 0
# WWID:  0x60a98000572d4474563464507665446d
#         STATISTICS FOR LUN :/dev/rdisk/disk6


# Convert info to output needed for generic diskstat check
def parse_hpux_lunstats(string_table: StringTable) -> Section:
    luns: dict[str, dict[str, float]] = {}
    disk = {}
    for line in string_table:
        if len(line) != 2:
            continue

        left = line[0].strip()
        right = line[1].strip()
        if left == "STATISTICS FOR LUN":
            disk = luns.setdefault(right, {})
        elif left == "Bytes read":
            disk["read_throughput"] = float(right)
        elif left == "Bytes written":
            disk["write_throughput"] = float(right)

    return luns


agent_section_hpux_lunstats = AgentSection(
    name="hpux_lunstats",
    parse_function=parse_hpux_lunstats,
    parsed_section_name="diskstat_io",
)
