#!/usr/bin/env python3
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from dataclasses import dataclass
from enum import Enum
from typing import Final, Mapping

from .agent_based_api.v1 import register, Result, Service, State
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable

# Sample output:

# <<<mssql_availability_groups>>>
# AGTEST_1 SQL01\TESTINSTANCE1 2 HEALTHY ONLINE
# AGTEST_2 SQL01\TESTINSTANCE1 2 HEALTHY ONLINE
# AGTEST_3 SQL01\TESTINSTANCE2 0 NOT_HEALTHY ONLINE_IN_PROGRESS
#
# Columns are:
# name primary_replica synchronization_health synchronization_health_desc primary_recovery_health_desc


class SyncState(Enum):
    HEALTHY = "HEALTHY"
    NOT_HEALTHY = "NOT_HEALTHY"


@dataclass(frozen=True)
class AGAttributes:
    primary_replica: str
    sync_state: SyncState


Section = Mapping[str, AGAttributes]


_SYNC_STATE_MAPPING: Final[Mapping] = {
    SyncState.HEALTHY: State.OK,
    SyncState.NOT_HEALTHY: State.CRIT,
}


def parse_mssql_availability_groups(string_table: StringTable) -> Section:
    """
    >>> parse_mssql_availability_groups(
    ...   [["AGTEST_1", "SQL01\\\\TESTINSTANCE1", "2", "HEALTHY", "ONLINE"],
    ...    ["AGTEST_2", "SQL01\\\\TESTINSTANCE1", "2", "HEALTHY", "ONLINE"],
    ...    ["AGTEST_3", "SQL01\\\\TESTINSTANCE2", "0", "NOT_HEALTHY", "ONLINE_IN_PROGRESS"]]
    ... ) == {
    ...   "AGTEST_1": AGAttributes("SQL01\\\\TESTINSTANCE1", SyncState.HEALTHY),
    ...   "AGTEST_2": AGAttributes("SQL01\\\\TESTINSTANCE1", SyncState.HEALTHY),
    ...   "AGTEST_3": AGAttributes("SQL01\\\\TESTINSTANCE2", SyncState.NOT_HEALTHY),
    ... }
    True
    """
    return {line[0]: AGAttributes(line[1], SyncState(line[3])) for line in string_table}


def discover_mssql_availability_groups(section: Section) -> DiscoveryResult:
    for availability_group in section:
        yield Service(item=availability_group)


def check_mssql_availability_groups(item: str, section: Section) -> CheckResult:
    """
    >>> section = {
    ...   "AGTEST_1": AGAttributes("SQL01\\\\TESTINSTANCE1", SyncState.HEALTHY),
    ...   "AGTEST_2": AGAttributes("SQL01\\\\TESTINSTANCE1", SyncState.HEALTHY),
    ...   "AGTEST_3": AGAttributes("SQL01\\\\TESTINSTANCE2", SyncState.NOT_HEALTHY),
    ... }
    >>> list(check_mssql_availability_groups("AGTEST_1", section)) == [
    ...   Result(state=State.OK, summary="Primary replica: SQL01\\\\TESTINSTANCE1"),
    ...   Result(state=State.OK, summary="Synchronization state: HEALTHY"),
    ... ]
    True
    >>> list(check_mssql_availability_groups("AGTEST_3", section)) == [
    ...   Result(state=State.OK, summary="Primary replica: SQL01\\\\TESTINSTANCE2"),
    ...   Result(state=State.CRIT, summary="Synchronization state: NOT_HEALTHY"),
    ... ]
    True
    """
    if (attributes := section.get(item)) is None:
        return

    yield Result(
        state=State.OK,
        summary=f"Primary replica: {attributes.primary_replica}",
    )

    yield Result(
        state=_SYNC_STATE_MAPPING[attributes.sync_state],
        summary=f"Synchronization state: {attributes.sync_state.value}",
    )


register.agent_section(
    name="mssql_availability_groups",
    parse_function=parse_mssql_availability_groups,
)

register.check_plugin(
    name="mssql_availability_groups",
    discovery_function=discover_mssql_availability_groups,
    check_function=check_mssql_availability_groups,
    service_name="MSSQL Availability Group %s",
)
