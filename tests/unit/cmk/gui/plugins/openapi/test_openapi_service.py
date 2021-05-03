#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import urllib

from cmk.utils.livestatus_helpers.testing import MockLiveStatusConnection


def test_openapi_livestatus_service(
    wsgi_app,
    with_automation_user,
    suppress_automation_calls,
    mock_livestatus,
    with_host,
):
    live: MockLiveStatusConnection = mock_livestatus
    username, secret = with_automation_user
    wsgi_app.set_authorization(('Bearer', username + " " + secret))

    live.add_table(
        'services',
        [
            {
                'host_name': 'heute',
                'host_alias': 'heute',
                'description': 'Filesystem /opt/omd/sites/heute/tmp',
                'state': 0,
                'state_type': 'hard',
                'last_check': 1593697877,
                'acknowledged': 0,
            },
            {
                'host_name': 'example.com',
                'host_alias': 'example.com',
                'description': 'Filesystem /boot',
                'state': 0,
                'state_type': 'hard',
                'last_check': 0,
                'acknowledged': 0,
            },
        ],
    )

    live.expect_query([
        'GET services',
        'Columns: host_name description',
    ],)

    with live:
        base = '/NO_SITE/check_mk/api/1.0'

        resp = wsgi_app.call_method(
            'get',
            base + "/domain-types/service/collections/all",
            status=200,
        )
        assert len(resp.json['value']) == 2

    live.expect_query([
        'GET services',
        'Columns: host_name description',
        'Filter: host_alias ~ heute',
    ],)

    with live:
        resp = wsgi_app.call_method(
            'get',
            base +
            '/domain-types/service/collections/all?query={"op": "~", "left": "host_alias", "right": "heute"}',
            status=200,
        )
        assert len(resp.json['value']) == 1

    live.expect_query([
        'GET services',
        'Columns: host_name description',
        'Filter: host_name = example.com',
    ])
    with live:
        resp = wsgi_app.call_method(
            'get',
            base + "/objects/host/example.com/collections/services",
            status=200,
        )
        assert len(resp.json['value']) == 1


def test_openapi_livestatus_collection_link(
    wsgi_app,
    with_automation_user,
    suppress_automation_calls,
    mock_livestatus,
    with_host,
):
    live: MockLiveStatusConnection = mock_livestatus
    username, secret = with_automation_user
    wsgi_app.set_authorization(('Bearer', username + " " + secret))

    live.add_table(
        'services',
        [
            {
                'host_name': 'heute',
                'host_alias': 'heute',
                'description': 'Filesystem /opt/omd/sites/heute/tmp',
                'state': 0,
                'state_type': 'hard',
                'last_check': 1593697877,
                'acknowledged': 0,
            },
            {
                'host_name': 'example.com',
                'host_alias': 'example.com',
                'description': 'Filesystem /boot',
                'state': 0,
                'state_type': 'hard',
                'last_check': 0,
                'acknowledged': 0,
            },
        ],
    )

    live.expect_query([
        'GET services',
        'Columns: host_name description',
    ],)

    with live:
        base = '/NO_SITE/check_mk/api/1.0'

        resp = wsgi_app.call_method(
            'get',
            base + "/domain-types/service/collections/all",
            status=200,
        )
        assert resp.json_body["value"][0]["links"][0][
            "href"] == 'http://localhost/NO_SITE/check_mk/api/1.0/objects/host/heute/actions/show_service/invoke?service_description=Filesystem+%2Fopt%2Fomd%2Fsites%2Fheute%2Ftmp'


def test_openapi_specific_service(
    wsgi_app,
    with_automation_user,
    suppress_automation_calls,
    mock_livestatus,
    with_host,
):
    live: MockLiveStatusConnection = mock_livestatus
    username, secret = with_automation_user
    wsgi_app.set_authorization(('Bearer', username + " " + secret))

    live.add_table(
        'services',
        [
            {
                'host_name': 'heute',
                'host_alias': 'heute',
                'description': 'Filesystem',
                'state': 0,
                'state_type': 'hard',
                'last_check': 1593697877,
                'acknowledged': 0,
            },
            {
                'host_name': 'example.com',
                'host_alias': 'example.com',
                'description': 'Filesystem /boot',
                'state': 0,
                'state_type': 'hard',
                'last_check': 0,
                'acknowledged': 0,
            },
        ],
    )

    live.expect_query([
        'GET services',
        'Columns: description host_name state_type state last_check',
        'Filter: host_name = heute',
        'Filter: description = Filesystem',
        'And: 2',
    ])
    with live:
        base = '/NO_SITE/check_mk/api/1.0'

        resp = wsgi_app.call_method(
            'get',
            base + "/objects/host/heute/actions/show_service/invoke?service_description=Filesystem",
            status=200,
        )
        assert resp.json_body["extensions"] == {
            'description': 'Filesystem',
            'host_name': 'heute',
            'state_type': 'hard',
            'state': 0,
            'last_check': 1593697877
        }


def test_openapi_service_with_slash_character(
    wsgi_app,
    with_automation_user,
    suppress_automation_calls,
    mock_livestatus,
    with_host,
):
    live: MockLiveStatusConnection = mock_livestatus
    username, secret = with_automation_user
    wsgi_app.set_authorization(('Bearer', username + " " + secret))

    live.add_table(
        'services',
        [
            {
                'host_name': 'heute',
                'host_alias': 'heute',
                'description': 'Filesystem',
                'state': 0,
                'state_type': 'hard',
                'last_check': 1593697877,
                'acknowledged': 0,
            },
            {
                'host_name': 'example.com',
                'host_alias': 'example.com',
                'description': 'Filesystem /böot',
                'state': 0,
                'state_type': 'hard',
                'last_check': 0,
                'acknowledged': 0,
            },
        ],
    )

    live.expect_query([
        'GET services',
        'Columns: description host_name state_type state last_check',
        'Filter: host_name = example.com',
        'Filter: description = Filesystem /böot',
        'And: 2',
    ])
    with live:
        base = '/NO_SITE/check_mk/api/1.0'
        service_description = urllib.parse.quote("Filesystem /böot", safe=' ').replace(" ", "+")

        resp = wsgi_app.call_method(
            'get',
            base +
            f"/objects/host/example.com/actions/show_service/invoke?service_description={service_description}",
            status=200,
        )
        assert resp.json_body["extensions"] == {
            'description': 'Filesystem /böot',
            'host_name': 'example.com',
            'state_type': 'hard',
            'state': 0,
            'last_check': 0
        }


def test_openapi_non_existing_service(
    wsgi_app,
    with_automation_user,
    suppress_automation_calls,
    mock_livestatus,
    with_host,
):
    live: MockLiveStatusConnection = mock_livestatus
    username, secret = with_automation_user
    wsgi_app.set_authorization(('Bearer', username + " " + secret))

    live.add_table(
        'services',
        [
            {
                'host_name': 'heute',
                'host_alias': 'heute',
                'description': 'Filesystem',
                'state': 0,
                'state_type': 'hard',
                'last_check': 1593697877,
                'acknowledged': 0,
            },
            {
                'host_name': 'example.com',
                'host_alias': 'example.com',
                'description': 'Filesystem /boot',
                'state': 0,
                'state_type': 'hard',
                'last_check': 0,
                'acknowledged': 0,
            },
        ],
    )

    live.expect_query([
        'GET services', 'Columns: description host_name state_type state last_check',
        'Filter: host_name = heute', 'Filter: description = CPU', 'And: 2'
    ])

    with live:
        base = '/NO_SITE/check_mk/api/1.0'

        _ = wsgi_app.call_method(
            'get',
            base + "/objects/host/heute/actions/show_service/invoke?service_description=CPU",
            status=404,
        )
