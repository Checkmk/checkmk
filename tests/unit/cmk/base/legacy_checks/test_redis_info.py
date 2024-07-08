#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import datetime
from zoneinfo import ZoneInfo

import pytest
import time_machine

from cmk.base.legacy_checks.redis_info import (
    check_redis_info,
    check_redis_info_clients,
    check_redis_info_persistence,
    discover_redis_info,
    discover_redis_info_clients,
    discover_redis_info_persistence,
)


@pytest.mark.parametrize(
    "section, expected",
    [
        pytest.param(
            {},
            [],
            id="empty",
        ),
        pytest.param(
            {"127.0.0.1:6379": {"host": "127.0.0.1", "port": "6379"}},
            [("127.0.0.1:6379", {})],
            id="info_found",
        ),
    ],
)
def test_discover_redis_info(section, expected):
    assert list(discover_redis_info(section)) == expected


@pytest.mark.parametrize(
    "item, params, section, expected",
    [
        pytest.param(
            "127.0.0.1:6379",
            {},
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
                }
            },
            [
                (0, "Mode: Standalone"),
                (
                    0,
                    "Up since Fri Dec  6 08:44:54 2019, uptime: 2:51:06",
                    [("uptime", 10266, None, None)],
                ),
                (0, "Version: 6.0.16"),
                (0, "GCC compiler version: 7.4.0"),
                (0, "PID: 1064"),
                (0, "IP: 127.0.0.1"),
                (0, "Port: 6379"),
            ],
            id="host_port",
        ),
        pytest.param(
            "/path/mysocket:unix-socket",
            {},
            {
                "/path/mysocket:unix-socket": {
                    "host": "/path/mysocket",
                    "port": "unix-socket",
                    "Server": {"redis_version": "6.0.16"},
                }
            },
            [(0, "Version: 6.0.16"), (0, "Socket: /path/mysocket")],
            id="socket",
        ),
    ],
)
def test_check_redis_info(item, params, section, expected):
    with time_machine.travel(
        datetime.datetime.fromisoformat("2019-12-06T11:36:00Z").replace(tzinfo=ZoneInfo("UTC")),
        tick=False,
    ):

        assert list(check_redis_info(item, params, section)) == expected


@pytest.mark.parametrize(
    "section, expected",
    [
        pytest.param(
            {"127.0.0.1:6379": {"host": "127.0.0.1", "port": "6379"}},
            [],
            id="empty",
        ),
        pytest.param(
            {
                "127.0.0.1:6379": {
                    "Persistence": {"rdb_last_bgsave_status": "ok"},
                    "host": "127.0.0.1",
                    "port": "6379",
                }
            },
            [("127.0.0.1:6379", {})],
            id="persistence_found",
        ),
    ],
)
def test_discover_redis_info_persistence(section, expected):
    assert list(discover_redis_info_persistence(section)) == expected


@pytest.mark.parametrize(
    "item, params, section, expected",
    [
        pytest.param(
            "127.0.0.1:6379",
            {},
            {},
            [],
            id="empty",
        ),
        pytest.param(
            "127.0.0.1:6379",
            {"rdb_last_bgsave_state": 1, "aof_last_rewrite_state": 1},
            {
                "127.0.0.1:6379": {
                    "Persistence": {
                        "rdb_last_bgsave_status": "ok",
                        "aof_last_bgrewrite_status": "ok",
                        "rdb_last_save_time": "1575618357",
                        "rdb_changes_since_last_save": "0",
                    },
                    "host": "127.0.0.1",
                    "port": "6379",
                }
            },
            [
                (0, "Last RDB save operation: successful"),
                (0, "Last AOF rewrite operation: successful"),
                (0, "Last successful RDB save: 2019-12-06 07:45:57"),
                (0, "Number of changes since last dump: 0", [("changes_sld", "0", None, None)]),
            ],
            id="full_persistence",
        ),
    ],
)
def test_check_redis_info_persistence(item, params, section, expected):
    with time_machine.travel(
        datetime.datetime.fromisoformat("2019-12-06T11:36:00Z").replace(tzinfo=ZoneInfo("UTC")),
        tick=False,
    ):
        assert list(check_redis_info_persistence(item, params, section)) == expected


@pytest.mark.parametrize(
    "section, expected",
    [
        pytest.param(
            {"127.0.0.1:6379": {"host": "127.0.0.1", "port": "6379"}},
            [],
            id="empty",
        ),
        pytest.param(
            {
                "127.0.0.1:6379": {
                    "Clients": {"connected_clients": 1},
                    "host": "127.0.0.1",
                    "port": "6379",
                }
            },
            [("127.0.0.1:6379", {})],
            id="clients_found",
        ),
    ],
)
def test_discover_redis_info_clients(section, expected):
    assert list(discover_redis_info_clients(section)) == expected


@pytest.mark.parametrize(
    "section, params, expected",
    [
        pytest.param({"127.0.0.1:6379": {"host": "127.0.0.1", "port": "6379"}}, {}, [], id="empty"),
        pytest.param(
            {
                "127.0.0.1:6379": {
                    "Clients": {
                        "connected_clients": 1,
                        "blocked_clients": 0,
                        "client_longest_output_list": 0,
                        "client_biggest_input_buf": 0,
                    },
                    "host": "127.0.0.1",
                    "port": "6379",
                }
            },
            {},
            [
                (0, "Number of client connections: 1", [("clients_connected", 1, None, None)]),
                (0, "Longest output list: 0", [("clients_output", 0, None, None)]),
                (0, "Biggest input buffer: 0", [("clients_input", 0, None, None)]),
                (
                    0,
                    "Number of clients pending on a blocking call: 0",
                    [("clients_blocked", 0, None, None)],
                ),
            ],
            id="full_clients",
        ),
    ],
)
def test_check_redis_info_clients(section, params, expected):
    assert list(check_redis_info_clients("127.0.0.1:6379", params, section)) == expected
