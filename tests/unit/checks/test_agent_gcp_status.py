#!/usr/bin/env python3
# Copyright (C) 2023 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import freezegun

from tests.testlib import SpecialAgent


@freezegun.freeze_time("2022-01-14 03:21:34")
def test_gcp_status_argument_parsing() -> None:
    # Assemble
    agent = SpecialAgent("agent_gcp_status")
    # Act
    arguments = agent.argument_func({}, "host", "ipaddress")
    # Assert
    assert arguments == ["--date", "2022-01-14"]
