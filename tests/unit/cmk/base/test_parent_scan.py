#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable, Sequence
from subprocess import CompletedProcess

from cmk.base.parent_scan import gateway_reachable_via_ping
from cmk.ccc.hostaddress import HostAddress

_FOREIGN_REPLIES_ONLY = """\
PING 10.255.255.1 (10.255.255.1) 56(84) bytes of data.
64 bytes from 127.0.0.1: icmp_seq=1 ttl=64 time=0.032 ms (DIFFERENT ADDRESS!)
64 bytes from 127.0.0.1: icmp_seq=2 ttl=64 time=0.033 ms (DIFFERENT ADDRESS!)

--- 10.255.255.1 ping statistics ---
1 packets transmitted, 2 received, -100% packet loss, time 0ms
rtt min/avg/max/mdev = 0.032/0.032/0.033/0.000 ms
"""


def _ping_printing(*outputs: str) -> Callable[[Sequence[str]], CompletedProcess[str]]:
    remaining = iter(outputs)

    def run_ping(command: Sequence[str]) -> CompletedProcess[str]:
        return CompletedProcess(command, 0, stdout=next(remaining))

    return run_ping


def test_gateway_answered_only_by_another_host_is_unreachable() -> None:
    reachable = gateway_reachable_via_ping(
        HostAddress("10.255.255.1"),
        2,
        run_ping=_ping_printing(_FOREIGN_REPLIES_ONLY, _FOREIGN_REPLIES_ONLY),
    )

    assert not reachable


def test_gateway_answering_among_foreign_replies_is_reachable() -> None:
    output = """\
PING 127.0.0.2 (127.0.0.2) 56(84) bytes of data.
64 bytes from 127.0.0.1: icmp_seq=1 ttl=64 time=0.029 ms (DIFFERENT ADDRESS!)
64 bytes from 127.0.0.2: icmp_seq=1 ttl=64 time=0.031 ms (DUP!)
64 bytes from 127.0.0.1: icmp_seq=2 ttl=64 time=0.031 ms (DIFFERENT ADDRESS!)

--- 127.0.0.2 ping statistics ---
1 packets transmitted, 2 received, +1 duplicates, -100% packet loss, time 0ms
rtt min/avg/max/mdev = 0.029/0.030/0.031/0.000 ms
"""

    reachable = gateway_reachable_via_ping(
        HostAddress("127.0.0.2"), 2, run_ping=_ping_printing(output)
    )

    assert reachable


def test_gateway_answering_after_a_run_with_only_foreign_replies_is_reachable() -> None:
    gateway_answers = """\
PING 10.255.255.1 (10.255.255.1) 56(84) bytes of data.
64 bytes from 10.255.255.1: icmp_seq=1 ttl=64 time=0.031 ms
64 bytes from 10.255.255.1: icmp_seq=2 ttl=64 time=0.029 ms

--- 10.255.255.1 ping statistics ---
2 packets transmitted, 2 received, 0% packet loss, time 201ms
rtt min/avg/max/mdev = 0.029/0.030/0.031/0.001 ms
"""

    reachable = gateway_reachable_via_ping(
        HostAddress("10.255.255.1"),
        2,
        run_ping=_ping_printing(_FOREIGN_REPLIES_ONLY, gateway_answers),
    )

    assert reachable


def test_gateway_without_any_reply_is_pinged_only_once() -> None:
    commands: list[Sequence[str]] = []

    def run_ping(command: Sequence[str]) -> CompletedProcess[str]:
        commands.append(command)
        return CompletedProcess(
            command,
            1,
            stdout="""\
PING 10.255.255.1 (10.255.255.1) 56(84) bytes of data.

--- 10.255.255.1 ping statistics ---
2 packets transmitted, 0 received, 100% packet loss, time 0ms

""",
        )

    gateway_reachable_via_ping(HostAddress("10.255.255.1"), 2, run_ping=run_ping)

    assert len(commands) == 1
