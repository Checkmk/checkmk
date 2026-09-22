#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from cmk.utils.mtr_config import section_names


@pytest.mark.parametrize(
    "mtr_config, expected_result",
    [
        pytest.param(
            [{"hostname": "foo.example.com", "dns": False}],
            ["foo.example.com"],
            id="lone destination keeps its bare address",
        ),
        pytest.param(
            [
                {"hostname": "foo.example.com", "enforce_what": "ipv4"},
                {"hostname": "bar.example.com", "enforce_what": "ipv6"},
            ],
            ["foo.example.com", "bar.example.com"],
            id="distinct addresses need no suffix",
        ),
        pytest.param(
            [
                {"hostname": "foo.example.com", "enforce_what": "ipv4"},
                {"hostname": "foo.example.com", "enforce_what": "ipv6"},
            ],
            ["foo.example.com (IPv4)", "foo.example.com (IPv6)"],
            id="IP version",
        ),
        pytest.param(
            [
                {"hostname": "foo.example.com", "type": "icmp"},
                {"hostname": "foo.example.com", "type": "tcp"},
                {"hostname": "foo.example.com", "type": "udp"},
            ],
            [
                "foo.example.com (ICMP)",
                "foo.example.com (TCP)",
                "foo.example.com (UDP)",
            ],
            id="connection type",
        ),
        pytest.param(
            [
                {"hostname": "foo.example.com", "type": "tcp", "port": 80},
                {"hostname": "foo.example.com", "type": "tcp", "port": 8080},
            ],
            ["foo.example.com (port 80)", "foo.example.com (port 8080)"],
            id="only the differing setting shows up",
        ),
        pytest.param(
            [
                {"hostname": "foo.example.com", "enforce_what": "ipv4", "port": 80},
                {"hostname": "foo.example.com", "enforce_what": "ipv6", "port": 8080},
            ],
            [
                "foo.example.com (IPv4 port 80)",
                "foo.example.com (IPv6 port 8080)",
            ],
            id="tokens keep their fixed order",
        ),
        pytest.param(
            [
                {"hostname": "foo.example.com", "address": "10.0.0.1", "max_hops": 15},
                {"hostname": "foo.example.com", "address": "10.0.0.2", "max_hops": 30},
            ],
            [
                "foo.example.com (from 10.0.0.1 max hops 15)",
                "foo.example.com (from 10.0.0.2 max hops 30)",
            ],
            id="source address and max hops",
        ),
        pytest.param(
            [
                {"hostname": "foo.example.com"},
                {"hostname": "foo.example.com", "size": 128},
            ],
            ["foo.example.com", "foo.example.com (size 128)"],
            id="unset against set",
        ),
        pytest.param(
            [
                {"hostname": "foo.example.com", "enforce_what": "ipv4"},
                {"hostname": "foo.example.com", "enforce_what": "ipv6"},
                {"hostname": "bar.example.com", "enforce_what": "ipv6"},
            ],
            ["foo.example.com (IPv4)", "foo.example.com (IPv6)", "bar.example.com"],
            id="each address is grouped on its own",
        ),
    ],
)
def test_section_names(
    mtr_config: Sequence[Mapping[str, Any]], expected_result: Sequence[str]
) -> None:
    assert section_names(mtr_config) == expected_result


@pytest.mark.parametrize(
    "mtr_config",
    [
        pytest.param(
            [
                {"hostname": "foo.example.com", "enforce_what": "ipv6"},
                {"hostname": "foo.example.com", "enforce_what": "ipv6"},
            ],
            id="identical entries",
        ),
        pytest.param(
            [
                {"hostname": "foo.example.com", "count": 10},
                {"hostname": "foo.example.com", "count": 20},
            ],
            id="differing only in how often the trace runs",
        ),
    ],
)
def test_indistinguishable_entries_collide(mtr_config: Sequence[Mapping[str, Any]]) -> None:
    """The rulespec turns a collision into a validation error - see _validate_unique_sections."""
    names = section_names(mtr_config)
    assert len(set(names)) < len(names)
