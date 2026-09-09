#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import cmk.plugins.aws.special_agent.agent_aws as agent
from cmk.plugins.aws.special_agent.agent_aws import parse_arguments

PROXY_ARGS = [
    "--hostname",
    "foo",
    "--piggyback-naming-convention",
    "ip_region_instance",
    "--proxy-host",
    "proxy.example.com",
    "--proxy-port",
    "3128",
    "--proxy-user",
    "alice",
]


def test_proxy_without_secret_has_no_credentials() -> None:
    args = parse_arguments(PROXY_ARGS)

    config = agent._get_proxy(args)  # noqa: SLF001

    assert config is not None
    assert config.proxies == {"https": "proxy.example.com:3128"}


def test_proxy_secret_becomes_part_of_the_address() -> None:
    args = parse_arguments([*PROXY_ARGS, "--proxysecret", "s3cret"])

    config = agent._get_proxy(args)  # noqa: SLF001

    assert config is not None
    assert config.proxies == {"https": "alice:s3cret@proxy.example.com:3128"}
