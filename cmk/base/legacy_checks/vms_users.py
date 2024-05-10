#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Example output from agent:
# <<<vms_users>>>
# AEP 2 - - 1
# SYSTEM 1
# TCPIP$FTP - - - 1


from cmk.base.check_api import LegacyCheckDefinition, saveint
from cmk.base.config import check_info

from cmk.agent_based.v2 import StringTable


def inventory_vms_users(info):
    if len(info) > 0:
        return [(None, {})]
    return []


def check_vms_users(item, params, info):
    infos = []
    num_sessions = 0
    for line in info:
        # complete missing columns
        padding = [0] * (5 - len(line))
        interactive, _subproc, _batch, _network = list(map(saveint, line[1:])) + padding
        if interactive:
            num_sessions += interactive
            infos.append("%s: %d" % (line[0], interactive))

    perfdata = [("sessions", num_sessions)]

    if num_sessions:
        return (0, "Interactive users: " + ", ".join(infos), perfdata)
    return (0, "No interactive users", perfdata)


def parse_vms_users(string_table: StringTable) -> StringTable:
    return string_table


check_info["vms_users"] = LegacyCheckDefinition(
    parse_function=parse_vms_users,
    service_name="VMS Users",
    discovery_function=inventory_vms_users,
    check_function=check_vms_users,
)
