#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json

import pytest

from tests.testlib import SpecialAgent

from cmk.base.sources.programs import SpecialAgentConfiguration

pytestmark = pytest.mark.checks


@pytest.mark.parametrize(
    "params, expected_args",
    [
        (
            {
                "subscription": "banana",
                "tenant": "strawberry",
                "client": "blueberry",
                "secret": "vurystrong",
                "config": {},
            },
            SpecialAgentConfiguration(
                [
                    "--subscription",
                    "banana",
                    "--tenant",
                    "strawberry",
                    "--client",
                    "blueberry",
                    "--monitor-costs",
                ],
                json.dumps(
                    {
                        "secret": "vurystrong",
                    }
                ),
            ),
        ),
    ],
)
def test_azure_argument_parsing(params, expected_args):
    """Tests if all required arguments are present."""
    agent = SpecialAgent("agent_azure")
    arguments = agent.argument_func(params, "testhost", "address")
    assert arguments == expected_args
