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

from cmk.agent_based.v1 import check_levels as check_levels_v1
from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    IgnoreResultsError,
    render,
    Result,
    Service,
    State,
)
from cmk.plugins.oracle.agent_based.libinstance import GeneralError, Instance, InvalidData, Section


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


def discover_oracle_instance(section: Section) -> DiscoveryResult:
    yield from (Service(item=item) for item in section)


def check_oracle_instance(item: str, params: _Params, section: Section) -> CheckResult:
    if isinstance((instance := section.get(item)), GeneralError | InvalidData):
        yield Result(state=State.CRIT, summary=instance.error)
        return
    if instance is None:
        yield Result(
            state=State.CRIT, summary="Database or necessary processes not running or login failed"
        )
        return

    # Handle old oracle agent plug-in output
    if instance.old_agent:
        yield Result(state=State.OK, summary=f"Status {instance.openmode}")
        yield Result(state=State.OK, summary=f"Version {instance.version}")
        yield _asses_property("Logins", instance.logins, params, _LOGINS_MAP)
        return

    yield Result(state=State.OK, summary=f"{instance.type} Name {instance.display_name}")

    status_state = State.OK
    # Check state for PRIMARY Database. Normaly there are always OPEN
    if instance.database_role == "PRIMARY" and instance.openmode not in (
        "OPEN",
        "READ ONLY",
        "READ WRITE",
    ):
        status_state = State(params["primarynotopen"])
        yield Result(
            state=status_state,
            summary=f"Status {instance.openmode}{' (allowed by rule)' if status_state is State.OK else ''}",
        )
    else:
        yield Result(state=State.OK, summary=f"Status {instance.openmode}")

    if not instance.pdb:
        yield Result(state=State.OK, summary=f"Role {instance.database_role}")
        yield Result(state=State.OK, summary=f"Version {instance.version}")

    if instance.host_name:
        yield Result(state=State.OK, summary=f"Running on: {instance.host_name}")

    # ASM has no login and archivelog check
    if instance.database_role != "ASM":
        yield from _check_archive_log(instance, params)

    if instance.pdb and instance.ptotal_size is not None:
        yield from check_levels_v1(
            instance.ptotal_size,
            metric_name="oracle_pdb_total_size",
            render_func=render.bytes,
            label="PDB size",
        )


def _asses_property(
    label: str, value: str, params: _Params, key_map: Mapping[str, _ParamsKey]
) -> Result:
    return Result(
        state=State.OK if (key := key_map.get(value.upper())) is None else State(params[key]),
        summary=f"{label} {value.lower()}",
    )


def _check_archive_log(instance: Instance, params: _Params) -> Iterable[Result]:
    # logins are only possible when the database is open
    if instance.openmode == "OPEN":
        yield _asses_property("Logins", instance.logins, params, _LOGINS_MAP)

    # the new internal database _MGMTDB from 12.1.0.2 is always in NOARCHIVELOG mode
    if instance.name == "_MGMTDB" or instance.sid == "-MGMTDB" or instance.pdb:
        return

    assert instance.log_mode is not None
    yield _asses_property("Log Mode", instance.log_mode, params, _ARCHIVELOG_MAP)

    # archivelog is only valid in non pdb
    # force logging is only usable when archivelog is enabled
    if instance.log_mode != "ARCHIVELOG":
        return

    if instance.archiver != "STARTED":
        assert instance.archiver is not None
        yield Result(state=State.CRIT, summary=f"Archiver {instance.archiver.lower()}")

    assert instance.force_logging is not None
    yield _asses_property("Force Logging", instance.force_logging, params, _FORCELOGGING_MAP)


check_plugin_oracle_instance = CheckPlugin(
    name="oracle_instance",
    service_name="ORA %s Instance",
    discovery_function=discover_oracle_instance,
    check_function=check_oracle_instance,
    check_ruleset_name="oracle_instance",
    check_default_parameters={
        "logins": 2,
        "noforcelogging": 1,
        "noarchivelog": 1,
        "primarynotopen": 2,
        "archivelog": 0,
        "forcelogging": 0,
    },
)


def discover_oracle_instance_uptime(section: Section) -> DiscoveryResult:
    yield from (
        Service(item=item)
        for item, data in section.items()
        if isinstance(data, Instance) and data.up_seconds is not None and data.up_seconds != -1
    )


class _UptimeMultiItemParams(TypedDict, total=False):
    max: tuple[float, float]
    min: tuple[float, float]


def check_oracle_instance_uptime(
    item: str, params: _UptimeMultiItemParams, section: Section
) -> CheckResult:
    if not isinstance((data := section.get(item)), Instance):
        # Error is already shown in main check
        raise IgnoreResultsError("Login into database failed")

    if data.popenmode == "MOUNTED":
        yield Result(state=State.OK, summary="PDB in mounted state has no uptime information")
        return

    if data.up_seconds is None:
        return

    yield Result(
        state=State.OK, summary=f"Up since {render.datetime(time.time() - data.up_seconds)}"
    )

    yield from check_levels_v1(
        data.up_seconds,
        levels_lower=params.get("min"),
        levels_upper=params.get("max"),
        metric_name="uptime",
        render_func=render.timespan,
        label="Uptime",
    )


check_plugin_oracle_instance_uptime = CheckPlugin(
    name="oracle_instance_uptime",
    sections=["oracle_instance"],
    service_name="ORA %s Uptime",
    discovery_function=discover_oracle_instance_uptime,
    check_function=check_oracle_instance_uptime,
    check_ruleset_name="uptime_multiitem",
    check_default_parameters={},
)
