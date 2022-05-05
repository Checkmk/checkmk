#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
# type: ignore[list-item,import,assignment,misc,operator,attr-defined]  # TODO: see which are needed in this file

import re

from cmk.base.check_api import savefloat, saveint

from .temperature import check_temperature

#   .--CPU-----------------------------------------------------------------.
#   |                           ____ ____  _   _                           |
#   |                          / ___|  _ \| | | |                          |
#   |                         | |   | |_) | | | |                          |
#   |                         | |___|  __/| |_| |                          |
#   |                          \____|_|    \___/                           |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def inventory_dell_poweredge_cpu(info):
    for _chassisIndex, _Index, StateSettings, _Status, LocationName in info[0]:
        if LocationName != "" and StateSettings != "1":
            yield LocationName, None


def check_dell_poweredge_cpu(item, _no_params, info):
    for chassisIndex, Index, _StateSettings, Status, LocationName in info[0]:
        if item == LocationName:
            BrandName = None
            for line in info[1]:
                if line[0] == chassisIndex and line[1] == Index:
                    BrandName = line[2]

            state_table = {
                "1": ("other", 1),
                "2": ("unknown", 1),
                "3": ("", 0),
                "4": ("non-critical", 1),
                "5": ("critical", 2),
                "6": ("non-recoverable", 2),
            }

            infotext, state = state_table.get(Status, ("unknown state", 2))
            if BrandName:
                infotext += " " + BrandName

            return state, infotext
    return None


# .
#   .--memory--------------------------------------------------------------.
#   |                                                                      |
#   |              _ __ ___   ___ _ __ ___   ___  _ __ _   _               |
#   |             | '_ ` _ \ / _ \ '_ ` _ \ / _ \| '__| | | |              |
#   |             | | | | | |  __/ | | | | | (_) | |  | |_| |              |
#   |             |_| |_| |_|\___|_| |_| |_|\___/|_|   \__, |              |
#   |                                                  |___/               |
#   '----------------------------------------------------------------------'


def inventory_dell_poweredge_mem(info):
    inventory = []
    for line in info:
        location = line[1]
        if location != "":
            inventory.append((location, None))
    return inventory


def check_dell_poweredge_mem(item, _no_params, info):
    di = {}
    for status, location, size, di["Speed"], di["MFR"], di["P/N"], di["S/N"] in info:

        di["Size"] = str(int((saveint(size) / 1024.0) / 1024.0)) + "GB"
        if item == location:
            state_table = {
                "1": ("other", 1),
                "2": ("unknown", 1),
                "3": ("", 0),
                "4": ("nonCritical", 1),
                "5": ("Critical", 2),
                "6": ("NonRecoverable", 2),
            }
            infotext, state = state_table.get(status, ("unknown state", 2))
            for parameter, value in di.items():
                infotext += ", %s: %s" % (parameter, value)

            infotext = re.sub("^, ", "", infotext)

            return state, infotext

    return 3, "Memory Device not found"


# .
#   .--netdev--------------------------------------------------------------.
#   |                              _      _                                |
#   |                   _ __   ___| |_ __| | _____   __                    |
#   |                  | '_ \ / _ \ __/ _` |/ _ \ \ / /                    |
#   |                  | | | |  __/ || (_| |  __/\ V /                     |
#   |                  |_| |_|\___|\__\__,_|\___| \_/                      |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def inventory_dell_poweredge_netdev(info):
    inventory = []
    for line in info:
        if line[1] != "2" and line[4] != "":
            inventory.append((line[4], None))
    return inventory


def check_dell_poweredge_netdev(item, _no_params, info):
    di = {}
    for status, connection_status, di["Product"], cur_mac, fqdd in info:
        if item == fqdd:
            di["MAC"] = "-".join(["%02X" % ord(c) for c in cur_mac]).strip()
            state_table = {
                "1": ("other,", 1),
                "2": ("unknown,", 1),
                "3": ("", 0),
                "4": ("nonCritical,", 1),
                "5": ("Critical,", 2),
                "6": ("NonRecoverable,", 2),
            }
            connection_table = {
                "1": ("connected, ", 0),
                "2": ("disconnected, ", 2),
                "3": ("driverBad, ", 2),
                "4": ("driverDisabled, ", 2),
                "10": ("hardwareInitializing, ", 2),
                "11": ("hardwareResetting, ", 2),
                "12": ("hardwareClosing, ", 2),
                "13": ("hardwareNotReady, ", 2),
            }
            dev_state_txt, dev_state = state_table.get(status, ("unknown device status,", 2))
            conn_state_txt, conn_state = connection_table.get(connection_status, ("", 0))
            state = max(dev_state, conn_state)
            infotext = "%s %s" % (dev_state_txt, conn_state_txt)
            for parameter, value in di.items():
                infotext += "%s: %s, " % (parameter, value)
            infotext = re.sub(", $", "", infotext)

            return state, infotext

    return 3, "network device not found"


# .
#   .--PCI-----------------------------------------------------------------.
#   |                           ____   ____ ___                            |
#   |                          |  _ \ / ___|_ _|                           |
#   |                          | |_) | |    | |                            |
#   |                          |  __/| |___ | |                            |
#   |                          |_|    \____|___|                           |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def inventory_dell_poweredge_pci(info):
    inventory = []
    for line in info:
        fqdd = line[4]
        if fqdd != "":
            inventory.append((fqdd, None))
    return inventory


def check_dell_poweredge_pci(item, _no_params, info):
    di = {}
    for status, di["BusWidth"], di["MFR"], di["Desc."], fqdd in info:

        if item == fqdd:
            state_table = {
                "1": ("other", 1),
                "2": ("unknown", 1),
                "3": ("", 0),
                "4": ("nonCritical", 1),
                "5": ("Critical", 2),
                "6": ("NonRecoverable", 2),
            }
            infotext, state = state_table.get(status, ("unknown state", 2))
            for parameter, value in di.items():
                infotext += ", %s: %s" % (parameter, value)

            infotext = re.sub("^, ", "", infotext)

            return state, infotext

    return 3, "Memory Device not found"


# .
#   .--status--------------------------------------------------------------.
#   |                         _        _                                   |
#   |                     ___| |_ __ _| |_ _   _ ___                       |
#   |                    / __| __/ _` | __| | | / __|                      |
#   |                    \__ \ || (_| | |_| |_| \__ \                      |
#   |                    |___/\__\__,_|\__|\__,_|___/                      |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def inventory_dell_poweredge_status(info):
    if info:
        return [(None, None)]
    return []


def check_dell_poweredge_status(item, _no_params, info):
    di = {}
    (
        di["racURL"],
        di["Chassis"],
        di["Slot"],
        di["Model"],
        status,
        di["ServiceTag"],
        di["ExpressServiceCode"],
    ) = info[0]

    state_table = {
        "1": ("other, ", 1),
        "2": ("unknown, ", 1),
        "3": ("", 0),
        "4": ("nonCritical, ", 1),
        "5": ("Critical, ", 2),
        "6": ("NonRecoverable, ", 2),
    }
    infotext, state = state_table.get(status, "2")
    for parameter, value in di.items():
        infotext += "%s: %s, " % (parameter, value)
    infotext = re.sub(", $", "", infotext)

    return state, infotext


# .
#   .--power---------------------------------------------------------------.
#   |                                                                      |
#   |                    _ __   _____      _____ _ __                      |
#   |                   | '_ \ / _ \ \ /\ / / _ \ '__|                     |
#   |                   | |_) | (_) \ V  V /  __/ |                        |
#   |                   | .__/ \___/ \_/\_/ \___|_|                        |
#   |                   |_|                                                |
#   '----------------------------------------------------------------------'


def inventory_dell_poweredge_amperage_power(info):
    inventory = []
    for line in info:
        if line[6] != "" and line[5] in ("24", "26"):
            inventory.append((line[6], None))
    return inventory


def inventory_dell_poweredge_amperage_current(info):
    inventory = []
    for line in info:
        if line[6] != "" and line[5] in ("23", "25"):
            inventory.append((line[6], None))
    return inventory


def check_dell_poweredge_amperage(item, _no_params, info):
    for (
        _chassisIndex,
        _Index,
        StateSettings,
        Status,
        Reading,
        ProbeType,
        LocationName,
        UpperCritical,
        UpperNonCritical,
    ) in info:

        if item == LocationName:
            if StateSettings == "1":  # unknown
                return 3, "Object's state is unknown"
            state_table = {
                "1": ("other", 1),
                "2": ("unknown", 1),
                "3": ("", 0),
                "4": ("nonCriticalUpper", 1),
                "5": ("CriticalUpper", 2),
                "6": ("NonRecoverableUpper", 2),
                "7": ("nonCriticalLower", 1),
                "8": ("CriticalLower", 2),
                "9": ("NonRecoverableLower", 2),
                "10": ("failed", 2),
            }
            state_txt, state = state_table.get(Status, "2")

            if UpperNonCritical and UpperCritical:
                limittext = " (upper limits %s/%s)" % (UpperNonCritical, UpperCritical)
                maxi = savefloat(UpperCritical) * 1.1
            else:
                limittext = ""
                maxi = ""

            if ProbeType in ("23", "25"):  # Amps
                current = str(int(Reading) / 10.0)
                infotext = "%s Ampere %s" % (current, state_txt)
                perfdata = [("current", current + "A", UpperNonCritical, UpperCritical, "", maxi)]
            elif ProbeType in ("24", "26"):  # Watts
                infotext = "%s Watt %s" % (Reading, state_txt)
                perfdata = [("power", Reading + "W", UpperNonCritical, UpperCritical, "", maxi)]
            else:
                infotext = "Unknown Probe Type %s" % ProbeType
                return 3, infotext

            return state, infotext + limittext, perfdata

    return 3, "Amperage Device not found"


# .
#   .--temperature---------------------------------------------------------.
#   |      _                                      _                        |
#   |     | |_ ___ _ __ ___  _ __   ___ _ __ __ _| |_ _   _ _ __ ___       |
#   |     | __/ _ \ '_ ` _ \| '_ \ / _ \ '__/ _` | __| | | | '__/ _ \      |
#   |     | ||  __/ | | | | | |_) |  __/ | | (_| | |_| |_| | | |  __/      |
#   |      \__\___|_| |_| |_| .__/ \___|_|  \__,_|\__|\__,_|_|  \___|      |
#   |                       |_|                                            |
#   '----------------------------------------------------------------------'


def dell_poweredge_temp_makeitem(chassisIndex, Index, LocationName):
    if LocationName:
        item = LocationName
    else:
        item = chassisIndex + "-" + Index
    if item.endswith(" Temp"):
        item = item[:-5]
    return item


def inventory_dell_poweredge_temp(info):
    for line in info:
        if line[2] != "1":  # StateSettings not 'unknown'
            item = dell_poweredge_temp_makeitem(line[0], line[1], line[5])
            yield item, {}


def check_dell_poweredge_temp(item, params, info):
    for (
        chassisIndex,
        Index,
        _StateSettings,
        Status,
        Reading,
        LocationName,
        UpperCritical,
        UpperNonCritical,
        LowerNonCritical,
        LowerCritical,
    ) in info:
        if not Reading:
            continue
        if item == dell_poweredge_temp_makeitem(chassisIndex, Index, LocationName):
            temp = int(Reading) / 10.0

            if UpperNonCritical and UpperCritical:
                levels = (int(UpperNonCritical) / 10.0, int(UpperCritical) / 10.0)
            else:
                levels = None, None
            if LowerNonCritical and LowerCritical:
                lower_levels = int(LowerNonCritical) / 10.0, int(LowerCritical) / 10.0
            else:
                lower_levels = None, None

            state_table = {
                "1": ("other", 1),
                "2": ("unknown", 1),
                "3": ("", 0),
                "4": ("nonCriticalUpper", 1),
                "5": ("CriticalUpper", 2),
                "6": ("NonRecoverableUpper", 2),
                "7": ("nonCriticalLower", 1),
                "8": ("CriticalLower", 2),
                "9": ("NonRecoverableLower", 2),
                "10": ("failed", 2),
            }
            state_txt, state = state_table.get(Status, ("unknown state", 3))
            if state:
                yield state, state_txt
            yield check_temperature(
                temp,
                params,
                "dell_poweredge_temp_%s" % item,
                dev_levels=levels,
                dev_levels_lower=lower_levels,
            )
