#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.plugins.tcp.server_side_calls.check_tcp import active_check_tcp
from cmk.server_side_calls.v1 import ActiveCheckCommand, HostConfig, IPv4Config

TEST_CONFIG = HostConfig(name="testhost", ipv4_config=IPv4Config(address="1.2.3.4"))


DAY = 86400


def test_check_tcp_arguments_minimal() -> None:
    assert list(active_check_tcp({"port": 1}, TEST_CONFIG)) == [
        ActiveCheckCommand(
            service_description="TCP Port 1",
            command_arguments=["-p", "1", "-H", "1.2.3.4"],
        ),
    ]


def test_check_tcp_arguments_full() -> None:
    assert list(
        active_check_tcp(
            {
                "port": 1,
                "svc_description": "foo",
                "hostname": "bar",
                "response_time": ("fixed", (0.001, 0.002)),
                "timeout": 3,
                "refuse_state": "ok",
                "send_string": "baz",
                "escape_send_string": True,
                "expect": ["qux", "mux"],
                "expect_all": True,
                "jail": True,
                "mismatch_state": "warn",
                "delay": 4,
                "maxbytes": 5,
                "ssl": True,
                "cert_days": ("fixed", (6.0 * DAY, 7.0 * DAY)),
                "quit_string": "quux",
            },
            TEST_CONFIG,
        )
    ) == [
        ActiveCheckCommand(
            service_description="foo",
            command_arguments=[
                "-p",
                "1",
                "-w",
                "0.001000",
                "-c",
                "0.002000",
                "-t",
                "3",
                "-r",
                "ok",
                "--escape",
                "-s",
                "baz",
                "-e",
                "qux",
                "-e",
                "mux",
                "-A",
                "--jail",
                "-M",
                "warn",
                "-d",
                "4",
                "-m",
                "5",
                "--ssl",
                "-D",
                "6,7",
                "-q",
                "quux",
                "-H",
                "bar",
            ],
        )
    ]
