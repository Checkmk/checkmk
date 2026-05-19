#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.ccc.hostaddress import HostAddress
from cmk.gui import sites
from cmk.gui.livestatus_utils.commands.acknowledgments import (
    acknowledge_host_problem,
    acknowledge_service_problem,
)
from cmk.gui.session_context import SuperUserContext
from cmk.livestatus_client.testing import MockLiveStatusConnection


@pytest.mark.usefixtures("request_context")
def test_acknowledge_service_problem(mock_livestatus: MockLiveStatusConnection) -> None:
    with mock_livestatus(expect_status_query=True) as live, SuperUserContext():
        live.expect_query("GET hosts\nColumns: name\nFilter: name = example.com")
        live.expect_query(
            "COMMAND [...] ACKNOWLEDGE_SVC_PROBLEM;example.com;drain;1;0;0;;;",
            match_type="ellipsis",
        )
        acknowledge_service_problem(sites.live(), HostAddress("example.com"), "drain")


@pytest.mark.usefixtures("request_context")
def test_acknowledge_host_problem(mock_livestatus: MockLiveStatusConnection) -> None:
    with mock_livestatus(expect_status_query=True) as live, SuperUserContext():
        live.expect_query("GET hosts\nColumns: name\nFilter: name = example.com")
        live.expect_query(
            "COMMAND [...] ACKNOWLEDGE_HOST_PROBLEM;example.com;1;0;0;;;",
            match_type="ellipsis",
        )
        acknowledge_host_problem(sites.live(), HostAddress("example.com"))
