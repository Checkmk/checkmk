#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

import pytest

from cmk.plugins.veeam.server_side_calls.special_agent import commands_function, Params
from cmk.server_side_calls.v1 import HostConfig, IPv4Config, Secret

HOST_CONFIG = HostConfig(name="veeam-server", ipv4_config=IPv4Config(address="1.2.3.4"))

BASE_PARAMS = {
    "port": 9419,
    "user": "monitoring",
    "password": Secret(1),
    "disable_cert_verification": False,
}


def _arguments(params: Mapping[str, object]) -> Sequence[str | Secret]:
    (command,) = commands_function(Params.model_validate(params), HOST_CONFIG)
    return command.command_arguments


@pytest.mark.parametrize(
    "connection, expected_address",
    [
        pytest.param(("ip_address", None), "1.2.3.4", id="IP address of the host"),
        pytest.param(("host_name", None), "veeam-server", id="name of the host"),
        pytest.param(("custom_address", "backup.example.com"), "backup.example.com", id="custom"),
    ],
)
def test_connection_address_is_derived_from_the_host(
    connection: tuple[str, str | None], expected_address: str
) -> None:
    assert _arguments({**BASE_PARAMS, "connection": connection})[-1] == expected_address


def test_custom_address_resolves_macros() -> None:
    host_config = HostConfig(
        name="veeam-server",
        ipv4_config=IPv4Config(address="1.2.3.4"),
        macros={"$CUSTOM$": "backup.example.com"},
    )

    (command,) = commands_function(
        Params.model_validate({**BASE_PARAMS, "connection": ("custom_address", "$CUSTOM$")}),
        host_config,
    )

    assert command.command_arguments[-1] == "backup.example.com"


def test_certificate_is_verified_against_the_host_name_by_default() -> None:
    arguments = _arguments({**BASE_PARAMS, "connection": ("ip_address", None)})

    assert list(arguments) == [
        "--user",
        "monitoring",
        "--password-id",
        Secret(1),
        "--port",
        "9419",
        "--cert-server-name",
        "veeam-server",
        "1.2.3.4",
    ]


def test_skipping_verification_disables_certificate_verification() -> None:
    arguments = _arguments(
        {
            **BASE_PARAMS,
            "connection": ("ip_address", None),
            "disable_cert_verification": True,
        }
    )

    assert "--disable-cert-verification" in arguments
    assert "--cert-server-name" not in arguments
