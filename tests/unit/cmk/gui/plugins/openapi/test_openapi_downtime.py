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
            base + '/domain-types/downtime/collections/host',
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
            base + '/domain-types/downtime/collections/host',
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
            base + '/domain-types/downtime/collections/service',
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
            base + '/domain-types/downtime/collections/service',
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


def test_openapi_show_downtimes_with_query(
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


def test_openapi_create_host_downtime_with_query(
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

    live.add_table('hosts', [
        {
            'name': 'heute',
            'address': '127.0.0.1',
            'alias': 'heute',
            'downtimes_with_info': [],
            'scheduled_downtime_depth': 0,
        },
        {
            'name': 'example.com',
            'address': '0.0.0.0',
            'alias': 'example',
            'downtimes_with_info': [],
            'scheduled_downtime_depth': 0,
        },
    ])

    live.expect_query(['GET hosts', 'Columns: name', 'Filter: name ~ heute'])
    live.expect_query(
        'COMMAND [...] SCHEDULE_HOST_DOWNTIME;heute;1577836800;1577923200;0;0;0;test123-...;Downtime for ...',
        match_type='ellipsis',
    )
    with live:
        wsgi_app.post(
            base + '/domain-types/downtime/collections/host',
            content_type='application/json',
            params=json.dumps({
                'downtime_type': 'host_by_query',
                'start_time': '2020-01-01T00:00:00Z',
                'end_time': '2020-01-02T00:00:00Z',
                'query': {
                    "op": "~",
                    "left": "hosts.name",
                    "right": "heute"
                },
            }),
            status=204,
        )


def test_openapi_create_service_downtime_with_query(
    wsgi_app,
    with_automation_user,
    suppress_automation_calls,
    mock_livestatus,
):
    live: MockLiveStatusConnection = mock_livestatus
    username, secret = with_automation_user
    wsgi_app.set_authorization(('Bearer', username + " " + secret))
    base = '/NO_SITE/check_mk/api/v0'

    live.add_table(
        'services',
        [
            {
                'host_name': 'heute',
                'host_alias': 'heute',
                'description': 'Memory',
                'state': 0,
                'state_type': 'hard',
                'last_check': 1593697877,
                'acknowledged': 0,
            },
            {
                'host_name': 'example',
                'host_alias': 'example',
                'description': 'CPU',
                'state': 0,
                'state_type': 'hard',
                'last_check': 1593697877,
                'acknowledged': 0,
            },
        ],
    )

    live.expect_query(
        ['GET services', 'Columns: description host_name', 'Filter: host_name ~ heute'],)
    live.expect_query(
        'COMMAND [...] SCHEDULE_SVC_DOWNTIME;heute;Memory;1577836800;1577923200;0;0;0;...;Downtime for service Memory@heute',
        match_type='ellipsis',
    )

    with live:
        wsgi_app.post(
            base + '/domain-types/downtime/collections/service',
            content_type='application/json',
            params=json.dumps({
                'downtime_type': 'service_by_query',
                'start_time': '2020-01-01T00:00:00Z',
                'end_time': '2020-01-02T00:00:00Z',
                'query': {
                    "op": "~",
                    "left": "services.host_name",
                    "right": "heute"
                },
            }),
            status=204,
        )


def test_openapi_create_service_downtime_with_non_matching_query(
    wsgi_app,
    with_automation_user,
    suppress_automation_calls,
    mock_livestatus,
):
    live: MockLiveStatusConnection = mock_livestatus
    username, secret = with_automation_user
    wsgi_app.set_authorization(('Bearer', username + " " + secret))
    base = '/NO_SITE/check_mk/api/v0'

    live.add_table(
        'services',
        [
            {
                'host_name': 'heute',
                'host_alias': 'heute',
                'description': 'Memory',
                'state': 0,
                'state_type': 'hard',
                'last_check': 1593697877,
                'acknowledged': 0,
            },
        ],
    )

    live.expect_query(
        ['GET services', 'Columns: description host_name', 'Filter: host_name ~ example'],)

    with live:
        wsgi_app.post(
            base + '/domain-types/downtime/collections/service',
            content_type='application/json',
            params=json.dumps({
                'downtime_type': 'service_by_query',
                'start_time': '2020-01-01T00:00:00Z',
                'end_time': '2020-01-02T00:00:00Z',
                'query': {
                    "op": "~",
                    "left": "services.host_name",
                    "right": "example",
                }
            }),
            status=204,
        )


def test_openapi_delete_downtime_with_query(
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

    live.expect_query(['GET downtimes', 'Columns: id is_service', 'Filter: host_name ~ heute'],)
    live.expect_query(
        'COMMAND [...] DEL_SVC_DOWNTIME;123',
        match_type='ellipsis',
    )

    with live:
        wsgi_app.post(
            base + '/domain-types/downtime/actions/delete/invoke',
            content_type='application/json',
            params=json.dumps({
                'delete_type': 'query',
                'query': {
                    "op": "~",
                    "left": "downtimes.host_name",
                    "right": "heute"
                },
            }),
            status=204,
        )


def test_openapi_delete_downtime_with_params(
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
        'host_name': 'heute',
        'service_description': 'Memory',
        'is_service': 1,
        'author': 'random',
        'start_time': 1606913913,
        'end_time': 1606913913,
        'recurring': 0,
        'comment': 'some service downtime'
    }])

    live.expect_query([
        'GET downtimes',
        'Columns: id is_service',
        'Filter: host_name = heute',
        'Filter: service_description = CPU load',
        'Filter: service_description = Memory',
        'Or: 2',
        'And: 2',
    ])
    live.expect_query('COMMAND [...] DEL_SVC_DOWNTIME;123', match_type='ellipsis')
    live.expect_query('COMMAND [...] DEL_SVC_DOWNTIME;124', match_type='ellipsis')

    with live:
        wsgi_app.post(
            base + '/domain-types/downtime/actions/delete/invoke',
            content_type='application/json',
            params=json.dumps({
                'delete_type': 'params',
                'hostname': 'heute',
                'services': ["CPU load", "Memory"],
            }),
            status=204,
        )
