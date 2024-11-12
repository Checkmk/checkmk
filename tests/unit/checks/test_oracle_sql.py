#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import pytest

from tests.testlib import Check

from .checktestlib import assertDiscoveryResultsEqual, DiscoveryResult

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
                "FOOBAR1 SQL YOLBE AFS RABAT REPL ERROR STMT": {
                    "details": [],
                    "elapsed": None,
                    "exit": 0,
                    "long": [],
                    "parsing_error": {
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
                    "perfdata": [],
                }
            },
        ),
        (
            INFO_2,
            {
                "FOOBAR1 SQL NBA SESSION LEVEL": {
                    "details": ["Session Level: 5"],
                    "elapsed": 0.26815,
                    "exit": 0,
                    "long": [],
                    "parsing_error": {},
                    "perfdata": [],
                }
            },
        ),
        (
            INFO_3,
            {
                "BULU SQL BLABLI NBA SHA FILE": {
                    "details": [],
                    "elapsed": 0.29285,
                    "exit": 2,
                    "long": [
                        "Monitoring SHA/RAB Resultat = 1",
                        "TODO siehe FOOBAR; Monitoring SHA",
                    ],
                    "parsing_error": {
                        ("unknown", 'Unexpected Keyword: "detail". Line was', 3): [
                            "detail:SHA-TT File (sha-ra), welches Sachen macht."
                        ]
                    },
                    "perfdata": [],
                }
            },
        ),
        (
            INFO_4,
            {
                "YOBLE1 SQL NBA SESSIONS": {
                    "details": [
                        "Active sessions: 0 (warn/crit at "
                        "10/20) / Inactive sessions: 0 "
                        "(warn/crit at 10/40)"
                    ],
                    "elapsed": 0.29444,
                    "exit": 0,
                    "long": ["Avara SEP_ID: 301"],
                    "parsing_error": {},
                    "perfdata": [
                        ("sessions_active", 0, 10, 20),
                        ("sessions_inactive", 0, 10, 40),
                        ("sessions_maxage", 0),
                    ],
                }
            },
        ),
        (
            INFO_5,
            {
                "YOBLE1 SQL NBA SESSIONS": {
                    "details": [
                        "Active sessions: 0 (warn/crit at "
                        "10/20) / Inactive sessions: 0 "
                        "(warn/crit at 10/40)"
                    ],
                    "elapsed": None,
                    "exit": 0,
                    "long": ["Avara SEP_ID: 301"],
                    "parsing_error": {},
                    "perfdata": [
                        ("sessions_active", 0, 10, 20),
                        ("sessions_inactive", 0, 10, 40),
                        ("sessions_maxage", 0),
                    ],
                }
            },
        ),
    ],
)
def test_oracle_sql_parse(info, expected):
    assert Check(check_name).run_parse(info) == expected


@pytest.mark.parametrize(
    "info,expected",
    [
        (INFO_1, [("FOOBAR1 SQL YOLBE AFS RABAT REPL ERROR STMT", {})]),
        (INFO_2, [("FOOBAR1 SQL NBA SESSION LEVEL", {})]),
        (INFO_3, [("BULU SQL BLABLI NBA SHA FILE", {})]),
        (INFO_4, [("YOBLE1 SQL NBA SESSIONS", {})]),
    ],
)
def test_oracle_sql_discovery(info, expected):
    oracle_sql = Check(check_name)
    discovery_result = DiscoveryResult(oracle_sql.run_discovery(oracle_sql.run_parse(info)))
    discovery_expected = DiscoveryResult(expected)
    assertDiscoveryResultsEqual(oracle_sql, discovery_result, discovery_expected)


@pytest.mark.parametrize(
    "info, item, expected",
    [
        (
            INFO_1,
            "FOOBAR1 SQL YOLBE AFS RABAT REPL ERROR STMT",
            [
                (
                    2,
                    "PL/SQL failure: ERROR at line 17: ORA-06550: line 17, column 5: PL/SQL: "
                    "ORA-00933: SQL command not properly ended ORA-06550: line 7, column 5:",
                )
            ],
        ),
        (
            INFO_2,
            "FOOBAR1 SQL NBA SESSION LEVEL",
            [(0, "Session Level: 5", [("elapsed_time", 0.26815)])],
        ),
        (
            INFO_3,
            "BULU SQL BLABLI NBA SHA FILE",
            [
                (
                    3,
                    'Unexpected Keyword: "detail". Line was: detail:SHA-TT File (sha-ra), '
                    "welches Sachen macht.",
                ),
                (
                    0,
                    "\nMonitoring SHA/RAB Resultat = 1\nTODO siehe FOOBAR; Monitoring SHA",
                ),
            ],
        ),
        (
            INFO_4,
            "YOBLE1 SQL NBA SESSIONS",
            [
                (
                    0,
                    "Active sessions: 0 (warn/crit at 10/20) / Inactive sessions: 0 (warn/crit "
                    "at 10/40)",
                    [
                        ("sessions_active", 0, 10, 20),
                        ("sessions_inactive", 0, 10, 40),
                        ("sessions_maxage", 0),
                        ("elapsed_time", 0.29444),
                    ],
                ),
                (0, "\nAvara SEP_ID: 301"),
            ],
        ),
    ],
)
def test_oracle_sql_check(info, item, expected):
    oracle_sql = Check(check_name)
    result = list(oracle_sql.run_check(item, {}, oracle_sql.run_parse(info)))
    assert result == expected
