#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable, Mapping
from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from cmk.bakery.v2 import OS, Plugin, PluginConfig, Secret
from cmk.plugins.mssql.bakery.mk_ms_sql import bakery_plugin_mk_ms_sql
from tests.testlib.unit.bakelet_testing import APIBakeletTestSet, run_v2_bakelet_test

PLUGIN_NAME = "mk_ms_sql"

_GuiConfType = Mapping[str, object]


def _password(password: str) -> Secret:
    return Secret(password, "explicit_password", "uuid")


mk_ms_sql_conf: _GuiConfType = {
    "deployment": ("sync", None),
    "main": {"auth": ("local", None)},
    "other": [],
}


mk_ms_sql_result_lines = [
    "---",
    "mssql:",
    "  main:",
    "    authentication:",
    "      username: ''",
    "      type: integrated",
]

mk_ms_sql_result_lines_full = [
    "---",
    "mssql:",
    "  main:",
    "    authentication:",
    "      username: u",
    "      password: p",
    "      type: sql_server",
    "    connection:",
    "      hostname: h",
    "      fail_over_partner: f",
    "      port: 12345",
    "      timeout: 100",
    "      trust_server_certificate: false",
    "      tls:",
    "        ca: ''",
    "        client_certificate: path/to/file",
    "      backend: odbc",
    "      exclude_databases:",
    "      - model",
    "      - master",
    "      - msdb",
    "      - tempdb",
    "    cache_age: 501",
    "    piggyback_host: AXZ",
    "    sections:",
    "    - instance: null",
    "    - databases:",
    "        is_async: true",
    "    - backup:",
    "        is_async: true",
    "    - mirroring: null",
    "    options:",
    "      max_connections: 100",
]

mk_ms_sql_conf_full: _GuiConfType = {
    "deployment": ("sync", None),
    "main": {
        "auth": ("remote", {"user": "u", "password": _password("p")}),
        "conn": {
            "hostname": "h",
            "fail_over_partner": "f",
            "port": 12345,
            "timeout": 100,
            "trust_server_certificate": False,
            "tls": {
                "ca": "aaaa",  # must be ignored
                "client_certificate": "path/to/file",
            },
            "backend": "odbc",
            "exclude_databases": ["model", "master", "msdb", "tempdb"],
        },
        "sections": {
            "instance": "sync",
            "databases": "asynchronous",
            "backup": "asynchronous",
            "jobs": "disabled",
            "mirroring": "sync",
        },
        "cache_age": 501,
        "piggyback_host": "AXZ",
        "options": {"max_connections": 100},
    },
    "other": [],
}

mk_ms_sql_result_lines_conn = [
    "---",
    "mssql:",
    "  main:",
    "    authentication:",
    "      username: u",
    "      password: p",
    "      type: sql_server",
    "    connection:",
    "      hostname: h",
    "      fail_over_partner: f",
    "      port: 12345",
    "      timeout: 100",
    "      trust_server_certificate: true",
]

mk_ms_sql_conf_conn: _GuiConfType = {
    "deployment": ("sync", None),
    "main": {
        "auth": ("remote", {"user": "u", "password": _password("p")}),
        "conn": {
            "hostname": "h",
            "fail_over_partner": "f",
            "port": 12345,
            "timeout": 100,
            "trust_server_certificate": True,
            "tls": {
                "ca": "",  # must be ignored
                "client_certificate": "",
            },
        },
    },
    "other": [],
}

mk_ms_sql_result_lines_section = [
    "---",
    "mssql:",
    "  main:",
    "    authentication:",
    "      username: u",
    "      password: p",
    "      type: sql_server",
    "    sections:",
    "    - instance: null",
]

mk_ms_sql_conf_section: _GuiConfType = {
    "deployment": ("sync", None),
    "main": {
        "auth": ("remote", {"user": "u", "password": _password("p")}),
        "sections": {
            "instance": "sync",
        },
    },
    "other": [],
}

mk_ms_sql_result_lines_discovery_no = [
    "---",
    "mssql:",
    "  main:",
    "    authentication:",
    "      username: u",
    "      password: p",
    "      type: sql_server",
    "    discovery:",
    "      detect: false",
]

mk_ms_sql_result_lines_discovery_include = [
    "---",
    "mssql:",
    "  main:",
    "    authentication:",
    "      username: u",
    "      password: p",
    "      type: sql_server",
    "    discovery:",
    "      detect: true",
    "      include:",
    "      - '1'",
    "      - '2'",
]

mk_ms_sql_conf_discovery_no: _GuiConfType = {
    "deployment": ("sync", None),
    "main": {
        "auth": ("remote", {"user": "u", "password": _password("p")}),
        "discovery": {"detect": False, "instances": ("all", None)},
    },
    "other": [],
}

mk_ms_sql_conf_discovery_include: _GuiConfType = {
    "deployment": ("sync", None),
    "main": {
        "auth": ("remote", {"user": "u", "password": _password("p")}),
        "discovery": {"detect": True, "instances": ("include", ["1", "2"])},
    },
    "other": [],
}

mk_ms_sql_result_lines_discovery_exclude = [
    "---",
    "mssql:",
    "  main:",
    "    authentication:",
    "      username: u",
    "      password: p",
    "      type: sql_server",
    "    discovery:",
    "      detect: true",
    "      exclude:",
    "      - A",
    "      - '2'",
]

mk_ms_sql_conf_discovery_exclude: _GuiConfType = {
    "deployment": ("sync", None),
    "main": {
        "auth": ("remote", {"user": "u", "password": _password("p")}),
        "discovery": {"detect": True, "instances": ("exclude", ["A", "2"])},
    },
    "other": [],
}

mk_ms_sql_result_lines_instances_short = [
    "---",
    "mssql:",
    "  main:",
    "    authentication:",
    "      username: u",
    "      password: p",
    "      type: sql_server",
    "    instances:",
    "    - sid: a",
    "      alias: alias",
    "      piggyback:",
    "        hostname: h",
]

mk_ms_sql_conf_instances_short: _GuiConfType = {
    "deployment": ("sync", None),
    "main": {
        "auth": ("remote", {"user": "u", "password": _password("p")}),
        "instances": [{"sid": "a", "alias": "alias", "piggyback": {"hostname": "h"}}],
    },
    "other": [],
}

mk_ms_sql_result_lines_instances_empty_piggyback = [
    "---",
    "mssql:",
    "  main:",
    "    authentication:",
    "      username: u",
    "      password: p",
    "      type: sql_server",
    "    instances:",
    "    - sid: a",
]

mk_ms_sql_conf_instances_empty_piggyback: _GuiConfType = {
    "deployment": ("sync", None),
    "main": {
        "auth": ("remote", {"user": "u", "password": _password("p")}),
        "instances": [{"sid": "a", "piggyback": {}}],
    },
    "other": [],
}

mk_ms_sql_result_lines_instances_full = [
    "---",
    "mssql:",
    "  main:",
    "    authentication:",
    "      username: u",
    "      password: p",
    "      type: sql_server",
    "    instances:",
    "    - sid: a",
    "      alias: alias",
    "      piggyback:",
    "        hostname: h",
    "    - sid: b",
    "      connection:",
    "        hostname: h",
    "        fail_over_partner: f",
    "        port: 12345",
    "        timeout: 100",
    "        trust_server_certificate: false",
    "        backend: auto",
    "      authentication:",
    "        username: u",
    "        password: p",
    "        type: sql_server",
    "      alias: b_alias",
    "      piggyback:",
    "        hostname: h",
    "        cache_age: 505",
    "        sections:",
    "        - instance: null",
    "        - databases:",
    "            is_async: true",
    "        - backup:",
    "            is_async: true",
    "        - mirroring: null",
]

mk_ms_sql_conf_instances_full: _GuiConfType = {
    "deployment": ("sync", None),
    "main": {
        "auth": ("remote", {"user": "u", "password": _password("p")}),
        "instances": [
            {"sid": "a", "alias": "alias", "piggyback": {"hostname": "h"}},
            {
                "sid": "b",
                "alias": "b_alias",
                "auth": ("remote", {"user": "u", "password": _password("p")}),
                "conn": {
                    "hostname": "h",
                    "fail_over_partner": "f",
                    "port": 12345,
                    "timeout": 100,
                    "trust_server_certificate": False,
                    "backend": "auto",
                },
                "piggyback": {
                    "hostname": "h",
                    "sections": {
                        "instance": "sync",
                        "databases": "asynchronous",
                        "backup": "asynchronous",
                        "jobs": "disabled",
                        "mirroring": "sync",
                    },
                    "cache_age": 505,
                },
            },
        ],
    },
    "other": [],
}

mk_ms_sql_result_lines_options = [
    "---",
    "mssql:",
    "  main:",
    "    authentication:",
    "      username: u",
    "      password: p",
    "      type: sql_server",
    "    options:",
    "      max_connections: 100",
    "      ignore_inactive_local_instances: true",
]

mk_ms_sql_conf_options: _GuiConfType = {
    "deployment": ("sync", None),
    "main": {
        "auth": ("remote", {"user": "u", "password": _password("p")}),
        "options": {"max_connections": 100, "ignore_inactive_local_instances": True},
    },
    "other": [],
}

mk_ms_sql_result_lines_configs = [
    "---",
    "mssql:",
    "  main:",
    "    authentication:",
    "      username: u",
    "      password: p",
    "      type: sql_server",
    "  configs:",
    "  - main:",
    "      authentication:",
    "        username: a",
    "        password: a",
    "        type: sql_server",
    "  - main:",
    "      authentication:",
    "        username: b",
    "        password: b",
    "        type: sql_server",
]

mk_ms_sql_conf_configs: _GuiConfType = {
    "deployment": ("sync", None),
    "main": {
        "auth": ("remote", {"user": "u", "password": _password("p")}),
    },
    "other": [
        {"auth": ("remote", {"user": "a", "password": _password("a")})},
        {"auth": ("remote", {"user": "b", "password": _password("b")})},
    ],
}


def _source(base_os: OS) -> Path:
    return Path("..", "mk-sql.exe") if base_os == OS.WINDOWS else Path("..", "linux", "mk-sql")


def _target(base_os: OS) -> Path:
    return Path("mk-sql.exe") if base_os == OS.WINDOWS else Path("mk-sql")


files: list[Plugin | PluginConfig] = [
    Plugin(
        base_os=OS.WINDOWS,
        source=_source(OS.WINDOWS),
        target=_target(OS.WINDOWS),
    )
]

files += [PluginConfig(base_os=OS.WINDOWS, lines=mk_ms_sql_result_lines, target=Path("mk-sql.yml"))]

files_base: list[Plugin | PluginConfig] = [
    Plugin(
        base_os=base_os,
        source=_source(base_os),
        target=_target(base_os),
    )
    for base_os in (OS.LINUX, OS.WINDOWS)
]


def _combine(lines: Iterable[str]) -> list[Plugin | PluginConfig]:
    return files_base + [
        PluginConfig(base_os=base_os, lines=list(lines), target=Path("mk-sql.yml"))
        for base_os in (OS.LINUX, OS.WINDOWS)
    ]


TEST_SETS: dict[str, APIBakeletTestSet] = {
    "do_not_deploy": APIBakeletTestSet(
        conf={"deployment": ("do_not_deploy", None)},
        files=[],
    ),
    "default": APIBakeletTestSet(
        conf=mk_ms_sql_conf,
        files=files,
    ),
    "deploy_without_main": APIBakeletTestSet(
        conf={"deployment": ("sync", None)},
        files=files,
    ),
    "full": APIBakeletTestSet(
        conf=mk_ms_sql_conf_full,
        files=_combine(mk_ms_sql_result_lines_full),
    ),
    "conn": APIBakeletTestSet(
        conf=mk_ms_sql_conf_conn,
        files=_combine(mk_ms_sql_result_lines_conn),
    ),
    "section": APIBakeletTestSet(
        conf=mk_ms_sql_conf_section,
        files=_combine(mk_ms_sql_result_lines_section),
    ),
    "discovery_no": APIBakeletTestSet(
        conf=mk_ms_sql_conf_discovery_no,
        files=_combine(mk_ms_sql_result_lines_discovery_no),
    ),
    "discovery_include": APIBakeletTestSet(
        conf=mk_ms_sql_conf_discovery_include,
        files=_combine(mk_ms_sql_result_lines_discovery_include),
    ),
    "discovery_exclude": APIBakeletTestSet(
        conf=mk_ms_sql_conf_discovery_exclude,
        files=_combine(mk_ms_sql_result_lines_discovery_exclude),
    ),
    "instances_short": APIBakeletTestSet(
        conf=mk_ms_sql_conf_instances_short,
        files=_combine(mk_ms_sql_result_lines_instances_short),
    ),
    "instances_empty_piggyback": APIBakeletTestSet(
        conf=mk_ms_sql_conf_instances_empty_piggyback,
        files=_combine(mk_ms_sql_result_lines_instances_empty_piggyback),
    ),
    "instances_full": APIBakeletTestSet(
        conf=mk_ms_sql_conf_instances_full,
        files=_combine(mk_ms_sql_result_lines_instances_full),
    ),
    "options": APIBakeletTestSet(
        conf=mk_ms_sql_conf_options,
        files=_combine(mk_ms_sql_result_lines_options),
    ),
    "configs": APIBakeletTestSet(
        conf=mk_ms_sql_conf_configs,
        files=_combine(mk_ms_sql_result_lines_configs),
    ),
}


@pytest.mark.parametrize("test_name", TEST_SETS)
def test_mk_ms_sql(
    test_name: str,
    mocker: MockerFixture,
    tmp_path: Path,
) -> None:
    run_v2_bakelet_test(bakery_plugin_mk_ms_sql, TEST_SETS[test_name], mocker, tmp_path)
