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

import time
from collections.abc import Iterable, Mapping
from typing import Literal, TypedDict

from cmk.base.check_api import check_levels, discover, MKCounterWrapped
from cmk.base.config import check_info, factory_settings
from cmk.base.plugins.agent_based.agent_based_api.v1 import render
from cmk.base.plugins.agent_based.utils.oracle_instance import (
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


_ParamsKey = Literal["logins", "noforcelogging", "noarchivelog", "forcelogging", "archivelog"]

_LOGINS_MAP: Mapping[str, _ParamsKey] = {
    "RESTRICTED": "logins",
}

_ARCHIVELOG_MAP: Mapping[str, _ParamsKey] = {
    "ARCHIVELOG": "archivelog",
    "NOARCHIVELOG": "noarchivelog",
}

_FORCELOGGING_MAP: Mapping[str, _ParamsKey] = {
    "YES": "forcelogging",
    "NO": "noforcelogging",
}


def check_oracle_instance(  # pylint: disable=too-many-branches
    item: str, params: _Params, section: Section
) -> Iterable[tuple[int, str, list] | tuple[int, str]]:
    if isinstance((instance := section.get(item)), (GeneralError, InvalidData)):
        yield 2, instance.error
        return
    if instance is None:
        yield 2, "Database or necessary processes not running or login failed"
        return

    # Handle old oracle agent plugin output
    if instance.old_agent:
        yield 0, f"Status {instance.openmode}"
        yield 0, f"Version {instance.version}"
        yield _asses_property("Logins", instance.logins, params, _LOGINS_MAP)
        return

    yield 0, f"{instance.type} Name {instance.display_name}"

    status_state = 0
    # Check state for PRIMARY Database. Normaly there are always OPEN
    if instance.database_role == "PRIMARY" and instance.openmode not in (
        "OPEN",
        "READ ONLY",
        "READ WRITE",
    ):
        status_state = params["primarynotopen"]
        yield status_state, f"Status {instance.openmode} {' (allowed by rule)' if status_state == 0 else ''}"
    else:
        yield 0, f"Status {instance.openmode}"

    if not instance.pdb:
        yield 0, f"Role {instance.database_role}"
        yield 0, f"Version {instance.version}"

    if instance.host_name:
        yield 0, f"Running on: {instance.host_name}"

    # ASM has no login and archivelog check
    if instance.database_role != "ASM":
        # logins are only possible when the database is open
        if instance.openmode == "OPEN":
            yield _asses_property("Logins", instance.logins, params, _LOGINS_MAP)

        # the new internal database _MGMTDB from 12.1.0.2 is always in NOARCHIVELOG mode
        if instance.name != "_MGMTDB" and instance.sid != "-MGMTDB" and not instance.pdb:
            assert instance.log_mode is not None
            yield _asses_property("Log Mode", instance.log_mode, params, _ARCHIVELOG_MAP)

            # archivelog is only valid in non pdb
            # force logging is only usable when archivelog is enabled
            if instance.log_mode == "ARCHIVELOG":
                if instance.archiver != "STARTED":
                    assert instance.archiver is not None
                    yield 2, f"Archiver {instance.archiver.lower()}"

                assert instance.force_logging is not None
                yield _asses_property(
                    "Force Logging", instance.force_logging, params, _FORCELOGGING_MAP
                )

    if instance.pdb and instance.ptotal_size is not None:
        yield check_levels(
            instance.ptotal_size,
            "fs_size",
            None,
            human_readable_func=render.bytes,
            infoname="PDB size",
        )


def _asses_property(
    label: str, value: str, params: _Params, key_map: Mapping[str, _ParamsKey]
) -> tuple[int, str]:
    return (
        0 if (key := key_map.get(value.upper())) is None else params[key],
        f"{label} {value.lower()}",
    )


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

    yield 0, f"Up since {render.datetime(time.time() - data.up_seconds)}", []

    yield check_levels(
        data.up_seconds,
        "uptime",
        params.get("max", (None, None)) + params.get("min", (None, None)),
        human_readable_func=render.timespan,
        infoname="Uptime",
    )


check_info["oracle_instance.uptime"] = {
    "check_function": check_oracle_instance_uptime,
    "discovery_function": discover_oracle_instance_uptime,
    "service_name": "ORA %s Uptime",
    "check_ruleset_name": "uptime_multiitem",
}
