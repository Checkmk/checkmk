#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest  # type: ignore[import]
from testlib import SpecialAgent  # type: ignore[import]

pytestmark = pytest.mark.checks


@pytest.mark.parametrize('params,expected_args', [
    ({
        'username': 'user',
        'password': 'password',
        'skip_elements': []
    }, ["-u", "user", "-s", "password", "address"]),
    ({
        'username': 'user',
        'password': 'password',
        'skip_elements': ['ctr_volumes']
    }, ['-u', 'user', '-s', 'password', '--nocounters volumes', 'address']),
])
def test_netapp_argument_parsing(params, expected_args):
    """Tests if all required arguments are present."""
    agent = SpecialAgent('agent_netapp')
    arguments = agent.argument_func(params, "host", "address")
    assert arguments == expected_args
