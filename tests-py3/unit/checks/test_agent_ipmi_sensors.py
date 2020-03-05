#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest  # type: ignore[import]

pytestmark = pytest.mark.checks


@pytest.mark.parametrize('params,expected_args', [
    ({
        'username': 'user',
        'password': 'password',
        'privilege_lvl': 'user'
    }, ["-u", "user", "-p", "password", "-l", "user", "--ipmi-command", "freeipmi", "address"]),
    ({
        'username': 'user',
        'ipmi_driver': 'driver',
        'password': 'password',
        'privilege_lvl': 'user'
    }, [
        "-u", "user", "-p", "password", "-l", "user", "--ipmi-command", "freeipmi", "-D", "driver",
        "address"
    ]),
])
def test_ipmi_sensors_argument_parsing(check_manager, params, expected_args):
    """Tests if all required arguments are present."""
    agent = check_manager.get_special_agent('agent_ipmi_sensors')
    arguments = agent.argument_func(params, "host", "address")
    assert arguments == expected_args
