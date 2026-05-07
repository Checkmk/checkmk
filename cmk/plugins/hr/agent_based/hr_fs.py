#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, MutableMapping, Sequence
from typing import Any

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_value_store,
    RuleSetType,
    SimpleSNMPSection,
    SNMPTree,
    StringTable,
)
from cmk.plugins.lib.df import (
    df_check_filesystem_list,
    df_discovery,
    EXCLUDED_MOUNTPOINTS,
    FILESYSTEM_DEFAULT_PARAMS,
    FSBlock,
)
from cmk.plugins.lib.ucd_hr_detection import HR

# .1.3.6.1.2.1.25.2.3.1.2.1 .1.3.6.1.2.1.25.2.1.2 --> HOST-RESOURCES-MIB::hrStorageType.1
# .1.3.6.1.2.1.25.2.3.1.2.3 .1.3.6.1.2.1.25.2.1.3 --> HOST-RESOURCES-MIB::hrStorageType.3
# .1.3.6.1.2.1.25.2.3.1.3.1 Physical memory --> HOST-RESOURCES-MIB::hrStorageDescr.1
# .1.3.6.1.2.1.25.2.3.1.3.3 Virtual memory --> HOST-RESOURCES-MIB::hrStorageDescr.3
# .1.3.6.1.2.1.25.2.3.1.4.1 1024 --> HOST-RESOURCES-MIB::hrStorageAllocationUnits.1
# .1.3.6.1.2.1.25.2.3.1.4.3 1024 --> HOST-RESOURCES-MIB::hrStorageAllocationUnits.3
# .1.3.6.1.2.1.25.2.3.1.5.1 8122520 --> HOST-RESOURCES-MIB::hrStorageSize.1
# .1.3.6.1.2.1.25.2.3.1.5.3 21230740 --> HOST-RESOURCES-MIB::hrStorageSize.3
# .1.3.6.1.2.1.25.2.3.1.6.1 7749124 --> HOST-RESOURCES-MIB::hrStorageUsed.1
# .1.3.6.1.2.1.25.2.3.1.6.3 7749124 --> HOST-RESOURCES-MIB::hrStorageUsed.3


Section = Sequence[FSBlock]


def _to_mb(raw: str, unit_size: int) -> float:
    unscaled = int(raw)
    if unscaled < 0:
        unscaled += 2**32
    return unscaled * unit_size / 1048576.0


def parse_hr_fs(string_table: StringTable) -> Section:
    section = []
    for hrtype, hrdescr, hrunits, hrsize, hrused in string_table:
        # NOTE: These types are defined in the HR-TYPES-MIB.
        #       .1.3.6.1.2.1.25.2.1 +
        #                           +-> .4 "hrStorageFixedDisk"
        if hrtype not in {
            ".1.3.6.1.2.1.25.2.1.4",
            # This strange value below is needed for VCenter Appliances
            ".1.3.6.1.2.1.25.2.3.1.2.4",
        }:
            continue

        try:
            unit_size = int(hrunits)
            size_mb = _to_mb(hrsize, unit_size)
            used_mb = _to_mb(hrused, unit_size)
        except ValueError:
            continue

        section.append((fix_hr_fs_mountpoint(hrdescr), size_mb, size_mb - used_mb, 0))

    return section


snmp_section_hr_fs = SimpleSNMPSection(
    name="hr_fs",
    parse_function=parse_hr_fs,
    fetch=SNMPTree(
        base=".1.3.6.1.2.1.25.2.3.1",
        oids=[
            "2",  # hrStorageType
            "3",  # hrStorageDescr
            "4",  # hrStorageAllocationUnits
            "5",  # hrStorageSize
            "6",  # hrStorageUsed
        ],
    ),
    detect=HR,
)


# Juniper devices put information about the device into the
# field where we expect the mount point. Ugly. Remove that crap.
def fix_hr_fs_mountpoint(mp: str) -> str:
    mp = mp.replace("\\", "/")
    if "mounted on:" in mp:
        return mp.rsplit(":", 1)[-1].strip()
    if "Label:" in mp:
        pos = mp.find("Label:")
        return mp[:pos].rstrip()
    return mp


def discover_hr_fs(params: Sequence[Mapping[str, Any]], section: Section) -> DiscoveryResult:
    yield from df_discovery(
        params,
        [
            descr
            for descr, size, *_unused in section
            if descr not in EXCLUDED_MOUNTPOINTS and size != 0
        ],
    )


def check_hr_fs(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:
    yield from check_hr_fs_testable(item, params, section, value_store=get_value_store())


def check_hr_fs_testable(
    item: str, params: Mapping[str, Any], section: Section, value_store: MutableMapping[str, object]
) -> CheckResult:
    yield from df_check_filesystem_list(
        value_store=value_store,
        item=item,
        params=params,
        fslist_blocks=section,
    )


check_plugin_hr_fs = CheckPlugin(
    name="hr_fs",
    service_name="Filesystem %s",
    discovery_function=discover_hr_fs,
    discovery_default_parameters={"groups": []},
    discovery_ruleset_name="filesystem_groups",
    discovery_ruleset_type=RuleSetType.ALL,
    check_function=check_hr_fs,
    check_ruleset_name="filesystem",
    check_default_parameters=FILESYSTEM_DEFAULT_PARAMS,
)
