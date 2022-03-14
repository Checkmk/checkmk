#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

#################################################################################
# NOTE: This check really only makes sense as a cluster check!
#       Read comment in parse function to understand why.
#################################################################################

# Microsoft documentation:
# https://docs.microsoft.com/en-us/sql/relational-databases/system-catalog-views/
# sys-database-mirroring-transact-sql?view=sql-server-ver15

# database table: sys.database_mirroring (on database [master])

# mirroring states:
#                    0    = Suspended
#                    1    = Disconnected from the other partner
#                    2    = Synchronizing
#                    3    = Pending Failover
#                    4    = Synchronized
#                    5    = The partners are not synchronized. Failover is not possible now.
#                    6    = The partners are synchronized. Failover is potentially possible.
#                    NULL = Database is inaccessible or is not mirrored. This case is
#                           filtered out by the agent plugin, as these instances are not
#                           relevant.

# mirroring witness states:
#                           0    = Unknown
#                           1    = Connected
#                           2    = Disconnected
#                           NULL = No witness exists, the database is not online or the
#                                  database is not mirrored.

from typing import Mapping, NamedTuple, Optional, Sequence

from cmk.base.plugins.agent_based.agent_based_api.v1 import register, Result, Service, State
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import (
    CheckResult,
    DiscoveryResult,
    StringTable,
)


class MirroringConfig(NamedTuple):
    server_name: str
    database_name: str
    mirroring_state: int
    mirroring_state_desc: str
    mirroring_role: int
    mirroring_role_desc: str
    mirroring_safety_level: int
    mirroring_safety_level_desc: str
    mirroring_partner_name: str
    mirroring_partner_instance: str
    mirroring_witness_name: str
    mirroring_witness_state: int
    mirroring_witness_state_desc: str


MirroringSection = Mapping[str, MirroringConfig]


def _convert_datatypes(raw_configline: Sequence) -> Sequence:
    """
    >>> _convert_datatypes(['', '', '72', '', '20', '', '68', '', '', '', '', '42', ''])
    ['', '', 72, '', 20, '', 68, '', '', '', '', 42, '']

    """
    return [int(e[1]) if e[0] in {2, 4, 6, 11} else e[1] for e in enumerate(raw_configline)]


def _title_from_header(raw_header: str) -> str:
    """
    >>> _title_from_header('mirroring_state_desc')
    'Mirroring state'
    >>> _title_from_header('database_name')
    'Database name'
    """
    return raw_header.replace("_desc", "").replace("_", " ").capitalize()


def _details_text(detail: str, mirroring_config: MirroringConfig) -> str:
    """
    >>> _details_text('mirroring_state_desc', MirroringConfig(
    ... server_name='',
    ... database_name='',
    ... mirroring_state=0,
    ... mirroring_state_desc='This is the interesting bit',
    ... mirroring_role='',
    ... mirroring_role_desc='',
    ... mirroring_safety_level=0,
    ... mirroring_safety_level_desc='',
    ... mirroring_partner_name='',
    ... mirroring_partner_instance='',
    ... mirroring_witness_name='',
    ... mirroring_witness_state=0,
    ... mirroring_witness_state_desc='',
    ... ))
    'Mirroring state: This is the interesting bit'
    """
    return f"{_title_from_header(detail)}: {getattr(mirroring_config, detail)}"


def parse_mssql_mirroring(string_table: StringTable) -> MirroringSection:
    section = {}

    for raw_configline in string_table:
        if len(raw_configline) != 13:
            continue
        if raw_configline[5] != "PRINCIPAL":
            # NOTE: From two hosts (main and failover), we may get the following lines:

            # server_name   ... database_name   ... mirroring_state_desc    ... mirroring_role_desc  ... mirroring_parter_name   ...
            # server1       ... mydb            ... SYNCHRONISED            ... PRINCIPAL            ... mydb_backup             ...
            # server2       ... mydb_backup     ... SYNCHRONISED            ... MIRROR               ... mydb                    ...

            # This leads to duplicate services and alerts in the event that services are not clustered.
            # To avoid this, mirrors are actively skipped. Also, the monitoring user that queries the
            # databases' mirroring status needs extended permissions to view any mirroring role other
            # than "PRINCIPAL". These include destructive permissions, which should not be given to the
            # user. Mirros are still skipped to be safe.
            continue
        mirroring_config = MirroringConfig(*_convert_datatypes(raw_configline))
        section[mirroring_config.database_name] = mirroring_config

    return section


register.agent_section(
    name="mssql_mirroring",
    parse_function=parse_mssql_mirroring,
)


def discover_mssql_mirroring(section: MirroringSection) -> DiscoveryResult:
    yield from (Service(item=database_name) for database_name in section)


def check_mssql_mirroring(
    item: str,
    params: Mapping[str, int],  # the int is actually a Checkmk state
    section: MirroringSection,
) -> CheckResult:

    mirroring_config = section.get(item)
    if not mirroring_config:
        return

    yield Result(
        state=State.OK,
        summary=f"Principal: {mirroring_config.server_name}",
    )
    yield Result(
        state=State.OK,
        summary=f"Mirror: {mirroring_config.mirroring_partner_instance}",
    )

    # For an explanation of state mappings, see comment at beginning
    for state_to_check, desired_state, criticality in [
        ("mirroring_state", 4, params["mirroring_state_criticality"]),
        ("mirroring_witness_state", 1, params["mirroring_witness_state_criticality"]),
    ]:
        state = State.OK
        if getattr(mirroring_config, state_to_check) != desired_state:
            state = State(criticality)
        yield Result(
            state=state,
            notice=_details_text(f"{state_to_check}_desc", mirroring_config),
        )

    for detail in [
        "mirroring_safety_level_desc",
        "mirroring_partner_name",
        "mirroring_witness_name",
    ]:
        yield Result(state=State.OK, notice=_details_text(detail, mirroring_config))


def cluster_check_mssql_mirroring(
    item: str,
    params: Mapping[str, int],  # the int is actually a Checkmk state
    section: Mapping[str, Optional[MirroringSection]],
) -> CheckResult:

    node_results = {
        node_name: list(check_mssql_mirroring(item, params, node_section))
        for node_name, node_section in section.items()
        if node_section
    }
    results = {k: v for k, v in node_results.items() if v}

    if len(results) > 1:
        yield Result(
            state=State.CRIT,
            summary=f"Found principal database on more than one node: {(', ').join(results.keys())}",
        )
        return

    yield from (result for result_set in results.values() for result in result_set)


register.check_plugin(
    name="mssql_mirroring",
    sections=["mssql_mirroring"],
    service_name="MSSQL Mirroring Status: %s",
    discovery_function=discover_mssql_mirroring,
    check_function=check_mssql_mirroring,
    cluster_check_function=cluster_check_mssql_mirroring,
    check_ruleset_name="mssql_mirroring",
    check_default_parameters={
        "mirroring_state_criticality": 0,
        "mirroring_witness_state_criticality": 0,
    },
)
