#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import re
import uuid

import pytest

from tests.unit.cmk.gui.conftest import WebTestAppForCMK

from cmk.gui.fields import FOLDER_PATTERN, FolderField
from cmk.gui.fields.utils import BaseSchema


@pytest.mark.parametrize(
    "given, expected",
    [
        ("%%%%", False),
        ("root", False),
        ("/", True),
        ("/foo", True),
        ("/foo/bar", True),
        ("//", False),
        ("///", False),
        ("\\", True),
        ("\\foo", True),
        ("\\foo\\bar", True),
        ("\\\\", False),
        ("\\\\\\", False),
        ("~", True),
        ("~foo", True),
        ("~foo~bar", True),
        ("~~", False),
        ("~~~", False),
        # This really should be false, but it is tricky to implement. Skipped for now.
        # ('/foo~bar\\baz', False),
        ("0123456789ABCDEF0123456789ABCDEF", True),
        ("0123456789ABCDEF0123456789ABCDEFG", False),
        ("0123456789abcdef0123456789abcdef", True),
        ("0123456789abcdef0123456789abcdefg", False),
        ("~DCN~DE.KAE.BS", True),
    ],
)
def test_folder_regexp(given, expected):
    regexp = re.compile(f"(?:^{FOLDER_PATTERN})$")
    match = regexp.findall(given)
    assert bool(match) == expected, match


def test_folder_schema(request_context):
    class FolderSchema(BaseSchema):
        folder = FolderField(required=True)

    schema = FolderSchema()
    assert schema.load({"folder": "/"})["folder"]
    assert schema.load({"folder": "\\"})["folder"]
    assert schema.load({"folder": "~"})["folder"]


def test_openapi_folder_validation(aut_user_auth_wsgi_app: WebTestAppForCMK):
    aut_user_auth_wsgi_app.call_method(
        "post",
        "/NO_SITE/check_mk/api/1.0/domain-types/folder_config/collections/all",
        params='{"name": "new_folder", "title": "foo", "parent": "abababaabababaababababbbabababab"}',
        status=400,
        headers={"Accept": "application/json"},
        content_type="application/json",
    )

    aut_user_auth_wsgi_app.call_method(
        "post",
        "/NO_SITE/check_mk/api/1.0/domain-types/folder_config/collections/all",
        params='{"name": "new_folder", "title": "foo", "parent": "/", "attributes": {"foo": "bar"}}',
        status=400,
        headers={"Accept": "application/json"},
        content_type="application/json",
    )


def test_openapi_folders_recursively(aut_user_auth_wsgi_app: WebTestAppForCMK):
    resp = aut_user_auth_wsgi_app.call_method(
        "get",
        "/NO_SITE/check_mk/api/1.0/domain-types/folder_config/collections/all?recursive=1",
        status=200,
        headers={"Accept": "application/json"},
    )
    assert len(resp.json["value"]) == 1


def test_openapi_folders(aut_user_auth_wsgi_app: WebTestAppForCMK):
    resp = aut_user_auth_wsgi_app.call_method(
        "get",
        "/NO_SITE/check_mk/api/1.0/domain-types/folder_config/collections/all",
        status=200,
        headers={"Accept": "application/json"},
    )
    assert resp.json["value"] == []

    other_folder = aut_user_auth_wsgi_app.call_method(
        "post",
        "/NO_SITE/check_mk/api/1.0/domain-types/folder_config/collections/all",
        params='{"name": "other_folder", "title": "bar", "parent": "/"}',
        status=200,
        headers={"Accept": "application/json"},
        content_type="application/json",
    )

    resp = new_folder = aut_user_auth_wsgi_app.call_method(
        "post",
        "/NO_SITE/check_mk/api/1.0/domain-types/folder_config/collections/all",
        params='{"name": "new_folder", "title": "foo", "parent": "~"}',
        status=200,
        headers={"Accept": "application/json"},
        content_type="application/json",
    )

    aut_user_auth_wsgi_app.call_method(
        "post",
        "/NO_SITE/check_mk/api/1.0/domain-types/folder_config/collections/all",
        params=r'{"name": "sub_folder", "title": "foo", "parent": "~new_folder"}',
        status=200,
        headers={"Accept": "application/json"},
        content_type="application/json",
    )

    # First test without an ETag, fails with 428 (precondition required)
    aut_user_auth_wsgi_app.follow_link(
        resp,
        ".../update",
        status=428,
        headers={"Accept": "application/json"},
        params='{"title": "foobar"}',
        content_type="application/json",
    )
    # First test without the proper ETag, fails with 412 (precondition failed)
    aut_user_auth_wsgi_app.follow_link(
        resp,
        ".../update",
        status=412,
        headers={"Accept": "application/json", "If-Match": "Witty Sensationalist Header!"},
        params='{"title": "foobar"}',
        content_type="application/json",
    )
    # With the right ETag, the operation shall succeed
    resp = aut_user_auth_wsgi_app.follow_link(
        resp,
        ".../update",
        status=200,
        headers={"Accept": "application/json", "If-Match": resp.headers["ETag"]},
        params='{"title": "foobar"}',
        content_type="application/json",
    )
    # Even twice, as this is idempotent.
    resp = aut_user_auth_wsgi_app.follow_link(
        resp,
        ".../update",
        status=200,
        headers={"Accept": "application/json", "If-Match": resp.headers["ETag"]},
        params='{"title": "foobar"}',
        content_type="application/json",
    )

    # Move to the same source should give a 400
    aut_user_auth_wsgi_app.follow_link(
        resp,
        "cmk/move",
        status=400,
        headers={"Accept": "application/json", "If-Match": resp.headers["ETag"]},
        params=json.dumps({"destination": "~"}),
        content_type="application/json",
    )

    # Check that unknown folders also give a 400
    aut_user_auth_wsgi_app.follow_link(
        resp,
        "cmk/move",
        status=400,
        headers={"Accept": "application/json", "If-Match": resp.headers["ETag"]},
        params=json.dumps({"destination": "asdf"}),
        content_type="application/json",
    )

    # Check that moving onto itself gives a 400
    aut_user_auth_wsgi_app.follow_link(
        other_folder,
        "cmk/move",
        status=400,
        headers={"Accept": "application/json", "If-Match": other_folder.headers["ETag"]},
        params=json.dumps({"destination": "~other_folder"}),
        content_type="application/json",
    )

    # Check that moving into it's own subfolder is not possible.
    aut_user_auth_wsgi_app.follow_link(
        new_folder,
        "cmk/move",
        status=400,
        headers={"Accept": "application/json", "If-Match": resp.headers["ETag"]},
        params=json.dumps({"destination": "/new_folder/sub_folder"}),
        content_type="application/json",
    )

    aut_user_auth_wsgi_app.follow_link(
        new_folder,
        "cmk/move",
        status=200,
        headers={"Accept": "application/json", "If-Match": resp.headers["ETag"]},
        params=json.dumps({"destination": "\\other_folder"}),
        content_type="application/json",
    )

    # Delete all folders.
    coll = aut_user_auth_wsgi_app.get(
        "/NO_SITE/check_mk/api/1.0/domain-types/folder_config/collections/all",
        status=200,
        headers={"Accept": "application/json"},
    )
    for entry in coll.json["value"]:
        # Fetch the new E-Tag.
        self_link = [link["href"] for link in entry["links"] if link["rel"] == "self"]
        resp = aut_user_auth_wsgi_app.get(
            self_link[0],
            status=200,
            headers={"Accept": "application/json"},
        )
        # With the right ETag, the operation shall succeed
        aut_user_auth_wsgi_app.follow_link(
            resp,
            ".../delete",
            status=204,
            headers={"Accept": "application/json", "If-Match": resp.headers["ETag"]},
        )


def test_openapi_folder_config_collections(aut_user_auth_wsgi_app: WebTestAppForCMK):
    aut_user_auth_wsgi_app.call_method(
        "post",
        "/NO_SITE/check_mk/api/1.0/domain-types/folder_config/collections/all",
        params='{"name": "new_folder", "title": "foo", "parent": "/"}',
        status=200,
        headers={"Accept": "application/json"},
        content_type="application/json",
    )

    aut_user_auth_wsgi_app.call_method(
        "post",
        "/NO_SITE/check_mk/api/1.0/domain-types/folder_config/collections/all",
        params='{"name": "new_folder", "title": "foo", "parent": "/"}',
        status=400,
        headers={"Accept": "application/json"},
        content_type="application/json",
    )

    aut_user_auth_wsgi_app.call_method(
        "post",
        "/NO_SITE/check_mk/api/1.0/domain-types/host_config/collections/all",
        params='{"host_name": "host-1", "folder": "/new_folder"}',
        status=200,
        headers={"Accept": "application/json"},
        content_type="application/json",
    )
    aut_user_auth_wsgi_app.call_method(
        "post",
        "/NO_SITE/check_mk/api/1.0/domain-types/host_config/collections/all",
        params='{"host_name": "host-2", "folder": "/new_folder"}',
        status=200,
        headers={"Accept": "application/json"},
        content_type="application/json",
    )


def test_openapi_folder_hosts_sub_resource(aut_user_auth_wsgi_app: WebTestAppForCMK, with_host):
    aut_user_auth_wsgi_app.call_method(
        "get",
        "/NO_SITE/check_mk/api/1.0/objects/folder_config/~/collections/hosts",
        status=200,
        headers={"Accept": "application/json"},
    )


def test_openapi_hosts_in_folder_collection(aut_user_auth_wsgi_app: WebTestAppForCMK):
    aut_user_auth_wsgi_app.call_method(
        "post",
        "/NO_SITE/check_mk/api/1.0/domain-types/folder_config/collections/all",
        params='{"name": "new_folder", "title": "foo", "parent": "/"}',
        status=200,
        headers={"Accept": "application/json"},
        content_type="application/json",
    )
    aut_user_auth_wsgi_app.call_method(
        "post",
        "/NO_SITE/check_mk/api/1.0/domain-types/folder_config/collections/all",
        params='{"name": "new_folder", "title": "foo", "parent": "/"}',
        status=400,
        headers={"Accept": "application/json"},
        content_type="application/json",
    )
    aut_user_auth_wsgi_app.call_method(
        "post",
        "/NO_SITE/check_mk/api/1.0/domain-types/host_config/collections/all",
        params='{"host_name": "host-1", "folder": "/new_folder"}',
        status=200,
        headers={"Accept": "application/json"},
        content_type="application/json",
    )
    aut_user_auth_wsgi_app.call_method(
        "post",
        "/NO_SITE/check_mk/api/1.0/domain-types/host_config/collections/all",
        params='{"host_name": "host-2", "folder": "/new_folder"}',
        status=200,
        headers={"Accept": "application/json"},
        content_type="application/json",
    )
    resp = aut_user_auth_wsgi_app.call_method(
        "get",
        "/NO_SITE/check_mk/api/1.0/domain-types/folder_config/collections/all",
        params={"show_hosts": True},
        headers={"Accept": "application/json"},
    )
    hosts_ = resp.json["value"][0]["members"]["hosts"]["value"]
    assert len(hosts_) == 2
    resp = aut_user_auth_wsgi_app.call_method(
        "get",
        "/NO_SITE/check_mk/api/1.0/domain-types/folder_config/collections/all",
        params={"show_hosts": False},
        headers={"Accept": "application/json"},
    )
    assert "hosts" not in resp.json["value"][0]["members"]


def test_openapi_show_hosts_on_folder(aut_user_auth_wsgi_app: WebTestAppForCMK):
    aut_user_auth_wsgi_app.call_method(
        "post",
        "/NO_SITE/check_mk/api/1.0/domain-types/folder_config/collections/all",
        params='{"name": "new_folder", "title": "foo", "parent": "/"}',
        status=200,
        headers={"Accept": "application/json"},
        content_type="application/json",
    )

    resp = aut_user_auth_wsgi_app.call_method(
        "get",
        "/NO_SITE/check_mk/api/1.0/objects/folder_config/~new_folder",
        params={"show_hosts": True},
        status=200,
        headers={"Accept": "application/json"},
    )
    hosts_ = resp.json["members"]["hosts"]
    assert len(hosts_) > 0

    resp = aut_user_auth_wsgi_app.call_method(
        "get",
        "/NO_SITE/check_mk/api/1.0/objects/folder_config/~new_folder",
        params={"show_hosts": False},
        status=200,
        headers={"Accept": "application/json"},
    )
    assert "hosts" not in resp.json["members"]


def test_openapi_missing_folder(aut_user_auth_wsgi_app: WebTestAppForCMK):
    resp = aut_user_auth_wsgi_app.get(
        "/NO_SITE/check_mk/api/1.0/objects/folder_config/asdf" + uuid.uuid4().hex,
        status=404,
        headers={"Accept": "application/json"},
    )
    assert "title" in resp.json


def test_openapi_update_with_invalid_attribute_folder(aut_user_auth_wsgi_app: WebTestAppForCMK):
    resp = aut_user_auth_wsgi_app.call_method(
        "post",
        "/NO_SITE/check_mk/api/1.0/domain-types/folder_config/collections/all",
        params='{"name": "new_folder", "title": "foo", "parent": "/"}',
        status=200,
        headers={"Accept": "application/json"},
        content_type="application/json",
    )

    aut_user_auth_wsgi_app.follow_link(
        resp,
        ".../update",
        status=400,
        params=json.dumps({"title": "foo", "remove_attributes": ["tag_foobar"]}),
        headers={"Accept": "application/json", "If-Match": resp.headers["ETag"]},
        content_type="application/json",
    )


@pytest.mark.usefixtures("suppress_remote_automation_calls")
def test_openapi_bulk_actions_folders(aut_user_auth_wsgi_app: WebTestAppForCMK):
    base = "/NO_SITE/check_mk/api/1.0"

    _resp = aut_user_auth_wsgi_app.call_method(
        "post",
        "/NO_SITE/check_mk/api/1.0/domain-types/folder_config/collections/all",
        params='{"name": "new_folder", "title": "foo", "parent": "/"}',
        status=200,
        headers={"Accept": "application/json"},
        content_type="application/json",
    )

    _resp = aut_user_auth_wsgi_app.call_method(
        "put",
        base + "/domain-types/folder_config/actions/bulk-update/invoke",
        params=json.dumps(
            {
                "entries": [{"folder": "~new_folder", "remove_attributes": ["tag_foobar"]}],
            }
        ),
        status=400,
        headers={"Accept": "application/json"},
        content_type="application/json",
    )

    # add tag_address_family
    aut_user_auth_wsgi_app.call_method(
        "put",
        base + "/domain-types/folder_config/actions/bulk-update/invoke",
        params=json.dumps(
            {
                "entries": [
                    {
                        "folder": "~new_folder",
                        "update_attributes": {"tag_address_family": "ip-v4-only"},
                    }
                ],
            }
        ),
        status=200,
        headers={"Accept": "application/json"},
        content_type="application/json",
    )

    # check label was added
    resp = aut_user_auth_wsgi_app.get(
        base + "/objects/folder_config/~new_folder",
        status=200,
        headers={"Accept": "application/json"},
    )
    assert resp.json["extensions"]["attributes"]["tag_address_family"] == "ip-v4-only"

    # remove tag_address_family
    aut_user_auth_wsgi_app.call_method(
        "put",
        base + "/domain-types/folder_config/actions/bulk-update/invoke",
        params=json.dumps(
            {
                "entries": [{"folder": "~new_folder", "remove_attributes": ["tag_address_family"]}],
            }
        ),
        status=200,
        headers={"Accept": "application/json"},
        content_type="application/json",
    )

    # check label was removed
    resp = aut_user_auth_wsgi_app.get(
        base + "/objects/folder_config/~new_folder",
        headers={"Accept": "application/json"},
        status=200,
    )
    assert "tag_address_family" not in resp.json["extensions"]["attributes"]


@pytest.mark.usefixtures("suppress_remote_automation_calls")
def test_openapi_folder_update(aut_user_auth_wsgi_app: WebTestAppForCMK):
    base = "/NO_SITE/check_mk/api/1.0"

    resp = aut_user_auth_wsgi_app.call_method(
        "post",
        "/NO_SITE/check_mk/api/1.0/domain-types/folder_config/collections/all",
        params='{"name": "new_folder", "title": "fooo", "parent": "/"}',
        status=200,
        headers={"Accept": "application/json"},
        content_type="application/json",
    )

    # make sure we can update a folder without title argument (SUP-7195)
    resp = aut_user_auth_wsgi_app.call_method(
        "put",
        base + "/objects/folder_config/~new_folder",
        params=json.dumps({"update_attributes": {"tag_address_family": "no-ip"}}),
        status=200,
        headers={"Accept": "application/json", "If-Match": resp.headers["ETag"]},
        content_type="application/json",
    )
    # title should not change
    assert resp.json["title"] == "fooo"
    # double check
    resp = aut_user_auth_wsgi_app.follow_link(resp, "self", headers={"Accept": "application/json"})
    assert resp.json["title"] == "fooo"

    # actually change the title
    resp = aut_user_auth_wsgi_app.call_method(
        "put",
        base + "/objects/folder_config/~new_folder",
        params=json.dumps(
            {
                "title": "fo",
            }
        ),
        status=200,
        headers={"Accept": "application/json", "If-Match": resp.headers["ETag"]},
        content_type="application/json",
    )
    # title should be updated
    assert resp.json["title"] == "fo"
    # double check
    resp = aut_user_auth_wsgi_app.follow_link(resp, "self", headers={"Accept": "application/json"})
    assert resp.json["title"] == "fo"


@pytest.mark.usefixtures("suppress_remote_automation_calls")
def test_openapi_folder_root(aut_user_auth_wsgi_app: WebTestAppForCMK):
    _ = aut_user_auth_wsgi_app.call_method(
        "get",
        "/NO_SITE/check_mk/api/1.0/objects/folder_config/~",
        params={"show_hosts": False},
        headers={"Accept": "application/json"},
        status=200,
    )


def test_openapi_folder_remove_attribute(aut_user_auth_wsgi_app: WebTestAppForCMK):
    resp = aut_user_auth_wsgi_app.call_method(
        "post",
        "/NO_SITE/check_mk/api/1.0/domain-types/folder_config/collections/all",
        params='{"name": "new_folder", "title": "foo", "parent": "/", "attributes": {"tag_address_family": "ip-v6-only"}}',
        headers={"Accept": "application/json"},
        status=200,
        content_type="application/json",
    )

    resp = aut_user_auth_wsgi_app.follow_link(
        resp,
        ".../update",
        status=200,
        params=json.dumps(
            {
                "title": "foo",
                "remove_attributes": ["tag_address_family"],
            }
        ),
        headers={"Accept": "application/json", "If-Match": resp.headers["ETag"]},
        content_type="application/json",
    )
    assert "tag_address_family" not in resp.json["extensions"]["attributes"]
    # make sure changes are written to disk:
    resp = aut_user_auth_wsgi_app.follow_link(
        resp,
        "self",
        status=200,
        headers={"Accept": "application/json"},
    )
    assert "tag_address_family" not in resp.json["extensions"]["attributes"]
