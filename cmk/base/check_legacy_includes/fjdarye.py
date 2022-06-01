#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# tyxpe: ignore[list-item,import,assignment,misc,operator]  # TODO: see which are needed in this file
# pylint: disable=no-else-return

# check_mk plugin to monitor Fujitsu storage systems supporting FJDARY-E60.MIB or FJDARY-E100.MIB
# Copyright (c) 2012 FuH Entwicklungsgesellschaft mbH, Umkirch, Germany. All rights reserved.
# Author: Philipp Hoefflin, 2012, hoefflin+cmk@fuh-e.de

# generic data structure widely used in the FJDARY-Mibs:
# <oid>
# <oid>.1: Index
# <oid>.3: Status
# the latter can be one of the following:
fjdarye_item_status = {
    "1": (0, "Normal"),
    "2": (2, "Alarm"),
    "3": (1, "Warning"),
    "4": (2, "Invalid"),
    "5": (2, "Maintenance"),
    "6": (2, "Undefined"),
}


# generic inventory item - status other than 'invalid' is ok for inventory
def inventory_fjdarye_item(info):
    return [(index, {}) for index, status in info if status != "4"]


# generic check_function returning the nagios-code and the status text
def check_fjdarye_item(item, _no_param, info):
    for line in info:
        if line[0] == str(item):  # watch out! older versions discovered `int`s!
            return fjdarye_item_status[line[1]]
    return None


# .
#   .--single disks--------------------------------------------------------.
#   |               _             _            _ _     _                   |
#   |           ___(_)_ __   __ _| | ___    __| (_)___| | _____            |
#   |          / __| | '_ \ / _` | |/ _ \  / _` | / __| |/ / __|           |
#   |          \__ \ | | | | (_| | |  __/ | (_| | \__ \   <\__ \           |
#   |          |___/_|_| |_|\__, |_|\___|  \__,_|_|___/_|\_\___/           |
#   |                       |___/                                          |
#   +----------------------------------------------------------------------+
#   |                          disks main check                            |
#   '----------------------------------------------------------------------'

fjdarye_disks_status = {
    "1": (0, "available"),
    "2": (2, "broken"),
    "3": (1, "notavailable"),
    "4": (1, "notsupported"),
    "5": (0, "present"),
    "6": (1, "readying"),
    "7": (1, "recovering"),
    "64": (1, "partbroken"),
    "65": (1, "spare"),
    "66": (0, "formatting"),
    "67": (0, "unformated"),
    "68": (1, "notexist"),
    "69": (1, "copying"),
}


def parse_fjdarye_disks(info):
    parsed: dict = {}
    for idx, disk_state in info:
        state, state_readable = fjdarye_disks_status.get(
            disk_state,
            (3, "unknown[%s]" % disk_state),
        )
        parsed.setdefault(
            str(idx),
            {
                "state": state,
                "state_readable": state_readable,
                "state_disk": disk_state,
            },
        )
    return parsed


def inventory_fjdarye_disks(parsed):
    return [
        (idx, repr(attrs["state_readable"]))
        for idx, attrs in parsed.items()
        if attrs["state_disk"] != "3"
    ]


def check_fjdarye_disks(item, params, parsed):
    if isinstance(params, str):
        params = {"expected_state": params}

    if item in parsed:
        attrs = parsed[item]
        state_readable = attrs["state_readable"]
        expected_state = params.get("expected_state")
        check_state = 0
        infotext = "Status: %s" % state_readable
        if params.get("use_device_states"):
            check_state = attrs["state"]
            if check_state > 0:
                infotext += " (use device states)"
        elif expected_state and state_readable != expected_state:
            check_state = 2
            infotext += " (expected: %s)" % expected_state
        return check_state, infotext
    return None


# .
#   .--summary disks-------------------------------------------------------.
#   |                                                                      |
#   |           ___ _   _ _ __ ___  _ __ ___   __ _ _ __ _   _             |
#   |          / __| | | | '_ ` _ \| '_ ` _ \ / _` | '__| | | |            |
#   |          \__ \ |_| | | | | | | | | | | | (_| | |  | |_| |            |
#   |          |___/\__,_|_| |_| |_|_| |_| |_|\__,_|_|   \__, |            |
#   |                                                    |___/             |
#   |                            _ _     _                                 |
#   |                         __| (_)___| | _____                          |
#   |                        / _` | / __| |/ / __|                         |
#   |                       | (_| | \__ \   <\__ \                         |
#   |                        \__,_|_|___/_|\_\___/                         |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def fjdarye_disks_summary(parsed):
    states: dict = {}
    for attrs in parsed.values():
        if attrs["state_disk"] != "3":
            states.setdefault(attrs["state_readable"], 0)
            states[attrs["state_readable"]] += 1
    return states


def inventory_fjdarye_disks_summary(parsed):
    current_state = fjdarye_disks_summary(parsed)
    if len(current_state) > 0:
        return [(None, current_state)]
    return []


def fjdarye_disks_printstates(states):
    return ", ".join(["%s: %s" % (s.title(), c) for s, c in states.items()])


def check_fjdarye_disks_summary(index, params, parsed):
    map_states = {
        "available": 0,
        "broken": 2,
        "notavailable": 1,
        "notsupported": 1,
        "present": 0,
        "readying": 1,
        "recovering": 1,
        "partbroken": 1,
        "spare": 1,
        "formatting": 0,
        "unformated": 0,
        "notexist": 1,
        "copying": 1,
    }

    use_devices_states = False
    if "use_device_states" in params:
        use_devices_states = params["use_device_states"]
        del params["use_device_states"]
    expected_state = params

    current_state = fjdarye_disks_summary(parsed)
    infotext = fjdarye_disks_printstates(current_state)
    if use_devices_states:
        state = 0
        for state_readable in current_state:
            state = max(state, map_states.get(state_readable, 3))
        infotext += " (ignore expected state)"
        return state, infotext

    if current_state == expected_state:
        return 0, infotext

    result = 1
    for ename, ecount in expected_state.items():
        if current_state.get(ename, 0) < ecount:
            result = 2
            break

    return result, "%s (expected: %s)" % (infotext, fjdarye_disks_printstates(expected_state))


# .
#   .--rluns---------------------------------------------------------------.
#   |                            _                                         |
#   |                       _ __| |_   _ _ __  ___                         |
#   |                      | '__| | | | | '_ \/ __|                        |
#   |                      | |  | | |_| | | | \__ \                        |
#   |                      |_|  |_|\__,_|_| |_|___/                        |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def inventory_fjdarye_rluns(info):
    for line in info:
        rawdata = line[1]
        if rawdata[3] == "\xa0":  # RLUN is present
            yield line[0], "", None


def check_fjdarye_rluns(item, _no_params, info):
    for line in info:
        if item == line[0]:
            rawdata = line[1]
            if rawdata[3] != "\xa0":
                return (2, "RLUN is not present")
            elif rawdata[2] == "\x08":
                return (1, "RLUN is rebuilding")
            elif rawdata[2] == "\x07":
                return (1, "RLUN copyback in progress")
            elif rawdata[2] == "\x41":
                return (1, "RLUN spare is in use")
            elif rawdata[2] == "B":
                return (0, "RLUN is in RAID0 state")  # assumption state 42
            elif rawdata[2] == "\x00":
                return (0, "RLUN is in normal state")  # assumption
            return (2, "RLUN in unknown state %02x" % ord(rawdata[2]))
    return None


# .

fjdarye_sum_status = {1: "unknown", 2: "unused", 3: "ok", 4: "warning", 5: "failed"}


def inventory_fjdarye_sum(info):
    if len(info[0]) == 1:
        yield "0", {}


def check_fjdarye_sum(index, _no_param, info):
    for line in info:
        if len(info[0]) == 1:
            status = int(line[0])
            text = "Status is %s" % fjdarye_sum_status[status]

            if status == 3:
                return (0, "%s" % text)
            elif status == 4:
                return (1, "%s" % text)
            return (2, "%s" % text)

    return (3, "No status summary present")
