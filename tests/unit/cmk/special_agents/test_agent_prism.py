#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.special_agents.agent_prism import base_url


@pytest.mark.parametrize(
    "server, expected",
    [
        pytest.param("prism.example.com", "https://prism.example.com:9440", id="host name"),
        pytest.param("192.0.2.7", "https://192.0.2.7:9440", id="IPv4"),
        pytest.param("2001:db8::7", "https://[2001:db8::7]:9440", id="IPv6 in brackets"),
    ],
)
def test_base_url_puts_only_ipv6_in_brackets(server: str, expected: str) -> None:
    assert base_url(server, 9440) == expected
