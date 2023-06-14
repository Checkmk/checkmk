#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from tests.testlib import SpecialAgent


def test_gcp_status_argument_parsing() -> None:
    # Assemble
    agent = SpecialAgent("agent_gcp_status")
    # Act
    arguments = agent.argument_func({"regions": ["asia-east1"]}, "host", "ipaddress")
    # Assert
    assert arguments == ["asia-east1"]
