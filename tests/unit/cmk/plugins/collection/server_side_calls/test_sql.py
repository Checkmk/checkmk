#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping, Sequence

import pytest

from cmk.plugins.sql.server_side_calls.sql import active_check_sql
from cmk.server_side_calls.v1 import HostConfig, IPv4Config, Secret

MINIMAL_CONFIG = {
    "description": "foo",
    "dbms": "postgres",
    "name": "bar",
    "user": "hans",
    "password": Secret(0),
    "sql": "",
}

MINIMAL_HOST_CONFIG = HostConfig(
    name="hostname",
    ipv4_config=IPv4Config(address="ipaddress"),
)


def test_check_sql_simple_ok_case() -> None:
    (command,) = active_check_sql(
        {
            **MINIMAL_CONFIG,
            "perfdata": "my_metric_name",
            "text": "my_additional_text",
        },
        MINIMAL_HOST_CONFIG,
    )
    assert command.command_arguments == [
        "--hostname=ipaddress",
        "--dbms=postgres",
        "--name=bar",
        "--user=hans",
        "--password-id",
        Secret(0),
        "--metrics=my_metric_name",
        "--text=my_additional_text",
        "--sql-statement",
        "",
    ]


def test_check_sql_port_macro_missing() -> None:
    with pytest.raises(ValueError):
        (_command,) = active_check_sql(
            {
                **MINIMAL_CONFIG,
                "port": ("macro", "$missing$"),
            },
            MINIMAL_HOST_CONFIG,
        )


def test_check_sql_port_macro_invalid() -> None:
    with pytest.raises(ValueError):
        (_command,) = active_check_sql(
            {
                **MINIMAL_CONFIG,
                "port": ("macro", "$invalid$"),
            },
            HostConfig(
                name="hostname",
                ipv4_config=IPv4Config(address="ipaddress"),
                macros={"invalid": "nan"},
            ),
        )


@pytest.mark.parametrize(
    "params,host_config, expected_arguments",
    [
        pytest.param(
            {
                **MINIMAL_CONFIG,
                "port": ("macro", "$my_port$"),
            },
            HostConfig(
                name="hostname",
                ipv4_config=IPv4Config(address="ipaddress"),
                macros={"$my_port$": "5432"},
            ),
            [
                "--hostname=ipaddress",
                "--dbms=postgres",
                "--name=bar",
                "--user=hans",
                "--password-id",
                Secret(0),
                "--port=5432",
                "--sql-statement",
                "",
            ],
            id="port macro",
        ),
        pytest.param(
            {
                "description": "foo",
                "dbms": "postgres",
                "name": "bar",
                "user": "$my_user$",
                "password": Secret(0),
                "sql": "",
            },
            HostConfig(
                name="hostname",
                ipv4_config=IPv4Config(address="ipaddress"),
                macros={"$my_user$": "my_user"},
            ),
            [
                "--hostname=ipaddress",
                "--dbms=postgres",
                "--name=bar",
                "--user=my_user",
                "--password-id",
                Secret(0),
                "--sql-statement",
                "",
            ],
            id="user macro",
        ),
        pytest.param(
            {
                "description": "foo",
                "dbms": "postgres",
                "name": "bar",
                "user": "hans",
                "password": Secret(0),
                "sql": "$my_sql_command$",
            },
            HostConfig(
                name="hostname",
                ipv4_config=IPv4Config(address="ipaddress"),
                macros={"$my_sql_command$": "SELECT column FROM table;"},
            ),
            [
                "--hostname=ipaddress",
                "--dbms=postgres",
                "--name=bar",
                "--user=hans",
                "--password-id",
                Secret(0),
                "--sql-statement",
                "SELECT column FROM table\\;",
            ],
            id="sql macro",
        ),
    ],
)
def test_check_sql_macros_replaced(
    params: Mapping[str, str | Secret],
    host_config: HostConfig,
    expected_arguments: Sequence[str | Secret],
) -> None:
    (command,) = active_check_sql(
        params,
        host_config,
    )
    assert command.command_arguments == expected_arguments


def test_check_sql_explicit_port_and_procedure() -> None:
    (command,) = active_check_sql(
        {
            **MINIMAL_CONFIG,
            "host": "db.example.com",
            "port": ("explicit", 6432),
            "procedure": {"useprocs": True},
        },
        MINIMAL_HOST_CONFIG,
    )

    assert command.command_arguments == [
        "--hostname=db.example.com",
        "--dbms=postgres",
        "--name=bar",
        "--user=hans",
        "--password-id",
        Secret(0),
        "--port=6432",
        "--procedure",
        "--sql-statement",
        "",
    ]


@pytest.mark.parametrize(
    "levels, levels_low, expected_levels",
    [
        pytest.param(("fixed", (5.0, 10.0)), None, ["-w:5.0", "-c:10.0"], id="upper only"),
        pytest.param(None, ("fixed", (2.0, 1.0)), ["-w2.0:", "-c1.0:"], id="lower only"),
        pytest.param(
            ("fixed", (5.0, 10.0)), ("fixed", (2.0, 1.0)), ["-w2.0:5.0", "-c1.0:10.0"], id="both"
        ),
        pytest.param(
            ("no_levels", None), ("fixed", (2.0, 1.0)), ["-w2.0:", "-c1.0:"], id="upper disabled"
        ),
    ],
)
def test_check_sql_levels_are_passed_as_ranges(
    levels: tuple[str, tuple[float, float] | None] | None,
    levels_low: tuple[str, tuple[float, float] | None] | None,
    expected_levels: list[str],
) -> None:
    (command,) = active_check_sql(
        {**MINIMAL_CONFIG, "levels": levels, "levels_low": levels_low},
        MINIMAL_HOST_CONFIG,
    )

    assert command.command_arguments[6:8] == expected_levels


def test_check_sql_multiline_statement_is_escaped() -> None:
    (command,) = active_check_sql(
        {**MINIMAL_CONFIG, "sql": "SELECT 0, 'ok';\nSELECT 1"},
        MINIMAL_HOST_CONFIG,
    )

    assert command.command_arguments[-1] == "SELECT 0, 'ok'\\;\\nSELECT 1"
