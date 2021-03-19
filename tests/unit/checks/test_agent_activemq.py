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
        "use_piggyback": False,
        'servername': 'testserver',
        'port': 8161,
        'protocol': 'http'
    }, ["--servername", "testserver", "--port", "8161", '--protocol', 'http']),
    ({
        'use_piggyback': True,
        'servername': 'testserver',
        'port': 8161,
        'protocol': 'https'
    }, ["--servername", "testserver", "--port", "8161", '--protocol', 'https', "--piggyback"]),
])
def test_activemq_argument_parsing(params, expected_args):
    """Tests if all required arguments are present."""
    agent = SpecialAgent('agent_activemq')
    arguments = agent.argument_func(params, "host", "address")
    assert arguments == expected_args
