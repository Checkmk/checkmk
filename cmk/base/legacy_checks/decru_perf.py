#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

from cmk.agent_based.legacy.v0_unstable import (
    check_levels,
    LegacyCheckDefinition,
    LegacyCheckResult,
)
from cmk.agent_based.v2 import DiscoveryResult, Service, SNMPTree, StringTable
from cmk.plugins.lib.decru import DETECT_DECRU

check_info = {}


def discover_decru_perf(string_table: StringTable) -> DiscoveryResult:
    perf_names = {
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

    for index, _rate in string_table:
        def_name = "unknown %s" % index
        name = perf_names.get(int(index), def_name)
        yield Service(item=f"{index}: {name}")


def check_decru_perf(
    item: str, _no_params: Mapping[str, object], info: StringTable
) -> LegacyCheckResult:
    index, _name = item.split(":", 1)
    for perf in info:
        if perf[0] == index:
            yield check_levels(
                int(perf[1]),
                "rate",
                None,
                human_readable_func=lambda x: f"{x}/s",
                infoname="Current rate",
            )
            return


def parse_decru_perf(string_table: StringTable) -> StringTable:
    return string_table


check_info["decru_perf"] = LegacyCheckDefinition(
    name="decru_perf",
    parse_function=parse_decru_perf,
    detect=DETECT_DECRU,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.12962.1.1.2.1.1",
        oids=["1", "2"],
    ),
    service_name="COUNTER %s",
    discovery_function=discover_decru_perf,
    check_function=check_decru_perf,
)
