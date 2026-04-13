#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

from cmk.bakery.v2_unstable import OS, Plugin, PluginConfig
from cmk.plugins.postgres.bakery.mk_postgres import bakery_plugin_mk_postgres

CONFIG = {
    "deployment": ("sync", None),
    "instances_settings": {
        "instances": [
            {
                "instance_pgpass_filepath": "some/other/path",
                "instance_username": "instance_user",
                "instance_env_filepath": "/some/path",
                "instance_name": "",
            },
            {
                "instance_pgpass_filepath": "some/other/path2",
                "instance_username": "instance_user2",
                "instance_env_filepath": "/some/path2",
                "instance_name": "",
            },
        ],
        "db_username": "user",
    },
}

CONFIG_LINES_LINUX = [
    "# Credentials for postgres instances",
    "DBUSER=user",
    "INSTANCE=/some/path:instance_user:some/other/path:",
    "INSTANCE=/some/path2:instance_user2:some/other/path2:",
]

CONFIG_LINES_WINDOWS = [
    "# Credentials for postgres instances",
    "DBUSER=user",
    "INSTANCE=/some/path|instance_user|some/other/path|",
    "INSTANCE=/some/path2|instance_user2|some/other/path2|",
]


def test_no_deploy() -> None:
    conf = bakery_plugin_mk_postgres.parameter_parser({"deployment": ("do_not_deploy", None)})
    assert not list(bakery_plugin_mk_postgres.files_function(conf))


def test_deploy_sync() -> None:
    conf = bakery_plugin_mk_postgres.parameter_parser(CONFIG)
    result = list(bakery_plugin_mk_postgres.files_function(conf))
    assert result == [
        Plugin(base_os=OS.LINUX, source=Path("mk_postgres.py"), interval=None),
        PluginConfig(
            base_os=OS.LINUX,
            lines=CONFIG_LINES_LINUX,
            target=Path("postgres.cfg"),
            include_header=True,
        ),
        Plugin(base_os=OS.WINDOWS, source=Path("mk_postgres.py"), interval=None),
        PluginConfig(
            base_os=OS.WINDOWS,
            lines=CONFIG_LINES_WINDOWS,
            target=Path("postgres.cfg"),
            include_header=True,
        ),
    ]


def test_deploy_cached() -> None:
    conf = bakery_plugin_mk_postgres.parameter_parser({"deployment": ("cached", 300.0)})
    result = list(bakery_plugin_mk_postgres.files_function(conf))
    assert result == [
        Plugin(base_os=OS.LINUX, source=Path("mk_postgres.py"), interval=300),
        Plugin(base_os=OS.WINDOWS, source=Path("mk_postgres.py"), interval=300),
    ]


def test_deploy_with_pg_binary_path() -> None:
    conf = bakery_plugin_mk_postgres.parameter_parser(
        {
            "deployment": ("sync", None),
            "instances_settings": {
                "instances": [
                    {
                        "instance_pgpass_filepath": "some/other/path",
                        "instance_username": "instance_user",
                        "instance_env_filepath": "/some/path",
                        "instance_name": "",
                    },
                ],
                "db_username": "user",
                "pg_binary_path": "/usr/bin/psql",
            },
        }
    )
    result = list(bakery_plugin_mk_postgres.files_function(conf))
    assert result == [
        Plugin(base_os=OS.LINUX, source=Path("mk_postgres.py"), interval=None),
        PluginConfig(
            base_os=OS.LINUX,
            lines=[
                "# Credentials for postgres instances",
                "DBUSER=user",
                "PG_BINARY_PATH=/usr/bin/psql",
                "INSTANCE=/some/path:instance_user:some/other/path:",
            ],
            target=Path("postgres.cfg"),
            include_header=True,
        ),
        Plugin(base_os=OS.WINDOWS, source=Path("mk_postgres.py"), interval=None),
        PluginConfig(
            base_os=OS.WINDOWS,
            lines=[
                "# Credentials for postgres instances",
                "DBUSER=user",
                "PG_BINARY_PATH=/usr/bin/psql",
                "INSTANCE=/some/path|instance_user|some/other/path|",
            ],
            target=Path("postgres.cfg"),
            include_header=True,
        ),
    ]
