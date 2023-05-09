#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import pytest  # type: ignore[import]
from testlib import SpecialAgent  # type: ignore[import]

from cmk.base.checkers.programs import SpecialAgentConfiguration

pytestmark = pytest.mark.checks


@pytest.mark.parametrize(
    'params, expected_args',
    [
        (
            {
                'subscription': 'banana',
                'tenant': 'strawberry',
                'client': 'blueberry',
                'secret': 'vurystrong',
                'config': {},
            },
            SpecialAgentConfiguration(
                [
                    '--subscription',
                    'banana',
                    '--tenant',
                    'strawberry',
                    '--client',
                    'blueberry',
                ],
                json.dumps({
                    'secret': 'vurystrong',
                }),
            ),
        ),
    ],
)
@pytest.mark.usefixtures("config_load_all_checks")
def test_azure_argument_parsing(params, expected_args):
    """Tests if all required arguments are present."""
    agent = SpecialAgent('agent_azure')
    arguments = agent.argument_func(params, "testhost", "address")
    assert arguments == expected_args
