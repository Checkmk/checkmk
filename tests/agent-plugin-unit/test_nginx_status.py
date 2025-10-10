#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"

import sys

if sys.version_info[0] == 2:
    import agents.plugins.nginx_status_2 as nginx_status
else:
    from agents.plugins import nginx_status


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
