#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.agent_based.v2 import StringTable
from cmk.plugins.redis.agent_based.redis_base import parse_redis_info, Section


@pytest.mark.parametrize(
    ["string_table", "expected"],
    [
        pytest.param([], {}, id="empty"),
        pytest.param(
            [
                ["[[[127.0.0.1;6379|127.0.0.1|6379]]]"],
                ["# Server"],
                ["redis_version", "6.0.16"],
                ["redis_mode", "standalone"],
                ["gcc_version", "7.4.0"],
                ["uptime_in_seconds", "10266"],
                ["process_id", "1064"],
                ["# Persistence"],
                ["rdb_last_save_time", "1607213094"],
                ["rdb_last_bgsave_status", "ok"],
                ["aof_last_bgrewrite_status", "ok"],
                ["rdb_changes_since_last_save", "0"],
                ["# Clients"],
                ["connected_clients", "1"],
                ["blocked_clients", "0"],
                ["client_longest_output_list", "0"],
                ["client_biggest_input_buf", "0"],
            ],
            {
                "127.0.0.1:6379": {
                    "host": "127.0.0.1",
                    "port": "6379",
                    "Server": {
                        "redis_version": "6.0.16",
                        "redis_mode": "standalone",
                        "gcc_version": "7.4.0",
                        "uptime_in_seconds": 10266,
                        "process_id": 1064,
                    },
                    "Persistence": {
                        "rdb_last_bgsave_status": "ok",
                        "aof_last_bgrewrite_status": "ok",
                        "rdb_last_save_time": 1607213094,
                        "rdb_changes_since_last_save": 0,
                    },
                    "Clients": {
                        "connected_clients": 1,
                        "blocked_clients": 0,
                        "client_longest_output_list": 0,
                        "client_biggest_input_buf": 0,
                    },
                },
            },
            id="host_port",
        ),
        pytest.param(
            [
                ["[[[/path/mysocket;unix-socket|/path/mysocket|unix-socket]]]"],
            ],
            {
                "/path/mysocket:unix-socket": {
                    "host": "/path/mysocket",
                    "port": "unix-socket",
                }
            },
            id="socket",
        ),
        pytest.param(
            [
                [
                    "[[[/omd/sites/heute/tmp/run/redis;unix-socket|/omd/sites/heute/tmp/run/redis|unix-socket]]]"
                ],
            ],
            {
                "/omd/sites/heute/tmp/run/redis:unix-socket": {
                    "host": "/omd/sites/heute/tmp/run/redis",
                    "port": "unix-socket",
                }
            },
            id="checkmk_instance",
        ),
        pytest.param(
            [
                [
                    "[[[/omd/sites/heute/tmp/run/redis;unix-socket|/omd/sites/heute/tmp/run/redis|unix-socket]]]"
                ],
                [
                    "error",
                    "Could not connect to Redis at /omd/sites/heute/tmp/run/redis",
                    "Permission denied",
                ],
            ],
            {
                "/omd/sites/heute/tmp/run/redis:unix-socket": {
                    "error": "Could not connect to Redis at /omd/sites/heute/tmp/run/redis: Permission denied",
                    "host": "/omd/sites/heute/tmp/run/redis",
                    "port": "unix-socket",
                },
            },
            id="permission_denied",
        ),
    ],
)
def test_parse_redis_info(string_table: StringTable, expected: Section) -> None:
    assert parse_redis_info(string_table) == expected
