#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

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
