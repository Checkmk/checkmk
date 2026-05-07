#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from collections.abc import Mapping, MutableMapping, Sequence
from typing import Any

from cmk.agent_based.v2 import (
    any_of,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    equals,
    get_value_store,
    Result,
    Service,
    SNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.plugins.lib.diskstat import check_diskstat_dict_legacy

FJDARYE_SUPPORTED_DEVICES = [
    ".1.3.6.1.4.1.211.1.21.1.150",  # fjdarye500
    ".1.3.6.1.4.1.211.1.21.1.153",  # fjdarye600
]

FjdaryeCAPortsSection = Mapping[str, Mapping[str, float | str]]


def parse_fjdarye_ca_ports(
    string_table: Sequence[StringTable],
) -> FjdaryeCAPortsSection:
    map_modes = {
        "11": "CA",
        "12": "RA",
        "13": "CARA",
        "20": "Initiator",
    }
    parsed: MutableMapping[str, MutableMapping[str, float | str]] = {}

    for ports in string_table:
        for index, mode, read_iops, write_iops, read_mb, write_mb in ports:
            mode_readable = map_modes[mode]
            port = parsed.setdefault(
                index,
                {
                    "mode": mode_readable,
                    "read_ios": float(read_iops),
                    "read_throughput": float(read_mb) * 1024**2,
                },
            )
            if mode_readable != "Initiator":
                port.update(
                    {
                        "write_ios": float(write_iops),
                        "write_throughput": float(write_mb) * 1024**2,
                    }
                )
    return parsed


snmp_section_fjdarye_ca_ports = SNMPSection(
    name="fjdarye_ca_ports",
    parse_function=parse_fjdarye_ca_ports,
    fetch=[
        SNMPTree(
            base=f"{device_oid}.5.5.2.1",
            oids=[
                # fjdaryPfCaPortRdIOPS
                #     "This shows the READ IOPS for the CA,CARA mode.
                #      The Initiator IOPS is shown for RA,Initiator mode."
                # fjdaryPfCaPortWtIOPS
                #     "This shows the WRITE IOPS for the CA,CARA mode.
                #      The Target IOPS is shown for the RA mode.
                #      This information is an invalid value for the Initiator mode."
                # fjdaryPfCaPortRdTp
                #     "This shows the amount of the READ Throughput for the CA,CARA mode.
                #      The Initiator Throughput is shown for RA,Initiator mode.
                #      The unit is MB/sec."
                # fjdaryPfCaPortWtTp
                #     "This shows the amount of the WRITE Throughput for the CA,CARA mode.
                #      The Target Throughput is shown for the RA mode.
                #      The unit is MB/sec.
                #      This information is an invalid value for the Initiator mode."
                "1",  # FJDARY-E150::fjdaryPfCaPortIndex
                "2",  # FJDARY-E150::fjdaryPfCaPortMode
                "3",  # FJDARY-E150::fjdaryPfCaPortRdIOPS
                "4",  # FJDARY-E150::fjdaryPfCaPortWtIOPS
                "5",  # FJDARY-E150::fjdaryPfCaPortRdTp
                "6",  # FJDARY-E150::fjdaryPfCaPortWtTp
            ],
        )
        for device_oid in FJDARYE_SUPPORTED_DEVICES
    ],
    detect=any_of(
        *[equals(".1.3.6.1.2.1.1.2.0", device_oid) for device_oid in FJDARYE_SUPPORTED_DEVICES]
    ),
)


def discover_fjdarye_ca_ports(
    params: Mapping[str, Sequence[str | float]],
    section: FjdaryeCAPortsSection,
) -> DiscoveryResult:
    indices = params["indices"]
    modes = params["modes"]

    for disk_index, attrs in section.items():
        if indices and disk_index not in indices:
            continue
        if modes and attrs["mode"] not in modes:
            continue
        yield Service(item=disk_index)


def check_fjdarye_ca_ports(
    item: str, params: Mapping[str, Any], section: FjdaryeCAPortsSection
) -> CheckResult:
    if (disk := section.get(item)) is None:
        return

    yield Result(state=State.OK, summary=f"Mode: {disk['mode']}")

    yield from check_diskstat_dict_legacy(
        disk={k: v for k, v in disk.items() if k != "mode" and isinstance(v, float)},
        params=params,
        value_store=get_value_store(),
        this_time=time.time(),
    )


check_plugin_fjdarye_ca_ports = CheckPlugin(
    name="fjdarye_ca_ports",
    service_name="CA Port IO %s",
    discovery_function=discover_fjdarye_ca_ports,
    check_function=check_fjdarye_ca_ports,
    discovery_ruleset_name="inventory_fujitsu_ca_ports",
    discovery_default_parameters={"indices": [], "modes": ["CA", "CARA"]},
    check_ruleset_name="diskstat",
    check_default_parameters={},
)
