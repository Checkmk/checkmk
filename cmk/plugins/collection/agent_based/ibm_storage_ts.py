#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Sequence
from typing import NamedTuple

from cmk.agent_based.v2 import (
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


class Info(NamedTuple):
    product: str
    vendor: str
    version: str


class Library(NamedTuple):
    entry: str
    status: str
    serial: str
    drive_count: str
    fault: str
    severity: str
    descr: str


class Drive(NamedTuple):
    entry: str
    serial: str
    write_warn: str
    write_err: str
    read_warn: str
    read_err: str


class Collection(NamedTuple):
    info: Info
    status: str
    libraries: list[Library]
    drives: list[Drive]


Section = Collection | None

IBM_STORAGE_TS_STATUS_NAME_MAP = {
    "1": "other",
    "2": "unknown",
    "3": "Ok",
    "4": "non-critical",
    "5": "critical",
    "6": "non-Recoverable",
}

IBM_STORAGE_TS_STATUS_NAGIOS_MAP = {
    "1": State.WARN,
    "2": State.WARN,
    "3": State.OK,
    "4": State.WARN,
    "5": State.CRIT,
    "6": State.CRIT,
}

IBM_STORAGE_TS_FAULT_NAGIOS_MAP = {
    "0": State.OK,  # no fault (undocumented)
    "1": State.OK,  # informational
    "2": State.WARN,  # minor
    "3": State.CRIT,  # major
    "4": State.CRIT,  # critical
}


def parse_ibm_storage_ts(string_table: Sequence[StringTable]) -> Section:
    if not any(string_table):
        return None

    info_raw, status_raw, library_raw, drives_raw = string_table

    return Collection(
        Info(*info_raw[0]),
        status_raw[0][0],
        [Library(*library) for library in library_raw],
        [Drive(*drive) for drive in drives_raw],
    )


snmp_section_ibm_storage_ts = SNMPSection(
    name="ibm_storage_ts",
    detect=equals(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.2.6.210"),
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.2.6.210.1",
            oids=["1", "3", "4"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.2.6.210.2",
            oids=["1"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.2.6.210.3.1.1",
            oids=["1", "2", "10", "11", "22", "23", "24"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.2.6.210.3.2.1",
            oids=["1", "10", "15", "16", "17", "18"],
        ),
    ],
    parse_function=parse_ibm_storage_ts,
)


def discover_ibm_storage_ts(section: Section) -> DiscoveryResult:
    if section is not None:
        yield Service()


def check_ibm_storage_ts(section: Section) -> CheckResult:
    if section is None:
        return
    yield Result(
        state=State.OK,
        summary=f"{section.info.vendor} {section.info.product}, Version {section.info.version}",
    )


check_plugin_ibm_storage_ts = CheckPlugin(
    name="ibm_storage_ts",
    service_name="Info",
    discovery_function=discover_ibm_storage_ts,
    check_function=check_ibm_storage_ts,
)


def check_ibm_storage_ts_status(section: Section) -> CheckResult:
    if section is None:
        return

    yield Result(
        state=State(IBM_STORAGE_TS_STATUS_NAGIOS_MAP[section.status]),
        summary="Device Status: %s" % IBM_STORAGE_TS_STATUS_NAME_MAP[section.status],
    )


check_plugin_ibm_storage_ts_status = CheckPlugin(
    name="ibm_storage_ts_status",
    service_name="Status",
    sections=["ibm_storage_ts"],
    discovery_function=discover_ibm_storage_ts,
    check_function=check_ibm_storage_ts_status,
)


def discover_ibm_storage_ts_library(section: Section) -> DiscoveryResult:
    if section is None:
        return
    for library in section.libraries:
        yield Service(item=library.entry)


def check_ibm_storage_ts_library(item: str, section: Section) -> CheckResult:
    if section is None:
        return

    for library in section.libraries:
        if item == library.entry:
            state_device = IBM_STORAGE_TS_STATUS_NAGIOS_MAP[library.status]
            fault_status = IBM_STORAGE_TS_FAULT_NAGIOS_MAP[library.severity]
            # I have the suspicion that these status are dependent in the device anyway
            # but who knows?
            infotext = f"Device {library.serial}, Status: {IBM_STORAGE_TS_STATUS_NAME_MAP[library.status]}, Drives: {library.drive_count}"
            if library.fault != "0":
                infotext += f", Fault: {library.descr} ({library.fault})"
            yield Result(
                state=State.worst(state_device, fault_status),
                summary=infotext,
            )


check_plugin_ibm_storage_ts_library = CheckPlugin(
    name="ibm_storage_ts_library",
    service_name="Library %s",
    sections=["ibm_storage_ts"],
    discovery_function=discover_ibm_storage_ts_library,
    check_function=check_ibm_storage_ts_library,
)


def discover_ibm_storage_ts_drive(section: Section) -> DiscoveryResult:
    if section is None:
        return
    for drive in section.drives:
        yield Service(item=drive.entry)


def _check_drive(counter: str, state: State, summary: str) -> CheckResult:
    if counter == "":
        yield Result(state=State.UNKNOWN, summary=summary.format("got empty string for"))
        return
    if counter != "0":
        yield Result(state=state, summary=summary.format(counter))


def check_ibm_storage_ts_drive(item: str, section: Section) -> CheckResult:
    if section is None:
        return
    for drive in section.drives:
        if item == drive.entry:
            yield Result(state=State.OK, summary=f"S/N: {drive.serial}")
            yield from _check_drive(drive.write_err, State.CRIT, "{} hard write errors")
            yield from _check_drive(drive.write_warn, State.WARN, "{} recovered write errors")
            yield from _check_drive(drive.read_err, State.CRIT, "{} hard read errors")
            yield from _check_drive(drive.read_warn, State.WARN, "{} recovered read errors")


check_plugin_ibm_storage_ts_drive = CheckPlugin(
    name="ibm_storage_ts_drive",
    service_name="Drive %s",
    sections=["ibm_storage_ts"],
    discovery_function=discover_ibm_storage_ts_drive,
    check_function=check_ibm_storage_ts_drive,
)
