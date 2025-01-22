#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import pytest

from tests.unit.cmk.plugins.oracle.agent_based.utils_inventory import sort_inventory_result

from cmk.checkengine.checking import CheckPluginName

from cmk.base.api.agent_based.register import AgentBasedPlugins

from cmk.agent_based.v2 import CheckResult, InventoryResult, Result, Service, State, TableRow
from cmk.plugins.lib.oracle_instance import GeneralError, Instance, InvalidData
from cmk.plugins.oracle.agent_based import oracle_instance_check
from cmk.plugins.oracle.agent_based.oracle_instance_inventory import inventory_oracle_instance
from cmk.plugins.oracle.agent_based.oracle_instance_section import parse_oracle_instance


def test_parse_oracle_instance_db_without_host_12() -> None:
    assert parse_oracle_instance(
        [
            [
                "XE",
                "11.2.0.2.0",
                "OPEN",
                "ALLOWED",
                "STOPPED",
                "1212537",
                "2858521146",
                "NOARCHIVELOG",
                "PRIMARY",
                "NO",
                "XE",
                "290520181207",
            ],
        ]
    ) == {
        "XE": Instance(
            archiver="STOPPED",
            database_role="PRIMARY",
            db_creation_time="290520181207",
            force_logging="NO",
            log_mode="NOARCHIVELOG",
            logins="ALLOWED",
            name="XE",
            old_agent=False,
            openmode="OPEN",
            pluggable="FALSE",
            pname=None,
            popenmode=None,
            prestricted=None,
            ptotal_size=None,
            pup_seconds=None,
            sid="XE",
            up_seconds=1212537,
            version="11.2.0.2.0",
        ),
    }


def test_parse_oracle_instance_db_with_additional_error_info() -> None:
    assert parse_oracle_instance(
        [
            [
                "+ASM",
                "FAILURE",
                "ORA-99999 tnsping failed for +ASM ERROR: ORA-28002: the password will expire within 1 days",
            ],
            [
                "NAME DATABASE_ROLE OPEN_MODE DB_UNIQUE_NAME FLASHBACK_ON FORCE_LOGGING SWITCHOVER_STATUS"
            ],  # This should be ignored because the length is 1
            [
                "SEUSAZQ1 PRIMARY READ WRITE SEUSAZQ1 YES YES TO STANDBY"
            ],  # This should be ignored because length is 1
        ]
    ) == {
        "+ASM": GeneralError(
            sid="+ASM",
            error="ORA-99999 tnsping failed for +ASM ERROR: ORA-28002: the password will expire within 1 days",
        )
    }


def test_parse_oracle_instance_db_with_host_13() -> None:
    assert parse_oracle_instance(
        [
            [
                "IC731",
                "12.1.0.2.0",
                "OPEN",
                "ALLOWED",
                "STARTED",
                "2144847",
                "3190399742",
                "ARCHIVELOG",
                "PRIMARY",
                "YES",
                "IC73",
                "130920150251",
                "my-oracle-server",
            ],
        ]
    ) == {
        "IC731": Instance(
            archiver="STARTED",
            database_role="PRIMARY",
            db_creation_time="130920150251",
            force_logging="YES",
            log_mode="ARCHIVELOG",
            logins="ALLOWED",
            name="IC73",
            old_agent=False,
            openmode="OPEN",
            pluggable="FALSE",
            pname=None,
            popenmode=None,
            prestricted=None,
            ptotal_size=None,
            pup_seconds=None,
            sid="IC731",
            up_seconds=2144847,
            version="12.1.0.2.0",
            host_name="my-oracle-server",
        )
    }


def test_parse_oracle_instance_error() -> None:
    assert parse_oracle_instance(
        [
            [
                "+ASM",
                "FAILURE",
                "ORA-99999 tnsping failed for +ASM ERROR: ORA-28002: the password will expire within 1 days",
            ],
        ]
    ) == {
        "+ASM": GeneralError(
            "+ASM",
            "ORA-99999 tnsping failed for +ASM ERROR: ORA-28002: the password will expire within 1 days",
        ),
    }


def test_parse_oracle_instance_invalid() -> None:
    assert parse_oracle_instance(
        [
            ["I442", "FAILURE"],
        ]
    ) == {
        "I442": InvalidData("I442", error="Invalid data from agent"),
    }


def test_discover_oracle_instance(agent_based_plugins: AgentBasedPlugins) -> None:
    assert list(
        agent_based_plugins.check_plugins[CheckPluginName("oracle_instance")].discovery_function(
            {
                "a": InvalidData("a", "This is an error"),
                "b": GeneralError("b", "something went wrong"),
                "c": Instance(sid="c", version="", openmode="", logins=""),
            },
        )
    ) == [
        Service(item="a"),
        Service(item="b"),
        Service(item="c"),
    ]


@pytest.mark.parametrize(
    ["agent_line", "expected_result"],
    [
        pytest.param(
            [
                "IC731",
                "12.1.0.2.0",
                "OPEN",
                "ALLOWED",
                "STARTED",
                "2144847",
                "3190399742",
                "ARCHIVELOG",
                "PRIMARY",
                "YES",
                "IC73",
                "130920150251",
            ],
            [
                Result(state=State.OK, summary="Database Name IC73"),
                Result(state=State.OK, summary="Status OPEN"),
                Result(state=State.OK, summary="Role PRIMARY"),
                Result(state=State.OK, summary="Version 12.1.0.2.0"),
                Result(state=State.OK, summary="Logins allowed"),
                Result(state=State.OK, summary="Log Mode archivelog"),
                Result(state=State.OK, summary="Force Logging yes"),
            ],
            id="normal",
        ),
        pytest.param(
            [
                "IC731",
                "12.1.0.2.0",
                "LOCKED",
                "ALLOWED",
                "STARTED",
                "2144847",
                "3190399742",
                "ARCHIVELOG",
                "PRIMARY",
                "YES",
                "IC73",
                "130920150251",
            ],
            [
                Result(state=State.OK, summary="Database Name IC73"),
                Result(state=State.CRIT, summary="Status LOCKED"),
                Result(state=State.OK, summary="Role PRIMARY"),
                Result(state=State.OK, summary="Version 12.1.0.2.0"),
                Result(state=State.OK, summary="Log Mode archivelog"),
                Result(state=State.OK, summary="Force Logging yes"),
            ],
            id="locked",
        ),
        pytest.param(
            [
                "IC731",
                "12.1.0.2.0",
                "OPEN",
                "RESTRICTED",
                "STARTED",
                "2144847",
                "3190399742",
                "ARCHIVELOG",
                "PRIMARY",
                "YES",
                "IC73",
                "130920150251",
            ],
            [
                Result(state=State.OK, summary="Database Name IC73"),
                Result(state=State.OK, summary="Status OPEN"),
                Result(state=State.OK, summary="Role PRIMARY"),
                Result(state=State.OK, summary="Version 12.1.0.2.0"),
                Result(state=State.CRIT, summary="Logins restricted"),
                Result(state=State.OK, summary="Log Mode archivelog"),
                Result(state=State.OK, summary="Force Logging yes"),
            ],
            id="logins_restricted",
        ),
        pytest.param(
            [
                "IC731",
                "12.1.0.2.0",
                "OPEN",
                "ALLOWED",
                "STARTED",
                "2144847",
                "3190399742",
                "NOARCHIVELOG",
                "PRIMARY",
                "YES",
                "IC73",
                "130920150251",
            ],
            [
                Result(state=State.OK, summary="Database Name IC73"),
                Result(state=State.OK, summary="Status OPEN"),
                Result(state=State.OK, summary="Role PRIMARY"),
                Result(state=State.OK, summary="Version 12.1.0.2.0"),
                Result(state=State.OK, summary="Logins allowed"),
                Result(state=State.WARN, summary="Log Mode noarchivelog"),
            ],
            id="no_archive_log",
        ),
        pytest.param(
            [
                "IC731",
                "12.1.0.2.0",
                "OPEN",
                "ALLOWED",
                "STOPPED",
                "2144847",
                "3190399742",
                "ARCHIVELOG",
                "PRIMARY",
                "YES",
                "IC73",
                "130920150251",
            ],
            [
                Result(state=State.OK, summary="Database Name IC73"),
                Result(state=State.OK, summary="Status OPEN"),
                Result(state=State.OK, summary="Role PRIMARY"),
                Result(state=State.OK, summary="Version 12.1.0.2.0"),
                Result(state=State.OK, summary="Logins allowed"),
                Result(state=State.OK, summary="Log Mode archivelog"),
                Result(state=State.CRIT, summary="Archiver stopped"),
                Result(state=State.OK, summary="Force Logging yes"),
            ],
            id="archiver_stopped",
        ),
        pytest.param(
            [
                "IC731",
                "12.1.0.2.0",
                "OPEN",
                "ALLOWED",
                "STARTED",
                "2144847",
                "3190399742",
                "ARCHIVELOG",
                "PRIMARY",
                "NO",
                "IC73",
                "130920150251",
            ],
            [
                Result(state=State.OK, summary="Database Name IC73"),
                Result(state=State.OK, summary="Status OPEN"),
                Result(state=State.OK, summary="Role PRIMARY"),
                Result(state=State.OK, summary="Version 12.1.0.2.0"),
                Result(state=State.OK, summary="Logins allowed"),
                Result(state=State.OK, summary="Log Mode archivelog"),
                Result(state=State.WARN, summary="Force Logging no"),
            ],
            id="logging_not_forced",
        ),
        pytest.param(
            [
                "IC731",
                "FAILURE",
                "ORA-99999 tnsping failed for IC731 ERROR: ORA-28002: the password will expire within 1 days",
            ],
            [
                Result(
                    state=State.CRIT,
                    summary="ORA-99999 tnsping failed for IC731 ERROR: ORA-28002: the password will expire within 1 days",
                ),
            ],
            id="error",
        ),
    ],
)
def test_check_oracle_instance(
    agent_based_plugins: AgentBasedPlugins,
    agent_line: list[str],
    expected_result: CheckResult,
) -> None:
    assert (
        list(
            agent_based_plugins.check_plugins[CheckPluginName("oracle_instance")].check_function(
                item="IC731",
                params={
                    "logins": 2,
                    "noforcelogging": 1,
                    "noarchivelog": 1,
                    "primarynotopen": 2,
                    "archivelog": 0,
                    "forcelogging": 0,
                },
                section=parse_oracle_instance([agent_line]),
            )
        )
        == expected_result
    )


def test_check_oracle_instance_empty_section(agent_based_plugins: AgentBasedPlugins) -> None:
    assert list(
        agent_based_plugins.check_plugins[CheckPluginName("oracle_instance")].check_function(
            item="item",
            params={
                "logins": 2,
                "noforcelogging": 1,
                "noarchivelog": 1,
                "primarynotopen": 2,
            },
            section={},
        )
    ) == [
        Result(
            state=State.CRIT,
            summary="Database or necessary processes not running or login failed",
        )
    ]


@pytest.mark.parametrize(
    "line, expected_data",
    [
        ([], []),
        (
            [
                "SID",
                "VERSION",
            ],
            [],
        ),
        (
            ["SID", "VERSION", "OPENMODE", "LOGINS", "_UNUSED1", "_UNUSED2"],
            [
                TableRow(
                    path=["software", "applications", "oracle", "instance"],
                    key_columns={
                        "sid": "SID",
                    },
                    inventory_columns={
                        "pname": None,
                        "version": "VERSION",
                        "openmode": "OPENMODE",
                        "logmode": None,
                        "logins": "LOGINS",
                        "db_creation_time": None,
                    },
                    status_columns={"db_uptime": None, "host": None},
                ),
            ],
        ),
        (
            [
                "SID",
                "VERSION",
                "OPENMODE",
                "LOGINS",
                "_ARCHIVER",
                "123",
                "0",
                "NO",
                "ASM",
                "NO",
                "_NAME",
            ],
            [
                TableRow(
                    path=["software", "applications", "oracle", "instance"],
                    key_columns={
                        "sid": "SID",
                    },
                    inventory_columns={
                        "pname": None,
                        "version": "VERSION",
                        "openmode": "OPENMODE",
                        "logmode": "NO",
                        "logins": "LOGINS",
                        "db_creation_time": None,
                    },
                    status_columns={
                        "db_uptime": 123,
                        "host": None,
                    },
                ),
            ],
        ),
        (
            [
                "SID",
                "VERSION",
                "OPENMODE",
                "LOGINS",
                "_ARCHIVER",
                "123",
                "0",
                "NO",
                "ASM",
                "NO",
                "_NAME",
            ],
            [
                TableRow(
                    path=["software", "applications", "oracle", "instance"],
                    key_columns={
                        "sid": "SID",
                    },
                    inventory_columns={
                        "pname": None,
                        "version": "VERSION",
                        "openmode": "OPENMODE",
                        "logmode": "NO",
                        "logins": "LOGINS",
                        "db_creation_time": None,
                    },
                    status_columns={
                        "db_uptime": 123,
                        "host": None,
                    },
                ),
            ],
        ),
        (
            [
                "SID",
                "VERSION",
                "OPENMODE",
                "LOGINS",
                "_ARCHIVER",
                "123",
                "_DBID",
                "LOGMODE",
                "_DATABASE_ROLE",
                "_FORCE_LOGGING",
                "_NAME",
                "080220151025",
            ],
            [
                TableRow(
                    path=["software", "applications", "oracle", "instance"],
                    key_columns={
                        "sid": "SID",
                    },
                    inventory_columns={
                        "pname": None,
                        "version": "VERSION",
                        "openmode": "OPENMODE",
                        "logmode": "LOGMODE",
                        "logins": "LOGINS",
                        "db_creation_time": "2015-02-08 10:25",
                    },
                    status_columns={
                        "db_uptime": 123,
                        "host": None,
                    },
                ),
            ],
        ),
        (
            [
                "SID",
                "VERSION",
                "OPENMODE",
                "LOGINS",
                "_ARCHIVER",
                "123",
                "_DBID",
                "LOGMODE",
                "_DATABASE_ROLE",
                "_FORCE_LOGGING",
                "_NAME",
                "080220151025",
            ],
            [
                TableRow(
                    path=["software", "applications", "oracle", "instance"],
                    key_columns={
                        "sid": "SID",
                    },
                    inventory_columns={
                        "pname": None,
                        "version": "VERSION",
                        "openmode": "OPENMODE",
                        "logmode": "LOGMODE",
                        "logins": "LOGINS",
                        "db_creation_time": "2015-02-08 10:25",
                    },
                    status_columns={
                        "db_uptime": 123,
                        "host": None,
                    },
                ),
            ],
        ),
        (
            [
                "SID",
                "VERSION",
                "OPENMODE",
                "LOGINS",
                "_ARCHIVER",
                "123",
                "_DBID",
                "LOGMODE",
                "_DATABASE_ROLE",
                "_FORCE_LOGGING",
                "_NAME",
                "RAW_DB_CREATION_TIME",
                "_PLUGGABLE",
                "_CON_ID",
                "PNAME",
                "_PDBID",
                "_POPENMODE",
                "_PRESTRICTED",
                "42424242",
                "_PRECOVERY_STATUS",
                "232323",
                "_PBLOCK_SIZE",
            ],
            [
                TableRow(
                    path=["software", "applications", "oracle", "instance"],
                    key_columns={
                        "sid": "SID",
                    },
                    inventory_columns={
                        "pname": "PNAME",
                        "version": "VERSION",
                        "openmode": "OPENMODE",
                        "logmode": "LOGMODE",
                        "logins": "LOGINS",
                        "db_creation_time": None,
                    },
                    status_columns={
                        "db_uptime": 123,
                        "host": None,
                    },
                ),
            ],
        ),
        (
            [
                "SID",
                "VERSION",
                "OPENMODE",
                "LOGINS",
                "_ARCHIVER",
                "123",
                "_DBID",
                "LOGMODE",
                "_DATABASE_ROLE",
                "_FORCE_LOGGING",
                "_NAME",
                "080220151025",
                "_PLUGGABLE",
                "_CON_ID",
                "PNAME",
                "_PDBID",
                "_POPENMODE",
                "_PRESTRICTED",
                "42424242",
                "_PRECOVERY_STATUS",
                "232323",
                "_PBLOCK_SIZE",
            ],
            [
                TableRow(
                    path=["software", "applications", "oracle", "instance"],
                    key_columns={
                        "sid": "SID",
                    },
                    inventory_columns={
                        "pname": "PNAME",
                        "version": "VERSION",
                        "openmode": "OPENMODE",
                        "logmode": "LOGMODE",
                        "logins": "LOGINS",
                        "db_creation_time": "2015-02-08 10:25",
                    },
                    status_columns={
                        "db_uptime": 123,
                        "host": None,
                    },
                ),
            ],
        ),
    ],
)
def test_inv_oracle_instance(
    line: list[str],
    expected_data: InventoryResult,
) -> None:
    assert list(inventory_oracle_instance(parse_oracle_instance([line]))) == expected_data


def test_inv_oracle_instance_multiline() -> None:
    lines = [
        [
            "SID-ERROR",
            "FAILURE",
            "ERROR: ORA-12541: TNS:no listener   SP2-0751: Unable to connect to Oracle.  "
            "Exiting SQL*Plus",
        ],
        [
            "SID",
            "VERSION",
            "OPENMODE",
            "LOGINS",
            "_ARCHIVER",
            "123",
            "_DBID",
            "LOGMODE",
            "_DATABASE_ROLE",
            "_FORCE_LOGGING",
            "_NAME",
            "080220151025",
            "_PLUGGABLE",
            "_CON_ID",
            "",
            "_PDBID",
            "_POPENMODE",
            "_PRESTRICTED",
            "42424242",
            "_PRECOVERY_STATUS",
            "232323",
            "_PBLOCK_SIZE",
        ],
        [
            "SID",
            "VERSION",
            "_OPENMODE",
            "LOGINS",
            "_ARCHIVER",
            "123456",
            "_DBID",
            "LOGMODE",
            "_DATABASE_ROLE",
            "_FORCE_LOGGING",
            "_NAME",
            "080220151026",
            "TRUE",
            "_CON_ID",
            "PNAME",
            "_PDBID",
            "POPENMODE",
            "_PRESTRICTED",
            "42424242",
            "_PRECOVERY_STATUS",
            "456",
            "_PBLOCK_SIZE",
        ],
    ]
    expected_data = [
        TableRow(
            path=["software", "applications", "oracle", "instance"],
            key_columns={
                "sid": "SID-ERROR",
            },
            inventory_columns={
                "pname": None,
                "version": None,
                "openmode": None,
                "logmode": None,
                "logins": None,
                "db_creation_time": None,
            },
        ),
        TableRow(
            path=["software", "applications", "oracle", "instance"],
            key_columns={
                "sid": "SID",
            },
            inventory_columns={
                "pname": None,
                "version": "VERSION",
                "openmode": "OPENMODE",
                "logmode": "LOGMODE",
                "logins": "LOGINS",
                "db_creation_time": "2015-02-08 10:25",
            },
            status_columns={
                "db_uptime": 123,
                "host": None,
            },
        ),
        TableRow(
            path=["software", "applications", "oracle", "instance"],
            key_columns={
                "sid": "SID",
            },
            inventory_columns={
                "pname": "PNAME",
                "version": "VERSION",
                "openmode": "POPENMODE",
                "logmode": "LOGMODE",
                "logins": "ALLOWED",
                "db_creation_time": "2015-02-08 10:26",
            },
            status_columns={
                "db_uptime": 456,
                "host": None,
            },
        ),
    ]

    assert sort_inventory_result(
        inventory_oracle_instance(parse_oracle_instance(lines))
    ) == sort_inventory_result(expected_data)


def test_discover_template_database_negative_uptime():
    # SUP-21457
    instance_line = "OOOOOOOO|19.17.0.0.0|OPEN|ALLOWED|STARTED|111111|2222222222|ARCHIVELOG|PRIMARY|NO|OOOOOOOO|333333333333|TRUE|3|TTTT|4444444444|MOUNTED||5555555555|ENABLED|-1|6666|HHHHHHHH"
    string_table = [instance_line.split("|")]
    section = parse_oracle_instance(string_table)
    items = list(oracle_instance_check.discover_oracle_instance_uptime(section))
    assert not items
