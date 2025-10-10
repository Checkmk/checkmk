#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"

import datetime as dt
from zoneinfo import ZoneInfo

import pytest

from cmk.ccc.hostaddress import HostName
from cmk.gui import sites
from cmk.gui.config import load_config
from cmk.gui.livestatus_utils.commands import force_schedule
from cmk.gui.session import SuperUserContext
from cmk.gui.utils.script_helpers import application_and_request_context
from cmk.utils.livestatus_helpers.testing import MockLiveStatusConnection


@pytest.fixture(name="check_time")
def _check_time():
    return dt.datetime(1970, 1, 1, tzinfo=ZoneInfo("UTC"))


@pytest.mark.usefixtures("request_context")
def test_force_schedule_host_check(
    mock_livestatus: MockLiveStatusConnection, check_time: dt.datetime
) -> None:
    with (
        mock_livestatus(expect_status_query=True) as live,
        application_and_request_context(),
        SuperUserContext(),
    ):
        load_config()
        live.expect_query(
            "COMMAND [...] SCHEDULE_FORCED_HOST_CHECK;example.com;0", match_type="ellipsis"
        )
        force_schedule.force_schedule_host_check(sites.live(), HostName("example.com"), check_time)


@pytest.mark.usefixtures("request_context")
def test_force_schedule_service_check(
    mock_livestatus: MockLiveStatusConnection, check_time: dt.datetime
) -> None:
    with mock_livestatus(expect_status_query=True) as live, SuperUserContext():
        load_config()
        live.expect_query(
            "COMMAND [...] SCHEDULE_FORCED_SVC_CHECK;example.com;CPU Load;0", match_type="ellipsis"
        )
        force_schedule.force_schedule_service_check(
            sites.live(), HostName("example.com"), "CPU Load", check_time
        )
