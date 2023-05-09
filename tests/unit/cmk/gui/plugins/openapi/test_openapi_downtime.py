#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import json

from cmk.utils.livestatus_helpers.testing import MockLiveStatusConnection


def test_openapi_list_all_downtimes(
    wsgi_app,
    with_automation_user,
    suppress_automation_calls,
    mock_livestatus,
    with_host,
):
    live: MockLiveStatusConnection = mock_livestatus
    username, secret = with_automation_user
    wsgi_app.set_authorization(('Bearer', username + " " + secret))
    base = '/NO_SITE/check_mk/api/1.0'

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
    with_groups,
):
    live: MockLiveStatusConnection = mock_livestatus
    username, secret = with_automation_user
    wsgi_app.set_authorization(('Bearer', username + " " + secret))
    base = '/NO_SITE/check_mk/api/1.0'

    live.add_table('hostgroups', [
        {
            'members': ['example.com', 'heute'],
            'name': 'windows',
        },
    ],
                   site='NO_SITE')
    live.expect_query('GET hostgroups\nColumns: members\nFilter: name = windows')
    live.expect_query(
        'GET hosts\nColumns: name\nFilter: name = example.com\nFilter: name = heute\nOr: 2')
    live.expect_query(
        'COMMAND [...] SCHEDULE_HOST_DOWNTIME;heute;1577836800;1577923200;1;0;0;test123-...;Downtime for ...',
        match_type='ellipsis',
        site_id='NO_SITE')
    live.expect_query(
        'COMMAND [...] SCHEDULE_HOST_DOWNTIME;example.com;1577836800;1577923200;1;0;0;test123-...;Downtime for ...',
        match_type='ellipsis',
        site_id='NO_SITE',
    )
    with live:
        wsgi_app.post(
            base + '/domain-types/downtime/collections/host',
            content_type='application/json',
            params=json.dumps({
                'downtime_type': 'hostgroup',
                'hostgroup_name': 'windows',
                'start_time': '2020-01-01T00:00:00Z',
                'end_time': '2020-01-02T00:00:00Z',
            }),
            status=204,
        )


def test_openapi_schedule_host_downtime(
    wsgi_app,
    with_automation_user,
    mock_livestatus,
    with_host,
):
    live: MockLiveStatusConnection = mock_livestatus
    username, secret = with_automation_user
    wsgi_app.set_authorization(('Bearer', username + " " + secret))
    base = '/NO_SITE/check_mk/api/1.0'

    live.expect_query('GET hosts\nColumns: name\nFilter: name = example.com')
    live.expect_query('GET hosts\nColumns: name\nFilter: name = example.com')
    live.expect_query(
        'COMMAND [...] SCHEDULE_HOST_DOWNTIME;example.com;1577836800;1577923200;1;0;0;test123-...;Downtime for ...',
        match_type='ellipsis',
        site_id='NO_SITE',
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


def test_openapi_schedule_host_downtime_for_host_without_config(
    wsgi_app,
    with_automation_user,
    mock_livestatus,
):
    live: MockLiveStatusConnection = mock_livestatus
    live.set_sites(['NO_SITE'])
    username, secret = with_automation_user
    wsgi_app.set_authorization(('Bearer', username + " " + secret))

    base = "/NO_SITE/check_mk/api/1.0"

    monitored_only_host = "this-host-only.exists-in.livestatus"

    live.add_table(
        "hosts",
        [
            {
                "name": monitored_only_host,
            },
        ],
    )

    live.expect_query(f"GET hosts\nColumns: name\nFilter: name = {monitored_only_host}")
    live.expect_query(f"GET hosts\nColumns: name\nFilter: name = {monitored_only_host}")
    live.expect_query(
        f"COMMAND [...] SCHEDULE_HOST_DOWNTIME;{monitored_only_host};1577836800;1577923200;1;0;0;test123-...;Downtime for ...",
        match_type="ellipsis",
    )
    with live:
        wsgi_app.post(
            base + "/domain-types/downtime/collections/host",
            content_type="application/json",
            params=json.dumps({
                "downtime_type": "host",
                "host_name": monitored_only_host,
                "start_time": "2020-01-01T00:00:00Z",
                "end_time": "2020-01-02T00:00:00Z",
            }),
            headers={"Accept": "application/json"},
            status=204,
        )


def test_openapi_schedule_servicegroup_downtime(
    wsgi_app,
    with_automation_user,
    mock_livestatus,
    with_groups,
):
    live: MockLiveStatusConnection = mock_livestatus
    username, secret = with_automation_user
    wsgi_app.set_authorization(('Bearer', username + " " + secret))
    base = '/NO_SITE/check_mk/api/1.0'

    live.add_table('servicegroups', [
        {
            'members': [['example.com', 'Memory'], ['example.com', 'CPU load'],
                        ['heute', 'CPU load']],
            'name': 'routers',
        },
    ],
                   site='NO_SITE')
    live.expect_query('GET servicegroups\nColumns: members\nFilter: name = routers')
    live.expect_query(
        'COMMAND [...] SCHEDULE_SVC_DOWNTIME;example.com;Memory;1577836800;1577923200;1;0;0;test123-...;Downtime for ...',
        match_type='ellipsis',
        site_id='NO_SITE',
    )
    live.expect_query(
        'COMMAND [...] SCHEDULE_SVC_DOWNTIME;example.com;CPU load;1577836800;1577923200;1;0;0;test123-...;Downtime for ...',
        match_type='ellipsis',
        site_id='NO_SITE',
    )
    live.expect_query(
        'COMMAND [...] SCHEDULE_SVC_DOWNTIME;heute;CPU load;1577836800;1577923200;1;0;0;test123-...;Downtime for ...',
        match_type='ellipsis',
        site_id='NO_SITE',
    )
    with live:
        wsgi_app.post(
            base + '/domain-types/downtime/collections/service',
            content_type='application/json',
            params=json.dumps({
                'downtime_type': 'servicegroup',
                'servicegroup_name': 'routers',
                'start_time': '2020-01-01T00:00:00Z',
                'end_time': '2020-01-02T00:00:00Z',
            }),
            status=204,
        )


def test_openapi_schedule_service_downtime(
    wsgi_app,
    with_automation_user,
    mock_livestatus,
    with_host,
):
    live: MockLiveStatusConnection = mock_livestatus
    username, secret = with_automation_user
    wsgi_app.set_authorization(('Bearer', username + " " + secret))
    base = '/NO_SITE/check_mk/api/1.0'

    live.expect_query('GET hosts\nColumns: name\nFilter: name = example.com')
    live.expect_query('GET hosts\nColumns: name\nFilter: name = example.com')
    live.expect_query(
        'COMMAND [...] SCHEDULE_SVC_DOWNTIME;example.com;Memory;1577836800;1577923200;1;0;0;test123-...;Downtime for ...',
        match_type='ellipsis',
        site_id='NO_SITE',
    )
    live.expect_query(
        'COMMAND [...] SCHEDULE_SVC_DOWNTIME;example.com;CPU load;1577836800;1577923200;1;0;0;test123-...;Downtime for ...',
        match_type='ellipsis',
        site_id='NO_SITE',
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


def test_openapi_schedule_service_downtime_with_non_matching_query(
    wsgi_app,
    with_automation_user,
    mock_livestatus,
):
    live: MockLiveStatusConnection = mock_livestatus
    username, secret = with_automation_user
    wsgi_app.set_authorization(('Bearer', username + " " + secret))
    base = '/NO_SITE/check_mk/api/1.0'

    live.expect_query('GET services\nColumns: description host_name\nFilter: host_name = nothing')

    with live:
        wsgi_app.post(
            base + '/domain-types/downtime/collections/service',
            content_type='application/json',
            params=json.dumps({
                'downtime_type': 'service_by_query',
                'query': {
                    'op': '=',
                    'left': 'services.host_name',
                    'right': 'nothing'
                },
                'start_time': '2020-01-01T00:00:00Z',
                'end_time': '2020-01-02T00:00:00Z',
            }),
            status=422,
        )


def test_openapi_schedule_host_downtime_with_non_matching_query(
    wsgi_app,
    with_automation_user,
    mock_livestatus,
):
    live: MockLiveStatusConnection = mock_livestatus
    username, secret = with_automation_user
    wsgi_app.set_authorization(('Bearer', username + " " + secret))
    base = '/NO_SITE/check_mk/api/1.0'

    live.expect_query('GET hosts\nColumns: name\nFilter: name = nothing')

    with live:
        wsgi_app.post(
            base + '/domain-types/downtime/collections/host',
            content_type='application/json',
            params=json.dumps({
                'downtime_type': 'host_by_query',
                'query': {
                    'op': '=',
                    'left': 'hosts.name',
                    'right': 'nothing'
                },
                'start_time': '2020-01-01T00:00:00Z',
                'end_time': '2020-01-02T00:00:00Z',
            }),
            status=422,
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
    base = '/NO_SITE/check_mk/api/1.0'

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


def test_openapi_show_downtime_with_params(
    wsgi_app,
    with_automation_user,
    suppress_automation_calls,
    mock_livestatus,
):
    live: MockLiveStatusConnection = mock_livestatus
    username, secret = with_automation_user
    wsgi_app.set_authorization(('Bearer', username + " " + secret))
    base = '/NO_SITE/check_mk/api/1.0'

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
        'Filter: host_name = example.com', 'Filter: is_service = 0', 'And: 2'
    ])
    with live:
        resp = wsgi_app.call_method(
            'get',
            base + '/domain-types/downtime/collections/all?host_name=example.com',
            status=200,
        )
        assert resp.json_body["value"][0]['id'] == '124'


def test_openapi_show_downtime_of_non_existing_host(
    wsgi_app,
    with_automation_user,
    suppress_automation_calls,
    mock_livestatus,
):
    live: MockLiveStatusConnection = mock_livestatus
    username, secret = with_automation_user
    wsgi_app.set_authorization(('Bearer', username + " " + secret))
    base = '/NO_SITE/check_mk/api/1.0'

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
        'Filter: host_name = nothing', 'Filter: is_service = 0', "And: 2"
    ])
    with live:
        _ = wsgi_app.call_method(
            'get',
            base + '/domain-types/downtime/collections/all?host_name=nothing',
            status=200,
        )


def test_openapi_create_host_downtime_with_query(
    wsgi_app,
    with_automation_user,
    suppress_automation_calls,
    mock_livestatus,
):
    live: MockLiveStatusConnection = mock_livestatus
    username, secret = with_automation_user
    wsgi_app.set_authorization(('Bearer', username + " " + secret))
    base = '/NO_SITE/check_mk/api/1.0'

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
    }],
                   site='NO_SITE')

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
    ],
                   site='NO_SITE')

    live.expect_query(['GET hosts', 'Columns: name', 'Filter: name ~ heute'])
    live.expect_query(['GET hosts', 'Columns: name', 'Filter: name = heute'])
    live.expect_query(
        'COMMAND [...] SCHEDULE_HOST_DOWNTIME;heute;1577836800;1577923200;1;0;0;test123-...;Downtime for ...',
        match_type='ellipsis',
        site_id='NO_SITE',
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
    base = '/NO_SITE/check_mk/api/1.0'

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
        site='NO_SITE',
    )

    live.expect_query(
        ['GET services', 'Columns: description host_name', 'Filter: host_name ~ heute'],)
    live.expect_query(
        'COMMAND [...] SCHEDULE_SVC_DOWNTIME;heute;Memory;1577836800;1577923200;1;0;0;...;Downtime for service Memory@heute',
        match_type='ellipsis',
        site_id='NO_SITE',
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
    base = '/NO_SITE/check_mk/api/1.0'

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
            status=422,
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
    base = '/NO_SITE/check_mk/api/1.0'

    live.add_table(
        'downtimes',
        [{
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
        }],
        site='NO_SITE',
    )

    live.expect_query(['GET downtimes', 'Columns: id is_service', 'Filter: host_name ~ heute'],)
    live.expect_query(
        'COMMAND [...] DEL_SVC_DOWNTIME;123',
        match_type='ellipsis',
        site_id='NO_SITE',
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


def test_openapi_delete_downtime_by_id(
    wsgi_app,
    with_automation_user,
    suppress_automation_calls,
    mock_livestatus,
):
    live: MockLiveStatusConnection = mock_livestatus
    username, secret = with_automation_user
    wsgi_app.set_authorization(('Bearer', username + " " + secret))
    base = '/NO_SITE/check_mk/api/1.0'
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
        'id': 1234,
        'host_name': 'heute',
        'service_description': 'Memory',
        'is_service': 1,
        'author': 'random',
        'start_time': 1606913913,
        'end_time': 1606913913,
        'recurring': 0,
        'comment': 'some service downtime'
    }],
                   site='NO_SITE')

    live.expect_query([
        'GET downtimes',
        'Columns: is_service',
        'Filter: id = 123',
    ])
    live.expect_query(
        'COMMAND [...] DEL_SVC_DOWNTIME;123',
        match_type='ellipsis',
        site_id='NO_SITE',
    )

    with live:
        wsgi_app.post(
            base + '/domain-types/downtime/actions/delete/invoke',
            content_type='application/json',
            params=json.dumps({
                'delete_type': 'by_id',
                'downtime_id': '123',
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
    base = '/NO_SITE/check_mk/api/1.0'

    live.add_table(
        'downtimes',
        [{
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
        }],
        site='NO_SITE',
    )

    live.expect_query([
        'GET downtimes',
        'Columns: id is_service',
        'Filter: host_name = heute',
        'Filter: service_description = CPU load',
        'Filter: service_description = Memory',
        'Or: 2',
        'And: 2',
    ])
    live.expect_query(
        'COMMAND [...] DEL_SVC_DOWNTIME;123',
        match_type='ellipsis',
        site_id='NO_SITE',
    )
    live.expect_query(
        'COMMAND [...] DEL_SVC_DOWNTIME;124',
        match_type='ellipsis',
        site_id='NO_SITE',
    )

    with live:
        wsgi_app.post(
            base + '/domain-types/downtime/actions/delete/invoke',
            content_type='application/json',
            params=json.dumps({
                'delete_type': 'params',
                'host_name': 'heute',
                'service_descriptions': ["CPU load", "Memory"],
            }),
            status=204,
        )


def test_openapi_downtime_non_existing_instance(
    wsgi_app,
    with_automation_user,
    suppress_automation_calls,
    mock_livestatus: MockLiveStatusConnection,
):
    username, secret = with_automation_user
    wsgi_app.set_authorization(('Bearer', username + " " + secret))
    base = '/NO_SITE/check_mk/api/1.0'

    live: MockLiveStatusConnection = mock_livestatus
    live.expect_query(["GET hosts", "Columns: name", "Filter: name = non-existant"])

    with live:
        wsgi_app.post(
            base + "/domain-types/downtime/collections/host",
            content_type="application/json",
            params=json.dumps({
                "downtime_type": "host",
                "host_name": "non-existant",
                "start_time": "2020-01-01T00:00:00Z",
                "end_time": "2020-01-02T00:00:00Z",
            }),
            headers={"Accept": "application/json"},
            status=400,
        )


def test_openapi_downtime_non_existing_groups(
    wsgi_app,
    with_automation_user,
    suppress_automation_calls,
):
    username, secret = with_automation_user
    wsgi_app.set_authorization(('Bearer', username + " " + secret))
    base = '/NO_SITE/check_mk/api/1.0'

    wsgi_app.post(
        base + '/domain-types/downtime/collections/host',
        content_type='application/json',
        params=json.dumps({
            'downtime_type': 'hostgroup',
            'hostgroup_name': 'non-existant',
            'start_time': '2020-01-01T00:00:00Z',
            'end_time': '2020-01-02T00:00:00Z',
        }),
        status=400,
    )


def test_openapi_downtime_get_single(
    wsgi_app,
    with_automation_user,
    suppress_automation_calls,
    mock_livestatus,
):
    live: MockLiveStatusConnection = mock_livestatus
    username, secret = with_automation_user
    wsgi_app.set_authorization(('Bearer', username + " " + secret))
    base = '/NO_SITE/check_mk/api/1.0'

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
        'Columns: id host_name service_description is_service author start_time end_time recurring comment',
        'Filter: id = 123',
    ])

    with live:
        resp = wsgi_app.call_method(
            'get',
            base + "/objects/downtime/123",
            status=200,
        )
        assert resp.json_body["title"] == "Downtime for service: CPU load"


def test_openapi_downtime_invalid_single(
    wsgi_app,
    with_automation_user,
    suppress_automation_calls,
    mock_livestatus,
):
    live: MockLiveStatusConnection = mock_livestatus
    username, secret = with_automation_user
    wsgi_app.set_authorization(('Bearer', username + " " + secret))
    base = '/NO_SITE/check_mk/api/1.0'

    live.expect_query([
        'GET downtimes',
        'Columns: id host_name service_description is_service author start_time end_time recurring comment',
        'Filter: id = 123',
    ])

    with live:
        _ = wsgi_app.call_method(
            'get',
            base + "/objects/downtime/123",
            status=404,
        )
