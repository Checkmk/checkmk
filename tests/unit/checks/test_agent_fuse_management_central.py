#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pytest

from tests.testlib import SpecialAgent

pytestmark = pytest.mark.checks


@pytest.mark.parametrize('arguments,expected_args', [
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
def test_parse_arguments(arguments, expected_args):
    agent = SpecialAgent('agent_fuse_management_central')
    parsed_arguments = agent.argument_func(arguments, "host", "127.0.0.1")
    assert parsed_arguments == expected_args
