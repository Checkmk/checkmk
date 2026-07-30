#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

import pytest

from cmk.plugins.kube.server_side_calls.special_agent_rustik import special_agent_rustik
from cmk.server_side_calls.v1 import (
    EnvProxy,
    HostConfig,
    IPv4Config,
    NoProxy,
    Secret,
    URLProxy,
)

HOST_CONFIG = HostConfig(name="kubi", ipv4_config=IPv4Config(address="11.211.3.32"))

SECRET = Secret(1)
URL = "https://11.211.3.32:8080"

MINIMAL_PARAMS: Mapping[str, object] = {"url": URL, "shared_secret": SECRET, "verify_cert": True}


def _arguments(
    params: Mapping[str, object], host_config: HostConfig = HOST_CONFIG
) -> Sequence[str | Secret]:
    (command,) = special_agent_rustik(params, host_config)
    return command.command_arguments


@pytest.mark.parametrize(
    "params, expected",
    [
        pytest.param({}, ["--secret-id", SECRET, URL], id="minimal"),
        pytest.param(
            {"verify_cert": False},
            ["--secret-id", SECRET, "--no-cert-check", URL],
            id="cert check disabled by the negated flag",
        ),
        pytest.param(
            {"proxy": EnvProxy()},
            ["--secret-id", SECRET, "--proxy", "FROM_ENVIRONMENT", URL],
            id="proxy from environment",
        ),
        pytest.param(
            {"proxy": NoProxy()},
            ["--secret-id", SECRET, "--proxy", "NO_PROXY", URL],
            id="no proxy",
        ),
        pytest.param(
            {"proxy": URLProxy(url="http://proxy:8080")},
            ["--secret-id", SECRET, "--proxy", "http://proxy:8080", URL],
            id="explicit proxy url",
        ),
        pytest.param({"timeout": {}}, ["--secret-id", SECRET, URL], id="timeouts left empty"),
        pytest.param(
            {"timeout": {"connect": 5}},
            ["--secret-id", SECRET, "--connect-timeout", "5", URL],
            id="connect timeout only",
        ),
        pytest.param(
            {"timeout": {"read": 8}},
            ["--secret-id", SECRET, "--read-timeout", "8", URL],
            id="read timeout only",
        ),
        pytest.param(
            {"verify_cert": False, "proxy": NoProxy(), "timeout": {"connect": 5, "read": 8}},
            [
                "--secret-id",
                SECRET,
                "--proxy",
                "NO_PROXY",
                "--connect-timeout",
                "5",
                "--read-timeout",
                "8",
                "--no-cert-check",
                URL,
            ],
            id="every option set",
        ),
    ],
)
def test_command_arguments(params: Mapping[str, object], expected: Sequence[str | Secret]) -> None:
    assert _arguments({**MINIMAL_PARAMS, **params}) == expected


def test_url_macros_are_replaced() -> None:
    host_config = HostConfig(
        name="kubi",
        ipv4_config=IPv4Config(address="11.211.3.32"),
        macros={"$HOSTADDRESS$": "11.211.3.32"},
    )

    arguments = _arguments({**MINIMAL_PARAMS, "url": "https://$HOSTADDRESS$:8080"}, host_config)

    assert arguments[-1] == URL
