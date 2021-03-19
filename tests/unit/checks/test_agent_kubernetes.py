#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest  # type: ignore[import]
from testlib import SpecialAgent  # type: ignore[import]

pytestmark = pytest.mark.checks


@pytest.mark.parametrize('params,expected_args', [
    (
        {
            'api-server-endpoint': ('url_custom', 'https://amazon.region1.com'),
            'token': ('password', 'XYZ'),
            'no-cert-check': False,
            'namespaces': False,
            'infos': ['nodes', 'services', 'pods'],
        },
        [
            "--token",
            "XYZ",
            "--infos",
            "nodes,services,pods",
            "--api-server-endpoint",
            "https://amazon.region1.com",
        ],
    ),
    (
        {
            'api-server-endpoint': ('hostname', {}),
            'token': ('password', 'XYZ'),
        },
        [
            "--token",
            "XYZ",
            "--infos",
            "nodes",
            "--api-server-endpoint",
            "https://host",
        ],
    ),
    (
        {
            'api-server-endpoint': (
                'ipaddress',
                {
                    'port': 522,
                    'path-prefix': '/some/prefix',
                },
            ),
            'token': ('password', 'XYZ'),
        },
        [
            "--token",
            "XYZ",
            "--infos",
            "nodes",
            "--api-server-endpoint",
            "https://127.0.0.1",
            "--port",
            "522",
            "--path-prefix",
            "/some/prefix",
        ],
    ),
])
def test_parse_arguments(params, expected_args):
    """Tests if all required arguments are present."""
    agent = SpecialAgent('agent_kubernetes')
    arguments = agent.argument_func(params, "host", "127.0.0.1")
    assert arguments == expected_args
