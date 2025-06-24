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
        "--password-reference",
        Secret(0),
        "--metrics=my_metric_name",
        "--text=my_additional_text",
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
                "--password-reference",
                Secret(0),
                "--port=5432",
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
                "--password-reference",
                Secret(0),
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
                "--password-reference",
                Secret(0),
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
