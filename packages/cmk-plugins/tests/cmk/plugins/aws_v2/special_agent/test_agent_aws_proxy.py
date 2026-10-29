#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import cmk.plugins.aws_v2.special_agent.agent_aws_v2 as agent
from cmk.plugins.aws_v2.special_agent.agent_aws_v2 import parse_arguments

BASE_ARGS = [
    "--hostname",
    "foo",
    "--piggyback-naming-convention",
    "ip_region_instance",
]

PROXY_ARGS = [
    *BASE_ARGS,
    "--proxy-host",
    "proxy.example.com",
    "--proxy-port",
    "3128",
    "--proxy-user",
    "alice",
]


def test_proxy_without_secret_has_no_credentials() -> None:
    config = agent._client_config(parse_arguments(PROXY_ARGS))  # noqa: SLF001

    assert config.proxies == {"https": "proxy.example.com:3128"}


def test_proxy_secret_becomes_part_of_the_address() -> None:
    config = agent._client_config(  # noqa: SLF001
        parse_arguments([*PROXY_ARGS, "--proxysecret", "s3cret"])
    )

    assert config.proxies == {"https": "alice:s3cret@proxy.example.com:3128"}


def test_no_proxy_without_a_proxy_host() -> None:
    config = agent._client_config(parse_arguments(BASE_ARGS))  # noqa: SLF001

    assert config.proxies is None


def test_throttled_calls_are_retried_in_standard_mode() -> None:
    config = agent._client_config(parse_arguments(BASE_ARGS))  # noqa: SLF001

    assert config.retries == {"mode": "standard"}
