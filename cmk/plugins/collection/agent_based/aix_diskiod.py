#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# <<<aix_diskiod>>>
# hdisk3 0.9 237.0 9.1 1337054478 1628926522
# hdisk5 0.9 237.1 8.8 1333731705 1633897629
# hdisk7 0.9 256.2 10.1 1537047014 1669194644
# hdisk6 0.9 236.6 9.1 1334163361 1626627852
# hdisk2 0.9 237.6 9.1 1334458233 1639383130
# hdisk9 0.8 239.4 9.3 1337740029 1658392394
# hdisk8 0.9 238.3 8.9 1332262996 1649741796
# hdisk4 0.9 237.4 8.8 1332426157 1638419364
# hdisk13 0.5 238.1 8.3 394246756 2585031872
# hdisk11 0.5 238.3 8.3 397601918 2584807275

# Columns means:
# 1. device
# 2. % tm_act
# 3. Kbps
# 4. tps
# 5. Kb_read    -> Kilobytes read since system boot
# 6. Kb_wrtn    -> Kilobytes written since system boot


from cmk.agent_based.v2 import AgentSection, StringTable
from cmk.plugins.lib import diskstat


def parse_aix_diskiod(string_table: StringTable) -> diskstat.Section | None:
    section = {}

    for device, _tm_act, _kbps, _tps, kb_read, kb_written in string_table:
        try:
            section[device] = {
                "read_throughput": int(kb_read) * 1024,
                "write_throughput": int(kb_written) * 1024,
            }
        except ValueError:
            continue

    return section if section else None


agent_section_aix_diskiod = AgentSection(
    name="aix_diskiod",
    parse_function=parse_aix_diskiod,
    parsed_section_name="diskstat_io",
)
