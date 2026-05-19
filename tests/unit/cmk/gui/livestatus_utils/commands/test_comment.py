#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.ccc.hostaddress import HostAddress
from cmk.ccc.site import SiteId
from cmk.gui import sites
from cmk.gui.livestatus_utils.commands.comment import (
    add_host_comment,
    add_service_comment,
    delete_host_comment,
    delete_service_comment,
)
from cmk.gui.session_context import SuperUserContext
from cmk.livestatus_client.testing import MockLiveStatusConnection


@pytest.mark.usefixtures("request_context")
def test_add_host_comment(mock_livestatus: MockLiveStatusConnection) -> None:
    with mock_livestatus(expect_status_query=True) as live, SuperUserContext():
        live.expect_query(
            "COMMAND [...] ADD_HOST_COMMENT;example.com;0;;test",
            match_type="ellipsis",
        )
        add_host_comment(sites.live(), HostAddress("example.com"), "test", SiteId("NO_SITE"))


@pytest.mark.usefixtures("request_context")
def test_add_service_comment(mock_livestatus: MockLiveStatusConnection) -> None:
    with mock_livestatus(expect_status_query=True) as live, SuperUserContext():
        live.expect_query(
            "COMMAND [...] ADD_SVC_COMMENT;example.com;CPU Load;0;;test",
            match_type="ellipsis",
        )
        add_service_comment(
            sites.live(), HostAddress("example.com"), "CPU Load", "test", SiteId("NO_SITE")
        )


@pytest.mark.usefixtures("request_context")
def test_delete_host_comment(mock_livestatus: MockLiveStatusConnection) -> None:
    with mock_livestatus(expect_status_query=True) as live, SuperUserContext():
        live.expect_query(
            "COMMAND [...] DEL_HOST_COMMENT;1234",
            match_type="ellipsis",
        )
        delete_host_comment(sites.live(), 1234, SiteId("NO_SITE"))


@pytest.mark.usefixtures("request_context")
def test_delete_service_comment(mock_livestatus: MockLiveStatusConnection) -> None:
    with mock_livestatus(expect_status_query=True) as live, SuperUserContext():
        live.expect_query(
            "COMMAND [...] DEL_SVC_COMMENT;1234",
            match_type="ellipsis",
        )
        delete_service_comment(sites.live(), 1234, SiteId("NO_SITE"))
