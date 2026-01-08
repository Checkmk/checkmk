#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"


from collections.abc import Sequence
from typing import TypedDict

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    OIDEnd,
    Result,
    Service,
    SNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.plugins.stormshield.lib import DETECT_STORMSHIELD


class DiskInfo(TypedDict):
    clusterindex: str
    index: str
    name: str
    selftest: str
    israid: str
    raidstatus: str
    position: str


Section = Sequence[DiskInfo]


def parse_stormshield_disk(string_table: Sequence[StringTable]) -> Section:
    standalone, cluster = string_table

    parsed = []

    if not cluster and not standalone:
        return []

    if cluster != []:
        for item in cluster:
            index = item[0].split(".")[0]
            parsed.append(
                DiskInfo(
                    clusterindex=index,
                    index=item[1],
                    name=item[2],
                    selftest=item[3],
                    israid=item[4],
                    raidstatus=item[5],
                    position=item[6],
                )
            )
        return parsed

    parsed.append(
        DiskInfo(
            clusterindex="0",
            index=standalone[0][0],
            name=standalone[0][1],
            selftest=standalone[0][2],
            israid=standalone[0][3],
            raidstatus=standalone[0][4],
            position=standalone[0][5],
        )
    )
    return parsed


def discover_stormshield_disk(section: Section) -> DiscoveryResult:
    for disk in section:
        yield Service(item=disk["clusterindex"])


def check_stormshield_disk(item: str, section: Section) -> CheckResult:
    for disk in section:
        if item == disk["clusterindex"]:
            infotext = f"Device Index {disk['index']}, Selftest: {disk['selftest']}, Device Mount Point Name: {disk['name']}"
            if disk["selftest"] != "PASSED":
                status = State.WARN
            else:
                status = State.OK
            if disk["israid"] != "0":
                infotext = (
                    infotext
                    + f", Raid active, Raid Status {disk['raidstatus']}, Disk Position {disk['position']}"
                )
            yield Result(state=status, summary=infotext)


snmp_section_stormshield_disk = SNMPSection(
    name="stormshield_disk",
    detect=DETECT_STORMSHIELD,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.11256.1.11.11.1",
            oids=[OIDEnd(), "1", "2", "3", "4", "5", "6"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.11256.1.10.5.1",
            oids=[OIDEnd(), "1", "2", "3", "4", "5", "6"],
        ),
    ],
    parse_function=parse_stormshield_disk,
)


check_plugin_stormshield_disk = CheckPlugin(
    name="stormshield_disk",
    service_name="Disk %s",
    discovery_function=discover_stormshield_disk,
    check_function=check_stormshield_disk,
)
