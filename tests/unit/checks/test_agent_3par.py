#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest  # type: ignore[import]
from testlib import SpecialAgent  # type: ignore[import]


@pytest.mark.parametrize("params,result", [
    ({
        "user": "user",
        "password": "d1ng",
        "port": 8080,
        "verify_cert": False,
        "values": ["x", "y"],
    }, [
        '--user', 'user', '--password', 'd1ng', '--port', 8080, '--no-cert-check', '--values',
        'x,y', "address"
    ]),
    ({
        "user": "user",
        "password": "d1ng",
        "port": 1234,
        "values": ["x", "y"],
    }, [
        '--user', 'user', '--password', 'd1ng', '--port', 1234, '--no-cert-check', '--values',
        'x,y', "address"
    ]),
    ({
        "user": "user",
        "password": "d1ng",
        "port": 8090,
        "verify_cert": True,
        "values": ["x", "y"],
    }, ['--user', 'user', '--password', 'd1ng', '--port', 8090, '--values', 'x,y', "address"]),
    ({
        "user": "user",
        "password": "d1ng",
        "port": 500,
        "verify_cert": True,
    }, ['--user', 'user', '--password', 'd1ng', '--port', 500, "address"]),
    ({
        "user": "user",
        "password": ("store", "pw-id"),
        "port": 8079,
        "verify_cert": True,
    }, ['--user', 'user', '--password', ('store', 'pw-id', '%s'), '--port', 8079, "address"]),
])
@pytest.mark.usefixtures("config_load_all_checks")
def test_3par(params, result):
    agent = SpecialAgent("agent_3par")
    arguments = agent.argument_func(params, "host", "address")
    assert arguments == result
