#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# In cooperation with Thorsten Bruhns from OPITZ Consulting


from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import (
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    IgnoreResultsError,
    LevelsT,
    render,
    Result,
    Service,
    State,
)

# <<<oracle_dataguard_stats:sep(124)>>>
# TESTDB|TESTDBU2|PHYSICAL STANDBY|apply finish time|+00 00:00:00.000|NOT ALLOWED|ENABLED|MAXIMUM PERFORMANCE|DISABLED||||APPLYING_LOG
# TESTDB|TESTDBU2|PHYSICAL STANDBY|apply lag|+00 00:00:00|NOT ALLOWED|ENABLED|MAXIMUM PERFORMANCE|DISABLED||||APPLYING_LOG
#
# TUX12C|TUXSTDB|PHYSICAL STANDBY|transport lag|+00 00:00:00
# TUX12C|TUXSTDB|PHYSICAL STANDBY|apply lag|+00 00:28:57
# TUX12C|TUXSTDB|PHYSICAL STANDBY|apply finish time|+00 00:00:17.180
# TUX12C|TUXSTDB|PHYSICAL STANDBY|estimated startup time|20


def inventory_oracle_dataguard_stats(section: Any) -> DiscoveryResult:
    for instance in section:
        yield Service(item=instance)


def _get_seconds(timestamp: str) -> int | None:
    if not timestamp or timestamp[0] != "+":
        return None

    days = int(timestamp[1:3])
    h = int(timestamp[4:6])
    min_ = int(timestamp[7:9])
    sec = int(timestamp[10:12])

    return sec + 60 * min_ + 3600 * h + 86400 * days


def check_oracle_dataguard_stats(item: str, params: Mapping[str, Any], section: Any) -> CheckResult:
    try:
        dgdata = section[item]
    except KeyError:
        # In case of missing information we assume that the login into
        # the database has failed and we simply skip this check. It won't
        # switch to UNKNOWN, but will get stale.
        raise IgnoreResultsError("Dataguard disabled or Instance not running")

    yield Result(state=State.OK, summary="Database Role %s" % (dgdata["database_role"].lower()))

    if "protection_mode" in dgdata:
        yield Result(
            state=State.OK, summary="Protection Mode %s" % (dgdata["protection_mode"].lower())
        )

    if "broker_state" in dgdata:
        yield Result(state=State.OK, summary="Broker %s" % (dgdata["broker_state"].lower()))

        # Observer is only usable with enabled Fast Start Failover!
        if "fs_failover_status" in dgdata and dgdata["fs_failover_status"] != "DISABLED":
            if dgdata["fs_failover_observer_present"] != "YES":
                yield Result(state=State.CRIT, summary="Observer not connected")
            else:
                yield Result(
                    state=State.OK,
                    summary="Observer connected {} from host {}".format(
                        dgdata["fs_failover_observer_present"].lower(),
                        dgdata["fs_failover_observer_host"],
                    ),
                )

                if (
                    dgdata["protection_mode"] == "MAXIMUM PERFORMANCE"
                    and dgdata["fs_failover_status"] == "TARGET UNDER LAG LIMIT"
                ) or (
                    dgdata["protection_mode"] == "MAXIMUM AVAILABILITY"
                    and dgdata["fs_failover_status"] == "SYNCHRONIZED"
                ):
                    state = State.OK
                else:
                    state = State.WARN
                yield Result(
                    state=state,
                    summary="Fast Start Failover %s" % (dgdata["fs_failover_status"].lower()),
                )

    # switchover_status is important for non broker environemnts as well.
    if "switchover_status" in dgdata:
        if dgdata["database_role"] == "PRIMARY":
            if dgdata["switchover_status"] in (
                "TO STANDBY",
                "SESSIONS ACTIVE",
                "RESOLVABLE GAP",
                "LOG SWITCH GAP",
            ):
                yield Result(state=State.OK, summary="Switchover to standby possible")
            else:
                primary_broker_state = params.get("primary_broker_state")
                if primary_broker_state or dgdata["broker_state"].lower() == "enabled":
                    # We need primary_broker_state False for Data-Guards without Broker
                    yield Result(
                        state=State.CRIT,
                        summary="Switchover to standby not possible! reason: %s"
                        % dgdata["switchover_status"].lower(),
                    )
                else:
                    yield Result(state=State.OK, summary="Switchoverstate ignored ")

        elif dgdata["database_role"] == "PHYSICAL STANDBY":
            # don't show the ok state, due to distracting 'NOT ALLOWED' state!
            if dgdata["switchover_status"] in ("SYNCHRONIZED", "NOT ALLOWED", "SESSIONS ACTIVE"):
                yield Result(state=State.OK, summary="Switchover to primary possible")
            else:
                yield Result(
                    state=State.CRIT,
                    summary="Switchover to primary not possible! reason: %s"
                    % dgdata["switchover_status"],
                )

    if dgdata["database_role"] != "PHYSICAL STANDBY":
        return

    if mrp_status := dgdata.get("mrp_status"):
        yield Result(
            state=State.OK, summary="Managed Recovery Process state %s" % mrp_status.lower()
        )

        if dgdata.get("open_mode", "") == "READ ONLY WITH APPLY":
            yield Result(
                state=State(params.get("active_dataguard_option")),
                summary="Active Data-Guard found",
            )

    elif mrp_status is not None:
        yield Result(state=State.OK, summary="Managed Recovery Process not started")

    for dgstat_param in ("apply finish time", "apply lag", "transport lag"):
        raw_value = dgdata["dgstat"][dgstat_param]
        seconds = _get_seconds(raw_value)
        pkey = dgstat_param.replace(" ", "_")
        label = dgstat_param.capitalize()
        # NOTE: not all of these metrics have params implemented, that's why we have to use 'get'

        if seconds is None:
            yield Result(
                state=State(params.get(f"missing_{pkey}_state", 0)),
                summary=f"{label}: {raw_value or 'no value'}",
            )
            continue

        levels_upper = params.get(pkey) or (None, None)
        levels_lower = params.get(f"{pkey}_min") or (None, None)

        yield from check_levels(
            seconds,
            levels_lower=_modernize_levels(levels_lower),
            levels_upper=_modernize_levels(levels_upper),
            metric_name=pkey,
            render_func=render.time_offset,
            label=label,
        )

    if (
        dgdata["database_role"] == "PHYSICAL STANDBY"
        and "broker_state" not in dgdata
        and "apply lag" in dgdata["dgstat"]
        and dgdata["dgstat"]["apply lag"] == ""
    ):
        # old sql cannot detect a started standby database without running media recovery
        # => add an information for old plug-in with possible wrong result
        yield Result(state=State.OK, summary="old plug-in data found, recovery active?")


def _modernize_levels(levels: None | tuple) -> LevelsT:
    match levels:
        case None | (None, None):
            return ("no_levels", None)
        case (warn, crit):
            return ("fixed", (warn, crit))
    raise ValueError(levels)


check_plugin_oracle_dataguard_stats = CheckPlugin(
    name="oracle_dataguard_stats",
    service_name="ORA %s Dataguard-Stats",
    discovery_function=inventory_oracle_dataguard_stats,
    check_function=check_oracle_dataguard_stats,
    check_ruleset_name="oracle_dataguard_stats",
    check_default_parameters={
        "apply_lag": (3600, 14400),
        "missing_apply_lag_state": 1,
        "active_dataguard_option": 1,
        "primary_broker_state": False,
    },
)
