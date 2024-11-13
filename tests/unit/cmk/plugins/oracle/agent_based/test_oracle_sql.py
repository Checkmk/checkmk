#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import datetime
from zoneinfo import ZoneInfo

import pytest
import time_machine

from cmk.agent_based.v2 import Metric, Result, Service, State
from cmk.plugins.oracle.agent_based.oracle_sql import (
    check_oracle_sql,
    discovery_oracle_sql,
    Instance,
    parse_metrics,
    parse_oracle_sql,
)

pytestmark = pytest.mark.checks
check_name = "oracle_sql"
INFO_1 = [
    ["[[[foobar1|YOLBE AFS RABAT REPL ERROR STMT]]]"],
    [
        "FOOBAR1|FAILURE|ERROR at line 17",
        " ORA-06550",
        " line 17, column 5",
        " PL/SQL",
        " ORA-00933",
        " SQL command not properly ended ORA-06550",
        " line 7, column 5",
        "",
    ],
]

INFO_2 = [
    ["[[[foobar1|NBA SESSION LEVEL]]]"],
    ["details", "Session Level", " 5"],
    ["exit", "0"],
    ["elapsed", "0.26815"],
]

INFO_3 = [
    ["[[[bulu|BLABLI NBA SHA FILE]]]"],
    ["long", "Monitoring SHA/RAB Resultat = 1"],
    [
        "detail",
        "SHA-TT File (sha-ra), welches Sachen macht.",
    ],
    ["long", "TODO siehe FOOBAR; Monitoring SHA"],
    ["exit", "2"],
    ["elapsed", "0.29285"],
]

INFO_4 = [
    ["[[[yoble1|NBA SESSIONS]]]"],
    ["long", "Avara SEP_ID", " 301"],
    [
        "details",
        "Active sessions",
        " 0 (warn/crit at 10/20) / Inactive sessions",
        " 0 (warn/crit at 10/40)",
    ],
    ["perfdata", "sessions_active=0;10;20"],
    ["perfdata", "sessions_inactive=0;10;40"],
    ["perfdata", "sessions_maxage=0"],
    ["exit", "0"],
    ["elapsed", "0.29444"],
]

# In SUP-21227 it was reported that the line 'elapsed:' shows up in the agent output. We did not
# obtain an agent output, but this could happen if `perl -MTime::HiRes=time -wle 'print time'`
# fails. This table was copied from INFO_4 and modified to match the ticket.
INFO_5 = [
    ["[[[yoble1|NBA SESSIONS]]]"],
    ["long", "Avara SEP_ID", " 301"],
    [
        "details",
        "Active sessions",
        " 0 (warn/crit at 10/20) / Inactive sessions",
        " 0 (warn/crit at 10/40)",
    ],
    ["perfdata", "sessions_active=0;10;20"],
    ["perfdata", "sessions_inactive=0;10;40"],
    ["perfdata", "sessions_maxage=0"],
    ["exit", "0"],
    ["elapsed", ""],
]


@pytest.mark.parametrize(
    "info,expected",
    [
        (
            INFO_1,
            {
                "FOOBAR1 SQL YOLBE AFS RABAT REPL ERROR STMT": Instance(
                    details=[],
                    elapsed=None,
                    exit=0,
                    long=[],
                    parsing_error={
                        ("instance", "PL/SQL failure", 2): [
                            "ERROR "
                            "at "
                            "line "
                            "17: "
                            "ORA-06550: "
                            "line "
                            "17, "
                            "column "
                            "5: "
                            "PL/SQL: "
                            "ORA-00933: "
                            "SQL "
                            "command "
                            "not "
                            "properly "
                            "ended "
                            "ORA-06550: "
                            "line "
                            "7, "
                            "column "
                            "5:"
                        ]
                    },
                    metrics=[],
                )
            },
        ),
        (
            INFO_2,
            {
                "FOOBAR1 SQL NBA SESSION LEVEL": Instance(
                    details=["Session Level: 5"],
                    elapsed=0.26815,
                    exit=0,
                    long=[],
                    parsing_error={},
                    metrics=[],
                )
            },
        ),
        (
            INFO_3,
            {
                "BULU SQL BLABLI NBA SHA FILE": Instance(
                    details=[],
                    elapsed=0.29285,
                    exit=2,
                    long=[
                        "Monitoring SHA/RAB Resultat = 1",
                        "TODO siehe FOOBAR; Monitoring SHA",
                    ],
                    parsing_error={
                        ("unknown", 'Unexpected Keyword: "detail". Line was', 3): [
                            "detail:SHA-TT File (sha-ra), welches Sachen macht."
                        ]
                    },
                    metrics=[],
                )
            },
        ),
        (
            INFO_4,
            {
                "YOBLE1 SQL NBA SESSIONS": Instance(
                    details=[
                        "Active sessions: 0 (warn/crit "
                        "at 10/20) / Inactive sessions: "
                        "0 (warn/crit at 10/40)"
                    ],
                    elapsed=0.29444,
                    exit=0,
                    long=["Avara SEP_ID: 301"],
                    parsing_error={},
                    metrics=[
                        Metric(name="sessions_active", value=0, levels=(10, 20), boundaries=None),
                        Metric(name="sessions_inactive", value=0, levels=(10, 40), boundaries=None),
                        Metric(name="sessions_maxage", value=0, levels=None, boundaries=None),
                    ],
                )
            },
        ),
        (
            INFO_5,
            {
                "YOBLE1 SQL NBA SESSIONS": Instance(
                    details=[
                        "Active sessions: 0 (warn/crit "
                        "at 10/20) / Inactive sessions: "
                        "0 (warn/crit at 10/40)"
                    ],
                    elapsed=None,
                    exit=0,
                    long=["Avara SEP_ID: 301"],
                    parsing_error={},
                    metrics=[
                        Metric(name="sessions_active", value=0, levels=(10, 20), boundaries=None),
                        Metric(name="sessions_inactive", value=0, levels=(10, 40), boundaries=None),
                        Metric(name="sessions_maxage", value=0, levels=None, boundaries=None),
                    ],
                )
            },
        ),
    ],
)
def test_oracle_sql_parse(info, expected):
    assert parse_oracle_sql(info) == expected


@pytest.mark.parametrize(
    "line,expected",
    [
        (
            "sessions_active=0",
            [Metric(name="sessions_active", value=0, levels=None, boundaries=None)],
        ),
        (
            "sessions_active=0;10;20",
            [Metric(name="sessions_active", value=0, levels=(10, 20), boundaries=None)],
        ),
        (
            "sessions_active=0;10;20;30;40",
            [Metric(name="sessions_active", value=0, levels=(10, 20), boundaries=(30, 40))],
        ),
        (
            "one=0;10;20;30;40 two=1;2;3 three=2;3;4;5;6",
            [
                Metric(name="one", value=0, levels=(10, 20), boundaries=(30, 40)),
                Metric(name="two", value=1, levels=(2, 3), boundaries=None),
                Metric(name="three", value=2, levels=(3, 4), boundaries=(5, 6)),
            ],
        ),
        (
            "tasks_waiting=2;;100 task_working=7",
            [
                Metric(name="tasks_waiting", value=2, levels=(None, 100), boundaries=None),
                Metric(name="task_working", value=7, levels=None, boundaries=None),
            ],
        ),
    ],
)
def test_parse_metrics(line, expected):
    assert list(parse_metrics(line)) == expected


@pytest.mark.parametrize(
    "info,expected",
    [
        (INFO_1, [Service(item="FOOBAR1 SQL YOLBE AFS RABAT REPL ERROR STMT")]),
        (INFO_2, [Service(item="FOOBAR1 SQL NBA SESSION LEVEL")]),
        (INFO_3, [Service(item="BULU SQL BLABLI NBA SHA FILE")]),
        (INFO_4, [Service(item="YOBLE1 SQL NBA SESSIONS")]),
    ],
)
def test_oracle_sql_discovery(info, expected):
    assert list(discovery_oracle_sql(parse_oracle_sql(info))) == expected


@pytest.mark.parametrize(
    "info, item, expected",
    [
        (
            INFO_1,
            "FOOBAR1 SQL YOLBE AFS RABAT REPL ERROR STMT",
            [
                Result(
                    state=State.CRIT,
                    summary="PL/SQL failure: ERROR at line 17: ORA-06550: line 17, "
                    "column 5: PL/SQL: ORA-00933: "
                    "SQL command not properly ended ORA-06550: line 7, column 5:",
                )
            ],
        ),
        (
            INFO_2,
            "FOOBAR1 SQL NBA SESSION LEVEL",
            [
                Result(state=State.OK, summary="Session Level: 5"),
                Metric("elapsed_time", 0.26815),
            ],
        ),
        (
            INFO_3,
            "BULU SQL BLABLI NBA SHA FILE",
            [
                Result(
                    state=State.UNKNOWN,
                    summary='Unexpected Keyword: "detail". Line was: '
                    "detail:SHA-TT File (sha-ra), welches Sachen macht.",
                ),
                Result(
                    state=State.OK,
                    summary="Monitoring SHA/RAB Resultat = 1",
                    details="TODO siehe FOOBAR; Monitoring SHA",
                ),
            ],
        ),
        (
            INFO_4,
            "YOBLE1 SQL NBA SESSIONS",
            [
                Result(
                    state=State.OK,
                    summary="Active sessions: 0 (warn/crit at 10/20) / "
                    "Inactive sessions: 0 (warn/crit at 10/40)",
                ),
                Metric("sessions_active", 0, levels=(10, 20)),
                Metric("sessions_inactive", 0, levels=(10, 40)),
                Metric("sessions_maxage", 0),
                Metric("elapsed_time", 0.29444),
                Result(state=State.OK, summary="Avara SEP_ID: 301"),
            ],
        ),
    ],
)
def test_oracle_sql_check(info, item, expected):
    result = list(check_oracle_sql(item, {}, parse_oracle_sql(info)))
    assert result == expected


def test_check_oracle_sql_cached() -> None:
    with time_machine.travel(datetime.datetime.fromtimestamp(10, tz=ZoneInfo("UTC"))):
        assert list(
            check_oracle_sql(
                item="SID SQL SQL",
                params={},
                section=parse_oracle_sql(
                    [
                        ["[[[sid|sql|cached(1,2)]]]"],
                        ["details", "DETAILS"],
                        ["perfdata", "metric_name=1;2;3;0;5"],
                        ["long", "LONG"],
                        ["exit", "0"],
                        ["elapsed", "123"],
                    ]
                ),
            )
        ) == [
            Result(state=State.OK, summary="DETAILS"),
            Metric("metric_name", 1.0, levels=(2.0, 3.0), boundaries=(0.0, 5.0)),
            Metric("elapsed_time", 123.0),
            Result(state=State.OK, summary="LONG"),
            Result(
                state=State.OK,
                summary="Cache generated 9 seconds ago, cache interval: 2 seconds, elapsed cache lifespan: 450.00%",
            ),
        ]
