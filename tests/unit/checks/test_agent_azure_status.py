#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from tests.testlib import SpecialAgent


def test_azure_status_argument_parsing() -> None:
    agent = SpecialAgent("agent_azure_status")
    params = {"regions": ["eastus", "centralus", "northcentralus"]}
    arguments = agent.argument_func(params, "testhost", "address")
    assert arguments == ["eastus", "centralus", "northcentralus"]
