#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.utils.type_defs import CheckPluginName

from cmk.base.plugins.agent_based.agent_based_api.v1 import Result, Service, State, TableRow
from cmk.base.plugins.agent_based.mssql_instance import (
    inventory_mssql_instance,
    parse_mssql_instance,
)

from .utils_inventory import sort_inventory_result

_AGENT_OUTPUT_1 = [
    ["MSSQL_MSSQLSERVER", "config", "10.50.6000.34", "Standard Edition", ""],
    ["MSSQL_ABC", "config", "10.50.6000.34", "Standard Edition", ""],
    ["MSSQL_ABCDEV", "config", "10.50.6000.34", "Standard Edition", ""],
    ["MSSQL_MSSQLSERVER", "state", "1", ""],
    ["MSSQL_ABC", "state", "1", ""],
    [
        "MSSQL_ABCDEV",
        "state",
        "0",
        "[DBNETLIB][ConnectionOpen (Connect()).]SQL Server existiert nicht oder Zugriff verweigert.",
    ],
    ["Hier kommt eine laaaangre Fehlermeldung"],
    ["die sich ueber                mehrere             Zeilen ersteckt"],
]

_AGENT_OUTPUT_2 = [
    ["MSSQL_SQL2019MT02", "config", "15.0.2000.5", "Standard Edition", ""],
    ["MSSQL_SQL2019MT02", "state", "1", ""],
    [
        "MSSQL_SQL2019MT02",
        "details",
        "15.0.4053.23",
        "RTM",
        "Standard Edition (64-bit)",
    ],
    ["MSSQL_SQL2017MT02", "config", "14.0.2000.5", "Standard Edition", ""],
    ["MSSQL_SQL2017MT02", "state", "1", ""],
    [
        "MSSQL_SQL2017MT02",
        "details",
        "14.0.4053.23",
        "RTM",
        "Standard Edition (64-bit)",
    ],
    ["MSSQL_SQL2016MT02", "config", "13.0.2000.5", "Standard Edition", ""],
    ["MSSQL_SQL2016MT02", "state", "1", ""],
    [
        "MSSQL_SQL2016MT02",
        "details",
        "13.0.4053.23",
        "RTM",
        "Standard Edition (64-bit)",
    ],
    ["MSSQL_SQL2014MT02", "config", "12.0.2000.5", "Standard Edition", ""],
    ["MSSQL_SQL2014MT02", "state", "1", ""],
    [
        "MSSQL_SQL2014MT02",
        "details",
        "12.0.4053.23",
        "RTM",
        "Standard Edition (64-bit)",
    ],
    ["MSSQL_SQL2012MT02", "config", "11.0.2000.5", "Standard Edition", ""],
    ["MSSQL_SQL2012MT02", "state", "1", ""],
    [
        "MSSQL_SQL2012MT02",
        "details",
        "11.0.4053.23",
        "RTM",
        "Standard Edition (64-bit)",
    ],
    ["MSSQL_SQL2008R2MT02", "config", "10.50.2000.5", "Standard Edition", ""],
    ["MSSQL_SQL2008R2MT02", "state", "1", ""],
    [
        "MSSQL_SQL2008R2MT02",
        "details",
        "10.50.4053.23",
        "RTM",
        "Standard Edition (64-bit)",
    ],
    ["MSSQL_SQL2008MT02", "config", "10.0.2000.5", "Standard Edition", ""],
    ["MSSQL_SQL2008MT02", "state", "1", ""],
    [
        "MSSQL_SQL2008MT02",
        "details",
        "10.0.4053.23",
        "RTM",
        "Standard Edition (64-bit)",
    ],
    ["MSSQL_SQL2005MT02", "config", "9.0.2000.5", "Standard Edition", ""],
    ["MSSQL_SQL2005MT02", "state", "1", ""],
    ["MSSQL_SQL2005MT02", "details", "9.0.4053.23", "RTM", "Standard Edition (64-bit)"],
    ["MSSQL_SQL2000MT02", "config", "8.0.2000.5", "Standard Edition", ""],
    ["MSSQL_SQL2000MT02", "state", "1", ""],
    ["MSSQL_SQL2000MT02", "details", "8.0.4053.23", "RTM", "Standard Edition (64-bit)"],
]


@pytest.mark.parametrize(
    "string_table, expected_result",
    [
        (
            _AGENT_OUTPUT_1,
            [
                Service(item="ABC"),
                Service(item="ABCDEV"),
                Service(item="MSSQLSERVER"),
            ],
        ),
        (
            _AGENT_OUTPUT_2,
            [
                Service(item="SQL2000MT02"),
                Service(item="SQL2005MT02"),
                Service(item="SQL2008MT02"),
                Service(item="SQL2008R2MT02"),
                Service(item="SQL2012MT02"),
                Service(item="SQL2014MT02"),
                Service(item="SQL2016MT02"),
                Service(item="SQL2017MT02"),
                Service(item="SQL2019MT02"),
            ],
        ),
    ],
)
def test_discover_mssql_instance(fix_register, string_table, expected_result) -> None:
    check_plugin = fix_register.check_plugins[CheckPluginName("mssql_instance")]
    section = parse_mssql_instance(string_table)
    assert sorted(check_plugin.discovery_function(section)) == expected_result


@pytest.mark.parametrize(
    "string_table, item, expected_result",
    [
        (
            _AGENT_OUTPUT_1,
            "ABC",
            [Result(state=State.OK, summary="Version: 10.50.6000.34 - Standard Edition")],
        ),
        (
            _AGENT_OUTPUT_1,
            "ABCDEV",
            [
                Result(
                    state=State.CRIT,
                    summary="Failed to connect to database ([DBNETLIB][ConnectionOpen (Connect()).]SQL Server existiert nicht oder Zugriff verweigert.)",
                ),
                Result(state=State.OK, summary="Version: 10.50.6000.34 - Standard Edition"),
            ],
        ),
        (
            _AGENT_OUTPUT_1,
            "MSSQLSERVER",
            [Result(state=State.OK, summary="Version: 10.50.6000.34 - Standard Edition")],
        ),
        (
            _AGENT_OUTPUT_2,
            "SQL2000MT02",
            [
                Result(
                    state=State.OK,
                    summary="Version: Microsoft SQL Server 2000 (RTM) (8.0.4053.23) - Standard Edition (64-bit)",
                )
            ],
        ),
        (
            _AGENT_OUTPUT_2,
            "SQL2005MT02",
            [
                Result(
                    state=State.OK,
                    summary="Version: Microsoft SQL Server 2005 (RTM) (9.0.4053.23) - Standard Edition (64-bit)",
                )
            ],
        ),
        (
            _AGENT_OUTPUT_2,
            "SQL2008MT02",
            [
                Result(
                    state=State.OK,
                    summary="Version: Microsoft SQL Server 2008 (RTM) (10.0.4053.23) - Standard Edition (64-bit)",
                )
            ],
        ),
        (
            _AGENT_OUTPUT_2,
            "SQL2008R2MT02",
            [
                Result(
                    state=State.OK,
                    summary="Version: Microsoft SQL Server 2008R2 (RTM) (10.50.4053.23) - Standard Edition (64-bit)",
                )
            ],
        ),
        (
            _AGENT_OUTPUT_2,
            "SQL2012MT02",
            [
                Result(
                    state=State.OK,
                    summary="Version: Microsoft SQL Server 2012 (RTM) (11.0.4053.23) - Standard Edition (64-bit)",
                )
            ],
        ),
        (
            _AGENT_OUTPUT_2,
            "SQL2014MT02",
            [
                Result(
                    state=State.OK,
                    summary="Version: Microsoft SQL Server 2014 (RTM) (12.0.4053.23) - Standard Edition (64-bit)",
                )
            ],
        ),
        (
            _AGENT_OUTPUT_2,
            "SQL2016MT02",
            [
                Result(
                    state=State.OK,
                    summary="Version: Microsoft SQL Server 2016 (RTM) (13.0.4053.23) - Standard Edition (64-bit)",
                )
            ],
        ),
        (
            _AGENT_OUTPUT_2,
            "SQL2017MT02",
            [
                Result(
                    state=State.OK,
                    summary="Version: Microsoft SQL Server 2017 (RTM) (14.0.4053.23) - Standard Edition (64-bit)",
                )
            ],
        ),
        (
            _AGENT_OUTPUT_2,
            "SQL2019MT02",
            [
                Result(
                    state=State.OK,
                    summary="Version: Microsoft SQL Server 2019 (RTM) (15.0.4053.23) - Standard Edition (64-bit)",
                )
            ],
        ),
    ],
)
def test_check_mssql_instance(fix_register, string_table, item, expected_result) -> None:
    check_plugin = fix_register.check_plugins[CheckPluginName("mssql_instance")]
    section = parse_mssql_instance(string_table)
    assert (
        list(check_plugin.check_function(item=item, params={}, section=section)) == expected_result
    )


@pytest.mark.parametrize(
    "string_table, expected_result",
    [
        ([], []),
        (
            [
                [
                    "MSSQL_MSSQLSERVER2",
                    "config",
                    "13.2.5026.0",
                    "Enterprise Edition: Core-based Licensing",
                    "",
                ],
                ["MSSQL_MSSQLSERVER2", "state", "1", ""],
                [
                    "MSSQL_MSSQLSERVER2",
                    "details",
                    "13.0.5622.0",
                    "SP2",
                    "Enterprise Edition: Core-based Licensing (64-bit)",
                ],
                [
                    "MSSQLSERVER",
                    "config",
                    "13.2.5026.0",
                    "Enterprise Edition: Core-based Licensing",
                    "",
                ],
                ["MSSQL_MSSQLSERVER", "state", "1", ""],
                [
                    "MSSQLSERVER",
                    "details",
                    "13.0.5622.0",
                    "SP2",
                    "Enterprise Edition: Core-based Licensing (64-bit)",
                ],
            ],
            [
                TableRow(
                    path=["software", "applications", "mssql", "instances"],
                    key_columns={
                        "name": "MSSQLSERVER",
                    },
                    inventory_columns={
                        "version": "13.2.5026.0",
                        "edition": "Enterprise Edition: Core-based Licensing",
                        "product": "Microsoft SQL Server 2016",
                        "clustered": False,
                        "cluster_name": "",
                    },
                    status_columns={},
                ),
                TableRow(
                    path=["software", "applications", "mssql", "instances"],
                    key_columns={
                        "name": "MSSQLSERVER2",
                    },
                    inventory_columns={
                        "version": "13.2.5026.0",
                        "edition": "Enterprise Edition: Core-based Licensing",
                        "product": "Microsoft SQL Server 2016",
                        "clustered": False,
                        "cluster_name": "",
                    },
                    status_columns={},
                ),
            ],
        ),
    ],
)
def test_inventory_mssql_instance(string_table, expected_result) -> None:
    assert sort_inventory_result(
        inventory_mssql_instance(parse_mssql_instance(string_table))
    ) == sort_inventory_result(expected_result)
