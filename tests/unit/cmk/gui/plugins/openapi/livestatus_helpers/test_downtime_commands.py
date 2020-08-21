#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import datetime as dt

import pytest  # type: ignore[import]
import pytz

import cmk.gui.plugins.openapi.livestatus_helpers.commands.downtimes as downtimes


@pytest.fixture(name='dates')
def _dates():
    return (dt.datetime(1970, 1, 1, tzinfo=pytz.timezone("UTC")),
            dt.datetime(1970, 1, 2, tzinfo=pytz.timezone("UTC")))


def test_host_downtime(mock_livestatus, dates):
    start_time, end_time = dates

    with mock_livestatus(expect_status_query=False) as live:
        live.expect_query(
            'COMMAND [...] SCHEDULE_HOST_DOWNTIME;example.com;0;86400;13;0;120;;Going down',
            match_type='ellipsis',
        )
        downtimes.schedule_host_downtime(
            live,
            'example.com',
            start_time,
            end_time,
            recur='weekday_start',
            duration=120,
            comment='Going down',
        )


def test_host_downtime_with_services(mock_livestatus, dates):
    start_time, end_time = dates

    with mock_livestatus(expect_status_query=False) as live:
        live.expect_query(
            'COMMAND [...] SCHEDULE_HOST_DOWNTIME;example.com;0;86400;13;0;120;;Going down',
            match_type='ellipsis',
        )
        live.expect_query(
            'GET services\nColumns: host_name description\nFilter: host_name = example.com',)
        live.expect_query(
            'COMMAND [...] SCHEDULE_SVC_DOWNTIME;example.com;Memory;0;86400;13;0;120;;Going down',
            match_type='ellipsis',
        )
        live.expect_query(
            'COMMAND [...] SCHEDULE_SVC_DOWNTIME;example.com;CPU load;0;86400;13;0;120;;Going down',
            match_type='ellipsis',
        )
        downtimes.schedule_host_downtime(
            live,
            'example.com',
            start_time,
            end_time,
            include_all_services=True,
            recur='weekday_start',
            duration=120,
            comment='Going down',
        )


def test_hostgroup_host_downtime(mock_livestatus, dates):
    start_time, end_time = dates

    with mock_livestatus(expect_status_query=False) as live:
        live.expect_query([
            "GET hostgroups",
            "Columns: members",
            "Filter: name = example",
        ])
        live.expect_query(
            'COMMAND [...] SCHEDULE_HOST_DOWNTIME;example.com;0;86400;17;0;120;;Boom',
            match_type='ellipsis',
        )
        live.expect_query(
            'COMMAND [...] SCHEDULE_HOST_DOWNTIME;heute;0;86400;17;0;120;;Boom',
            match_type='ellipsis',
        )

        downtimes.schedule_hostgroup_host_downtime(
            live,
            'example',
            start_time,
            end_time,
            recur="day_of_month",
            duration=120,
            comment="Boom",
        )


def test_hostgroup_host_downtime_with_services(mock_livestatus, dates):
    start_time, end_time = dates

    with mock_livestatus(expect_status_query=False) as live:
        live.expect_query([
            "GET hostgroups",
            "Columns: members",
            "Filter: name = example",
        ])
        live.expect_query(
            'COMMAND [...] SCHEDULE_HOST_DOWNTIME;example.com;0;86400;17;0;120;;Boom',
            match_type='ellipsis',
        )
        live.expect_query(
            'COMMAND [...] SCHEDULE_HOST_DOWNTIME;heute;0;86400;17;0;120;;Boom',
            match_type='ellipsis',
        )
        live.expect_query([
            'GET services',
            'Columns: host_name description',
            'Filter: host_name = example.com',
            'Filter: host_name = heute',
            'Or: 2',
        ])
        live.expect_query(
            'COMMAND [...] SCHEDULE_SVC_DOWNTIME;example.com;Memory;0;86400;17;0;120;;Boom',
            match_type='ellipsis',
        )
        live.expect_query(
            'COMMAND [...] SCHEDULE_SVC_DOWNTIME;example.com;CPU load;0;86400;17;0;120;;Boom',
            match_type='ellipsis',
        )
        live.expect_query(
            'COMMAND [...] SCHEDULE_SVC_DOWNTIME;heute;CPU load;0;86400;17;0;120;;Boom',
            match_type='ellipsis',
        )
        downtimes.schedule_hostgroup_host_downtime(
            live,
            'example',
            start_time,
            end_time,
            include_all_services=True,
            recur="day_of_month",
            duration=120,
            comment="Boom",
        )


def test_servicegroup_service_downtime(mock_livestatus, dates):
    start_time, end_time = dates

    with mock_livestatus(expect_status_query=False) as live:
        live.expect_query([
            "GET servicegroups",
            "Columns: members",
            "Filter: name = example",
        ])
        live.expect_query(
            'COMMAND [...] SCHEDULE_SVC_DOWNTIME;example.com;Memory;0;86400;17;0;120;;Boom',
            match_type='ellipsis',
        )
        live.expect_query(
            'COMMAND [...] SCHEDULE_SVC_DOWNTIME;example.com;CPU load;0;86400;17;0;120;;Boom',
            match_type='ellipsis',
        )
        live.expect_query(
            'COMMAND [...] SCHEDULE_SVC_DOWNTIME;heute;CPU load;0;86400;17;0;120;;Boom',
            match_type='ellipsis',
        )
        downtimes.schedule_servicegroup_service_downtime(
            live,
            'example',
            start_time,
            end_time,
            recur="day_of_month",
            duration=120,
            comment="Boom",
        )


def test_servicegroup_service_downtime_and_hosts(mock_livestatus, dates):
    start_time, end_time = dates

    with mock_livestatus(expect_status_query=False) as live:
        live.expect_query([
            "GET servicegroups",
            "Columns: members",
            "Filter: name = example",
        ])
        live.expect_query(
            'COMMAND [...] SCHEDULE_SVC_DOWNTIME;example.com;Memory;0;86400;17;0;120;;Boom',
            match_type='ellipsis',
        )
        live.expect_query(
            'COMMAND [...] SCHEDULE_SVC_DOWNTIME;example.com;CPU load;0;86400;17;0;120;;Boom',
            match_type='ellipsis',
        )
        live.expect_query(
            'COMMAND [...] SCHEDULE_SVC_DOWNTIME;heute;CPU load;0;86400;17;0;120;;Boom',
            match_type='ellipsis',
        )
        live.expect_query(
            'COMMAND [...] SCHEDULE_HOST_DOWNTIME;example.com;0;86400;17;0;120;;Boom',
            match_type='ellipsis',
        )
        live.expect_query(
            'COMMAND [...] SCHEDULE_HOST_DOWNTIME;heute;0;86400;17;0;120;;Boom',
            match_type='ellipsis',
        )
        downtimes.schedule_servicegroup_service_downtime(
            live,
            'example',
            start_time,
            end_time,
            include_hosts=True,
            recur="day_of_month",
            duration=120,
            comment="Boom",
        )
