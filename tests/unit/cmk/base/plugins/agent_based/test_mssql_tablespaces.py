#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Any, Mapping, Optional

import pytest

from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, Service, State
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import (
    CheckResult,
    DiscoveryResult,
    StringTable,
)
from cmk.base.plugins.agent_based.mssql_tablespaces import (
    cluster_check,
    check,
    discover,
    MSSQLTableSpace,
    parse,
    SectionTableSpaces,
)

WORKING_STRING_TABLE = [[
    "MSSQL_SQLEXPRESS",
    "master",
    "5.25",
    "MB",
    "1.59",
    "MB",
    "2464",
    "KB",
    "1096",
    "KB",
    "1024",
    "KB",
    "344",
    "KB",
]]

ERROR_STRING_TABLE = [
    ["MSSQL_Katze", "Kitty"] + ["-"] * 12 + "ERROR: Kitty ist auf die Nase gefallen!".split(" "),
]


@pytest.mark.parametrize(
    "string_table, expected_section",
    [
        pytest.param(
            WORKING_STRING_TABLE,
            {
                "MSSQL_SQLEXPRESS master": MSSQLTableSpace(
                    size=5505024.0,
                    unallocated=1667235.84,
                    reserved=2523136.0,
                    data=1122304.0,
                    indexes=1048576.0,
                    unused=352256.0,
                    error=None,
                )
            },
            id="working table",
        ),
        pytest.param(
            ERROR_STRING_TABLE,
            {
                "MSSQL_Katze Kitty": MSSQLTableSpace(
                    size=None,
                    unallocated=None,
                    reserved=None,
                    data=None,
                    indexes=None,
                    unused=None,
                    error="Kitty ist auf die Nase gefallen!",
                )
            },
            id="error",
        ),
    ],
)
def test_parse(string_table: StringTable, expected_section: SectionTableSpaces) -> None:
    assert parse(string_table) == expected_section


@pytest.mark.parametrize(
    "string_table, expected_services",
    [
        pytest.param(WORKING_STRING_TABLE, [Service(item="MSSQL_SQLEXPRESS master")],
                     id="working table"),
        pytest.param(ERROR_STRING_TABLE, [], id="error"),
    ],
)
def test_discover(string_table: StringTable, expected_services: DiscoveryResult) -> None:
    assert list(discover(parse(string_table))) == expected_services


@pytest.mark.parametrize(
    "item, params, string_table, expected_result",
    [
        pytest.param(
            "MSSQL_SQLEXPRESS master",
            {},
            WORKING_STRING_TABLE,
            [
                Result(state=State.OK, summary="Size: 5.25 MiB"),
                Metric(name="size", value=5505024.0),
                Result(state=State.OK, summary="Unallocated space: 1.59 MiB, 30.29%"),
                Metric(name="unallocated", value=1667235.84),
                Result(state=State.OK, summary="Reserved space: 2.41 MiB, 45.83%"),
                Metric(name="reserved", value=2523136.0),
                Result(state=State.OK, summary="Data: 1.07 MiB, 20.39%"),
                Metric(name="data", value=1122304.0),
                Result(state=State.OK, summary="Indexes: 1.00 MiB, 19.05%"),
                Metric(name="indexes", value=1048576.0),
                Result(state=State.OK, summary="Unused: 344 KiB, 6.40%"),
                Metric(name="unused", value=352256.0),
            ],
            id="no levels",
        ),
        pytest.param(
            "MSSQL_SQLEXPRESS master",
            {
                "size": (3 * 1024**2, 6 * 1024**2),
                "unallocated": (3146000, 2097000),
                "reserved": (30.0, 40.0),
            },
            WORKING_STRING_TABLE,
            [
                Result(state=State.WARN, summary="Size: 5.25 MiB (warn/crit at 3.00 MiB/6.00 MiB)"),
                Metric("size", 5505024.0, levels=(3145728.0, 6291456.0)),
                Result(
                    state=State.CRIT,
                    summary=
                    "Unallocated space: 1.59 MiB, 30.29% (warn/crit below 3.00 MiB/2.00 MiB)",
                ),
                Metric(name="unallocated", value=1667235.84),
                Result(
                    state=State.CRIT,
                    summary="Reserved space: 2.41 MiB, 45.83% (warn/crit at 30.00%/40.00%)",
                ),
                Metric("reserved", 2523136.0),
                Result(state=State.OK, summary="Data: 1.07 MiB, 20.39%"),
                Metric("data", 1122304.0),
                Result(state=State.OK, summary="Indexes: 1.00 MiB, 19.05%"),
                Metric("indexes", 1048576.0),
                Result(state=State.OK, summary="Unused: 344 KiB, 6.40%"),
                Metric("unused", 352256.0),
            ],
            id="levels",
        ),
        pytest.param(
            "MSSQL_Katze Kitty",
            {},
            ERROR_STRING_TABLE,
            [
                Result(state=State.CRIT, summary="Kitty ist auf die Nase gefallen!"),
            ],
            id="error",
        ),
    ],
)
def test_check(item: str, params: Mapping[str, Any], string_table: StringTable,
               expected_result: CheckResult) -> None:
    assert list(check(item, params, parse(string_table))) == expected_result


@pytest.mark.parametrize(["section", "expected_result"], [
    pytest.param(
        {
            'mssql-databases': {
                'MSSQL_MSSQL46 testdb': MSSQLTableSpace(size=5505024.0,
                                                        unallocated=1667235.84,
                                                        reserved=2523136.0,
                                                        data=1122304.0,
                                                        indexes=1048576.0,
                                                        unused=352256.0,
                                                        error=None)
            },
            'mssql-databases-2': {
                'MSSQL_MSSQL46 testdb': MSSQLTableSpace(size=22020096.0,
                                                        unallocated=6375342.08,
                                                        reserved=10420224.0,
                                                        data=2244608.0,
                                                        indexes=2097152.0,
                                                        unused=704512.0,
                                                        error=None)
            }
        }, [
            Result(state=State.OK, summary="Size: 5.25 MiB"),
            Metric(name="size", value=5505024.0),
            Result(state=State.OK, summary="Unallocated space: 1.59 MiB, 30.29%"),
            Metric(name="unallocated", value=1667235.84),
            Result(state=State.OK, summary="Reserved space: 2.41 MiB, 45.83%"),
            Metric(name="reserved", value=2523136.0),
            Result(state=State.OK, summary="Data: 1.07 MiB, 20.39%"),
            Metric(name="data", value=1122304.0),
            Result(state=State.OK, summary="Indexes: 1.00 MiB, 19.05%"),
            Metric(name="indexes", value=1048576.0),
            Result(state=State.OK, summary="Unused: 344 KiB, 6.40%"),
            Metric(name="unused", value=352256.0),
        ],
        id="take first node"),
    pytest.param(
        {
            'mssql-databases': None,
            'mssql-databases-2': {
                'MSSQL_MSSQL46 testdb': MSSQLTableSpace(size=22020096.0,
                                                        unallocated=6375342.08,
                                                        reserved=10420224.0,
                                                        data=2244608.0,
                                                        indexes=2097152.0,
                                                        unused=704512.0,
                                                        error=None)
            }
        }, [
            Result(state=State.OK, summary='Size: 21.0 MiB'),
            Metric('size', 22020096.0),
            Result(state=State.OK, summary='Unallocated space: 6.08 MiB, 28.95%'),
            Metric('unallocated', 6375342.08),
            Result(state=State.OK, summary='Reserved space: 9.94 MiB, 47.32%'),
            Metric('reserved', 10420224.0),
            Result(state=State.OK, summary='Data: 2.14 MiB, 10.19%'),
            Metric('data', 2244608.0),
            Result(state=State.OK, summary='Indexes: 2.00 MiB, 9.52%'),
            Metric('indexes', 2097152.0),
            Result(state=State.OK, summary='Unused: 688 KiB, 3.20%'),
            Metric('unused', 704512.0)
        ],
        id="take second node"),
])
def test_cluster_check(section: Mapping[str, Optional[SectionTableSpaces]],
                       expected_result: CheckResult) -> None:

    assert list(cluster_check('MSSQL_MSSQL46 testdb', {}, section)) == expected_result
