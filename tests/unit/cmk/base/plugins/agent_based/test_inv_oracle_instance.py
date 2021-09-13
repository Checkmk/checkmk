#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.utils.type_defs import InventoryPluginName, SectionName

from cmk.base.plugins.agent_based.agent_based_api.v1 import TableRow


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
def test_inv_oracle_instance(fix_register, line, expected_data):
    section = fix_register.agent_sections[SectionName("oracle_instance")]
    parsed = section.parse_function([line])
    inv_plugin = fix_register.inventory_plugins[InventoryPluginName("oracle_instance")]
    assert list(inv_plugin.inventory_function(parsed)) == expected_data


def test_inv_oracle_instance_multiline(fix_register):
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

    section = fix_register.agent_sections[SectionName("oracle_instance")]
    parsed = section.parse_function(lines)  # type: ignore[arg-type]
    inv_plugin = fix_register.inventory_plugins[InventoryPluginName("oracle_instance")]

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

    assert list(inv_plugin.inventory_function(parsed)) == expected_data  # type: ignore[union-attr]
