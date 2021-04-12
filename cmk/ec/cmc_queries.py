#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, Mapping, NamedTuple, Sequence, Set

from cmk.utils.type_defs import ContactgroupName, HostAddress, HostName, Timestamp, UserId
from livestatus import LocalConnection, MKLivestatusNotFoundError  # noqa: F401 # pylint: disable=unused-import

################################################################################


class HostInfo(NamedTuple):
    name: HostName
    alias: str
    address: HostAddress
    custom_variables: Mapping[str, str]
    contacts: Set[UserId]
    contact_groups: Set[ContactgroupName]


def _create_host_info(row: Mapping[str, Any]) -> HostInfo:
    return HostInfo(
        name=row['name'],
        alias=row['alias'],
        address=row['address'],
        custom_variables=row['custom_variables'],
        contacts={UserId(c) for c in row['contacts']},
        contact_groups=set(row['contact_groups']),
    )


def query_hosts_infos() -> Sequence[HostInfo]:
    return [
        _create_host_info(row)  #
        for row in LocalConnection().query_table_assoc(
            "GET hosts\n"
            "Columns: name alias address custom_variables contacts contact_groups")
    ]


################################################################################


def query_status_program_start() -> Timestamp:
    return LocalConnection().query_value("GET status\n"  #
                                         "Columns: program_start")
