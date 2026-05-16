#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# <<<mongodb_replica_status>>>
# <json>


import datetime
import enum
import json
import time
from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v1 import check_levels as check_levels_v1
from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_value_store,
    render,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.plugins.mongodb.lib import parse_date

Section = Mapping[str, Any]

CHECK_DEFAULT_PARAMETERS = {"levels_mongdb_replication_lag": (10, 60, 3600)}


def parse_mongodb_replica_set(string_table: StringTable) -> Section:
    if string_table:
        parsed: Section = json.loads(str(string_table[0][0]))
        return parsed
    return {}


#   .--replication lag-----------------------------------------------------.


class ReplicaState(enum.IntEnum):
    PRIMARY = 1
    ARBITER = 7


def discover_mongodb_replica_set(section: Section) -> DiscoveryResult:
    if section:
        yield Service()


def check_mongodb_replica_set_lag(params: Mapping[str, Any], section: Section) -> CheckResult:
    """based on MongoDB script 'db.printSlaveReplicationInfo'"""
    number_of_replica_set_members = len(section.get("members", []))
    if number_of_replica_set_members <= 1:
        yield Result(
            state=State.WARN, summary=f"Number of members is {number_of_replica_set_members}"
        )
        return

    primary, secondaries = _get_primary(section.get("members", []))

    start_operation_timestamp, name = _get_start_timestamp(primary, secondaries)

    long_output = []
    for member in secondaries:
        member_name = member.get("name", "unknown")

        if member.get("optime", {}).get("ts", {}).get("$timestamp", {}).get("t", None):
            member_optime_date = parse_date(member.get("optimeDate", {}).get("$date", 0))
            replication_lag_sec = _calculate_replication_lag(
                start_operation_timestamp, member_optime_date
            )

            yield from _check_lag_over_time(
                time.time(),
                member_name,
                name,
                replication_lag_sec,
                params.get("levels_mongdb_replication_lag", (10, 60, 3600)),
            )

            long_output.append(
                _get_long_output(member_name, member_optime_date, replication_lag_sec, name)
            )
        else:
            yield Result(
                state=State.OK,
                summary=f"{member_name}: no replication info yet, State: {member.get('state', 0)}",
            )

    if long_output:
        yield Result(state=State.OK, notice="\n" + "\n".join(long_output))


def _check_lag_over_time(
    new_timestamp: float,
    member_name: str,
    name: str,
    lag_in_sec: float,
    levels: tuple[float, float, float],
) -> CheckResult:
    member_state_name = f"mongodb.replica.set.lag.{member_name}"
    value_store = get_value_store()
    if lag_in_sec > levels[0]:
        last_timestamp = value_store.get(member_state_name, 0.0)
        lag_duration = new_timestamp - last_timestamp

        if last_timestamp == 0:
            value_store[member_state_name] = new_timestamp
            return

        yield from check_levels_v1(
            lag_duration,
            levels_upper=levels[1:],
            render_func=render.timespan,
            label=f"{member_name} is behind {name} for",
        )
    else:
        value_store[member_state_name] = 0.0


def _get_long_output(
    member_name: str, member_optime_date: float, replication_lag_sec: float, name: str
) -> str:
    log = []
    log.append(f"source: {member_name}")
    log.append(
        f"syncedTo: {datetime.datetime.fromtimestamp(member_optime_date).strftime('%Y-%m-%d %H:%M:%S')} (UTC)"
    )
    log.append(
        f"member ({member_name}) is {round(replication_lag_sec)}s "
        f"({round((replication_lag_sec / 36) / 100.0)}h) behind {name}"
    )
    log.append("")
    return "\n".join(log)


def _get_start_timestamp(
    primary: Mapping[str, Any], secondaries: list[Mapping[str, Any]]
) -> tuple[float, str]:
    start_operation_timestamp = 0.0
    name = "unknown"
    if primary:
        start_operation_timestamp = parse_date(primary.get("optimeDate", {}).get("$date", 0))
        name = f"primary ({primary.get('name')})"
    else:
        index_to_delete = -1
        for index, member in enumerate(secondaries):
            timestamp = parse_date(member.get("optimeDate", {}).get("$date", 0))
            if timestamp > start_operation_timestamp:
                start_operation_timestamp = timestamp
                name = f"freshest member ({member.get('name')}, no primary available at the moment)"
                index_to_delete = index

        if index_to_delete != -1:
            secondaries.pop(index_to_delete)

    return start_operation_timestamp, name


def _calculate_replication_lag(
    start_operation_time: float, secondary_operation_time: float
) -> float:
    return start_operation_time - secondary_operation_time


agent_section_mongodb_replica_set = AgentSection(
    name="mongodb_replica_set",
    parse_function=parse_mongodb_replica_set,
)


check_plugin_mongodb_replica_set = CheckPlugin(
    name="mongodb_replica_set",
    service_name="MongoDB Replication Lag",
    discovery_function=discover_mongodb_replica_set,
    check_function=check_mongodb_replica_set_lag,
    check_ruleset_name="mongodb_replica_set",
    check_default_parameters=CHECK_DEFAULT_PARAMETERS,
)


#   .--primary election----------------------------------------------------.


def check_mongodb_primary_election(section: Section) -> CheckResult:
    if not section.get("members"):
        yield Result(state=State.WARN, summary="Replica set has no members")
        return

    primary_dict = _get_primary(section.get("members", []))[0]
    primary_name = primary_dict.get("name", None)
    primary_election_time = _get_primary_election_time(primary_dict)

    if not primary_name or not primary_election_time:
        yield Result(state=State.WARN, summary="Can not retrieve primary name and election date")
        return

    value_store = get_value_store()
    last_primary_dict = value_store.get("mongodb_primary_election", {})

    primary_name_changed = bool(
        last_primary_dict and last_primary_dict.get("name", primary_name) != primary_name
    )
    election_date_changed = bool(
        last_primary_dict
        and last_primary_dict.get("election_time", primary_election_time) != primary_election_time
    )

    if last_primary_dict and (primary_name_changed or election_date_changed):
        reason = "node changed" if primary_name_changed else "election date changed"
        yield Result(
            state=State.WARN,
            summary=(
                f"New primary '{primary_name}' elected "
                f"{render.datetime(primary_election_time)} ({reason})"
            ),
        )
    else:
        yield Result(
            state=State.OK,
            summary=f"Primary '{primary_name}' elected {render.datetime(primary_election_time)}",
        )

    value_store["mongodb_primary_election"] = {
        "name": primary_name,
        "election_time": primary_election_time,
    }


def _get_primary_election_time(primary: Mapping[str, Any]) -> float | None:
    if not primary:
        return None
    timestamp: float | None = primary.get("electionTime", {}).get("$timestamp", {}).get("t", None)
    return timestamp


check_plugin_mongodb_replica_set_election = CheckPlugin(
    name="mongodb_replica_set_election",
    service_name="MongoDB Replica Set Primary Election",
    sections=["mongodb_replica_set"],
    discovery_function=discover_mongodb_replica_set,
    check_function=check_mongodb_primary_election,
)


def _get_primary(
    member_list: list[Mapping[str, Any]],
) -> tuple[Mapping[str, Any], list[Mapping[str, Any]]]:
    primary: Mapping[str, Any] = {}
    secondaries = []
    for member in member_list:
        if member.get("state", -1) == ReplicaState.PRIMARY:
            primary = member
            continue
        if member.get("state", -1) == ReplicaState.ARBITER:
            continue

        secondaries.append(member)
    return primary, secondaries
