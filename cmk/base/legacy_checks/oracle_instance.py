#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# In cooperation with Thorsten Bruhns

# <<<oracle_instance:sep(124)>>>
# TUX2|12.1.0.1.0|OPEN|ALLOWED|STARTED|6735|1297771692|ARCHIVELOG|PRIMARY|NO|TUX2
# TUX5|12.1.0.1.1|MOUNTED|ALLOWED|STARTED|82883|1297771692|NOARCHIVELOG|PRIMARY|NO|0|TUX5

# <<<oracle_instance:sep(124)>>>$
# +ASM|FAILURE|ORA-99999 tnsping failed for +ASM $
# ERROR:$
# ORA-28002: the password will expire within 1 days$


import datetime
import time
from collections.abc import Iterable
from typing import TypedDict

from cmk.base.check_api import check_levels, discover, get_bytes_human_readable, MKCounterWrapped
from cmk.base.config import check_info, factory_settings
from cmk.base.plugins.agent_based.oracle_instance import (
    GeneralError,
    Instance,
    InvalidData,
    Section,
)

factory_settings["oracle_instance_defaults"] = {
    "logins": 2,
    "noforcelogging": 1,
    "noarchivelog": 1,
    "primarynotopen": 2,
    "archivelog": 0,
    "forcelogging": 0,
}


class _Params(TypedDict, total=True):
    logins: int
    noforcelogging: int
    noarchivelog: int
    primarynotopen: int
    archivelog: int
    forcelogging: int


def _merge_states(state: int, infotext: str, value: int, column: str, data: str) -> tuple[int, str]:
    if column.lower() == data.lower():
        state = max(state, value)
        if value == 1:
            infotext += "(!)"
        elif value == 2:
            infotext += "(!!)"
    return state, infotext


def check_oracle_instance(  # pylint: disable=too-many-branches
    item: str, params: _Params, section: Section
) -> Iterable[tuple[int, str, list]]:
    if not (item_data := section.get(item)):
        yield 2, "Database or necessary processes not running or login failed", []
        return

    if isinstance(item_data, GeneralError):
        yield 2, item_data.err, []
        return

    if isinstance(item_data, InvalidData):
        yield 2, "Database not running, login failed or unvalid data from agent", []
        return

    state = 0

    # Handle old oracle agent plugin output
    if item_data.old_agent:
        infotext = "Status %s, Version %s, Logins %s" % (
            item_data.openmode,
            item_data.version,
            item_data.logins.lower(),
        )
        state, infotext = _merge_states(
            state, infotext, params["logins"], item_data.logins, "RESTRICTED"
        )
        yield state, infotext, []
        return

    if item_data.pdb:
        infotext = "PDB Name %s.%s, Status %s" % (
            item_data.name,
            item_data.pname,
            item_data.popenmode,
        )
    else:
        if item_data.pluggable.lower() == "true":
            infotext = "CDB Name %s, Status %s" % (item_data.name, item_data.openmode)
        else:
            infotext = "Database Name %s, Status %s" % (item_data.name, item_data.openmode)

    # Check state for PRIMARY Database. Normaly there are always OPEN
    if item_data.database_role == "PRIMARY" and item_data.openmode not in (
        "OPEN",
        "READ ONLY",
        "READ WRITE",
    ):
        state = int(params["primarynotopen"])
        if state == 1:
            infotext += "(!)"
        elif state == 2:
            infotext += "(!!)"
        elif state == 0:
            infotext += " (allowed by rule)"

    if not item_data.pdb:
        infotext += ", Role %s, Version %s" % (item_data.database_role, item_data.version)

    if item_data.host_name:
        infotext += f", Running on: {item_data.host_name}"

    # ASM has no login and archivelog check
    if item_data.database_role != "ASM":
        # logins are only possible when the database is open
        if item_data.openmode == "OPEN":
            infotext += ", Logins %s" % (item_data.logins.lower())
            state, infotext = _merge_states(
                state, infotext, params["logins"], item_data.logins, "RESTRICTED"
            )

        # the new internal database _MGMTDB from 12.1.0.2 is always in NOARCHIVELOG mode
        if item_data.name != "_MGMTDB" and item_data.sid != "-MGMTDB" and not item_data.pdb:
            assert item_data.log_mode is not None
            infotext += ", Log Mode %s" % (item_data.log_mode.lower())
            state, infotext = _merge_states(
                state, infotext, params["archivelog"], item_data.log_mode, "ARCHIVELOG"
            )
            state, infotext = _merge_states(
                state, infotext, params["noarchivelog"], item_data.log_mode, "NOARCHIVELOG"
            )

            # archivelog is only valid in non pdb
            # force logging is only usable when archivelog is enabled
            if item_data.log_mode == "ARCHIVELOG":
                if item_data.archiver != "STARTED":
                    assert item_data.archiver is not None
                    infotext += ". Archiver %s(!!)" % (item_data.archiver.lower())
                    state = 2

                assert item_data.force_logging is not None
                infotext += ", Force Logging %s" % (item_data.force_logging.lower())
                state, infotext = _merge_states(
                    state, infotext, params["forcelogging"], item_data.force_logging, "YES"
                )
                state, infotext = _merge_states(
                    state, infotext, params["noforcelogging"], item_data.force_logging, "NO"
                )

    perfdata = []

    if item_data.pdb:
        assert item_data.ptotal_size is not None
        infotext += ", PDB Size %s" % get_bytes_human_readable(int(item_data.ptotal_size))
        perfdata.append(("fs_size", int(item_data.ptotal_size)))

    yield state, infotext, perfdata


check_info["oracle_instance"] = {
    # section is already migrated!
    "check_function": check_oracle_instance,
    "discovery_function": discover(),
    "service_name": "ORA %s Instance",
    "default_levels_variable": "oracle_instance_defaults",
    "check_ruleset_name": "oracle_instance",
}


def discover_oracle_instance_uptime(section: Section) -> Iterable[tuple[str, dict]]:
    yield from (
        (
            item,
            {},
        )
        for item, data in section.items()
        if isinstance(data, Instance) and data.up_seconds is not None
    )


class _UptimeMultiItemParams(TypedDict, total=False):
    max: tuple[float, float]
    min: tuple[float, float]


def check_oracle_instance_uptime(
    item: str, params: _UptimeMultiItemParams, section: Section
) -> Iterable[tuple[int, str, list]]:
    if not isinstance((data := section.get(item)), Instance):
        # Error is already shown in main check
        raise MKCounterWrapped("Login into database failed")

    if data.up_seconds is None:
        return

    up_seconds = int(data.up_seconds)

    levels = params.get("max", (None, None)) + params.get("min", (None, None))
    yield check_levels(
        up_seconds,
        "uptime",
        levels,
        human_readable_func=lambda x: datetime.timedelta(seconds=int(x)),
        infoname="Up since %s, uptime"
        % time.strftime("%F %T", time.localtime(time.time() - up_seconds)),
    )


check_info["oracle_instance.uptime"] = {
    "check_function": check_oracle_instance_uptime,
    "discovery_function": discover_oracle_instance_uptime,
    "service_name": "ORA %s Uptime",
    "check_ruleset_name": "uptime_multiitem",
}
