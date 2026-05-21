#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# <<<tsm_storagepool>>>
# tsmfarm2      Bkup      LTOBACK               1399378.64
# tsmfarm2      Arch      LTOARCHCOPY            157288.14

# <<<tsm_storagepool>>>
# default        Bkup      VP4200.GOLD                                                254776345.58^M
# default        Bkup      VP4200.TDP                                                 204386407.76^M
# default        Bkup      VP860.CM                                                   122661787.24^M
# default                  DPC.EXC.2013                                                           ^M
# default                  DPC.EXC.CM                                                             ^M
# default                  DPC.EXCDAG                                                             ^M
# default                  DPC.GOLD.ALL                                                           ^M
# default                  DPC.GOLD.UNIX                                                          ^M
# default                  DPC.GOLD.VE


from collections.abc import Mapping

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Metric,
    render,
    Result,
    Service,
    State,
    StringTable,
)

Section = Mapping[str, Mapping[str, str]]


def parse_tsm_storagepools(string_table: StringTable) -> Section:
    parsed: dict[str, dict[str, str]] = {}
    for line in string_table:
        if len(line) < 4:
            continue

        inst, stype, name, size = line[:4]
        item = name if inst == "default" else f"{inst} / {name}"
        parsed.setdefault(item, {"type": stype, "size": size.replace(",", ".")})

    return parsed


def discover_tsm_storagepools(section: Section) -> DiscoveryResult:
    for item in section:
        yield Service(item=item)


def check_tsm_storagepools(item: str, section: Section) -> CheckResult:
    if (data := section.get(item)) is None:
        return

    size = int(float(data["size"]) * 1024**2)
    yield Result(
        state=State.OK,
        summary=f"Used size: {render.disksize(size)}, Type: {data['type']}",
    )
    yield Metric("used_space", size)


agent_section_tsm_storagepools = AgentSection(
    name="tsm_storagepools",
    parse_function=parse_tsm_storagepools,
)


check_plugin_tsm_storagepools = CheckPlugin(
    name="tsm_storagepools",
    service_name="TSM Storagepool %s",
    discovery_function=discover_tsm_storagepools,
    check_function=check_tsm_storagepools,
)
