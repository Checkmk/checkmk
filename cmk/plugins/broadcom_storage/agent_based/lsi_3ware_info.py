#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Possible output:
# # tw_cli show
#
# Ctl   Model        (V)Ports  Drives   Units   NotOpt  RRate   VRate  BBU
# ------------------------------------------------------------------------
# c0    9550SXU-4LP  4         3        2       0       1       1      -
# c1    9550SXU-8LP  8         7        3       0       1       1      -
#
# tw_cli version: 2.01.09.004

# Another version produces this output:
# <<<3ware_info>>>
# /c0 Model = 9550SXU-8LP
# /c0 Firmware Version = FE9X 3.08.00.029
# /c0 Serial Number = L320809A6450122
# Port   Status           Unit   Size        Blocks        Serial

# This version of the check currently only handles output of the first type


from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    State,
    StringTable,
)


def discover_3ware_info(section: StringTable) -> DiscoveryResult:
    for line in section:
        if len(line) == 8:
            yield Service(item=line[0])


def check_3ware_info(item: str, section: StringTable) -> CheckResult:
    infotext = ""
    for line in section:
        line_text = " ".join(line[1:])
        infotext = infotext + line_text + ";"
    yield Result(state=State.OK, summary=infotext)


def parse_3ware_info(string_table: StringTable) -> StringTable:
    return string_table


agent_section_3ware_info = AgentSection(
    name="3ware_info",
    parse_function=parse_3ware_info,
)


check_plugin_3ware_info = CheckPlugin(
    name="3ware_info",
    service_name="RAID 3ware controller %s",
    discovery_function=discover_3ware_info,
    check_function=check_3ware_info,
)
