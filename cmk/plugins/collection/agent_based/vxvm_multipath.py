#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Mapping, MutableMapping
from typing import NamedTuple

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

# Example output:
# <<<vxvm_multipath>>>
# sda                  ENABLED      OTHER_DISKS  1      1     0     other_disks
# LIO-Sechs_0          ENABLED      aluadisk     1      1     0     LIO-Sechs
# LIO-Sechs_1          ENABLED      aluadisk     1      1     0     LIO-Sechs
# LIO-Sechs_2          ENABLED      aluadisk     1      1     0     LIO-Sechs
#


class VXVMMultipathDisk(NamedTuple):
    name: str
    status: str
    paths: float
    active_paths: float
    inactive_paths: float
    enclosure: str


VXVMMultipathSection = Mapping[str, VXVMMultipathDisk]


def parse_vxvm_multipath(string_table: StringTable) -> VXVMMultipathSection:
    vxvm_multipath_disks: MutableMapping[str, VXVMMultipathDisk] = {}

    for line in string_table:
        try:
            name, status, _enc_type, paths, active_paths, inactive_paths, enclosure = line
        except ValueError:
            continue

        vxvm_multipath_disks[name] = VXVMMultipathDisk(
            name=name,
            status=status,
            paths=float(paths),
            active_paths=float(active_paths),
            inactive_paths=float(inactive_paths),
            enclosure=enclosure,
        )

    return vxvm_multipath_disks


agent_section_vxvm_multipath = AgentSection(
    name="vxvm_multipath",
    parse_function=parse_vxvm_multipath,
)


def discover_vxvm_multipath(section: VXVMMultipathSection) -> DiscoveryResult:
    for disk in section:
        yield Service(item=disk)


def check_vxvm_multipath(
    item: str,
    section: VXVMMultipathSection,
) -> CheckResult:
    if (disk := section.get(item)) is None:
        return

    state = State.OK
    if disk.active_paths != disk.paths and disk.active_paths >= disk.paths / 2:
        state = State.WARN
    elif disk.inactive_paths > 0 and disk.inactive_paths > disk.paths / 2:
        state = State.CRIT

    yield Result(
        state=state,
        summary=f"Status: {disk.status}, ({disk.active_paths:.0f}/{disk.paths:.0f}) Paths to enclosure {disk.enclosure} enabled",
    )


check_plugin_vxvm_multipath = CheckPlugin(
    name="vxvm_multipath",
    service_name="Multipath %s",
    discovery_function=discover_vxvm_multipath,
    check_function=check_vxvm_multipath,
)
