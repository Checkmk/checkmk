#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from typing import Union

import pytest

from tests.unit.conftest import FixRegister

from cmk.utils.type_defs import CheckPluginName, SectionName

from cmk.base.plugins.agent_based.agent_based_api.v1 import Result, Service, State
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import StringTable
from cmk.base.plugins.agent_based.mssql_blocked_sessions import (
    check_mssql_blocked_sessions,
    cluster_check_mssql_blocked_sessions,
    DBInstance,
    DEFAULT_PARAMETERS,
    discovery_mssql_blocked_sessions,
    Params,
    parse_mssql_blocked_sessions,
)

INFO_0 = [
    ["Blocked _Sessions"],
    [
        "119",
        "232292187",
        "LCK_M_U",
        "75",
    ],
    [
        "76",
        "221526672",
        "LCK_M_U",
        "115",
    ],
]

INFO_1 = [
    ["INST_ID1", "No blocking sessions"],
]


def default_parameters(
    *,
    ignore_waittypes: Union[list[str], None] = None,
    waittime: Union[tuple[float, float], None] = None,
) -> Params:
    params = DEFAULT_PARAMETERS.copy()
    if ignore_waittypes is not None:
        params["ignore_waittypes"] = ignore_waittypes
    if waittime is not None:
        params["waittime"] = waittime
    return params


def test_mssql_blocked_sessions_default(
    fix_register: FixRegister,
) -> None:
    parse_function = fix_register.agent_sections[
        SectionName("mssql_blocked_sessions")
    ].parse_function
    plugin = fix_register.check_plugins[CheckPluginName("mssql_blocked_sessions")]
    assert plugin
    assert list(
        plugin.check_function(
            params=DEFAULT_PARAMETERS,
            item="",
            section=parse_function(INFO_0),
        )
    ) == [
        Result(state=State.CRIT, summary="Summary: 119 blocked by 1 ID(s), 76 blocked by 1 ID(s)"),
        Result(
            state=State.OK,
            summary="Session 119 blocked by 75, Type: LCK_M_U, Wait: 2 days 16 hours",
        ),
        Result(
            state=State.OK,
            summary="Session 76 blocked by 115, Type: LCK_M_U, Wait: 2 days 13 hours",
        ),
    ]


def test_mssql_blocked_sessions_no_blocking_sessions(
    fix_register: FixRegister,
) -> None:
    parse_function = fix_register.agent_sections[
        SectionName("mssql_blocked_sessions")
    ].parse_function
    plugin = fix_register.check_plugins[CheckPluginName("mssql_blocked_sessions")]
    assert plugin
    assert list(
        plugin.check_function(
            params=DEFAULT_PARAMETERS,
            item="INST_ID1",
            section=parse_function(INFO_1),
        )
    ) == [
        Result(state=State.OK, summary="No blocking sessions"),
    ]


def test_mssql_blocked_sessions_waittime(fix_register: FixRegister) -> None:
    assert list(
        check_mssql_blocked_sessions(
            item="",
            params=default_parameters(waittime=(10, 100)),
            section={
                "": [
                    DBInstance(
                        session_id="sid",
                        wait_type="smth1",
                        blocking_session_id="bsid1",
                        wait_duration=25,
                    )
                ]
            },
        )
    ) == [
        Result(state=State.OK, summary="Summary: sid blocked by 1 ID(s)"),
        Result(
            state=State.WARN,
            summary="Session sid blocked by bsid1, Type: smth1, Wait: 25 seconds (warn/crit at 10 seconds/1 minute 40 seconds)",
        ),
    ]


def test_mssql_blocked_sessions_ignore_waittype(fix_register: FixRegister) -> None:
    assert list(
        check_mssql_blocked_sessions(
            item="",
            params=default_parameters(ignore_waittypes=["smth1"]),
            section={
                "": [
                    DBInstance(
                        session_id="sid",
                        wait_type="smth1",
                        blocking_session_id="bsid1",
                        wait_duration=25,
                    )
                ]
            },
        )
    ) == [
        Result(state=State.OK, summary="No blocking sessions"),
        Result(
            state=State.OK,
            summary="Ignored wait types: smth1",
        ),
    ]


def test_mssql_blocked_sessions_parsing(fix_register: FixRegister) -> None:
    assert parse_mssql_blocked_sessions([["ERROR: asd"]]) == {}
    assert parse_mssql_blocked_sessions([["No blocking sessions"]]) == {"": []}
    assert parse_mssql_blocked_sessions(
        [
            ["Blocked _Sessions"],
            ["INST_ID1", "119", "232292187", "LCK_M_U", "75"],
            ["INST_ID2", "76", "221526672", "LCK_M_U", "115"],
        ]
    ) == {
        "INST_ID1": [
            DBInstance(
                session_id="119",
                wait_type="LCK_M_U",
                blocking_session_id="75",
                wait_duration=232292.187,
            )
        ],
        "INST_ID2": [
            DBInstance(
                session_id="76",
                wait_type="LCK_M_U",
                blocking_session_id="115",
                wait_duration=221526.672,
            )
        ],
    }


DATA_GENERIC_0 = [
    ["ID 1", "1", "232292187", "Foo", "2"],
    ["ID 1", "3", "232292187", "Foo", "4"],
    ["ID 1", "5", "232292187", "Bar", "6"],
    ["ID 1", "7", "232292187", "Bar", "8"],
    ["ID 2", "1", "232292187", "Foo", "2"],
    ["ID 2", "3", "232292187", "Foo", "4"],
    ["ID 2", "5", "232292187", "Bar", "6"],
    ["ID 2", "7", "232292187", "Bar", "8"],
]

DATA_GENERIC_1 = [
    ["ID-1", "No blocking sessions"],
    ["MSSQLSERVER_SA", "No blocking sessions"],
    ["MSSQLSERVER_LIVE", "No blocking sessions"],
]


@pytest.mark.parametrize(
    "string_table, item, params, check_result",
    [
        (
            DATA_GENERIC_0,
            "ID 1",
            {"state": 2},
            [
                Result(
                    state=State.CRIT,
                    summary="Summary: 1 blocked by 1 ID(s), 3 blocked by 1 ID(s), 5 blocked by 1 ID(s), 7 blocked by 1 ID(s)",
                ),
                Result(
                    state=State.OK,
                    summary="Session 1 blocked by 2, Type: Foo, Wait: 2 days 16 hours",
                ),
                Result(
                    state=State.OK,
                    summary="Session 3 blocked by 4, Type: Foo, Wait: 2 days 16 hours",
                ),
                Result(
                    state=State.OK,
                    summary="Session 5 blocked by 6, Type: Bar, Wait: 2 days 16 hours",
                ),
                Result(
                    state=State.OK,
                    summary="Session 7 blocked by 8, Type: Bar, Wait: 2 days 16 hours",
                ),
            ],
        ),
        (
            DATA_GENERIC_1,
            "ID-1",
            {"state": 1},
            [
                Result(
                    state=State.OK,
                    summary="No blocking sessions",
                )
            ],
        ),
        (
            DATA_GENERIC_1,
            "ID-1",
            {"state": 2},
            [
                Result(
                    state=State.OK,
                    summary="No blocking sessions",
                )
            ],
        ),
        (
            DATA_GENERIC_1,
            "MSSQLSERVER_LIVE",
            {"state": 2},
            [
                Result(
                    state=State.OK,
                    summary="No blocking sessions",
                )
            ],
        ),
        (
            DATA_GENERIC_1,
            "MSSQLSERVER_SA",
            {"state": 2},
            [
                Result(
                    state=State.OK,
                    summary="No blocking sessions",
                )
            ],
        ),
        (
            [
                ["1", "232292187", "Foo", "2"],
                ["3", "232292187", "Foo", "4"],
                ["5", "232292187", "Bar", "6"],
                ["7", "232292187", "Bar", "8"],
            ],
            "",
            {"state": 2},
            [
                Result(
                    state=State.CRIT,
                    summary="Summary: 1 blocked by 1 ID(s), 3 blocked by 1 ID(s), 5 blocked by 1 ID(s), 7 blocked by 1 ID(s)",
                ),
                Result(
                    state=State.OK,
                    summary="Session 1 blocked by 2, Type: Foo, Wait: 2 days 16 hours",
                ),
                Result(
                    state=State.OK,
                    summary="Session 3 blocked by 4, Type: Foo, Wait: 2 days 16 hours",
                ),
                Result(
                    state=State.OK,
                    summary="Session 5 blocked by 6, Type: Bar, Wait: 2 days 16 hours",
                ),
                Result(
                    state=State.OK,
                    summary="Session 7 blocked by 8, Type: Bar, Wait: 2 days 16 hours",
                ),
            ],
        ),
    ],
)
def test_mssql_blocked_sessions_generic(
    fix_register: FixRegister,
    string_table: StringTable,
    params: Params,
    item: str,
    check_result: list[Result],
) -> None:
    assert (
        list(
            check_mssql_blocked_sessions(
                item=item, params=params, section=parse_mssql_blocked_sessions(string_table)
            )
        )
        == check_result
    )


@pytest.mark.parametrize(
    "string_table, discovery_result",
    [
        (DATA_GENERIC_0, [Service(item="ID 1"), Service(item="ID 2")]),
        (
            DATA_GENERIC_1,
            [
                Service(item="ID-1"),
                Service(item="MSSQLSERVER_SA"),
                Service(item="MSSQLSERVER_LIVE"),
            ],
        ),
    ],
)
def test_mssql_blocked_sessions_generic_discover(
    fix_register: FixRegister, string_table: StringTable, discovery_result: list[Service]
) -> None:
    assert (
        list(discovery_mssql_blocked_sessions(parse_mssql_blocked_sessions(string_table)))
        == discovery_result
    )


def test_mssql_blocked_sessions_generic_cluster(fix_register: FixRegister) -> None:
    assert list(
        cluster_check_mssql_blocked_sessions(
            item="ID 1",
            section={
                "server-1": parse_mssql_blocked_sessions([["ID 1", "No blocking sessions"]]),
                "server-2": parse_mssql_blocked_sessions([["ID 1", "1", "232292187", "Foo", "2"]]),
            },
            params={"state": 2},
        )
    ) == [
        Result(state=State.OK, notice="[server-1]: No blocking sessions"),
        Result(state=State.CRIT, summary="[server-2]: Summary: 1 blocked by 1 ID(s)"),
        Result(
            state=State.OK,
            notice="[server-2]: Session 1 blocked by 2, Type: Foo, Wait: 2 days 16 hours",
        ),
    ]
