#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"


from collections.abc import Sequence

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

Section = Sequence[StringTable] | None

ibm_storage_ts_status_name_map = {
    "1": "other",
    "2": "unknown",
    "3": "Ok",
    "4": "non-critical",
    "5": "critical",
    "6": "non-Recoverable",
}

ibm_storage_ts_status_nagios_map = {"1": 1, "2": 1, "3": 0, "4": 1, "5": 2, "6": 2}

ibm_storage_ts_fault_nagios_map = {
    "0": 0,  # no fault (undocumented)
    "1": 0,  # informational
    "2": 1,  # minor
    "3": 2,  # major
    "4": 2,  # critical
}


def parse_ibm_storage_ts(string_table: Sequence[StringTable]) -> Section:
    return string_table if any(string_table) else None


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
    product, vendor, version = section[0][0]
    yield Result(state=State.OK, summary=f"{vendor} {product}, Version {version}")


check_plugin_ibm_storage_ts = CheckPlugin(
    name="ibm_storage_ts",
    service_name="Info",
    discovery_function=discover_ibm_storage_ts,
    check_function=check_ibm_storage_ts,
)


def check_ibm_storage_ts_status(section: Section) -> CheckResult:
    if section is None:
        return
    (status,) = section[1][0]

    yield Result(
        state=State(ibm_storage_ts_status_nagios_map[status]),
        summary="Device Status: %s" % ibm_storage_ts_status_name_map[status],
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
    for entry, _status, _serial, _count, _fault, _severity, _descr in section[2]:
        yield Service(item=entry)


def check_ibm_storage_ts_library(item: str, section: Section) -> CheckResult:
    if section is None:
        return

    def worst_status(*args):
        order = [0, 1, 3, 2]
        return sorted(args, key=lambda x: order[x], reverse=True)[0]

    for entry, status, serial, count, fault, severity, descr in section[2]:
        if item == entry:
            dev_status = ibm_storage_ts_status_nagios_map[status]
            fault_status = ibm_storage_ts_fault_nagios_map[severity]
            # I have the suspicion that these status are dependent in the device anyway
            # but who knows?
            infotext = f"Device {serial}, Status: {ibm_storage_ts_status_name_map[status]}, Drives: {count}"
            if fault != "0":
                infotext += f", Fault: {descr} ({fault})"
            yield Result(
                state=State(worst_status(dev_status, fault_status)),
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
    for entry, _serial, _write_warn, _write_err, _read_warn, _read_err in section[3]:
        yield Service(item=entry)


def check_ibm_storage_ts_drive(item: str, section: Section) -> CheckResult:
    if section is None:
        return
    for line in section[3]:
        if item == line[0]:
            serial = line[1]
            write_warn, write_err, read_warn, read_err = map(int, line[2:])
            yield Result(state=State(0), summary="S/N: %s" % serial)
            if write_err > 0:
                yield Result(state=State(2), summary="%d hard write errors" % write_err)
            if write_warn > 0:
                yield Result(state=State(1), summary="%d recovered write errors" % write_warn)
            if read_err > 0:
                yield Result(state=State(2), summary="%d hard read errors" % read_err)
            if read_warn > 0:
                yield Result(state=State(1), summary="%d recovered read errors" % read_warn)


check_plugin_ibm_storage_ts_drive = CheckPlugin(
    name="ibm_storage_ts_drive",
    service_name="Drive %s",
    sections=["ibm_storage_ts"],
    discovery_function=discover_ibm_storage_ts_drive,
    check_function=check_ibm_storage_ts_drive,
)
