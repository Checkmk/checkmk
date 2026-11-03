#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

from cmk.bakery.v1 import OS, Plugin, PluginConfig
from cmk.base.plugins.bakery.mssql import get_mssql_files

_PASSWORD = ("cmk_postprocessed", "explicit_password", ("uuid-1", "mypass"))


def test_mssql_files_system_auth() -> None:
    conf = {"deployment": ("sync", None), "auth_default": ("system", None)}
    assert sorted(get_mssql_files(conf), key=repr) == sorted(
        [
            Plugin(base_os=OS.WINDOWS, source=Path("mssql.vbs")),
            PluginConfig(
                base_os=OS.WINDOWS,
                lines=["[auth]", "type = system", "[timeouts]"],
                target=Path("mssql.ini"),
            ),
        ],
        key=repr,
    )


def test_mssql_files_db_auth() -> None:
    conf = {
        "deployment": ("sync", None),
        "auth_default": ("db", {"user": "myuser", "password": _PASSWORD}),
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
        "deployment": ("sync", None),
        "auth_default": ("system", None),
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
        "deployment": ("sync", None),
        "auth_default": ("system", None),
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
        "deployment": ("sync", None),
        "auth_default": ("system", None),
        "auth_instances": [
            {"instance": "SERVER\\INST1", "auth": ("db", {"user": "user1", "password": _PASSWORD})},
        ],
    }
    assert sorted(get_mssql_files(conf), key=repr) == sorted(
        [
            Plugin(base_os=OS.WINDOWS, source=Path("mssql.vbs")),
            PluginConfig(
                base_os=OS.WINDOWS,
                lines=["[auth]", "type = system", "[timeouts]"],
                target=Path("mssql.ini"),
            ),
            PluginConfig(
                base_os=OS.WINDOWS,
                lines=[
                    "[auth]",
                    "type = db",
                    "username = user1",
                    "password = mypass",
                    "[timeouts]",
                ],
                target=Path("mssql_SERVER_INST1.ini"),
            ),
        ],
        key=repr,
    )


def test_mssql_files_all_options() -> None:
    conf = {
        "deployment": ("sync", None),
        "auth_default": ("db", {"user": "myuser", "password": _PASSWORD}),
        "auth_instances": [{"instance": "HOST\\INST", "auth": ("system", None)}],
        "inst_excludes": ["inst1", "inst2"],
        "timeout_connection": 15,
        "timeout_command": 30,
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
                    "[instance]",
                    "exclude = inst1,inst2",
                    "[timeouts]",
                    "timeout_connection = 15",
                    "timeout_command = 30",
                ],
                target=Path("mssql.ini"),
            ),
            PluginConfig(
                base_os=OS.WINDOWS,
                lines=[
                    "[auth]",
                    "type = system",
                    "[timeouts]",
                    "timeout_connection = 15",
                    "timeout_command = 30",
                ],
                target=Path("mssql_HOST_INST.ini"),
            ),
        ],
        key=repr,
    )


def test_mssql_files_sanitize_instance_with_comma() -> None:
    conf = {
        "deployment": ("sync", None),
        "auth_default": ("system", None),
        "auth_instances": [{"instance": "SERVER,1433", "auth": ("system", None)}],
    }
    assert [f.target for f in get_mssql_files(conf) if isinstance(f, PluginConfig)] == [
        Path("mssql.ini"),
        Path("mssql_SERVER_1433.ini"),
    ]


def test_mssql_files_do_not_deploy() -> None:
    conf = {"deployment": ("do_not_deploy", None)}
    assert list(get_mssql_files(conf)) == []
