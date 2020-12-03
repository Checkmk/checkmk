#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import json

from cmk.gui.plugins.openapi.livestatus_helpers.testing import MockLiveStatusConnection


def test_openapi_list_all_downtimes(
    wsgi_app,
    with_automation_user,
    suppress_automation_calls,
    mock_livestatus,
):
    live: MockLiveStatusConnection = mock_livestatus
    username, secret = with_automation_user
    wsgi_app.set_authorization(('Bearer', username + " " + secret))
    base = '/NO_SITE/check_mk/api/v0'

    live.expect_query([
        'GET downtimes',
        'Columns: id host_name service_description is_service author start_time end_time recurring comment'
    ])
    with live:
        resp = wsgi_app.call_method('get',
                                    base + "/domain-types/downtime/collections/all",
                                    status=200)
        assert len(resp.json['value']) == 1


def test_openapi_schedule_hostgroup_downtime(
    wsgi_app,
    with_automation_user,
    mock_livestatus,
):
    live: MockLiveStatusConnection = mock_livestatus
    username, secret = with_automation_user
    wsgi_app.set_authorization(('Bearer', username + " " + secret))
    base = '/NO_SITE/check_mk/api/v0'

    live.expect_query('GET hostgroups\nColumns: members\nFilter: name = example',)
    live.expect_query(
        'COMMAND [...] SCHEDULE_HOST_DOWNTIME;example.com;1577836800;1577923200;0;0;0;test123-...;Downtime for ...',
        match_type='ellipsis',
    )
    live.expect_query(
        'COMMAND [...] SCHEDULE_HOST_DOWNTIME;heute;1577836800;1577923200;0;0;0;test123-...;Downtime for ...',
        match_type='ellipsis',
    )
    with live:
        wsgi_app.post(
            base + '/domain-types/downtime/collections/all',
            content_type='application/json',
            params=json.dumps({
                'downtime_type': 'hostgroup',
                'hostgroup_name': 'example',
                'start_time': '2020-01-01T00:00:00Z',
                'end_time': '2020-01-02T00:00:00Z',
            }),
            status=204,
        )


def test_openapi_schedule_host_downtime(
    wsgi_app,
    with_automation_user,
    mock_livestatus,
):
    live: MockLiveStatusConnection = mock_livestatus
    username, secret = with_automation_user
    wsgi_app.set_authorization(('Bearer', username + " " + secret))
    base = '/NO_SITE/check_mk/api/v0'

    live.expect_query(
        'COMMAND [...] SCHEDULE_HOST_DOWNTIME;example.com;1577836800;1577923200;0;0;0;test123-...;Downtime for ...',
        match_type='ellipsis',
    )
    with live:
        wsgi_app.post(
            base + '/domain-types/downtime/collections/all',
            content_type='application/json',
            params=json.dumps({
                'downtime_type': 'host',
                'host_name': 'example.com',
                'start_time': '2020-01-01T00:00:00Z',
                'end_time': '2020-01-02T00:00:00Z',
            }),
            status=204,
        )


def test_openapi_schedule_servicegroup_downtime(
    wsgi_app,
    with_automation_user,
    mock_livestatus,
):
    live: MockLiveStatusConnection = mock_livestatus
    username, secret = with_automation_user
    wsgi_app.set_authorization(('Bearer', username + " " + secret))
    base = '/NO_SITE/check_mk/api/v0'

    live.expect_query('GET servicegroups\nColumns: members\nFilter: name = example',)
    live.expect_query(
        'COMMAND [...] SCHEDULE_SVC_DOWNTIME;example.com;Memory;1577836800;1577923200;0;0;0;test123-...;Downtime for ...',
        match_type='ellipsis',
    )
    live.expect_query(
        'COMMAND [...] SCHEDULE_SVC_DOWNTIME;example.com;CPU load;1577836800;1577923200;0;0;0;test123-...;Downtime for ...',
        match_type='ellipsis',
    )
    live.expect_query(
        'COMMAND [...] SCHEDULE_SVC_DOWNTIME;heute;CPU load;1577836800;1577923200;0;0;0;test123-...;Downtime for ...',
        match_type='ellipsis',
    )
    with live:
        wsgi_app.post(
            base + '/domain-types/downtime/collections/all',
            content_type='application/json',
            params=json.dumps({
                'downtime_type': 'servicegroup',
                'servicegroup_name': 'example',
                'start_time': '2020-01-01T00:00:00Z',
                'end_time': '2020-01-02T00:00:00Z',
            }),
            status=204,
        )


def test_openapi_schedule_service_downtime(
    wsgi_app,
    with_automation_user,
    mock_livestatus,
):
    live: MockLiveStatusConnection = mock_livestatus
    username, secret = with_automation_user
    wsgi_app.set_authorization(('Bearer', username + " " + secret))
    base = '/NO_SITE/check_mk/api/v0'

    live.expect_query(
        'COMMAND [...] SCHEDULE_SVC_DOWNTIME;example.com;Memory;1577836800;1577923200;0;0;0;test123-...;Downtime for ...',
        match_type='ellipsis',
    )
    live.expect_query(
        'COMMAND [...] SCHEDULE_SVC_DOWNTIME;example.com;CPU load;1577836800;1577923200;0;0;0;test123-...;Downtime for ...',
        match_type='ellipsis',
    )
    with live:
        wsgi_app.post(
            base + '/domain-types/downtime/collections/all',
            content_type='application/json',
            params=json.dumps({
                'downtime_type': 'service',
                'host_name': 'example.com',
                'service_descriptions': ['Memory', 'CPU load'],
                'start_time': '2020-01-01T00:00:00Z',
                'end_time': '2020-01-02T00:00:00Z',
            }),
            status=204,
        )


def test_openapi_show_downtimes(
    wsgi_app,
    with_automation_user,
    suppress_automation_calls,
    mock_livestatus,
):
    live: MockLiveStatusConnection = mock_livestatus
    username, secret = with_automation_user
    wsgi_app.set_authorization(('Bearer', username + " " + secret))
    base = '/NO_SITE/check_mk/api/v0'

    live.add_table('downtimes', [{
        'id': 123,
        'host_name': 'heute',
        'service_description': 'CPU load',
        'is_service': 1,
        'author': 'random',
        'start_time': 1606913913,
        'end_time': 1606913913,
        'recurring': 0,
        'comment': 'literally nothing'
    }, {
        'id': 124,
        'host_name': 'example.com',
        'service_description': 'null',
        'is_service': 0,
        'author': 'random',
        'start_time': 1606913913,
        'end_time': 1606913913,
        'recurring': 0,
        'comment': 'some host downtime'
    }])

    live.expect_query([
        'GET downtimes',
        'Columns: id host_name service_description is_service author start_time end_time recurring comment',
        'Filter: host_name ~ heute'
    ])
    with live:
        resp = wsgi_app.call_method(
            'get',
            base +
            '/domain-types/downtime/collections/all?query={"op": "~", "left": "downtimes.host_name", "right": "heute"}',
            status=200)
        assert len(resp.json['value']) == 1
