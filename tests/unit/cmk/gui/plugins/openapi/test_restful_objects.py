#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json

from cmk.utils.livestatus_helpers.testing import MockLiveStatusConnection

import cmk.gui.plugins.openapi.restful_objects.decorators
from cmk.gui.plugins.openapi.restful_objects import response_schemas
from cmk.gui.plugins.openapi.restful_objects.type_defs import StatusCode, StatusCodeInt


def test_domain_object():
    errors = response_schemas.DomainObject().validate(
        {
            "domainType": "folder",
            "extensions": {
                "attributes": {
                    "meta_data": {
                        "created_at": 1583248090.277515,
                        "created_by": "test123-jinlc",
                        "update_at": 1583248090.277516,
                        "updated_at": 1583248090.324114,
                    }
                }
            },
            "links": [
                {
                    "domainType": "link",
                    "href": "/objects/folder/a71684ebd8fe49548263083a3da332c8",
                    "method": "GET",
                    "rel": "self",
                    "type": "application/json",
                },
                {
                    "domainType": "link",
                    "href": "/objects/folder/a71684ebd8fe49548263083a3da332c8",
                    "method": "PUT",
                    "rel": ".../update",
                    "type": "application/json",
                },
                {
                    "domainType": "link",
                    "href": "/objects/folder/a71684ebd8fe49548263083a3da332c8",
                    "method": "DELETE",
                    "rel": ".../delete",
                    "type": "application/json",
                },
            ],
            "members": {
                "move": {
                    "id": "move",
                    "links": [
                        {
                            "domainType": "link",
                            "href": "/objects/folder/a71684ebd8fe49548263083a3da332c8",
                            "method": "GET",
                            "rel": "up",
                            "type": "application/json",
                        },
                        {
                            "domainType": "link",
                            "href": "/objects/folder/a71684ebd8fe49548263083a3da332c8/actions/move/invoke",
                            "method": "GET",
                            "rel": '.../details;action="move"',
                            "type": "application/json",
                        },
                        {
                            "domainType": "link",
                            "href": "/objects/folder/a71684ebd8fe49548263083a3da332c8/actions/move/invoke",
                            "method": "POST",
                            "rel": '.../invoke;action="move"',
                            "type": "application/json",
                        },
                    ],
                    "memberType": "action",
                }
            },
            "title": "foobar",
        }
    )

    if errors:
        raise Exception(errors)


def test_status_codes_match():
    assert StatusCodeInt.__args__ == tuple(int(sc) for sc in StatusCode.__args__)  # type: ignore


def test_no_config_generation_on_get(
    wsgi_app,
    with_automation_user,
    with_host,
    monkeypatch,
    mocker,
):
    """
    update_config_generation should only be called on posts, not on gets: SUP-8793
    """
    username, secret = with_automation_user
    wsgi_app.set_authorization(("Bearer", username + " " + secret))
    base = "/NO_SITE/check_mk/api/1.0"

    mock = mocker.Mock()
    monkeypatch.setattr(
        cmk.gui.plugins.openapi.restful_objects.decorators,
        "activate_changes_update_config_generation",
        mock,
    )

    wsgi_app.call_method(
        "get",
        base + "/objects/host_config/heute",
        status=200,
        headers={"Accept": "application/json"},
    )
    # we have a get request, so we expect update_config not to be called
    mock.assert_not_called()

    wsgi_app.call_method(
        "post",
        base + "/domain-types/host_config/collections/all",
        params='{"host_name": "foobar", "folder": "/"}',
        status=200,
        content_type="application/json",
        headers={"Accept": "application/json"},
    )
    # we have a post request, so we expect update_config to be called
    mock.assert_called_once()


def test_no_config_generation_on_certain_posts(
    wsgi_app,
    with_automation_user,
    mock_livestatus,
    with_host,
    monkeypatch,
    mocker,
):
    """
    update_config_generation should not be called on certain posts: SUP-8793
    """
    live: MockLiveStatusConnection = mock_livestatus
    username, secret = with_automation_user
    wsgi_app.set_authorization(("Bearer", username + " " + secret))
    base = "/NO_SITE/check_mk/api/1.0"

    live.add_table(
        "hosts",
        [
            {
                "name": "heute",
                "state": 1,
            },
        ],
        site="NO_SITE",
    )

    live.expect_query("GET hosts\nColumns: name\nFilter: name = heute")
    live.expect_query("GET hosts\nColumns: state\nFilter: name = heute")
    live.expect_query("GET hosts\nColumns: name\nFilter: name = heute")
    live.expect_query(
        "COMMAND [...] ACKNOWLEDGE_HOST_PROBLEM;heute;2;1;0;test123-...;unittesting",
        match_type="ellipsis",
    )

    mock = mocker.Mock()
    monkeypatch.setattr(
        cmk.gui.plugins.openapi.restful_objects.decorators,
        "activate_changes_update_config_generation",
        mock,
    )

    with live:
        wsgi_app.call_method(
            "post",
            base + "/domain-types/acknowledge/collections/host",
            content_type="application/json",
            params=json.dumps(
                {
                    "acknowledge_type": "host",
                    "comment": "unittesting",
                    "host_name": "heute",
                }
            ),
            headers={"Accept": "application/json"},
            status=204,
        )
    # we have a post request, but explitily said so in the endpoint to not update_config,
    # so we expect update_config not to be called
    mock.assert_not_called()
