#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json

import pytest

from cmk.automations.results import DeleteHostsResult, RenameHostsResult


@pytest.mark.usefixtures("with_host")
def test_openapi_cluster_host(
    wsgi_app,
    with_automation_user,
):
    username, secret = with_automation_user
    wsgi_app.set_authorization(("Bearer", username + " " + secret))

    base = "/NO_SITE/check_mk/api/1.0"

    wsgi_app.call_method(
        "post",
        base + "/domain-types/host_config/collections/all",
        params='{"host_name": "foobar", "folder": "/"}',
        status=200,
        content_type="application/json; charset=utf-8",
    )

    wsgi_app.call_method(
        "post",
        base + "/domain-types/host_config/collections/clusters",
        params='{"host_name": "bazfoo", "folder": "/", "nodes": ["foobar"]}',
        status=200,
        content_type='application/json; charset="utf-8"',
    )

    wsgi_app.call_method(
        "get",
        base + "/objects/host_config/bazfoozle",
        status=404,
    )

    resp = wsgi_app.call_method(
        "get",
        base + "/objects/host_config/bazfoo",
        status=200,
    )

    wsgi_app.call_method(
        "put",
        base + "/objects/host_config/bazfoo/properties/nodes",
        params='{"nodes": ["not_existing"]}',
        status=400,
        headers={"If-Match": resp.headers["ETag"]},
        content_type="application/json",
    )

    wsgi_app.call_method(
        "put",
        base + "/objects/host_config/bazfoo/properties/nodes",
        params='{"nodes": ["example.com", "bazfoo"]}',
        status=400,
        headers={"If-Match": resp.headers["ETag"]},
        content_type="application/json",
    )

    wsgi_app.call_method(
        "put",
        base + "/objects/host_config/bazfoo/properties/nodes",
        params='{"nodes": ["example.com"]}',
        status=200,
        headers={"If-Match": resp.headers["ETag"]},
        content_type="application/json",
    )

    resp = wsgi_app.call_method(
        "get",
        base + "/objects/host_config/bazfoo",
        status=200,
    )
    assert resp.json["extensions"]["cluster_nodes"] == ["example.com"]


def test_openapi_hosts(
    monkeypatch: pytest.MonkeyPatch,
    wsgi_app,
    with_automation_user,
):

    username, secret = with_automation_user
    wsgi_app.set_authorization(("Bearer", username + " " + secret))

    base = "/NO_SITE/check_mk/api/1.0"

    resp = wsgi_app.call_method(
        "post",
        base + "/domain-types/host_config/collections/all",
        params='{"host_name": "foobar", "folder": "/"}',
        status=200,
        content_type="application/json",
    )

    resp = wsgi_app.follow_link(
        resp,
        "self",
        status=200,
    )

    attributes = {
        "ipaddress": "127.0.0.1",
        "snmp_community": {
            "type": "v1_v2_community",
            "community": "blah",
        },
    }
    resp = wsgi_app.follow_link(
        resp,
        ".../update",
        status=200,
        params=json.dumps({"attributes": attributes}),
        headers={"If-Match": resp.headers["ETag"]},
        content_type="application/json",
    )
    got_attributes = resp.json["extensions"]["attributes"]
    assert attributes.items() <= got_attributes.items()  # pylint: disable=dict-items-not-iterating

    resp = wsgi_app.follow_link(
        resp,
        ".../update",
        status=200,
        params='{"update_attributes": {"alias": "bar"}}',
        headers={"If-Match": resp.headers["ETag"]},
        content_type="application/json",
    )
    assert resp.json["extensions"]["attributes"]["alias"] == "bar"

    resp = wsgi_app.follow_link(
        resp,
        ".../update",
        status=200,
        params='{"remove_attributes": ["alias"]}',
        headers={"If-Match": resp.headers["ETag"]},
        content_type="application/json",
    )
    assert (
        resp.json["extensions"]["attributes"].items() >= {"ipaddress": "127.0.0.1"}.items()
    )  # pylint: disable=dict-items-not-iterating

    # make sure changes are written to disk:
    resp = wsgi_app.follow_link(resp, "self", status=200)
    assert (
        resp.json["extensions"]["attributes"].items() >= {"ipaddress": "127.0.0.1"}.items()
    )  # pylint: disable=dict-items-not-iterating

    # also try to update with wrong attribute
    wsgi_app.follow_link(
        resp,
        ".../update",
        status=400,
        params='{"attributes": {"foobaz": "bar"}}',
        headers={"If-Match": resp.headers["ETag"]},
        content_type="application/json",
    )

    monkeypatch.setattr(
        "cmk.gui.watolib.hosts_and_folders.delete_hosts",
        lambda *args, **kwargs: DeleteHostsResult(),
    )
    wsgi_app.follow_link(
        resp,
        ".../delete",
        status=204,
        content_type="application/json",
    )


def test_openapi_bulk_hosts(
    monkeypatch: pytest.MonkeyPatch,
    wsgi_app,
    with_automation_user,
):
    monkeypatch.setattr(
        "cmk.gui.watolib.hosts_and_folders.delete_hosts",
        lambda *args, **kwargs: DeleteHostsResult(),
    )

    username, secret = with_automation_user
    wsgi_app.set_authorization(("Bearer", username + " " + secret))

    base = "/NO_SITE/check_mk/api/1.0"

    resp = wsgi_app.call_method(
        "post",
        base + "/domain-types/host_config/actions/bulk-create/invoke",
        params=json.dumps(
            {
                "entries": [
                    {
                        "host_name": "foobar",
                        "folder": "/",
                        "attributes": {"ipaddress": "127.0.0.2"},
                    },
                    {
                        "host_name": "sample",
                        "folder": "/",
                        "attributes": {
                            "ipaddress": "127.0.0.2",
                            "site": "NO_SITE",
                        },
                    },
                ]
            }
        ),
        status=200,
        content_type="application/json",
    )
    assert len(resp.json["value"]) == 2

    _resp = wsgi_app.call_method(
        "put",
        base + "/domain-types/host_config/actions/bulk-update/invoke",
        params=json.dumps(
            {
                "entries": [
                    {
                        "host_name": "foobar",
                        "attributes": {
                            "ipaddress": "192.168.1.1",
                            "tag_address_family": "ip-v4-only",
                        },
                    }
                ],
            }
        ),
        status=200,
        content_type="application/json",
    )

    # verify attribute ipaddress is set corretly
    resp = wsgi_app.call_method(
        "get",
        base + "/objects/host_config/foobar",
        status=200,
    )
    assert resp.json["extensions"]["attributes"]["ipaddress"] == "192.168.1.1"

    # remove attribute ipaddress via bulk request
    wsgi_app.call_method(
        "put",
        base + "/domain-types/host_config/actions/bulk-update/invoke",
        params=json.dumps(
            {
                "entries": [{"host_name": "foobar", "remove_attributes": ["ipaddress"]}],
            }
        ),
        status=200,
        content_type="application/json",
    )

    # verify attribute ipaddress was removed correctly
    resp = wsgi_app.call_method(
        "get",
        base + "/objects/host_config/foobar",
        status=200,
    )
    assert "ipaddress" not in resp.json["extensions"]["attributes"]

    # adding invalid attribute should fail
    _resp = wsgi_app.call_method(
        "put",
        base + "/domain-types/host_config/actions/bulk-update/invoke",
        params=json.dumps(
            {
                "entries": [{"host_name": "foobar", "attributes": {"foobaz": "bar"}}],
            }
        ),
        status=400,
        content_type="application/json",
    )

    _resp = wsgi_app.call_method(
        "post",
        base + "/domain-types/host_config/actions/bulk-delete/invoke",
        params=json.dumps({"entries": ["foobar", "sample"]}),
        status=204,
        content_type="application/json",
    )


def test_openapi_bulk_simple(wsgi_app, with_automation_user, suppress_automation_calls):
    username, secret = with_automation_user
    wsgi_app.set_authorization(("Bearer", username + " " + secret))

    base = "/NO_SITE/check_mk/api/1.0"

    wsgi_app.call_method(
        "post",
        base + "/domain-types/host_config/actions/bulk-create/invoke",
        params=json.dumps(
            {"entries": [{"host_name": "example.com", "folder": "/", "attributes": {}}]}
        ),
        status=200,
        content_type="application/json",
    )


def test_openapi_host_rename(
    wsgi_app,
    with_automation_user,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr("cmk.gui.watolib.activate_changes.get_pending_changes_info", lambda: [])
    monkeypatch.setattr(
        "cmk.gui.watolib.host_rename.rename_hosts",
        lambda *args, **kwargs: RenameHostsResult({}),
    )

    username, secret = with_automation_user
    wsgi_app.set_authorization(("Bearer", username + " " + secret))

    base = "/NO_SITE/check_mk/api/1.0"

    wsgi_app.call_method(
        "post",
        base + "/domain-types/host_config/collections/all",
        params='{"host_name": "foobar", "folder": "/"}',
        status=200,
        content_type="application/json",
    )

    resp = wsgi_app.call_method(
        "get",
        base + "/objects/host_config/foobar",
        status=200,
    )

    _resp = wsgi_app.call_method(
        "put",
        base + "/objects/host_config/foobar/actions/rename/invoke",
        params='{"new_name": "foobaz"}',
        content_type="application/json",
        headers={"If-Match": resp.headers["ETag"]},
        status=200,
    )

    _resp = wsgi_app.call_method(
        "get",
        base + "/objects/host_config/foobaz",
        status=200,
    )


def test_openapi_host_rename_error_on_not_existing_host(
    wsgi_app,
    with_automation_user,
    suppress_automation_calls,
    monkeypatch,
):
    monkeypatch.setattr("cmk.gui.watolib.activate_changes.get_pending_changes_info", lambda: [])
    username, secret = with_automation_user
    wsgi_app.set_authorization(("Bearer", username + " " + secret))

    base = "/NO_SITE/check_mk/api/1.0"

    wsgi_app.call_method(
        "post",
        base + "/domain-types/host_config/collections/all",
        params='{"host_name": "foobar", "folder": "/"}',
        status=200,
        content_type="application/json",
    )

    resp = wsgi_app.call_method(
        "get",
        base + "/objects/host_config/foobar",
        status=200,
    )

    _resp = wsgi_app.call_method(
        "put",
        base + "/objects/host_config/fooba/actions/rename/invoke",
        params='{"new_name": "foobaz"}',
        content_type="application/json",
        headers={"If-Match": resp.headers["ETag"]},
        status=404,
    )


def test_openapi_host_rename_on_invalid_hostname(
    wsgi_app,
    with_automation_user,
    suppress_automation_calls,
    monkeypatch,
):
    monkeypatch.setattr("cmk.gui.watolib.activate_changes.get_pending_changes_info", lambda: [])
    username, secret = with_automation_user
    wsgi_app.set_authorization(("Bearer", username + " " + secret))

    base = "/NO_SITE/check_mk/api/1.0"

    wsgi_app.call_method(
        "post",
        base + "/domain-types/host_config/collections/all",
        params='{"host_name": "foobar", "folder": "/"}',
        status=200,
        content_type="application/json",
    )

    resp = wsgi_app.call_method(
        "get",
        base + "/objects/host_config/foobar",
        status=200,
    )

    _resp = wsgi_app.call_method(
        "put",
        base + "/objects/host_config/foobar/actions/rename/invoke",
        params='{"new_name": "foobar"}',
        content_type="application/json",
        headers={"If-Match": resp.headers["ETag"]},
        status=400,
    )


def test_openapi_host_rename_with_pending_activate_changes(
    wsgi_app,
    with_automation_user,
    suppress_automation_calls,
):
    username, secret = with_automation_user
    wsgi_app.set_authorization(("Bearer", username + " " + secret))

    base = "/NO_SITE/check_mk/api/1.0"

    wsgi_app.call_method(
        "post",
        base + "/domain-types/host_config/collections/all",
        params='{"host_name": "foobar", "folder": "/"}',
        status=200,
        content_type="application/json",
    )

    resp = wsgi_app.call_method(
        "get",
        base + "/objects/host_config/foobar",
        status=200,
    )

    _resp = wsgi_app.call_method(
        "put",
        base + "/objects/host_config/foobar/actions/rename/invoke",
        params='{"new_name": "foobaz"}',
        content_type="application/json",
        headers={"If-Match": resp.headers["ETag"]},
        status=409,
    )


def test_openapi_host_move(
    wsgi_app,
    with_automation_user,
    suppress_automation_calls,
):
    username, secret = with_automation_user
    wsgi_app.set_authorization(("Bearer", username + " " + secret))

    base = "/NO_SITE/check_mk/api/1.0"

    wsgi_app.call_method(
        "post",
        base + "/domain-types/host_config/collections/all",
        params='{"host_name": "foobar", "folder": "/"}',
        status=200,
        content_type="application/json",
    )

    resp = wsgi_app.call_method(
        "post",
        base + "/domain-types/folder_config/collections/all",
        params='{"name": "new_folder", "title": "foo", "parent": "/"}',
        content_type="application/json",
        status=200,
    )

    _resp = wsgi_app.call_method(
        "post",
        base + "/objects/host_config/foobar/actions/move/invoke",
        params='{"target_folder": "/new_folder"}',
        headers={"If-Match": resp.headers["ETag"]},
        content_type="application/json",
        status=200,
    )


def test_openapi_host_move_to_non_valid_folder(
    wsgi_app,
    with_automation_user,
    suppress_automation_calls,
):
    username, secret = with_automation_user
    wsgi_app.set_authorization(("Bearer", username + " " + secret))

    base = "/NO_SITE/check_mk/api/1.0"

    wsgi_app.call_method(
        "post",
        base + "/domain-types/host_config/collections/all",
        params='{"host_name": "foobar", "folder": "/"}',
        status=200,
        content_type="application/json",
    )

    resp = wsgi_app.call_method(
        "post",
        base + "/domain-types/folder_config/collections/all",
        params='{"name": "new_folder", "title": "foo", "parent": "/"}',
        content_type="application/json",
        status=200,
    )

    _resp = wsgi_app.call_method(
        "post",
        base + "/objects/host_config/foobar/actions/move/invoke",
        params='{"target_folder": "/"}',
        headers={"If-Match": resp.headers["ETag"]},
        content_type="application/json",
        status=400,
    )


def test_openapi_host_move_of_non_existing_host(
    wsgi_app,
    with_automation_user,
    suppress_automation_calls,
):
    username, secret = with_automation_user
    wsgi_app.set_authorization(("Bearer", username + " " + secret))

    base = "/NO_SITE/check_mk/api/1.0"

    _resp = wsgi_app.call_method(
        "post",
        base + "/objects/host_config/foobaz/actions/move/invoke",
        params='{"target_folder": "/"}',
        content_type="application/json",
        status=404,
    )


def test_openapi_host_update_invalid(
    wsgi_app,
    with_automation_user,
    suppress_automation_calls,
):
    username, secret = with_automation_user
    wsgi_app.set_authorization(("Bearer", username + " " + secret))

    base = "/NO_SITE/check_mk/api/1.0"

    resp = wsgi_app.call_method(
        "post",
        base + "/domain-types/host_config/collections/all",
        params='{"host_name": "example.com", "folder": "/"}',
        status=200,
        content_type="application/json",
    )

    wsgi_app.follow_link(
        resp,
        ".../update",
        status=400,
        params=json.dumps(
            {
                "attributes": {"ipaddress": "192.168.0.123"},
                "update_attributes": {"ipaddress": "192.168.0.123"},
                "remove_attributes": ["tag_foobar"],
            }
        ),
        headers={"If-Match": resp.headers["ETag"]},
        content_type="application/json",
    )
