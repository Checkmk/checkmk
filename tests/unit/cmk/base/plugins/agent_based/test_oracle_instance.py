#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from tests.unit.conftest import FixRegister

from cmk.utils.type_defs import CheckPluginName

from cmk.base.plugins.agent_based.agent_based_api.v1 import Result, Service, State, TableRow
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import CheckResult, InventoryResult
from cmk.base.plugins.agent_based.oracle_instance import (
    GeneralError,
    Instance,
    InvalidData,
    inventory_oracle_instance,
    parse_oracle_instance,
)

from .utils_inventory import sort_inventory_result


def test_parse_oracle_instance() -> None:
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
            ["I442", "FAILURE"],
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
        "I442": InvalidData("I442"),
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
            pdb=False,
            pluggable="FALSE",
            pname=None,
            popenmode=None,
            prestricted=None,
            ptotal_size=None,
            pup_seconds=None,
            sid="IC731",
            up_seconds="2144847",
            version="12.1.0.2.0",
        ),
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
            pdb=False,
            pluggable="FALSE",
            pname=None,
            popenmode=None,
            prestricted=None,
            ptotal_size=None,
            pup_seconds=None,
            sid="XE",
            up_seconds="1212537",
            version="11.2.0.2.0",
        ),
    }


def test_discover_oracle_instance(fix_register: FixRegister) -> None:
    assert list(
        fix_register.check_plugins[CheckPluginName("oracle_instance")].discovery_function(
            {
                "a": InvalidData(sid="a"),
                "b": GeneralError(
                    sid="b",
                    err="something went wrong",
                ),
                "c": Instance(sid="c"),
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
                Result(
                    state=State.OK,
                    summary="Database Name IC73, Status OPEN, Role PRIMARY, Version 12.1.0.2.0, Logins allowed, Log Mode archivelog, Force Logging yes",
                ),
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
                Result(
                    state=State.CRIT,
                    summary="Database Name IC73, Status LOCKED(!!), Role PRIMARY, Version 12.1.0.2.0, Log Mode archivelog, Force Logging yes",
                ),
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
                Result(
                    state=State.CRIT,
                    summary="Database Name IC73, Status OPEN, Role PRIMARY, Version 12.1.0.2.0, Logins restricted(!!), Log Mode archivelog, Force Logging yes",
                ),
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
                Result(
                    state=State.WARN,
                    summary="Database Name IC73, Status OPEN, Role PRIMARY, Version 12.1.0.2.0, Logins allowed, Log Mode noarchivelog(!)",
                ),
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
                Result(
                    state=State.CRIT,
                    summary="Database Name IC73, Status OPEN, Role PRIMARY, Version 12.1.0.2.0, Logins allowed, Log Mode archivelog. Archiver stopped(!!), Force Logging yes",
                ),
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
                Result(
                    state=State.WARN,
                    summary="Database Name IC73, Status OPEN, Role PRIMARY, Version 12.1.0.2.0, Logins allowed, Log Mode archivelog, Force Logging no(!)",
                ),
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
                )
            ],
            id="error",
        ),
    ],
)
def test_check_oracle_instance(
    fix_register: FixRegister,
    agent_line: list[str],
    expected_result: CheckResult,
) -> None:
    assert (
        list(
            fix_register.check_plugins[CheckPluginName("oracle_instance")].check_function(
                item="IC731",
                params={
                    "logins": 2,
                    "noforcelogging": 1,
                    "noarchivelog": 1,
                    "primarynotopen": 2,
                },
                section=parse_oracle_instance([agent_line]),
            )
        )
        == expected_result
    )


def test_check_oracle_instance_empty_section(fix_register: FixRegister) -> None:
    assert list(
        fix_register.check_plugins[CheckPluginName("oracle_instance")].check_function(
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
                "RAW_UP_SECONDS",
                "_DBID",
                "LOGMODE",
                "_DATABASE_ROLE",
                "_FORCE_LOGGING",
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
                        "logmode": "LOGMODE",
                        "logins": "LOGINS",
                        "db_creation_time": None,
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
                        "db_creation_time": None,
                    },
                    status_columns={
                        "db_uptime": 123,
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
                "RAW_UP_SECONDS",
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
                "RAW_UP_SECONDS",
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
                "_PTOTAL_SIZE",
                "_PRECOVERY_STATUS",
                "_PUP_SECONDS",
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
                "_PTOTAL_SIZE",
                "_PRECOVERY_STATUS",
                "_PUP_SECONDS",
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
            "_PTOTAL_SIZE",
            "_PRECOVERY_STATUS",
            "_PUP_SECONDS",
            "_PBLOCK_SIZE",
        ],
        [
            "SID",
            "VERSION",
            "_OPENMODE",
            "LOGINS",
            "_ARCHIVER",
            "_RAW_UP_SECONDS",
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
            "_PTOTAL_SIZE",
            "_PRECOVERY_STATUS",
            "456",
            "_PBLOCK_SIZE",
        ],
    ]
    expected_data = [
        TableRow(
            path=["software", "applications", "oracle", "instance"],
            key_columns={
                "sid": "SID",
            },
            inventory_columns={
                "pname": "",
                "version": "VERSION",
                "openmode": "OPENMODE",
                "logmode": "LOGMODE",
                "logins": "LOGINS",
                "db_creation_time": "2015-02-08 10:25",
            },
            status_columns={
                "db_uptime": 123,
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
            },
        ),
    ]

    assert sort_inventory_result(
        inventory_oracle_instance(parse_oracle_instance(lines))
    ) == sort_inventory_result(expected_data)
