#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# check_mk plug-in to monitor Fujitsu storage systems supporting FJDARY-E60.MIB or FJDARY-E100.MIB
# Copyright (c) 2012 FuH Entwicklungsgesellschaft mbH, Umkirch, Germany. All rights reserved.
# Author: Philipp Hoefflin, 2012, hoefflin+cmk@fuh-e.de

# generic data structure widely used in the FJDARY-Mibs:
# <oid>
# <oid>.1: Index
# <oid>.3: Status
# the latter can be one of the following:

from collections import Counter
from collections.abc import Mapping, MutableMapping, Sequence
from typing import Any, NamedTuple

from cmk.agent_based.v2 import (
    any_of,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    equals,
    Result,
    Service,
    SNMPSection,
    SNMPTree,
    State,
    StringTable,
)

FJDARYE_DISKS = {
    ".1.3.6.1.4.1.211.1.21.1.60": ".2.12.2.1",  # fjdarye60
    ".1.3.6.1.4.1.211.1.21.1.100": ".2.19.2.1",  # fjdarye100
    ".1.3.6.1.4.1.211.1.21.1.101": ".2.12.2.1",  # fjdarye101
    ".1.3.6.1.4.1.211.1.21.1.150": ".2.19.2.1",  # fjdarye500
    ".1.3.6.1.4.1.211.1.21.1.153": ".2.19.2.1",  # fjdarye600
}

FJDARYE_DISKS_STATUS = {
    "1": (State.OK, "available"),
    "2": (State.CRIT, "broken"),
    "3": (State.WARN, "notavailable"),
    "4": (State.WARN, "notsupported"),
    "5": (State.OK, "present"),
    "6": (State.WARN, "readying"),
    "7": (State.WARN, "recovering"),
    "64": (State.WARN, "partbroken"),
    "65": (State.WARN, "spare"),
    "66": (State.OK, "formatting"),
    "67": (State.OK, "unformated"),
    "68": (State.WARN, "notexist"),
    "69": (State.WARN, "copying"),
}


class FjdaryeDisk(NamedTuple):
    disk_index: str
    state: State
    state_description: str
    state_disk: str


SectionFjdaryeDisk = Mapping[str, FjdaryeDisk]

# fjdarye_disks ###########


def parse_fjdarye_disks(string_table: Sequence[StringTable]) -> SectionFjdaryeDisk:
    fjdarye_disks: MutableMapping[str, FjdaryeDisk] = {}
    for device in string_table:
        if not device:
            continue

        for disk_index, disk_state in device:
            state, state_description = FJDARYE_DISKS_STATUS.get(
                disk_state,
                (State.UNKNOWN, f"unknown[{disk_state}]"),
            )
            fjdarye_disks.setdefault(
                disk_index,
                FjdaryeDisk(
                    disk_index=disk_index,
                    state=state,
                    state_description=state_description,
                    state_disk=disk_state,
                ),
            )
    return fjdarye_disks


snmp_section_fjdarye_disks = SNMPSection(
    name="fjdarye_disks",
    parse_function=parse_fjdarye_disks,
    fetch=[
        SNMPTree(base=f"{device_oid}{disk_oid}", oids=["1", "3"])
        for device_oid, disk_oid in FJDARYE_DISKS.items()
    ],
    detect=any_of(*[equals(".1.3.6.1.2.1.1.2.0", device_oid) for device_oid in FJDARYE_DISKS]),
)


def discover_fjdarye_disks(section: SectionFjdaryeDisk) -> DiscoveryResult:
    for disk in section.values():
        if disk.state_disk != "3":
            yield Service(
                item=disk.disk_index, parameters={"expected_state": disk.state_description}
            )


def check_fjdarye_disks(
    item: str, params: Mapping[str, Any], section: SectionFjdaryeDisk
) -> CheckResult:
    if (fjdarye_disk := section.get(item)) is None:
        return

    if params.get("use_device_states") and fjdarye_disk.state is not State.OK:
        yield Result(
            state=fjdarye_disk.state,
            summary=f"Status: {fjdarye_disk.state_description} (using device states)",
        )
        return

    if (expected_state := params.get("expected_state")) and (
        expected_state != fjdarye_disk.state_description
    ):
        yield Result(
            state=State.CRIT,
            summary=f"Status: {fjdarye_disk.state_description} (expected: {expected_state})",
        )
        return

    yield Result(state=State.OK, summary=f"Status: {fjdarye_disk.state_description}")


check_plugin_fjdarye_disks = CheckPlugin(
    name="fjdarye_disks",
    service_name="Disk %s",
    discovery_function=discover_fjdarye_disks,
    check_function=check_fjdarye_disks,
    check_ruleset_name="raid_disk",
    check_default_parameters={},
)


# fjdarye_disks_summary ###########


def _fjdarye_disks_states_summary(section: SectionFjdaryeDisk) -> Mapping[str, int]:
    """
    >>> _fjdarye_disks_states_summary({})
    {}

    >>> _fjdarye_disks_states_summary({"0": FjdaryeDisk(disk_index="0", state=State.OK, state_description="available", state_disk="1")})
    {'available': 1}

    """
    # Note: This needs to be an actual dictionary, so that it can be (de-)serialized to and from the
    # autochecks file. Otherwise, discovery preview will show an error!
    return dict(
        Counter([disk.state_description for disk in section.values() if disk.state_disk != "3"])
    )


def discover_fjdarye_disks_summary(
    section: SectionFjdaryeDisk,
) -> DiscoveryResult:
    if current_disks_states := _fjdarye_disks_states_summary(section):
        yield Service(parameters=current_disks_states)


def _fjdarye_disks_printstates(states: Mapping[str, int]) -> str:
    """
    >>> _fjdarye_disks_printstates({"available": 4, "notavailable": 1})
    'Available: 4, Notavailable: 1'

    >>> _fjdarye_disks_printstates({})
    ''

    """
    return ", ".join([f"{s.title()}: {c}" for s, c in states.items()])


def check_fjdarye_disks_summary(
    params: Mapping[str, int | bool], section: SectionFjdaryeDisk
) -> CheckResult:
    current_disk_states = _fjdarye_disks_states_summary(section)
    current_disks_states_text = _fjdarye_disks_printstates(current_disk_states)

    if params.get("use_device_states"):
        yield Result(
            state=State.worst(*(disk.state for disk in section.values())),
            summary=f"{current_disks_states_text} (using device states)",
        )
        return

    expected_state = {k: v for k, v in params.items() if k != "use_device_states"}
    if current_disk_states == expected_state:
        yield Result(state=State.OK, summary=current_disks_states_text)
        return

    summary = (
        f"{current_disks_states_text} (expected: {_fjdarye_disks_printstates(expected_state)})"
    )
    for expected_state_name, expected_state_count in expected_state.items():
        if current_disk_states.get(expected_state_name, 0) < expected_state_count:
            yield Result(state=State.CRIT, summary=summary)
            return

    yield Result(state=State.WARN, summary=summary)


check_plugin_fjdarye_disks_summary = CheckPlugin(
    name="fjdarye_disks_summary",
    sections=["fjdarye_disks"],
    service_name="Disk summary",
    discovery_function=discover_fjdarye_disks_summary,
    check_function=check_fjdarye_disks_summary,
    check_ruleset_name="raid_summary",
    check_default_parameters={},
)
