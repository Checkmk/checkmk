#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re
from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
from typing import Final

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    State,
    StringTable,
)

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
    PARTIALLY_HEALTHY = "PARTIALLY_HEALTHY"


@dataclass(frozen=True)
class AGAttributes:
    primary_replica: str
    sync_state: SyncState


@dataclass(frozen=True)
class ErrorMessage:
    instance: str
    message: str


Section = Mapping[str, AGAttributes]


_SYNC_STATE_MAPPING: Final[Mapping] = {
    SyncState.HEALTHY: State.OK,
    SyncState.NOT_HEALTHY: State.CRIT,
    SyncState.PARTIALLY_HEALTHY: State.WARN,
}

_ERROR_REGEX = re.compile(r"(.*) ERROR: (.*)")


def _match_error_message(string_table: StringTable) -> ErrorMessage | None:
    try:
        if (error_match := _ERROR_REGEX.match(string_table[0][0])) is None:
            return None
    except IndexError:
        return None

    return ErrorMessage(instance=error_match.group(1), message=error_match.group(2))


def parse_mssql_availability_groups(string_table: StringTable) -> Section | ErrorMessage:
    if (error_msg := _match_error_message(string_table)) is not None:
        return error_msg

    return {
        line[0]: AGAttributes(line[1], SyncState(line[3]))
        for line in string_table
        if len(line) >= 4
    }


def discover_mssql_availability_groups(section: Section | ErrorMessage) -> DiscoveryResult:
    if isinstance(section, ErrorMessage):
        return

    for availability_group in section:
        yield Service(item=availability_group)


def check_mssql_availability_groups(item: str, section: Section | ErrorMessage) -> CheckResult:
    if isinstance(section, ErrorMessage):
        yield Result(
            state=State.UNKNOWN,
            summary=f"Error message from instance {section.instance}: {section.message}",
        )
        return

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


agent_section_mssql_availability_groups = AgentSection(
    name="mssql_availability_groups",
    parse_function=parse_mssql_availability_groups,
)

check_plugin_mssql_availability_groups = CheckPlugin(
    name="mssql_availability_groups",
    discovery_function=discover_mssql_availability_groups,
    check_function=check_mssql_availability_groups,
    service_name="MSSQL Availability Group %s",
)
