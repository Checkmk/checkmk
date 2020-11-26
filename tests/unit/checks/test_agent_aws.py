#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest  # type: ignore[import]

pytestmark = pytest.mark.checks


@pytest.mark.parametrize(
    'params, expected_args',
    [
        (
            {
                'access_key_id': 'strawberry',
                'secret_access_key': ('password', 'strawberry098'),
                'assume_role': {},
                'global_services': {
                    'ce': None,
                },
                'regions': [],
                'services': {
                    'ec2': {
                        'selection': 'all',
                        'limits': True,
                    },
                    'ebs': {
                        'selection': 'all',
                        'limits': True,
                    },
                    'cloudfront': None,
                },
            },
            [
                "--access-key-id",
                "strawberry",
                "--secret-access-key",
                "strawberry098",
                "--global-services",
                "ce",
                "--services",
                "cloudfront",
                "ebs",
                "ec2",
                "--ec2-limits",
                "--ebs-limits",
                "--hostname",
                "testhost",
            ],
        ),
    ],
)
def test_aws_argument_parsing(check_manager, params, expected_args):
    """Tests if all required arguments are present."""
    agent = check_manager.get_special_agent("agent_aws")
    arguments = agent.argument_func(params, "testhost", "address")
    assert arguments == expected_args
