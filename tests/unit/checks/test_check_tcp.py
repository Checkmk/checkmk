#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

import pytest

from tests.testlib import ActiveCheck

pytestmark = pytest.mark.checks


def active_check_tcp(params: Mapping[str, object]) -> list[str]:
    return ActiveCheck("check_tcp").run_argument_function(params)


def test_check_tcp_arguments_minimal() -> None:
    assert active_check_tcp({"port": 1}) == ["-p", "1", "-H", "$HOSTADDRESS$"]


def test_check_tcp_arguments_full() -> None:
    assert active_check_tcp(
        {
            "port": 1,
            "svc_description": "foo",
            "hostname": "bar",
            "response_time": (1.0, 2.0),
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
            "cert_days": (6, 7),
            "quit_string": "quux",
        }
    ) == [
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
    ]
