#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import datetime
from collections.abc import Mapping
from typing import Any
from zoneinfo import ZoneInfo

import pytest
import time_machine

from cmk.agent_based.v2 import CheckResult, DiscoveryResult, Metric, Result, Service, State
from cmk.plugins.redis.agent_based.redis_base import Section
from cmk.plugins.redis.agent_based.redis_info import check_redis_info, discover_redis_info
from cmk.plugins.redis.agent_based.redis_info_clients import (
    check_redis_info_clients,
    discover_redis_info_clients,
)
from cmk.plugins.redis.agent_based.redis_info_persistence import (
    check_redis_info_persistence,
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
            [Service(item="127.0.0.1:6379")],
            id="info_found",
        ),
    ],
)
def test_discover_redis_info(section: Section, expected: DiscoveryResult) -> None:
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
                Result(state=State.OK, summary="Mode: Standalone"),
                Result(state=State.OK, summary="Up since 2019-12-06 08:44:54"),
                Result(state=State.OK, summary="Uptime: 2 hours 51 minutes"),
                Metric(name="uptime", value=10266),
                Result(state=State.OK, summary="Version: 6.0.16"),
                Result(state=State.OK, summary="GCC compiler version: 7.4.0"),
                Result(state=State.OK, summary="PID: 1064"),
                Result(state=State.OK, summary="IP: 127.0.0.1"),
                Result(state=State.OK, summary="Port: 6379"),
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
            [
                Result(state=State.OK, summary="Version: 6.0.16"),
                Result(state=State.OK, summary="Socket: /path/mysocket"),
            ],
            id="socket",
        ),
        pytest.param(
            "/omd/sites/heute/tmp/run/redis:unix-socket",
            {},
            {
                "/omd/sites/heute/tmp/run/redis:unix-socket": {
                    "error": "Could not connect to Redis at /omd/sites/heute/tmp/run/redis: Permission denied",
                    "host": "/omd/sites/heute/tmp/run/redis",
                    "port": "unix-socket",
                },
            },
            [
                Result(
                    state=State.CRIT,
                    summary="Error: Could not connect to Redis at /omd/sites/heute/tmp/run/redis: Permission denied",
                )
            ],
            id="permission_denied",
        ),
    ],
)
def test_check_redis_info(
    item: str, params: Mapping[str, Any], section: Section, expected: CheckResult
) -> None:
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
            [Service(item="127.0.0.1:6379")],
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
                Result(state=State.OK, summary="Last RDB save operation: successful"),
                Result(state=State.OK, summary="Last AOF rewrite operation: successful"),
                Result(state=State.OK, summary="Last successful RDB save: 2019-12-06 07:45:57"),
                Result(state=State.OK, summary="Number of changes since last dump: 0"),
                Metric("changes_sld", 0),
            ],
            id="full_persistence",
        ),
    ],
)
def test_check_redis_info_persistence(
    item: str, params: Mapping[str, Any], section: Section, expected: CheckResult
) -> None:
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
            [Service(item="127.0.0.1:6379")],
            id="clients_found",
        ),
    ],
)
def test_discover_redis_info_clients(section: Section, expected: DiscoveryResult) -> None:
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
                Result(state=State.OK, summary="Number of client connections: 1"),
                Metric("clients_connected", 1),
                Result(state=State.OK, summary="Longest output list: 0"),
                Metric("clients_output", 0),
                Result(state=State.OK, summary="Biggest input buffer: 0"),
                Metric("clients_input", 0),
                Result(state=State.OK, summary="Number of clients pending on a blocking call: 0"),
                Metric("clients_blocked", 0),
            ],
            id="full_clients",
        ),
    ],
)
def test_check_redis_info_clients(
    params: Mapping[str, Any], section: Section, expected: CheckResult
) -> None:
    assert list(check_redis_info_clients("127.0.0.1:6379", params, section)) == expected
