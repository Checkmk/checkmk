#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import (
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    StringTable,
)
from cmk.plugins.decru.lib import DETECT_DECRU

_PERF_NAMES = {
    1: "read (bytes/s)",  # readBytesPerSec
    2: "write (bytes/s)",  # writeBytesPerSec
    3: "operations (/s)",  # opsPerSec
    4: "CIFS read (bytes/s)",  # cifs-readBytesPerSec
    5: "CIFS write (bytes/s)",  # cifs-writeBytesPerSec
    6: "CIFS operations (/s)",  # cifs-opsPerSec
    7: "NFS read (bytes/s)",  # nfs-readBytesPerSec
    8: "NFS write (bytes/s)",  # nfs-writeBytesPerSec
    9: "NFS operations (/s)",  # nfs-opsPerSec
}


def parse_decru_perf(string_table: StringTable) -> StringTable:
    return string_table


def discover_decru_perf(section: StringTable) -> DiscoveryResult:
    for index, _rate in section:
        name = _PERF_NAMES.get(int(index), f"unknown {index}")
        yield Service(item=f"{index}: {name}")


def check_decru_perf(item: str, section: StringTable) -> CheckResult:
    index, _name = item.split(":", 1)
    for perf in section:
        if perf[0] == index:
            yield from check_levels(
                int(perf[1]),
                metric_name="rate",
                render_func=lambda x: f"{x}/s",
                label="Current rate",
            )
            return


snmp_section_decru_perf = SimpleSNMPSection(
    name="decru_perf",
    detect=DETECT_DECRU,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.12962.1.1.2.1.1",
        oids=["1", "2"],
    ),
    parse_function=parse_decru_perf,
)


check_plugin_decru_perf = CheckPlugin(
    name="decru_perf",
    service_name="COUNTER %s",
    discovery_function=discover_decru_perf,
    check_function=check_decru_perf,
)
