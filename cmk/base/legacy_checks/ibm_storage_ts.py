#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Sequence

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import equals, SNMPTree, StringTable

check_info = {}


def inventory_ibm_storage_ts(info):
    return [(None, None)]


def check_ibm_storage_ts(_no_item, _no_params, info):
    product, vendor, version = info[0][0]
    return 0, f"{vendor} {product}, Version {version}"


def parse_ibm_storage_ts(string_table: Sequence[StringTable]) -> Sequence[StringTable] | None:
    return string_table if any(string_table) else None


check_info["ibm_storage_ts"] = LegacyCheckDefinition(
    name="ibm_storage_ts",
    parse_function=parse_ibm_storage_ts,
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
    service_name="Info",
    discovery_function=inventory_ibm_storage_ts,
    check_function=check_ibm_storage_ts,
)


def inventory_ibm_storage_ts_status(info):
    return [(None, None)]


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


def check_ibm_storage_ts_status(_no_item, _no_params, info):
    (status,) = info[1][0]

    return (
        ibm_storage_ts_status_nagios_map[status],
        "Device Status: %s" % ibm_storage_ts_status_name_map[status],
    )


check_info["ibm_storage_ts.status"] = LegacyCheckDefinition(
    name="ibm_storage_ts_status",
    service_name="Status",
    sections=["ibm_storage_ts"],
    discovery_function=inventory_ibm_storage_ts_status,
    check_function=check_ibm_storage_ts_status,
)


def inventory_ibm_storage_ts_library(info):
    for entry, _status, _serial, _count, _fault, _severity, _descr in info[2]:
        yield entry, None


def check_ibm_storage_ts_library(item, _no_params, info):
    def worst_status(*args):
        order = [0, 1, 3, 2]
        return sorted(args, key=lambda x: order[x], reverse=True)[0]

    for entry, status, serial, count, fault, severity, descr in info[2]:
        if item == entry:
            dev_status = ibm_storage_ts_status_nagios_map[status]
            fault_status = ibm_storage_ts_fault_nagios_map[severity]
            # I have the suspicion that these status are dependent in the device anyway
            # but who knows?
            infotext = f"Device {serial}, Status: {ibm_storage_ts_status_name_map[status]}, Drives: {count}"
            if fault != "0":
                infotext += f", Fault: {descr} ({fault})"
            return worst_status(dev_status, fault_status), infotext


check_info["ibm_storage_ts.library"] = LegacyCheckDefinition(
    name="ibm_storage_ts_library",
    service_name="Library %s",
    sections=["ibm_storage_ts"],
    discovery_function=inventory_ibm_storage_ts_library,
    check_function=check_ibm_storage_ts_library,
)


def inventory_ibm_storage_ts_drive(info):
    for entry, _serial, _write_warn, _write_err, _read_warn, _read_err in info[3]:
        yield entry, None


def check_ibm_storage_ts_drive(item, params, info):
    for line in info[3]:
        if item == line[0]:
            serial = line[1]
            write_warn, write_err, read_warn, read_err = map(int, line[2:])
            yield 0, "S/N: %s" % serial
            if write_err > 0:
                yield 2, "%d hard write errors" % write_err
            if write_warn > 0:
                yield 1, "%d recovered write errors" % write_warn
            if read_err > 0:
                yield 2, "%d hard read errors" % read_err
            if read_warn > 0:
                yield 1, "%d recovered read errors" % read_warn


check_info["ibm_storage_ts.drive"] = LegacyCheckDefinition(
    name="ibm_storage_ts_drive",
    service_name="Drive %s",
    sections=["ibm_storage_ts"],
    discovery_function=inventory_ibm_storage_ts_drive,
    check_function=check_ibm_storage_ts_drive,
)
