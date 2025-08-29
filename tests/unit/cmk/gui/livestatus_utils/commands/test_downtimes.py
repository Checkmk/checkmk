#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import datetime as dt
from zoneinfo import ZoneInfo

import pytest

from cmk.gui import sites
from cmk.gui.livestatus_utils.commands import downtimes
from cmk.gui.session import SuperUserContext
from cmk.utils.livestatus_helpers.testing import MockLiveStatusConnection


@pytest.fixture(name="dates")
def _dates():
    return (
        dt.datetime(1970, 1, 1, tzinfo=ZoneInfo("UTC")),
        dt.datetime(1970, 1, 2, tzinfo=ZoneInfo("UTC")),
    )


@pytest.mark.usefixtures("request_context")
def test_host_downtime(
    mock_livestatus: MockLiveStatusConnection, dates: tuple[dt.datetime, dt.datetime]
) -> None:
    start_time, end_time = dates

    with mock_livestatus(expect_status_query=True) as live, SuperUserContext():
        live.expect_query("GET hosts\nColumns: name\nFilter: name = example.com")
        live.expect_query(
            "COMMAND [...] SCHEDULE_HOST_DOWNTIME;example.com;0;86400;12;0;120;;Going down",
            match_type="ellipsis",
        )
        downtimes.schedule_host_downtime(
            sites.live(),
            "example.com",
            start_time,
            end_time,
            recur="weekday_start",
            duration=2,
            comment="Going down",
        )


@pytest.mark.usefixtures("request_context")
def test_host_downtime_with_services(
    mock_livestatus: MockLiveStatusConnection, dates: tuple[dt.datetime, dt.datetime]
) -> None:
    start_time, end_time = dates

    with mock_livestatus(expect_status_query=True) as live, SuperUserContext():
        live.expect_query("GET hosts\nColumns: name\nFilter: name = example.com")
        live.expect_query(
            "COMMAND [...] SCHEDULE_HOST_DOWNTIME;example.com;0;86400;12;0;120;;Going down",
            match_type="ellipsis",
        )
        live.expect_query(
            "GET services\nColumns: host_name description\nFilter: host_name = example.com",
        )
        live.expect_query(
            "COMMAND [...] SCHEDULE_SVC_DOWNTIME;example.com;Memory;0;86400;12;0;120;;Going down",
            match_type="ellipsis",
        )
        live.expect_query(
            "COMMAND [...] SCHEDULE_SVC_DOWNTIME;example.com;CPU load;0;86400;12;0;120;;Going down",
            match_type="ellipsis",
        )
        downtimes.schedule_host_downtime(
            sites.live(),
            "example.com",
            start_time,
            end_time,
            include_all_services=True,
            recur="weekday_start",
            duration=2,
            comment="Going down",
        )


@pytest.mark.usefixtures("request_context")
def test_hostgroup_host_downtime(
    mock_livestatus: MockLiveStatusConnection, dates: tuple[dt.datetime, dt.datetime]
) -> None:
    start_time, end_time = dates

    with mock_livestatus(expect_status_query=True) as live, SuperUserContext():
        live.expect_query(
            [
                "GET hostgroups",
                "Columns: members",
                "Filter: name = example",
            ]
        )
        live.expect_query(
            "COMMAND [...] SCHEDULE_HOST_DOWNTIME;example.com;0;86400;16;0;120;;Boom",
            match_type="ellipsis",
        )
        live.expect_query(
            "COMMAND [...] SCHEDULE_HOST_DOWNTIME;heute;0;86400;16;0;120;;Boom",
            match_type="ellipsis",
        )

        downtimes.schedule_hostgroup_host_downtime(
            sites.live(),
            "example",
            start_time,
            end_time,
            recur="day_of_month",
            duration=2,
            comment="Boom",
        )


@pytest.mark.usefixtures("request_context")
def test_hostgroup_host_downtime_with_services(
    mock_livestatus: MockLiveStatusConnection, dates: tuple[dt.datetime, dt.datetime]
) -> None:
    start_time, end_time = dates

    with mock_livestatus(expect_status_query=True) as live, SuperUserContext():
        live.expect_query(
            [
                "GET hostgroups",
                "Columns: members",
                "Filter: name = example",
            ]
        )
        live.expect_query(
            "COMMAND [...] SCHEDULE_HOST_DOWNTIME;example.com;0;86400;16;0;120;;Boom",
            match_type="ellipsis",
        )
        live.expect_query(
            "COMMAND [...] SCHEDULE_HOST_DOWNTIME;heute;0;86400;16;0;120;;Boom",
            match_type="ellipsis",
        )
        live.expect_query(
            "GET services\nColumns: host_name description\nFilter: host_name = example.com\nFilter: host_name = heute\nOr: 2"
        )
        live.expect_query(
            "COMMAND [...] SCHEDULE_SVC_DOWNTIME;example.com;Memory;0;86400;16;0;120;;Boom",
            match_type="ellipsis",
        )
        live.expect_query(
            "COMMAND [...] SCHEDULE_SVC_DOWNTIME;example.com;CPU load;0;86400;16;0;120;;Boom",
            match_type="ellipsis",
        )
        live.expect_query(
            "COMMAND [...] SCHEDULE_SVC_DOWNTIME;heute;CPU load;0;86400;16;0;120;;Boom",
            match_type="ellipsis",
        )

        downtimes.schedule_hostgroup_host_downtime(
            sites.live(),
            "example",
            start_time,
            end_time,
            include_all_services=True,
            recur="day_of_month",
            duration=2,
            comment="Boom",
        )


@pytest.mark.usefixtures("request_context")
def test_servicegroup_service_downtime(
    mock_livestatus: MockLiveStatusConnection, dates: tuple[dt.datetime, dt.datetime]
) -> None:
    start_time, end_time = dates

    with mock_livestatus(expect_status_query=True) as live, SuperUserContext():
        live.expect_query(
            [
                "GET servicegroups",
                "Columns: members",
                "Filter: name = example",
            ]
        )
        live.expect_query(
            "COMMAND [...] SCHEDULE_SVC_DOWNTIME;example.com;Memory;0;86400;16;0;120;;Boom",
            match_type="ellipsis",
        )
        live.expect_query(
            "COMMAND [...] SCHEDULE_SVC_DOWNTIME;example.com;CPU load;0;86400;16;0;120;;Boom",
            match_type="ellipsis",
        )
        live.expect_query(
            "COMMAND [...] SCHEDULE_SVC_DOWNTIME;heute;CPU load;0;86400;16;0;120;;Boom",
            match_type="ellipsis",
        )
        downtimes.schedule_servicegroup_service_downtime(
            sites.live(),
            "example",
            start_time,
            end_time,
            recur="day_of_month",
            duration=2,
            comment="Boom",
        )


@pytest.mark.usefixtures("request_context")
def test_servicegroup_service_downtime_and_hosts(
    mock_livestatus: MockLiveStatusConnection, dates: tuple[dt.datetime, dt.datetime]
) -> None:
    start_time, end_time = dates

    with mock_livestatus(expect_status_query=True) as live, SuperUserContext():
        live.expect_query(
            [
                "GET servicegroups",
                "Columns: members",
                "Filter: name = example",
            ]
        )
        live.expect_query(
            "COMMAND [...] SCHEDULE_SVC_DOWNTIME;example.com;Memory;0;86400;16;0;120;;Boom",
            match_type="ellipsis",
        )
        live.expect_query(
            "COMMAND [...] SCHEDULE_SVC_DOWNTIME;example.com;CPU load;0;86400;16;0;120;;Boom",
            match_type="ellipsis",
        )
        live.expect_query(
            "COMMAND [...] SCHEDULE_SVC_DOWNTIME;heute;CPU load;0;86400;16;0;120;;Boom",
            match_type="ellipsis",
        )

        live.expect_query(
            "COMMAND [...] SCHEDULE_HOST_DOWNTIME;...;0;86400;16;0;120;;Boom",
            match_type="ellipsis",
        )
        live.expect_query(
            "COMMAND [...] SCHEDULE_HOST_DOWNTIME;...;0;86400;16;0;120;;Boom",
            match_type="ellipsis",
        )
        downtimes.schedule_servicegroup_service_downtime(
            sites.live(),
            "example",
            start_time,
            end_time,
            include_hosts=True,
            recur="day_of_month",
            duration=2,
            comment="Boom",
        )


@pytest.mark.usefixtures("request_context")
def test_del_host_downtime(mock_livestatus: MockLiveStatusConnection) -> None:
    with mock_livestatus(expect_status_query=True) as live, SuperUserContext():
        live.expect_query("COMMAND [...] DEL_HOST_DOWNTIME;1", match_type="ellipsis")
        downtimes._del_host_downtime(sites.live(), 1, None)


@pytest.mark.usefixtures("request_context")
def test_del_service_downtime(mock_livestatus: MockLiveStatusConnection) -> None:
    with mock_livestatus(expect_status_query=True) as live, SuperUserContext():
        live.expect_query("COMMAND [...] DEL_SVC_DOWNTIME;1", match_type="ellipsis")
        downtimes._del_service_downtime(sites.live(), 1, None)


def test_recur_mode_fixed_no_duration() -> None:
    assert downtimes._recur_mode("fixed", 0) == 1


def test_recur_mode_fixed_with_duration() -> None:
    assert downtimes._recur_mode("fixed", 30) == 0


def test_recur_mode_second_week_no_duration() -> None:
    assert downtimes._recur_mode("second_week", 0) == 9


def test_deduplicate_list() -> None:
    assert downtimes._deduplicate([1, 1, 2, 1, 3, 4, 5, 1, 2, 3, 6, 1]) == [1, 2, 3, 4, 5, 6]


def test_deduplicate_tuple() -> None:
    assert downtimes._deduplicate((1, 1, 2, 1, 3, 4, 5, 1, 2, 3, 6, 1)) == [1, 2, 3, 4, 5, 6]


def test_deduplicate_strings() -> None:
    assert downtimes._deduplicate(["Hello", "Hello", "World", "World", "World", "!", "!", "!"]) == [
        "Hello",
        "World",
        "!",
    ]
