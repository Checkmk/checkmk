#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import re
import uuid
from ast import literal_eval
from typing import Sequence

import pytest

from tests.unit.cmk.gui.conftest import WebTestAppForCMK

from cmk.utils import paths, version

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
        ("/foo/bar/", True),
        ("//", False),
        ("///", False),
        ("\\", True),
        ("\\foo", True),
        ("\\foo\\bar", True),
        ("\\foo\\bar\\", True),
        ("\\\\", False),
        ("\\\\\\", False),
        ("~", True),
        ("~foo", True),
        ("~foo~bar", True),
        ("~foo~bar~", True),
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


def _create_criticality_tag(aut_user_auth_wsgi_app: WebTestAppForCMK) -> None:
    aut_user_auth_wsgi_app.call_method(
        "post",
        "/NO_SITE/check_mk/api/1.0/domain-types/host_tag_group/collections/all",
        params=json.dumps(
            {
                "ident": "criticality",
                "title": "criticality",
                "topic": "nothing",
                "tags": [
                    {
                        "ident": "discovered",
                        "title": "discovered",
                    }
                ],
            }
        ),
        headers={"Accept": "application/json"},
        status=200,
        content_type="application/json",
    )


def test_openapi_create_folder_with_network_scan(
    aut_user_auth_wsgi_app: WebTestAppForCMK, with_automation_user: tuple[str, str]
) -> None:
    _create_criticality_tag(aut_user_auth_wsgi_app)
    user, _ = with_automation_user
    aut_user_auth_wsgi_app.call_method(
        "post",
        "/NO_SITE/check_mk/api/1.0/domain-types/folder_config/collections/all",
        params=json.dumps(
            dict(
                name="my_folder_name",
                title="some title",
                parent="~",
                attributes=dict(
                    network_scan={
                        "addresses": [
                            {"type": "network_range", "network": "172.10.9.0/24"},
                            {
                                "addresses": ["10.10.10.10", "10.10.10.9"],
                                "type": "explicit_addresses",
                            },
                            {
                                "from_address": "192.168.178.10",
                                "to_address": "192.168.178.20",
                                "type": "address_range",
                            },
                        ],
                        "exclude_addresses": [
                            {"regexp_list": ["some_pattern"], "type": "exclude_by_regexp"}
                        ],
                        "scan_interval": 86400,
                        "time_allowed": [{"start": "00:00:00", "end": "23:00:00"}],
                        "set_ip_address": True,
                        "tag_criticality": "discovered",
                        "run_as": user,
                        "translate_names": {"drop_domain": True, "convert_case": "lower"},
                    }
                ),
            )
        ),
        status=200,
        headers={"Accept": "application/json"},
        content_type="application/json",
    )
    path = paths.omd_root / "etc/check_mk/conf.d/wato/my_folder_name/.wato"
    with path.open() as fo:
        result = literal_eval(fo.read())
    assert user == result["attributes"]["network_scan"].pop("run_as")
    assert result["attributes"]["network_scan"] == {
        "exclude_ranges": [("ip_regex_list", ["some_pattern"])],
        "ip_ranges": [
            ("ip_network", ("172.10.9.0", 24)),
            ("ip_list", ["10.10.10.10", "10.10.10.9"]),
            ("ip_range", ("192.168.178.10", "192.168.178.20")),
        ],
        "max_parallel_pings": 100,
        "scan_interval": 86400,
        "set_ipaddress": True,
        "time_allowed": [((0, 0), (23, 0))],
        "tag_criticality": "discovered",
        "translate_names": {"case": "lower", "drop_domain": True},
    }


def test_openapi_show_folder_with_network_scan_result(
    aut_user_auth_wsgi_app: WebTestAppForCMK, with_automation_user: tuple[str, str]
) -> None:
    _create_criticality_tag(aut_user_auth_wsgi_app)
    path = paths.omd_root / "etc/check_mk/conf.d/wato/my_folder_name/.wato"
    path.parent.mkdir(parents=True, exist_ok=True)
    user, _ = with_automation_user
    with path.open("w") as fo:
        fo.write(
            str(
                {
                    "title": "Clients (9)",
                    "attributes": {
                        "network_scan": {
                            "ip_ranges": [
                                ("ip_network", ("172.10.9.0", 24)),
                                ("ip_list", ["10.10.10.10", "10.10.10.9"]),
                                ("ip_range", ("192.168.178.10", "192.168.178.20")),
                            ],
                            "exclude_ranges": [("ip_regex_list", ["some_pattern"])],
                            "scan_interval": 86400,
                            "time_allowed": [((0, 0), (23, 0))],
                            "set_ipaddress": True,
                            "tag_criticality": "discovered",
                            "run_as": user,
                            "translate_names": {"drop_domain": True, "case": "lower"},
                        },
                        "network_scan_result": {
                            "start": 1661972701.0,
                            "end": 1661972713.0,
                            "state": True,
                            "output": "The network scan found 10 new hosts.",
                        },
                        "meta_data": {
                            "created_at": 1635451787.0,
                            "created_by": user,
                            "updated_at": 1661980583.1332564,
                        },
                    },
                    "num_hosts": 40,
                    "lock": False,
                    "lock_subfolders": False,
                    "__id": "cf2b6294fec34e57af4a164ee99134d7",
                }
            )
        )
    resp = aut_user_auth_wsgi_app.call_method(
        "get",
        "/NO_SITE/check_mk/api/1.0/domain-types/folder_config/collections/all",
        params={"show_hosts": False},
        headers={"Accept": "application/json"},
    )
    assert resp.json["value"][0]["extensions"] == {
        "path": "/my_folder_name",
        "attributes": {
            "network_scan": {
                "addresses": [
                    {"type": "network_range", "network": "172.10.9.0/24"},
                    {
                        "addresses": ["10.10.10.10", "10.10.10.9"],
                        "type": "explicit_addresses",
                    },
                    {
                        "from_address": "192.168.178.10",
                        "to_address": "192.168.178.20",
                        "type": "address_range",
                    },
                ],
                "exclude_addresses": [
                    {"regexp_list": ["some_pattern"], "type": "exclude_by_regexp"}
                ],
                "scan_interval": 86400,
                "time_allowed": [{"start": "00:00:00", "end": "23:00:00"}],
                "set_ip_address": True,
                "tag_criticality": "discovered",
                "run_as": user,
                "translate_names": {"convert_case": "lower", "drop_domain": True},
            },
            "network_scan_result": {
                "start": "2022-08-31T19:05:01+00:00",
                "end": "2022-08-31T19:05:13+00:00",
                "state": "succeeded",
                "output": "The network scan found 10 new hosts.",
            },
            "meta_data": {
                "created_at": "2021-10-28T20:09:47+00:00",
                "updated_at": "2022-08-31T21:16:23.133256+00:00",
                "created_by": user,
            },
        },
    }


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


def test_openapi_folder_config_collections_recursive_list(aut_user_auth_wsgi_app: WebTestAppForCMK):
    def _create_folder(fname: str, parent: str):
        params = f'{{"name": "{fname}", "title": "{fname}", "parent": "{parent}"}}'
        aut_user_auth_wsgi_app.call_method(
            "post",
            "/NO_SITE/check_mk/api/1.0/domain-types/folder_config/collections/all",
            params=params,
            status=200,
            headers={"Accept": "application/json"},
            content_type="application/json",
        )
        parent += f"{fname}~"

    def _create_folders_recursive(folders: Sequence[str]):
        _create_folder(folders[0], "~")
        parent = f"~{folders[0]}"
        for fname in folders[1:]:
            _create_folder(fname, parent)
            parent += f"~{fname}"

    _create_folders_recursive(["I", "want", "those"])
    _create_folders_recursive(["na", "na", "batman"])

    response = aut_user_auth_wsgi_app.call_method(
        "get",
        "/NO_SITE/check_mk/api/1.0/domain-types/folder_config/collections/all",
        params={"parent": "~I", "recursive": "True"},
        status=200,
        headers={"Accept": "application/json"},
    )

    for folder in response.json["value"]:
        assert "batman" not in folder["id"]


@pytest.mark.skipif(version.is_raw_edition(), reason="Tested Attribute is not in RAW")
def test_bake_agent_package_attribute_regression(
    base: str, aut_user_auth_wsgi_app: WebTestAppForCMK
) -> None:
    folder_name = "blablabla"

    aut_user_auth_wsgi_app.post(
        url=base + "/domain-types/folder_config/collections/all",
        params=json.dumps(
            {
                "name": folder_name,
                "title": folder_name,
                "parent": "~",
                "attributes": {"bake_agent_package": True},
            }
        ),
        headers={"Accept": "application/json"},
        content_type="application/json",
        status=200,
    )

    # see if we get an outbound validation error on a single folder
    aut_user_auth_wsgi_app.get(
        url=base + "/objects/folder_config/~" + folder_name,
        headers={"Accept": "application/json"},
        status=200,
    )

    # see if we get an outbound validation error on all folders
    aut_user_auth_wsgi_app.get(
        url=base + "/domain-types/folder_config/collections/all",
        headers={"Accept": "application/json"},
        status=200,
    )
