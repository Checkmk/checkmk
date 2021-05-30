#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pytest

from testlib import SpecialAgent

pytestmark = pytest.mark.checks


@pytest.mark.parametrize('params,expected_args', [
    (
        {
            'user': "admin",
            'password': "pass",
            'url': "http://fuse.com/api/v1/alerts",
        },
        [
            "admin",
            "pass",
            "http://fuse.com/api/v1/alerts",
            "host",
        ],
    )
])
def test_parse_arguments(params, expected_args):
    agent = SpecialAgent('agent_fuse')
    arguments = agent.argument_func(params, "host", "127.0.0.1")
    assert arguments == expected_args
