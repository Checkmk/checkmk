#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="type-arg"


import time
from collections.abc import Iterable, Mapping, Sequence

from cmk.agent_based.legacy.v0_unstable import (
    check_levels,
    LegacyCheckDefinition,
    LegacyCheckResult,
)
from cmk.agent_based.v2 import render, StringTable

check_info = {}

Section = Mapping[str, Sequence[str]]


def saveint(i: str) -> int:
    """Tries to cast a string to an integer and return it. In case this
    fails, it returns 0.

    Advice: Please don't use this function in new code. It is understood as
    bad style these days, because in case you get 0 back from this function,
    you can not know whether it is really 0 or something went wrong."""
    try:
        return int(i)
    except (TypeError, ValueError):
        return 0


def parse_plesk_backups(string_table: StringTable) -> Section:
    return {line[0]: line for line in string_table}


def discover_plesk_backups(section: Section) -> Iterable[tuple[str, Mapping]]:
    yield from ((item, {}) for item in section)


def check_plesk_backups(
    item: str, params: Mapping[str, object], section: Section
) -> LegacyCheckResult:
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
    name="plesk_backups",
    parse_function=parse_plesk_backups,
    service_name="Plesk Backup %s",
    discovery_function=discover_plesk_backups,
    check_function=check_plesk_backups,
    check_ruleset_name="plesk_backups",
    check_default_parameters={
        "backup_age": None,
        "total_size": None,
        "no_backup_configured_state": 1,
        "no_backup_found_state": 1,
    },
)
