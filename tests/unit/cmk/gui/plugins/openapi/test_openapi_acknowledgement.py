#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import json

import pytest  # type: ignore[import]

from cmk.gui.plugins.openapi.livestatus_helpers.testing import MockLiveStatusConnection


@pytest.mark.parametrize(
    argnames=[
        'service',
        'acknowledgement_sent',
    ],
    argvalues=[
        ['CPU load', True],  # service Failed, acked.
        ['Memory', False],  # service OK, not failed.
    ])
def test_openapi_acknowledge_all_services(
    wsgi_app,
    with_automation_user,
    mock_livestatus,
    service,
    acknowledgement_sent,
):
    live: MockLiveStatusConnection = mock_livestatus
    username, secret = with_automation_user
    wsgi_app.set_authorization(('Bearer', username + " " + secret))
    base = '/NO_SITE/check_mk/api/v0'

    live.add_table('services', [
        {
            'host_name': 'example.com',
            'description': 'CPU load',
            'state': 1
        },
        {
            'host_name': 'heute',
            'description': 'CPU load',
            'state': 1
        },
        {
            'host_name': 'example.com',
            'description': 'Memory',
            'state': 0
        },
        {
            'host_name': 'heute',
            'description': 'Memory',
            'state': 0
        },
    ])

    live.expect_query([
        'GET services',
        'Columns: host_name description state',
        f'Filter: description = {service}',
    ])

    if acknowledgement_sent:
        live.expect_query(
            f'COMMAND [...] ACKNOWLEDGE_SVC_PROBLEM;example.com;{service};2;1;1;test123-...;Hello world!',
            match_type='ellipsis',
        )
        live.expect_query(
            f'COMMAND [...] ACKNOWLEDGE_SVC_PROBLEM;heute;{service};2;1;1;test123-...;Hello world!',
            match_type='ellipsis',
        )

    with live:
        wsgi_app.post(
            base + "/domain-types/acknowledge/collections/service",
            params=json.dumps({
                'acknowledge_type': 'service',
                'service_description': service,
                'sticky': True,
                'notify': True,
                'persistent': True,
                'comment': 'Hello world!',
            }),
            content_type='application/json',
            status=204,
        )


@pytest.mark.parametrize(
    argnames=[
        'service',
        'acknowledgement_sent',
    ],
    argvalues=[
        ['Memory', True],  # ack sent
        ['Filesystem /boot', True],  # slashes in name, ack sent
        ['CPU load', False],  # service OK, ack not sent
    ])
def test_openapi_acknowledge_specific_service(
    wsgi_app,
    with_automation_user,
    mock_livestatus,
    service,
    acknowledgement_sent,
):
    live: MockLiveStatusConnection = mock_livestatus
    username, secret = with_automation_user
    wsgi_app.set_authorization(('Bearer', username + " " + secret))
    base = '/NO_SITE/check_mk/api/v0'

    live.add_table('services', [
        {
            'host_name': 'heute',
            'description': 'Memory',
            'state': 1,
        },
        {
            'host_name': 'heute',
            'description': 'CPU load',
            'state': 0,
        },
        {
            'host_name': 'heute',
            'description': 'Filesystem /boot',
            'state': 1,
        },
    ])

    live.expect_query([
        'GET services',
        'Columns: host_name description state',
        'Filter: host_name ~ heute',
        f'Filter: description ~ {service}',
        'And: 2',
    ])

    if acknowledgement_sent:
        live.expect_query(
            f'COMMAND [...] ACKNOWLEDGE_SVC_PROBLEM;heute;{service};2;1;1;test123-...;Hello world!',
            match_type='ellipsis',
        )

    with live:
        wsgi_app.post(
            base + "/domain-types/acknowledge/collections/service",
            params=json.dumps({
                'acknowledge_type': 'service_by_query',
                'query': {
                    'op': 'and',
                    'expr': [{
                        'op': '~',
                        'left': 'services.host_name',
                        'right': 'heute'
                    }, {
                        'op': '~',
                        'left': 'services.description',
                        'right': service
                    }]
                },
                'sticky': True,
                'notify': True,
                'persistent': True,
                'comment': 'Hello world!',
            }),
            content_type='application/json',
            status=204,
        )


@pytest.mark.parametrize(
    argnames=[
        'host_name',
        'acknowledgement_sent',
    ],
    argvalues=[
        ['example.com', True],  # host not ok, ack sent
        ['heute', False],  # host ok, ack not sent
    ])
def test_openapi_acknowledge_host(
    wsgi_app,
    with_automation_user,
    mock_livestatus,
    host_name,
    acknowledgement_sent,
):
    live: MockLiveStatusConnection = mock_livestatus
    username, secret = with_automation_user
    wsgi_app.set_authorization(('Bearer', username + " " + secret))
    base = '/NO_SITE/check_mk/api/v0'

    live.add_table('hosts', [
        {
            'name': 'example.com',
            'state': 1,
        },
        {
            'name': 'heute',
            'state': 0,
        },
    ])

    live.expect_query(f'GET hosts\nColumns: name state\nFilter: name = {host_name}')

    if acknowledgement_sent:
        live.expect_query(
            f'COMMAND [...] ACKNOWLEDGE_HOST_PROBLEM;{host_name};2;1;1;test123-...;Hello world!',
            match_type='ellipsis',
        )

    with live:
        wsgi_app.post(
            base + "/domain-types/acknowledge/collections/host",
            params=json.dumps({
                'acknowledge_type': 'host',
                'host_name': host_name,
                'sticky': True,
                'notify': True,
                'persistent': True,
                'comment': 'Hello world!',
            }),
            content_type='application/json',
            status=204,
        )


def test_openapi_bulk_acknowledge(
    wsgi_app,
    with_automation_user,
    mock_livestatus,
):
    live: MockLiveStatusConnection = mock_livestatus
    username, secret = with_automation_user
    wsgi_app.set_authorization(('Bearer', username + " " + secret))
    base = '/NO_SITE/check_mk/api/v0'

    live.add_table('services', [{
        'host_name': 'heute',
        'description': 'Memory',
        'state': 1,
    }, {
        'host_name': 'example.com',
        'description': 'CPU load',
        'state': 1
    }])

    live.expect_query([
        'GET services',
        'Columns: host_name description state',
        'Filter: description = Memory',
        'Filter: description = CPU load',
        'Or: 2',
    ])

    live.expect_query(
        'COMMAND [...] ACKNOWLEDGE_SVC_PROBLEM;heute;Memory;2;1;1;test123-...;Hello world!',
        match_type='ellipsis',
    )
    live.expect_query(
        'COMMAND [...] ACKNOWLEDGE_SVC_PROBLEM;example.com;CPU load;2;1;1;test123-...;Hello world!',
        match_type='ellipsis')

    with live():
        wsgi_app.post(
            base + "/domain-types/acknowledge/collections/service",
            params=json.dumps({
                'acknowledge_type': 'service_by_query',
                'query': {
                    'op': 'or',
                    'expr': [{
                        'op': '=',
                        'left': 'description',
                        'right': 'Memory'
                    }, {
                        'op': '=',
                        'left': 'description',
                        'right': 'CPU load'
                    }]
                },
                'sticky': True,
                'notify': True,
                'persistent': True,
                'comment': 'Hello world!',
            }),
            content_type='application/json',
            status=204,
        )


def test_openapi_acknowledge_servicegroup(
    wsgi_app,
    with_automation_user,
    mock_livestatus,
):
    live: MockLiveStatusConnection = mock_livestatus
    username, secret = with_automation_user
    wsgi_app.set_authorization(('Bearer', username + " " + secret))
    base = '/NO_SITE/check_mk/api/v0'

    live.add_table('servicegroups', [
        {
            'members': [('example.com', 'Memory'), ('example.com', 'CPU load')],
            'name': 'windows',
        },
    ])

    live.expect_query('GET servicegroups\nColumns: members\nFilter: name = windows',)
    live.expect_query(
        'COMMAND [...] ACKNOWLEDGE_SVC_PROBLEM;example.com;Memory;1;0;0;test123-...;Acknowledged',
        match_type='ellipsis',
    )
    live.expect_query(
        'COMMAND [...] ACKNOWLEDGE_SVC_PROBLEM;example.com;CPU load;1;0;0;test123-...;Acknowledged',
        match_type='ellipsis',
    )
    with live:
        wsgi_app.post(
            base + '/domain-types/acknowledge/collections/service',
            content_type='application/json',
            params=json.dumps({
                'acknowledge_type': 'servicegroup',
                'servicegroup_name': 'windows',
                'sticky': False,
                'notify': False,
                'persistent': False,
                'comment': 'Acknowledged',
            }),
            status=204,
        )


def test_openapi_acknowledge_hostgroup(
    wsgi_app,
    with_automation_user,
    mock_livestatus,
):
    live: MockLiveStatusConnection = mock_livestatus
    username, secret = with_automation_user
    wsgi_app.set_authorization(('Bearer', username + " " + secret))
    base = '/NO_SITE/check_mk/api/v0'

    live.add_table('hostgroups', [
        {
            'members': ['example.com', 'heute'],
            'name': 'samples',
        },
    ])

    live.expect_query('GET hostgroups\nColumns: members\nFilter: name = samples')
    live.expect_query(
        'COMMAND [...] ACKNOWLEDGE_HOST_PROBLEM;example.com;1;0;0;test123-...;Acknowledged',
        match_type='ellipsis',
    )
    live.expect_query(
        'COMMAND [...] ACKNOWLEDGE_HOST_PROBLEM;heute;1;0;0;test123-...;Acknowledged',
        match_type='ellipsis',
    )

    with live:
        wsgi_app.post(
            base + '/domain-types/acknowledge/collections/host',
            content_type='application/json',
            params=json.dumps({
                'acknowledge_type': 'hostgroup',
                'hostgroup_name': 'samples',
                'sticky': False,
                'notify': False,
                'persistent': False,
                'comment': 'Acknowledged'
            }),
            status=204,
        )


def test_openapi_acknowledge_host_with_query(
    wsgi_app,
    with_automation_user,
    mock_livestatus,
):
    live: MockLiveStatusConnection = mock_livestatus
    username, secret = with_automation_user
    wsgi_app.set_authorization(('Bearer', username + " " + secret))
    base = '/NO_SITE/check_mk/api/v0'

    live.add_table('hosts', [
        {
            'name': 'example.com',
            'state': 1,
        },
        {
            'name': 'heute',
            'state': 0,
        },
    ])

    live.expect_query('GET hosts\nColumns: name\nFilter: state = 1')
    live.expect_query(
        'COMMAND [...] ACKNOWLEDGE_HOST_PROBLEM;example.com;1;0;0;test123...;Acknowledged',
        match_type='ellipsis',
    )

    with live:
        wsgi_app.post(
            base + '/domain-types/acknowledge/collections/host',
            content_type='application/json',
            params=json.dumps({
                'acknowledge_type': 'host_by_query',
                'query': '{"op": "=", "left": "hosts.state", "right": "1"}',
                'sticky': False,
                'notify': False,
                'persistent': False,
                'comment': 'Acknowledged',
            }),
            status=204,
        )


def test_openapi_acknowledge_host_with_non_matching_query(
    wsgi_app,
    with_automation_user,
    mock_livestatus,
):
    live: MockLiveStatusConnection = mock_livestatus
    username, secret = with_automation_user
    wsgi_app.set_authorization(('Bearer', username + " " + secret))
    base = '/NO_SITE/check_mk/api/v0'

    live.add_table('hosts', [
        {
            'name': 'example.com',
            'state': 1,
        },
        {
            'name': 'heute',
            'state': 0,
        },
    ])

    live.expect_query('GET hosts\nColumns: name\nFilter: name = servo')

    with live:
        wsgi_app.post(
            base + '/domain-types/acknowledge/collections/host',
            content_type='application/json',
            params=json.dumps({
                'acknowledge_type': 'host_by_query',
                'query': '{"op": "=", "left": "hosts.name", "right": "servo"}',
                'sticky': False,
                'notify': False,
                'persistent': False,
                'comment': 'Acknowledged',
            }),
            status=404,
        )
