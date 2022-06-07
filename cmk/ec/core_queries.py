#!/usr/bin/env python3
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, Iterable, Mapping, NamedTuple, Sequence

from livestatus import LocalConnection

from cmk.utils.type_defs import (
    ContactgroupName,
    HostAddress,
    HostName,
    TimeperiodName,
    Timestamp,
    UserId,
)

################################################################################


# NOTE: This function is a polished copy of cmk/base/notify.py. :-/
def query_contactgroups_members(group_names: Iterable[ContactgroupName]) -> set[UserId]:
    query = "GET contactgroups\nColumns: members"
    num_group_names = 0
    for group_name in group_names:
        query += f"\nFilter: name = {group_name}"
        num_group_names += 1
    query += f"\nOr: {num_group_names}"
    contact_lists: list[list[str]] = (
        LocalConnection().query_column(query) if num_group_names else []
    )
    return {UserId(contact) for contact_list in contact_lists for contact in contact_list}


################################################################################


class HostInfo(NamedTuple):
    name: HostName
    alias: str
    address: HostAddress
    custom_variables: Mapping[str, str]
    contacts: set[UserId]
    contact_groups: set[ContactgroupName]


def _create_host_info(row: Mapping[str, Any]) -> HostInfo:
    return HostInfo(
        name=row["name"],
        alias=row["alias"],
        address=row["address"],
        custom_variables=row["custom_variables"],
        contacts={UserId(c) for c in row["contacts"]},
        contact_groups=set(row["contact_groups"]),
    )


def query_hosts_infos() -> Sequence[HostInfo]:
    return [
        _create_host_info(row)  #
        for row in LocalConnection().query_table_assoc(
            "GET hosts\nColumns: name alias address custom_variables contacts contact_groups"
        )
    ]


################################################################################


def query_hosts_scheduled_downtime_depth(host_name: HostName) -> int:
    return LocalConnection().query_value(
        "GET hosts\nColumns: scheduled_downtime_depth\n" f"Filter: host_name = {host_name}"
    )


################################################################################


def query_status_program_start() -> Timestamp:
    return LocalConnection().query_value("GET status\nColumns: program_start")  #


################################################################################


def query_status_enable_notifications() -> bool:
    return bool(LocalConnection().query_value("GET status\nColumns: enable_notifications"))  #


################################################################################


def query_timeperiods_in() -> Mapping[TimeperiodName, bool]:
    return {
        name: bool(in_)  #
        for name, in_ in LocalConnection().query("GET timeperiods\nColumns: name in")  #
    }
