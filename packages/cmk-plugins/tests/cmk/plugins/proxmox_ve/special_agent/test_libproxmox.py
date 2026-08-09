#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.plugins.proxmox_ve.special_agent.libproxmox import _host_port_for_url


@pytest.mark.parametrize(
    "host, port, expected",
    [
        pytest.param("2a01:4f9:2b:1c86::2", 8006, "[2a01:4f9:2b:1c86::2]:8006", id="ipv6"),
        pytest.param("::1", 8006, "[::1]:8006", id="ipv6_loopback"),
        pytest.param("192.168.1.10", 8006, "192.168.1.10:8006", id="ipv4"),
        pytest.param("pve1.example.com", 8006, "pve1.example.com:8006", id="hostname"),
    ],
)
def test_host_port_for_url(host: str, port: int, expected: str) -> None:
    assert _host_port_for_url(host, port) == expected
