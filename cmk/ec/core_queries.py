#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Protocol

from cmk.ccc.hostaddress import HostAddress, HostName
from cmk.ccc.user import UserId

from .config import TimeperiodName

_ContactgroupName = str
_HostGroupName = str


class Connection(Protocol):
    def query(self, query: str) -> Sequence[Sequence[Any]]: ...


# NOTE: This function is a polished copy of cmk/base/notify.py. :-/
def query_contactgroups_members(
    connection: Connection, group_names: Iterable[_ContactgroupName]
) -> set[UserId]:
    query = "GET contactgroups\nColumns: members"
    num_group_names = 0
    for group_name in group_names:
        query += f"\nFilter: name = {group_name}"
        num_group_names += 1
    query += f"\nOr: {num_group_names}"
    return {
        UserId(contact)
        for row in (connection.query(query) if num_group_names else [])
        for contact in row[0]
    }


@dataclass(frozen=True, kw_only=True)
class HostInfo:
    name: HostName
    alias: str
    address: HostAddress
    custom_variables: Mapping[str, str]
    contacts: set[UserId]
    contact_groups: set[_ContactgroupName]
    host_groups: set[_HostGroupName]


def query_hosts_infos(connection: Connection) -> Sequence[HostInfo]:
    return [
        HostInfo(
            name=name,
            alias=alias,
            address=address,
            custom_variables=custom_variables,
            contacts={UserId(contact) for contact in contacts},
            contact_groups=set(contact_groups),
            host_groups=set(groups),
        )
        for name, alias, address, custom_variables, contacts, contact_groups, groups in connection.query(
            "GET hosts\nColumns: name alias address custom_variables contacts contact_groups groups"
        )
    ]


def query_hosts_scheduled_downtime_depth(connection: Connection, host_name: HostName) -> int:
    return int(
        connection.query(
            f"GET hosts\nColumns: scheduled_downtime_depth\nFilter: host_name = {host_name}"
        )[0][0]
    )


def query_status_program_start(connection: Connection) -> int:
    return int(connection.query("GET status\nColumns: program_start")[0][0])


def query_status_enable_notifications(connection: Connection) -> bool:
    return bool(connection.query("GET status\nColumns: enable_notifications")[0][0])


def query_timeperiods_in(connection: Connection) -> Mapping[TimeperiodName, bool]:
    return {name: bool(in_) for name, in_ in connection.query("GET timeperiods\nColumns: name in")}
