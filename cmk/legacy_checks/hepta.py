#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Device Manual: https://www.hopf.com/downloads/manuals/8030hepta-gps_v0400_en.pdf


import struct
import time
from collections.abc import Mapping, Sequence

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    SNMPSection,
    SNMPTree,
    startswith,
    State,
    StringTable,
)

Section = Mapping[str, str]


def _get_time(timefromdevice: str) -> str:
    length = len(timefromdevice)
    date_and_time = {8: ">HBBBBBB", 11: ">HBBBBBBcBB"}
    if length == 8:
        timedecoded = struct.unpack(date_and_time[length], timefromdevice.encode("latin-1"))
        return time.strftime(
            "%d-%m-%Y %H:%M:%S", time.strptime(str(timedecoded), "(%Y, %m, %d, %H, %M, %S, %f)")
        )
    if length == 11:
        timedecoded = struct.unpack(date_and_time[length], timefromdevice.encode("latin-1"))
        offset = str(timedecoded[7]) + str(timedecoded[8]) + ":" + str(timedecoded[9])
        date = time.strftime(
            "%d-%m-%Y %H:%M:%S %Z",
            time.strptime(str(timedecoded[0:7]), "(%Y, %m, %d, %H, %M, %S, %f)"),
        )
        return f"{date}{offset}"
    return ""


def parse_hepta(string_table: Sequence[StringTable]) -> Section | None:
    if not any(string_table):
        return None
    (
        (
            device_type,
            serial_number,
            fw_version,
            fw_date,
            version,
            ntp_stratum,
            local,
            sync_state,
        ),
    ) = string_table[0] or string_table[1]
    return {
        "devicetype": device_type,
        "serialnumber": serial_number,
        "firmwareversion": fw_version,
        "firmwaredate": _get_time(fw_date),
        "version": version,
        "ntpstratum": ntp_stratum,
        "syncmoduletimesyncstate": sync_state,
        "syncmoduletimelocal": _get_time(local),
    }


def discover_hepta(section: Section) -> DiscoveryResult:
    if section:
        yield Service()


def check_hepta(section: Section) -> CheckResult:
    yield Result(
        state=State.OK,
        summary=(
            f"DeviceType {section['devicetype']} ; "
            f"SerialNumber {section['serialnumber']} ; "
            f"FirmwareVersion {section['firmwareversion']} ; "
            f"FirmwareDate {section['firmwaredate']} ; "
            f"Version {section['version']}"
        ),
    )


snmp_section_hepta = SNMPSection(
    name="hepta",
    detect=startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.12527"),
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.12527.29",
            oids=["1.1.0", "1.3.0", "1.4.0", "1.5.0", "1.6.0", "2.1.2.0", "3.1.0", "3.5.0"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.12527.40",
            oids=["1.1.0", "1.3.0", "1.4.0", "1.5.0", "1.6.0", "2.1.2.0", "3.1.0", "3.5.0"],
        ),
    ],
    parse_function=parse_hepta,
)


check_plugin_hepta = CheckPlugin(
    name="hepta",
    service_name="HPF Info",
    discovery_function=discover_hepta,
    check_function=check_hepta,
)

# .
#   .--SyncModuleTimeSyncState---------------------------------------------.
#   |    ____                   __  __           _       _     _____ _     |
#   |   / ___| _   _ _ __   ___|  \/  | ___   __| |_   _| | __|_   _(_)    |
#   |   \___ \| | | | '_ \ / __| |\/| |/ _ \ / _` | | | | |/ _ \| | | |    |
#   |    ___) | |_| | | | | (__| |  | | (_) | (_| | |_| | |  __/| | | |    |
#   |   |____/ \__, |_| |_|\___|_|  |_|\___/ \__,_|\__,_|_|\___||_| |_|    |
#   |          |___/                                                       |
#   |                   ____                   ____  _        _            |
#   |    _ __ ___   ___/ ___| _   _ _ __   ___/ ___|| |_ __ _| |_ ___      |
#   |   | '_ ` _ \ / _ \___ \| | | | '_ \ / __\___ \| __/ _` | __/ _ \     |
#   |   | | | | | |  __/___) | |_| | | | | (__ ___) | || (_| | ||  __/     |
#   |   |_| |_| |_|\___|____/ \__, |_| |_|\___|____/ \__\__,_|\__\___|     |
#   |                         |___/                                        |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'


def discover_hepta_time_sync(section: Section) -> DiscoveryResult:
    yield Service(item="SyncModuleTimeSyncState")


def check_hepta_time_sync(item: str, section: Section) -> CheckResult:
    if section["syncmoduletimesyncstate"] == "R":
        yield Result(state=State.OK, summary="Radio synchronous with high precision")
    elif section["syncmoduletimesyncstate"] == "r":
        yield Result(state=State.WARN, summary="Radio synchronous with low precision")
    elif section["syncmoduletimesyncstate"] == "C":
        yield Result(
            state=State.CRIT, summary="Crystal"
        )  # In manual the Crystal mode means Invalid Statum
    elif section["syncmoduletimesyncstate"] == "I":
        yield Result(state=State.CRIT, summary="Invalid time and date")
    else:
        yield Result(state=State.UNKNOWN, summary="No data available")


check_plugin_hepta_syncmoduletimesyncstate = CheckPlugin(
    name="hepta_syncmoduletimesyncstate",
    service_name="%s",
    sections=["hepta"],
    discovery_function=discover_hepta_time_sync,
    check_function=check_hepta_time_sync,
)


# .
#   .--ntpSysStratum-------------------------------------------------------.
#   |          _        ____            ____  _             _              |
#   |    _ __ | |_ _ __/ ___| _   _ ___/ ___|| |_ _ __ __ _| |_ _   _      |
#   |   | '_ \| __| '_ \___ \| | | / __\___ \| __| '__/ _` | __| | | |     |
#   |   | | | | |_| |_) |__) | |_| \__ \___) | |_| | | (_| | |_| |_| |     |
#   |   |_| |_|\__| .__/____/ \__, |___/____/ \__|_|  \__,_|\__|\__,_|     |
#   |             |_|         |___/                                        |
#   |                                                                      |
#   |                              _ __ ___                                |
#   |                             | '_ ` _ \                               |
#   |                             | | | | | |                              |
#   |                             |_| |_| |_|                              |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'
def discover_hepta_ntpsysstratum(section: Section) -> DiscoveryResult:
    yield Service(item="ntpSysStratum")


def check_hepta_ntpsysstratum(item: str, section: Section) -> CheckResult:
    if section["ntpstratum"] == "1":
        yield Result(state=State.OK, summary="Stratum 1, Primary Reference ")
    elif section["ntpstratum"] == "16":
        yield Result(state=State.CRIT, summary="Stratum Invalid")
    elif section["ntpstratum"] == "0":
        yield Result(state=State.UNKNOWN, summary="Stratum Unknown")
    else:
        yield Result(state=State.WARN, summary="Stratum is using secondary reference(via NTP)")


check_plugin_hepta_ntpsysstratum = CheckPlugin(
    name="hepta_ntpsysstratum",
    service_name="%s",
    sections=["hepta"],
    discovery_function=discover_hepta_ntpsysstratum,
    check_function=check_hepta_ntpsysstratum,
)


# .
#   .--SyncModuleTimeLocal-------------------------------------------------.
#   |    ____                   __  __           _       _     _____ _     |
#   |   / ___| _   _ _ __   ___|  \/  | ___   __| |_   _| | __|_   _(_)    |
#   |   \___ \| | | | '_ \ / __| |\/| |/ _ \ / _` | | | | |/ _ \| | | |    |
#   |    ___) | |_| | | | | (__| |  | | (_) | (_| | |_| | |  __/| | | |    |
#   |   |____/ \__, |_| |_|\___|_|  |_|\___/ \__,_|\__,_|_|\___||_| |_|    |
#   |          |___/                                                       |
#   |                               _                    _                 |
#   |                _ __ ___   ___| |    ___   ___ __ _| |                |
#   |               | '_ ` _ \ / _ \ |   / _ \ / __/ _` | |                |
#   |               | | | | | |  __/ |__| (_) | (_| (_| | |                |
#   |               |_| |_| |_|\___|_____\___/ \___\__,_|_|                |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'
def discover_hepta_syncmoduletimelocal(section: Section) -> DiscoveryResult:
    yield Service(item="SyncModuleTimeLocal")


def check_hepta_syncmoduletimelocal(item: str, section: Section) -> CheckResult:
    yield Result(state=State.OK, summary=f"Module Time: {section['syncmoduletimelocal']}")


check_plugin_hepta_syncmoduletimelocal = CheckPlugin(
    name="hepta_syncmoduletimelocal",
    service_name="%s",
    sections=["hepta"],
    discovery_function=discover_hepta_syncmoduletimelocal,
    check_function=check_hepta_syncmoduletimelocal,
)
