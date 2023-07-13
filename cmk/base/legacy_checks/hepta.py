#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Device Manual: https://www.hopf.com/downloads/manuals/8030hepta-gps_v0400_en.pdf


import struct
import time
from collections.abc import Iterable, Mapping

from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree, startswith

Section = Mapping[str, str]


def get_time(timefromdevice):
    length = len(timefromdevice)
    DateAndTime = dict({8: ">HBBBBBB", 11: ">HBBBBBBcBB"})
    if length in {8, 11}:
        timedecoded = struct.unpack(DateAndTime[length], timefromdevice.encode("latin-1"))
        if length == 8:
            timedevice = time.strftime(
                "%d-%m-%Y %H:%M:%S", time.strptime(str(timedecoded), "(%Y, %m, %d, %H, %M, %S, %f)")
            )
        else:
            offset = str(timedecoded[7]) + str(timedecoded[8]) + ":" + str(timedecoded[9])
            date = time.strftime(
                "%d-%m-%Y %H:%M:%S %Z",
                time.strptime(str(timedecoded[0:7]), "(%Y, %m, %d, %H, %M, %S, %f)"),
            )
            timedevice = str(date) + "" + str(offset)
    return timedevice


def parse_hepta(info):
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
    ) = (
        info[0] or info[1]
    )
    return {
        "devicetype": device_type,
        "serialnumber": serial_number,
        "firmwareversion": fw_version,
        "firmwaredate": get_time(fw_date),
        "version": version,
        "ntpstratum": ntp_stratum,
        "syncmoduletimesyncstate": sync_state,
        "syncmoduletimelocal": get_time(local),
    }


def discover_hepta(section: Section) -> Iterable[tuple[None, dict]]:
    if section:
        yield None, {}


def check_hepta(item, params, parsed):
    yield (
        0,
        "DeviceType %s ; SerialNumber %s ; FirmwareVersion %s ; FirmwareDate %s ; "
        "Version %s"
        % (
            parsed["devicetype"],
            parsed["serialnumber"],
            parsed["firmwareversion"],
            parsed["firmwaredate"],
            parsed["version"],
        ),
    )


check_info["hepta"] = LegacyCheckDefinition(
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


def inventory_hepta_time_sync(info):
    yield "SyncModuleTimeSyncState", {}


def check_hepta_time_sync(item, params, parsed):
    if parsed["syncmoduletimesyncstate"] == "R":
        yield (0, "Radio synchronous with high precision")
    elif parsed["syncmoduletimesyncstate"] == "r":
        yield (1, "Radio synchronous with low precision")
    elif parsed["syncmoduletimesyncstate"] == "C":
        yield (2, "Crystal")  # In manual the Crystal mode means Invalid Statum
    elif parsed["syncmoduletimesyncstate"] == "I":
        yield (2, "Invalid time and date")
    else:
        yield (3, "No data available")


check_info["hepta.syncmoduletimesyncstate"] = LegacyCheckDefinition(
    service_name="%s",
    discovery_function=inventory_hepta_time_sync,
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
def inventory_hepta_ntpsysstratum(info):
    yield "ntpSysStratum", {}


def check_hepta_ntpsysstratum(item, params, parsed):
    if parsed["ntpstratum"] == "1":
        yield (0, "Stratum 1, Primary Reference ")
    elif parsed["ntpstratum"] == "16":
        yield (2, "Stratum Invalid")
    elif parsed["ntpstratum"] == "0":
        yield (3, "Stratum Unknown")
    else:
        yield (1, "Stratum is using secondary reference(via NTP)")


check_info["hepta.ntpsysstratum"] = LegacyCheckDefinition(
    service_name="%s",
    discovery_function=inventory_hepta_ntpsysstratum,
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
def inventory_hepta_syncmoduletimelocal(info):
    yield "SyncModuleTimeLocal", {}


def check_hepta_syncmoduletimelocal(item, params, parsed):
    yield (0, "Module Time: %s " % parsed["syncmoduletimelocal"])


check_info["hepta.syncmoduletimelocal"] = LegacyCheckDefinition(
    service_name="%s",
    discovery_function=inventory_hepta_syncmoduletimelocal,
    check_function=check_hepta_syncmoduletimelocal,
)
