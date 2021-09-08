#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from tests.testlib import SpecialAgent

pytestmark = pytest.mark.checks


@pytest.mark.parametrize(
    "params,expected_args",
    [
        (
            {"instances": ["5"]},
            [
                "--section_url",
                "salesforce_instances",
                "https://api.status.salesforce.com/v1/instances/5/status",
            ],
        ),
    ],
)
def test_agent_salesforce_argument_parsing(params, expected_args):
    """Tests if all required arguments are present."""
    agent = SpecialAgent("agent_salesforce")
    arguments = agent.argument_func(params, "host", "address")
    assert arguments == expected_args
