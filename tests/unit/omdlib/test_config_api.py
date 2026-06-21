#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import pytest

from omdlib import main
from omdlib.config_api import (
    ip_address_list_has_error,
    ip_listen_address_has_error,
    network_port_has_error,
)
from omdlib.system_apache import apache_TCP_addr_has_error


@pytest.mark.parametrize(
    "value",
    [
        pytest.param(
            "0.0.0.0",
            id="IP4 address.",
        ),
        pytest.param(
            "0.0.0.0 ::",
            id="Accept all IP4 & IP6 addresses.",
        ),
        pytest.param(
            "1::",
            id="Specify two IP6 addresses.",
        ),
        pytest.param(
            "0.0.0.0 ::/0",
            id="Default value.",
        ),
    ],
)
def test__error_from_config_choice_accept_value(value: str) -> None:
    assert main._error_from_config_choice(ip_address_list_has_error, value) is None


@pytest.mark.parametrize(
    "value",
    [
        pytest.param(
            "६.६.६.६",
            id="Originally valid in Checkmk (but not with xinitd. I kind of want to keep it.",
        ),
        pytest.param(
            "",
            id="This value is needed (I think).",
        ),
        pytest.param(
            "0.0.0.00.0.0.0",
            id="Somebody forgot a whitespace :( ",
        ),
        pytest.param(
            "a::::a",
            id="Invalid ip6 address.",
        ),
        pytest.param(
            "a::b::c",
            id="Invalid ip6 address.",
        ),
        pytest.param(
            ":::",
            id="Invalid ip6 address.",
        ),
    ],
)
def test__error_from_config_choice_reject_value(value: str) -> None:
    assert main._error_from_config_choice(ip_address_list_has_error, value) is not None


@pytest.mark.parametrize(
    "value",
    [
        "[::]",
        "127.0.0.1",
        "example.com",
        "abc",
        "0.0.0",
        "a_b_c",
    ],
)
def test__ok_from_apache_tcp_addr_has_error(value: str) -> None:
    assert main._error_from_config_choice(apache_TCP_addr_has_error, value) is None


@pytest.mark.parametrize(
    "value, message",
    [
        pytest.param(
            "",
            "This is invalid because of: empty host",
        ),
        pytest.param(
            "::",
            "This is invalid because of: empty host",
        ),
        pytest.param(
            "[:::::::]",
            "This is invalid because of: invalid IPv6 address",
        ),
        pytest.param(
            "[zzz]",
            "This is invalid because of: invalid IPv6 address",
        ),
    ],
)
def test__error_from_apache_tcp_addr_has_error(value: str, message: str) -> None:
    result = main._error_from_config_choice(apache_TCP_addr_has_error, value)
    assert result is not None
    assert result.endswith(message)


@pytest.mark.parametrize(
    "value",
    [
        pytest.param(
            "0.0.0.0",
            id="IP4 address.",
        ),
        pytest.param(
            "127.0.0.1",
            id="IP4 localhost.",
        ),
        pytest.param(
            "[::]",
            id="IPv6 wildcard address",
        ),
        pytest.param(
            "[::1]",
            id="IPv6 localhost.",
        ),
    ],
)
def test__error_from_config_choice_listen_address_accept_value(value: str) -> None:
    assert main._error_from_config_choice(ip_listen_address_has_error, value) is None


@pytest.mark.parametrize(
    "value, message",
    [
        pytest.param(
            "",
            "Empty address",
        ),
        pytest.param(
            "127.0.",
            "Invalid IPv4 address",
        ),
        pytest.param(
            "[:::::::",
            "Invalid IPv4 address",
        ),
        pytest.param(
            "[zzz]",
            "Invalid IPv6 address",
        ),
    ],
)
def test__error_from_config_choice_listen_address_has_error(value: str, message: str) -> None:
    result = main._error_from_config_choice(ip_listen_address_has_error, value)
    assert result is not None
    assert result.endswith(message)


def test__error_from_config_choice_network_port() -> None:
    assert main._error_from_config_choice(network_port_has_error, "1024") is None
    assert main._error_from_config_choice(network_port_has_error, "65535") is None
    assert main._error_from_config_choice(network_port_has_error, "22") == "Invalid port number"
    assert main._error_from_config_choice(network_port_has_error, "65536") == "Invalid port number"
    assert main._error_from_config_choice(network_port_has_error, "") == "Invalid port number"
