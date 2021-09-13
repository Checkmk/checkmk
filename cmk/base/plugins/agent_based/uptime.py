#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Example output from agent:
# <<<uptime>>>
# 15876.96 187476.72

import datetime
import re
from typing import Optional

from .agent_based_api.v1 import register
from .agent_based_api.v1.type_defs import StringTable
from .utils import uptime


def parse_human_read_uptime(string: str) -> int:
    """Human readable string as given by solaris uptime into seconds"""
    days, hrs, mins = 0, 0, 0
    mmin = re.search(r"(\d+) min\(s\)", string)
    if mmin:
        mins = int(mmin.group(1))

    mday = re.search(r"(\d+) day\(s\)", string)
    if mday:
        days = int(mday.group(1))

    mhrs = re.search(r"(\d+) hr\(s\)", string)
    if mhrs:
        hrs = int(mhrs.group(1))

    mhm = re.search(r"(\d+):(\d+)", string)
    if mhm:
        hrs = int(mhm.group(1))
        mins = int(mhm.group(2))

    return 86400 * days + 3600 * hrs + 60 * mins


def parse_solaris_uptime(info, from_boot_time) -> uptime.Section:
    """Solaris agent Version>= 1.5.0p15 delivers a lot of context information

        This was necesary because Solaris returns very inconsistent output for
        the standard uptime query. Thus some cross validation of the output is
        required.

        Output looks like this

    <<<uptime>>>
    1122                                                               # seconds since boot
    [uptime_solaris_start]
    SunOS unknown 5.10 Generic_147148-26 i86pc i386 i86pc              # uname
    global                                                             # zonename
      4:23pm  up 19 min(s),  2 users,  load average: 0.03, 0.09, 0.09  # uptime command
    unix:0:system_misc:snaptime     1131.467157594                     # snaptime
    [uptime_solaris_end]


        In an ideal situation uptime, from_boot_time, and snaptime represent
        the same value, and none of this redundancy would be required. They
        might be off by 30s at most.

        We generously allow 600s seconds difference between pairs, and require
        only that a pair between uptime, from_boot_time, snaptime overlaps to
        validate the uptime. Otherwise a message is printed and the check
        returns unknown."""

    uptime_struct = {}
    uptime_struct["from_boot_time"] = from_boot_time
    uptime_struct["uname"] = " ".join(info[0])
    uptime_struct["zonename"] = info[1][0]
    uptime_match = re.match(r".*up (.*), +\d+ user.*", " ".join(info[2]))
    assert uptime_match
    uptime_struct["uptime_parsed"] = parse_human_read_uptime(uptime_match.group(1))
    uptime_struct["snaptime"] = float(info[3][1])

    if abs(uptime_struct["uptime_parsed"] - uptime_struct["from_boot_time"]) < 600:
        uptime_struct["uptime_sec"] = uptime_struct["from_boot_time"]
    elif abs(uptime_struct["uptime_parsed"] - uptime_struct["snaptime"]) < 600:
        uptime_struct["uptime_sec"] = uptime_struct["snaptime"]
    elif abs(uptime_struct["from_boot_time"] - uptime_struct["snaptime"]) < 600:
        uptime_struct["uptime_sec"] = uptime_struct["from_boot_time"]
    else:

        uptimes_summary = "Uptime command: %s; Kernel time since boot: %s; Snaptime: %s" % tuple(
            datetime.timedelta(seconds=x)
            for x in (
                uptime_struct["uptime_parsed"],
                uptime_struct["from_boot_time"],
                uptime_struct["snaptime"],
            )
        )

        uptime_struct["message"] = (
            "Your Solaris system gives inconsistent uptime information. " "Please get it fixed. "
        ) + uptimes_summary

    return uptime.Section(
        uptime_struct.get("uptime_sec"),
        uptime_struct.get("message"),
    )


def parse_uptime(string_table: StringTable) -> Optional[uptime.Section]:
    if not string_table:
        return None

    def extract_solaris_subsection(info):
        is_solaris = False
        solaris_info = []
        for line in info:
            if line[-1] == "[uptime_solaris_start]":
                is_solaris = True
                continue
            if line[-1] == "[uptime_solaris_end]":
                is_solaris = False
                continue

            if is_solaris:
                solaris_info.append(line)
        return solaris_info

    from_boot_time = float(string_table[0][0])
    solaris_info = extract_solaris_subsection(string_table)

    if solaris_info:
        return parse_solaris_uptime(solaris_info, from_boot_time)

    return uptime.Section(from_boot_time, None)


register.agent_section(
    name="uptime",
    supersedes=["snmp_uptime"],
    parse_function=parse_uptime,
)

register.check_plugin(
    name="uptime",
    service_name="Uptime",
    discovery_function=uptime.discover,
    check_function=uptime.check,
    check_default_parameters={},
    check_ruleset_name="uptime",
)
