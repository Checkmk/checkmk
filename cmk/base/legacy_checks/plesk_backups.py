#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import time
from collections.abc import Iterable, Mapping, Sequence

from cmk.base.check_api import check_levels, CheckResult, LegacyCheckDefinition, saveint
from cmk.base.config import check_info

from cmk.agent_based.v2 import render, StringTable

Section = Mapping[str, Sequence[str]]


def parse_plesk_backups(string_table: StringTable) -> Section:
    return {line[0]: line for line in string_table}


def inventory_plesk_backups(section: Section) -> Iterable[tuple[str, Mapping]]:
    yield from ((item, {}) for item in section)


def check_plesk_backups(item: str, params: Mapping[str, object], section: Section) -> CheckResult:
    if (line := section.get(item)) is None:
        return

    if len(line) != 5 or line[1] != "0":
        match line[1]:
            case "2":
                yield 3, "Error in agent (%s)" % " ".join(line[1:])
            case "4":
                yield int(params.get("no_backup_configured_state", 1)), "No backup configured"  # type: ignore[call-overload]
            case "5":
                yield int(params.get("no_backup_found_state", 1)), "No backup found"  # type: ignore[call-overload]
            case _:
                yield 3, "Unexpected line %r" % line
        return

    _domain, _rc, r_timestamp, r_size, r_total_size = line
    size = saveint(r_size)
    total_size = saveint(r_total_size)
    timestamp = saveint(r_timestamp)

    # 1. check last backup size not 0 bytes
    yield check_levels(
        size,
        "last_backup_size",
        (None, None, 0, 0),
        infoname="Last Backup - Size",
        human_readable_func=render.disksize,
    )
    # 2. check age of last backup < 24h
    age_seconds = int(time.time()) - timestamp
    yield check_levels(
        age_seconds,
        "last_backup_age",
        params.get("backup_age"),
        infoname="Age",
        human_readable_func=render.timespan,
    )
    yield 0, "Backup time: %s" % time.strftime("%c", time.localtime(timestamp))
    # 3. check total size of directory above configured threshold
    yield check_levels(
        total_size,
        "total_size",
        params.get("total_size"),
        infoname="Total size",
        human_readable_func=render.disksize,
    )
    return


check_info["plesk_backups"] = LegacyCheckDefinition(
    parse_function=parse_plesk_backups,
    service_name="Plesk Backup %s",
    discovery_function=inventory_plesk_backups,
    check_function=check_plesk_backups,
    check_ruleset_name="plesk_backups",
    check_default_parameters={
        "backup_age": None,
        "total_size": None,
        "no_backup_configured_state": 1,
        "no_backup_found_state": 1,
    },
)
