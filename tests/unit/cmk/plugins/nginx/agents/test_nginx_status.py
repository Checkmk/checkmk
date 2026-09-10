#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# ruff: noqa: UP006  # PEP 585 (Type Hinting Generics In Standard Collections) is a Python 3.9 feature
# ruff: noqa: UP035  # PEP 585 (Type Hinting Generics In Standard Collections) is a Python 3.9 feature
# ruff: noqa: UP045  # PEP 604 (Allow writing union types as X | Y) is a Python 3.10 feature

from typing import List, Optional, Tuple

import pytest

from cmk.plugins.nginx.agents import nginx_status


class TestExtractStatsFromNetstat:
    """Check that network stats are correctly extracted from netstat output."""

    def test_with_empty_lines(self) -> None:
        assert not nginx_status.extract_stats_from_netstat([], [443])

    def test_nginx_process_not_found(self) -> None:
        lines = [
            "Active Internet connections (only servers)\n",
            "Proto Recv-Q Send-Q Local Address  Foreign Address  State   PID/Program name \n",
            "tcp        0      0 0.0.0.0:80     0.0.0.0:*        LISTEN  1/foo: master pro \n",
        ]
        assert not nginx_status.extract_stats_from_netstat(lines, [443])

    def test_with_http_port(self) -> None:
        lines = [
            "Active Internet connections (only servers)\n",
            "Proto Recv-Q Send-Q Local Address  Foreign Address  State   PID/Program name \n",
            "tcp        0      0 0.0.0.0:80     0.0.0.0:*        LISTEN  1/nginx: master pro \n",
            "tcp6       0      0 :::80          :::*             LISTEN  1/nginx: master pro \n",
        ]
        assert nginx_status.extract_stats_from_netstat(lines, [443]) == [
            ("http", "127.0.0.1", 80),
        ]

    def test_with_https_port(self) -> None:
        lines = [
            "Active Internet connections (only servers)\n",
            "Proto Recv-Q Send-Q Local Address  Foreign Address  State   PID/Program name \n",
            "tcp        0      0 0.0.0.0:443    0.0.0.0:*        LISTEN  1/nginx: master pro \n",
            "tcp6       0      0 :::443         :::*             LISTEN  1/nginx: master pro \n",
        ]
        assert nginx_status.extract_stats_from_netstat(lines, [443]) == [
            ("https", "127.0.0.1", 443),
        ]


class TestExtractStatsFromIproute2:
    """Check that network stats are correctly extracted from iproute2 (ss) output."""

    def test_with_empty_lines(self) -> None:
        assert nginx_status.extract_stats_from_iproute2([], [443]) == []

    def test_nginx_process_not_found(self) -> None:
        lines = [
            "State  Recv-Q  Send-Q  Local Address:Port  Peer Address:Port  Process \n",
            'LISTEN  0  511  0.0.0.0:80  0.0.0.0:*  users:(("foo",pid=1,fd=6))\n',
        ]
        assert not nginx_status.extract_stats_from_iproute2(lines, [443])

    def test_with_http_port(self) -> None:
        lines = [
            "State  Recv-Q  Send-Q  Local Address:Port  Peer Address:Port  Process \n",
            'LISTEN  0  511  0.0.0.0:80  0.0.0.0:*  users:(("nginx",pid=1,fd=6))\n',
            'LISTEN  0  511     [::]:80     [::]:*  users:(("nginx",pid=1,fd=7))\n',
        ]
        assert nginx_status.extract_stats_from_iproute2(lines, [443]) == [
            ("http", "127.0.0.1", 80),
        ]

    def test_with_https_port(self) -> None:
        lines = [
            "State   Recv-Q  Send-Q  Local Address:Port  Peer Address:Port  Process \n",
            'LISTEN  0  511  0.0.0.0:443  0.0.0.0:*  users:(("nginx",pid=1,fd=6))\n',
            'LISTEN  0  511     [::]:443     [::]:*  users:(("nginx",pid=1,fd=7))\n',
        ]
        assert nginx_status.extract_stats_from_iproute2(lines, [443]) == [
            ("https", "127.0.0.1", 443),
        ]

    def test_with_child_processes(self) -> None:
        lines = [
            "State  Recv-Q  Send-Q  Local Address:Port  Peer Address:Port  Process \n",
            'LISTEN  0  511  0.0.0.0:80  0.0.0.0:*  users:(("nginx",pid=1,fd=6),("nginx",pid=2,fd=6))\n',
        ]
        assert nginx_status.extract_stats_from_iproute2(lines, [443]) == [
            ("http", "127.0.0.1", 80),
        ]

    def test_with_socket_without_process(self) -> None:
        # Kernel-owned sockets (e.g. nfsd) have no process column in `ss -tlnp`.
        lines = [
            "State  Recv-Q  Send-Q  Local Address:Port  Peer Address:Port  Process \n",
            "LISTEN  0  64  0.0.0.0:2049  0.0.0.0:*\n",
            'LISTEN  0  511  0.0.0.0:443  0.0.0.0:*  users:(("nginx",pid=1,fd=6))\n',
        ]
        assert nginx_status.extract_stats_from_iproute2(lines, [443]) == [
            ("https", "127.0.0.1", 443),
        ]


def test_netstat_and_iproute2_return_same_stats() -> None:
    """Sanity check to see if there is drift between the two strategies."""
    netstat_lines = [
        "Active Internet connections (only servers)\n",
        "Proto Recv-Q Send-Q Local Address  Foreign Address  State   PID/Program name \n",
        "tcp        0      0 0.0.0.0:80     0.0.0.0:*        LISTEN  1/nginx: master pro \n",
        "tcp6       0      0 :::80          :::*             LISTEN  1/nginx: master pro \n",
    ]
    iproute2_lines = [
        "State   Recv-Q  Send-Q  Local Address:Port  Peer Address:Port  Process \n",
        'LISTEN  0  511  0.0.0.0:80  0.0.0.0:*  users:(("nginx",pid=1,fd=6))\n',
        'LISTEN  0  511     [::]:80     [::]:*  users:(("nginx",pid=1,fd=7))\n',
    ]

    netstat_stats = nginx_status.extract_stats_from_netstat(netstat_lines, [443])
    iproute2_stats = nginx_status.extract_stats_from_iproute2(iproute2_lines, [443])

    assert netstat_stats == iproute2_stats


@pytest.mark.parametrize(
    "raw, expected",
    [
        pytest.param(None, None, id="unset means autodetect"),
        pytest.param([], [], id="empty list"),
        pytest.param(
            [("http", "10.0.0.1", 8080)],
            [("http", "10.0.0.1", 8080, "nginx_status")],
            id="tuple gets default page",
        ),
        pytest.param(
            [{"protocol": "http", "address": "127.0.0.1", "port": 80}],
            [("http", "127.0.0.1", 80, "nginx_status")],
            id="dict without page",
        ),
        pytest.param(
            [{"protocol": "https", "address": "::1", "port": 443, "page": "status"}],
            [("https", "::1", 443, "status")],
            id="dict with page",
        ),
    ],
)
def test_parse_servers(raw: object, expected: Optional[List[Tuple[str, str, int, str]]]) -> None:
    assert nginx_status.parse_servers(raw) == expected


@pytest.mark.parametrize(
    "raw, expected",
    [
        pytest.param([443], [443], id="default"),
        pytest.param([443, 8443], [443, 8443], id="two ports"),
        pytest.param([], [], id="empty list"),
    ],
)
def test_parse_ssl_ports(raw: object, expected: List[int]) -> None:
    assert nginx_status.parse_ssl_ports(raw) == expected
