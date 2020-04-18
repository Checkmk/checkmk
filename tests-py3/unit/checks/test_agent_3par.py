#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest  # type: ignore[import]


@pytest.mark.parametrize("params,result", [
    ({
        "user": "user",
        "password": "d1ng",
        "verify_cert": False,
        "values": ["x", "y"],
    }, ['-u', 'user', '-pd1ng', '--verify-certs=no', '-v', 'x,y', "address"]),
    ({
        "user": "user",
        "password": "d1ng",
        "values": ["x", "y"],
    }, ['-u', 'user', '-pd1ng', '--verify-certs=no', '-v', 'x,y', "address"]),
    ({
        "user": "user",
        "password": "d1ng",
        "verify_cert": True,
        "values": ["x", "y"],
    }, ['-u', 'user', '-pd1ng', '--verify-certs=yes', '-v', 'x,y', "address"]),
    ({
        "user": "user",
        "password": "d1ng",
        "verify_cert": True,
    }, ['-u', 'user', '-pd1ng', '--verify-certs=yes', "address"]),
    ({
        "user": "user",
        "password": ("store", "pw-id"),
        "verify_cert": True,
    }, ['-u', 'user', ('store', 'pw-id', '-p%s'), '--verify-certs=yes', "address"]),
])
def test_3par(check_manager, params, result):
    agent = check_manager.get_special_agent("agent_3par")
    arguments = agent.argument_func(params, "host", "address")
    assert arguments == result
