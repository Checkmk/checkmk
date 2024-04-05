#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


# mypy: disable-error-code="var-annotated,arg-type"

import time

from cmk.base.check_api import get_bytes_human_readable, LegacyCheckDefinition, saveint
from cmk.base.config import check_info

from cmk.agent_based.v2.type_defs import StringTable


def inventory_plesk_backups(info):
    inventory = []
    for line in info:
        inventory.append((line[0], {}))
    return inventory


def check_plesk_backups(item, params, info):  # pylint: disable=too-many-branches
    for line in info:
        if item != line[0]:
            continue

        if len(line) != 5 or line[1] != "0":
            if line[1] == "2":
                return (3, "Error in agent (%s)" % " ".join(line[1:]))

            if line[1] == "4":
                state = params.get("no_backup_configured_state", 1)
                return (state, "No backup configured")

            if line[1] == "5":
                state = params.get("no_backup_found_state", 1)
                return (state, "No backup found")

            return (3, "Unexpected line %r" % line)

        _domain, _rc, timestamp, size, total_size = line
        size = saveint(size)
        total_size = saveint(total_size)
        timestamp = saveint(timestamp)

        status = 0
        output = []
        perfdata = []

        # 1. check last backup size not 0 bytes
        status_txt = ""
        if size == 0:
            status = 2
            status_txt = " (!!)"
        output.append(f"Last Backup - Size: {get_bytes_human_readable(size)}{status_txt}")
        perfdata.append(("last_backup_size", size))

        age_seconds = int(time.time()) - timestamp
        seconds = age_seconds % 60
        rem = int(age_seconds / 60.0)
        minutes = rem % 60
        hours = int((rem % 1440) / 60)
        days = int(rem / 1440)

        # 2. check age of last backup < 24h
        status_txt = ""
        warn, crit = None, None
        if "backup_age" in params:
            warn, crit = params["backup_age"]
            if age_seconds > params["backup_age"][1]:
                status = max(status, 2)
                status_txt = " (!!)"
            elif age_seconds > params["backup_age"][0]:
                status = max(status, 1)
                status_txt = " (!)"

        backup_time = time.strftime("%c", time.localtime(timestamp))
        output.append(
            "Age: %s (%dd %02d:%02d:%02d)%s"
            % (backup_time, days, hours, minutes, seconds, status_txt)
        )
        perfdata.append(("last_backup_age", age_seconds, warn, crit))

        # 3. check total size of directory above configured threshold
        status_txt = ""
        warn, crit = None, None
        if "total_size" in params:
            warn, crit = params["total_size"]
            if total_size > params["total_size"][1]:
                status = max(status, 2)
                status_txt = " (!!)"
            elif total_size > params["total_size"][0]:
                status = max(status, 1)
                status_txt = " (!)"
        output.append(f"Total Size: {get_bytes_human_readable(total_size)}{status_txt}")
        perfdata.append(("total_size", total_size))

        return (status, ", ".join(output), perfdata)

    return (3, "Domain not found")


def parse_plesk_backups(string_table: StringTable) -> StringTable:
    return string_table


check_info["plesk_backups"] = LegacyCheckDefinition(
    parse_function=parse_plesk_backups,
    service_name="Plesk Backup %s",
    discovery_function=inventory_plesk_backups,
    check_function=check_plesk_backups,
    check_ruleset_name="plesk_backups",
)
