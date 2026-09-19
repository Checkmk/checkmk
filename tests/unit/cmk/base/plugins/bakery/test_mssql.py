#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

from cmk.bakery.v1 import OS, Plugin, PluginConfig
from cmk.base.plugins.bakery.mssql import get_mssql_files


def test_mssql_files_system_auth() -> None:
    conf: dict[str, object] = {}
    assert sorted(get_mssql_files(conf), key=repr) == sorted(
        [
            Plugin(base_os=OS.WINDOWS, source=Path("mssql.vbs")),
            PluginConfig(
                base_os=OS.WINDOWS,
                lines=[
                    "[auth]",
                    "type = system",
                    "[timeouts]",
                ],
                target=Path("mssql.ini"),
            ),
        ],
        key=repr,
    )


def test_mssql_files_db_auth() -> None:
    conf = {
        "auth_default": ("db", ("myuser", "mypass")),
    }
    assert sorted(get_mssql_files(conf), key=repr) == sorted(
        [
            Plugin(base_os=OS.WINDOWS, source=Path("mssql.vbs")),
            PluginConfig(
                base_os=OS.WINDOWS,
                lines=[
                    "[auth]",
                    "type = db",
                    "username = myuser",
                    "password = mypass",
                    "[timeouts]",
                ],
                target=Path("mssql.ini"),
            ),
        ],
        key=repr,
    )


def test_mssql_files_with_excludes() -> None:
    conf = {
        "inst_excludes": ["inst1", "inst2"],
    }
    assert sorted(get_mssql_files(conf), key=repr) == sorted(
        [
            Plugin(base_os=OS.WINDOWS, source=Path("mssql.vbs")),
            PluginConfig(
                base_os=OS.WINDOWS,
                lines=[
                    "[auth]",
                    "type = system",
                    "[instance]",
                    "exclude = inst1,inst2",
                    "[timeouts]",
                ],
                target=Path("mssql.ini"),
            ),
        ],
        key=repr,
    )


def test_mssql_files_with_timeouts() -> None:
    conf = {
        "timeout_connection": 10,
        "timeout_command": 30,
    }
    assert sorted(get_mssql_files(conf), key=repr) == sorted(
        [
            Plugin(base_os=OS.WINDOWS, source=Path("mssql.vbs")),
            PluginConfig(
                base_os=OS.WINDOWS,
                lines=[
                    "[auth]",
                    "type = system",
                    "[timeouts]",
                    "timeout_connection = 10",
                    "timeout_command = 30",
                ],
                target=Path("mssql.ini"),
            ),
        ],
        key=repr,
    )


def test_mssql_files_with_auth_instances() -> None:
    conf = {
        "auth_instances": [
            ("SERVER\\INST1", ("db", ("user1", "pass1"))),
        ],
    }
    assert sorted(get_mssql_files(conf), key=repr) == sorted(
        [
            Plugin(base_os=OS.WINDOWS, source=Path("mssql.vbs")),
            PluginConfig(
                base_os=OS.WINDOWS,
                lines=[
                    "[auth]",
                    "type = system",
                    "[timeouts]",
                ],
                target=Path("mssql.ini"),
            ),
            PluginConfig(
                base_os=OS.WINDOWS,
                lines=[
                    "[auth]",
                    "type = db",
                    "username = user1",
                    "password = pass1",
                    "[timeouts]",
                ],
                target=Path("mssql_SERVER_INST1.ini"),
            ),
        ],
        key=repr,
    )


def test_mssql_files_sanitize_instance_with_comma() -> None:
    conf = {
        "auth_instances": [
            ("SERVER,1433", "system"),
        ],
    }
    # Check that the instance config file has commas replaced with underscores
    assert [
        r.target
        for r in get_mssql_files(conf)
        if isinstance(r, PluginConfig) and "mssql_" in str(r.target)
    ] == [Path("mssql_SERVER_1433.ini")]
