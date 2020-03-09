#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest  # type: ignore[import]


@pytest.mark.parametrize("params,result", [
    ({
        'username': 'user',
        'password': 'test'
    }, ['address', '8008', 'user', 'test']),
    ({
        'username': 'user',
        'password': 'test',
        'port': 8090
    }, ['address', '8090', 'user', 'test']),
])
def test_ddn_s2a(check_manager, params, result):
    agent = check_manager.get_special_agent("agent_ddn_s2a")
    arguments = agent.argument_func(params, "host", "address")
    assert arguments == result
