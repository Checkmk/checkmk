#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Header: Schedule Name, Application Name, Schedule Description, Failures
# <<<unitrends_backup:sep(124)>>>
# HEADER|DMZ-SR01|Hyper-V 2012|DMZ-HV01|0
# rodc2|18761|Incremental|Successful
# rodc2|18761|Incremental|Successful
# owncloud-test|18762|Incremental|Successful


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.config import check_info

from cmk.agent_based.v2 import StringTable


def inventory_unitrends_backup(info):
    inventory = []
    for line in info:
        if line[0] == "HEADER":
            inventory.append((line[1], None))
    return inventory


def check_unitrends_backup(item, _no_params, info):
    found = False
    details = []
    for line in info:
        if line[0] == "HEADER" and found:
            # We are finish collection detail informatoinen
            break

        if found is True:
            # Collection Backup deatils
            app_type, bid, backup_type, status = line
            details.append(f"Application Type: {app_type} ({bid}), {backup_type}: {status}")
            continue

        if line[0] == "HEADER" and line[1] == item:
            found = True
            _head, _sched_name, app_name, sched_desc, failures = line
            message = "{} Errors in last 24/h for Application {} ({}) ".format(
                failures,
                app_name,
                sched_desc,
            )

    if found is True:
        message += "\n" + "\n".join(details)
        if failures == "0":
            return 0, message
        return 2, message
    return 3, "Schedule not found in Agent Output"


def parse_unitrends_backup(string_table: StringTable) -> StringTable:
    return string_table


check_info["unitrends_backup"] = LegacyCheckDefinition(
    parse_function=parse_unitrends_backup,
    service_name="Schedule %s",
    discovery_function=inventory_unitrends_backup,
    check_function=check_unitrends_backup,
)
