#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import json
from typing import get_args

from werkzeug.test import create_environ

import cmk.gui.openapi.restful_objects.decorators
from cmk.gui.openapi.restful_objects import response_schemas
from cmk.gui.openapi.restful_objects.constructors import (
    absolute_url,
    collection_item,
    collection_property,
    link_rel,
    object_action,
    object_collection,
)
from cmk.gui.openapi.restful_objects.type_defs import StatusCode, StatusCodeInt
from cmk.gui.utils.script_helpers import application_and_request_context
from cmk.utils.livestatus_helpers.testing import MockLiveStatusConnection


def test_absolute_url_http() -> None:
    with application_and_request_context(create_environ(base_url="http://localhost:5000/")):
        assert (
            absolute_url("objects/host_config/example.com")
            == "http://localhost:5000/NO_SITE/check_mk/api/1.0/objects/host_config/example.com"
        )


def test_absolute_url_https() -> None:
    with application_and_request_context(create_environ(base_url="https://localhost:5000/")):
        assert (
            absolute_url("objects/host_config/example.com")
            == "https://localhost:5000/NO_SITE/check_mk/api/1.0/objects/host_config/example.com"
        )


def test_link_rel() -> None:
    expected = {
        "domainType": "link",
        "type": 'application/json;profile="urn:org.restfulobjects:rels/object"',
        "method": "GET",
        "rel": "urn:org.restfulobjects:rels/update",
        "title": "Update the object",
        "href": "https://localhost:5000/NO_SITE/check_mk/api/1.0/objects/foo/update",
    }
    with application_and_request_context(create_environ(base_url="https://localhost:5000/")):
        link = link_rel(
            ".../update",
            "/objects/foo/update",
            method="get",
            profile=".../object",
            title="Update the object",
        )
        assert link == expected, link


def test_object_action() -> None:
    with application_and_request_context():
        action = object_action("move", {"from": "to"}, "")
        assert len(action["links"]) > 0


def test_object_collection() -> None:
    expected = {
        "id": "all",
        "memberType": "collection",
        "value": [],
        "links": [
            {
                "rel": "self",
                "href": "https://localhost:5000/NO_SITE/check_mk/api/1.0/domain-types/host/collections/all",
                "method": "GET",
                "type": "application/json",
                "domainType": "link",
            }
        ],
    }
    with application_and_request_context(create_environ(base_url="https://localhost:5000/")):
        result = object_collection("all", "host", [], "")
        assert result == expected, result


def test_collection_property() -> None:
    with application_and_request_context(create_environ(base_url="http://localhost:5000/")):
        _base = "/objects/host_config/example.com"
        _hosts = [{"name": "host1"}, {"name": "host2"}]
        result = collection_property("hosts", _hosts, _base)
        assert result == {
            "id": "hosts",
            "memberType": "collection",
            "value": [{"name": "host1"}, {"name": "host2"}],
            "links": [
                {
                    "rel": "self",
                    "href": "http://localhost:5000/NO_SITE/check_mk/api/1.0/objects/host_config/example.com/collections/hosts",
                    "method": "GET",
                    "type": "application/json",
                    "domainType": "link",
                }
            ],
        }, result


def test_collection_item() -> None:
    expected = {
        "domainType": "link",
        "href": "https://localhost:5000/NO_SITE/check_mk/api/1.0/objects/folder_config/3",
        "method": "GET",
        "rel": 'urn:org.restfulobjects:rels/value;collection="all"',
        "title": "Foo",
        "type": 'application/json;profile="urn:org.restfulobjects:rels/object"',
    }
    with application_and_request_context(create_environ(base_url="https://localhost:5000/")):
        res = collection_item("folder_config", identifier="3", title="Foo")
        assert res == expected, res


def test_domain_object() -> None:
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


def test_status_codes_match() -> None:
    assert set(get_args(StatusCodeInt)) == {int(sc) for sc in get_args(StatusCode)}


def test_no_config_generation_on_get(
    aut_user_auth_wsgi_app,
    with_host,
    monkeypatch,
    mocker,
):
    """
    update_config_generation should only be called on posts, not on gets: SUP-8793
    """
    base = "/NO_SITE/check_mk/api/1.0"

    mock = mocker.Mock()
    monkeypatch.setattr(
        cmk.gui.openapi.restful_objects.decorators,
        "activate_changes_update_config_generation",
        mock,
    )

    aut_user_auth_wsgi_app.call_method(
        "get",
        base + "/objects/host_config/heute",
        status=200,
        headers={"Accept": "application/json"},
    )
    # we have a get request, so we expect update_config not to be called
    mock.assert_not_called()

    aut_user_auth_wsgi_app.call_method(
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
    aut_user_auth_wsgi_app,
    mock_livestatus,
    with_host,
    monkeypatch,
    mocker,
):
    """
    update_config_generation should not be called on certain posts: SUP-8793
    """
    live: MockLiveStatusConnection = mock_livestatus
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
        cmk.gui.openapi.restful_objects.decorators,
        "activate_changes_update_config_generation",
        mock,
    )

    with live:
        aut_user_auth_wsgi_app.call_method(
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
