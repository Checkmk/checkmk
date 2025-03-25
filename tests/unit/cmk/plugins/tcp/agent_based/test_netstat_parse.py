#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import pytest

from cmk.agent_based.v2 import StringTable
from cmk.plugins.tcp.agent_based.netstat import parse_netstat
from cmk.plugins.tcp.agent_based.win_netstat import parse_win_netstat
from cmk.plugins.tcp.lib.models import Connection, ConnectionState, Section, SplitIP


@pytest.mark.parametrize(
    ["info", "expected_parsed"],
    [
        ([], []),
        (
            [["tcp", "0", "0", "0.0.0.0:6556", "0.0.0.0:*", "LISTENING"]],
            [
                Connection(
                    proto="TCP",
                    local_address=SplitIP("0.0.0.0", "6556"),
                    remote_address=SplitIP("0.0.0.0", "*"),
                    state=ConnectionState.LISTENING,
                )
            ],
        ),
        # Some AIX systems separate the port with a dot (.) instead of a colon (:)
        (
            [["tcp4", "0", "0", "127.0.0.1.1234", "127.0.0.1.5678", "ESTABLISHED"]],
            [
                Connection(
                    proto="TCP",
                    local_address=SplitIP("127.0.0.1", "1234"),
                    remote_address=SplitIP("127.0.0.1", "5678"),
                    state=ConnectionState.ESTABLISHED,
                )
            ],
        ),
        # Solaris systems output a different format for udp (3 elements instead 5)
        (
            [
                ["udp", "-", "-", "*.*", "0.0.0.0:*"],
                ["udp", "*.68", "0.0.0.0:*"],
            ],
            [
                Connection(
                    proto="UDP",
                    local_address=SplitIP("*", "*"),
                    remote_address=SplitIP("0.0.0.0", "*"),
                    state=ConnectionState.LISTENING,
                ),
                Connection(
                    proto="UDP",
                    local_address=SplitIP("*", "68"),
                    remote_address=SplitIP("0.0.0.0", "*"),
                    state=ConnectionState.LISTENING,
                ),
            ],
        ),
        # The ss command has a different order of columns
        (
            [
                ["tcp", "LISTENING", "0", "4096", "127.0.0.1:8888", "0.0.0.0:*"],
                ["tcp", "LISTEN", "0", "4096", "127.0.0.1:8888", "0.0.0.0:*"],
                ["tcp", "TIME-WAIT", "0", "0", "10.230.254.109:8280", "172.17.0.3:39484"],
                ["tcp", "ESTAB", "0", "0", "10.230.254.109:8280", "172.17.0.3:39484"],
                ["tcp", "CLOSED", "0", "0", "10.230.254.109:8280", "172.17.0.3:39484"],
                ["tcp", "CLOSE-WAIT", "0", "0", "10.230.254.109:8280", "172.17.0.3:39484"],
                ["udp", "UNCONN", "0", "0", "127.0.0.1:778", "0.0.0.0:*"],
            ],
            [
                Connection(
                    proto="TCP",
                    local_address=SplitIP("127.0.0.1", "8888"),
                    remote_address=SplitIP("0.0.0.0", "*"),
                    state=ConnectionState.LISTENING,
                ),
                Connection(
                    proto="TCP",
                    local_address=SplitIP("127.0.0.1", "8888"),
                    remote_address=SplitIP("0.0.0.0", "*"),
                    state=ConnectionState.LISTENING,
                ),
                Connection(
                    proto="TCP",
                    local_address=SplitIP("10.230.254.109", "8280"),
                    remote_address=SplitIP("172.17.0.3", "39484"),
                    state=ConnectionState.TIME_WAIT,
                ),
                Connection(
                    proto="TCP",
                    local_address=SplitIP("10.230.254.109", "8280"),
                    remote_address=SplitIP("172.17.0.3", "39484"),
                    state=ConnectionState.ESTABLISHED,
                ),
                Connection(
                    proto="TCP",
                    local_address=SplitIP("10.230.254.109", "8280"),
                    remote_address=SplitIP("172.17.0.3", "39484"),
                    state=ConnectionState.CLOSED,
                ),
                Connection(
                    proto="TCP",
                    local_address=SplitIP("10.230.254.109", "8280"),
                    remote_address=SplitIP("172.17.0.3", "39484"),
                    state=ConnectionState.CLOSE_WAIT,
                ),
                Connection(
                    proto="UDP",
                    local_address=SplitIP("127.0.0.1", "778"),
                    remote_address=SplitIP("0.0.0.0", "*"),
                    state=ConnectionState.LISTENING,
                ),
            ],
        ),
    ],
)
def test_parse_netstat(info: StringTable, expected_parsed: Section) -> None:
    parsed = parse_netstat(info)
    assert parsed == expected_parsed


@pytest.mark.parametrize(
    ["info", "expected_parsed"],
    [
        pytest.param([], []),
        pytest.param(
            [
                ["TCP", "10.1.1.99:445", "10.1.1.123:52820", "HERGESTELLT"],
                ["TCP", "10.1.1.99:6556", "10.1.1.50:43257", "LISTENING"],
                ["UDP", "127.0.0.1:1042", "*:*"],
            ],
            [
                Connection(
                    proto="TCP",
                    local_address=SplitIP("10.1.1.99", "445"),
                    remote_address=SplitIP("10.1.1.123", "52820"),
                    state=ConnectionState.ESTABLISHED,
                ),
                Connection(
                    proto="TCP",
                    local_address=SplitIP("10.1.1.99", "6556"),
                    remote_address=SplitIP("10.1.1.50", "43257"),
                    state=ConnectionState.LISTENING,
                ),
                Connection(
                    proto="UDP",
                    local_address=SplitIP("127.0.0.1", "1042"),
                    remote_address=SplitIP("*", "*"),
                    state=ConnectionState.LISTENING,
                ),
            ],
        ),
    ],
)
def test_parse_win_netstat(info: StringTable, expected_parsed: Section) -> None:
    assert parse_win_netstat(info) == expected_parsed
