#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

import pytest

from cmk.plugins.collection.server_side_calls.sql import active_check_sql
from cmk.server_side_calls.v1 import HostConfig, IPv4Config, StoredSecret


@pytest.mark.parametrize(
    "params,expected_args",
    [
        (
            {
                "description": "foo",
                "dbms": "postgres",
                "name": "bar",
                "user": "hans",
                "password": ("store", "wurst"),
                "sql": (""),
                "perfdata": "my_metric_name",
                "text": "my_additional_text",
            },
            [
                "--hostname=ipaddress",
                "--dbms=postgres",
                "--name=bar",
                "--user=hans",
                StoredSecret(value="wurst", format="--password=%s"),
                "--metrics=my_metric_name",
                "--text=my_additional_text",
                "",
            ],
        ),
    ],
)
def test_check_sql_argument_parsing(
    params: Mapping[str, str | tuple[str]], expected_args: Sequence[str]
) -> None:
    """Tests if all required arguments are present."""
    (command,) = active_check_sql(
        params,
        HostConfig(
            name="hostname",
            ipv4_config=IPv4Config(address="ipaddress"),
        ),
        {},
    )
    assert command.command_arguments == expected_args
