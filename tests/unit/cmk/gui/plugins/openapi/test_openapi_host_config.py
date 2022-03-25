#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture

from tests.unit.cmk.gui.conftest import WebTestAppForCMK

from cmk.utils import version

from cmk.automations.results import DeleteHostsResult, RenameHostsResult

from cmk.gui.type_defs import CustomAttr
from cmk.gui.watolib.custom_attributes import save_custom_attrs_to_mk_file

managedtest = pytest.mark.skipif(not version.is_managed_edition(), reason="see #7213")


@pytest.fixture(name="base")
def fixture_base() -> str:
    return "/NO_SITE/check_mk/api/1.0"


@pytest.mark.usefixtures("with_host")
def test_openapi_cluster_host(base: str, aut_user_auth_wsgi_app: WebTestAppForCMK) -> None:
    aut_user_auth_wsgi_app.call_method(
        "post",
        base + "/domain-types/host_config/collections/all",
        params='{"host_name": "foobar", "folder": "/"}',
        status=200,
        headers={"Accept": "application/json"},
        content_type="application/json; charset=utf-8",
    )

    aut_user_auth_wsgi_app.call_method(
        "post",
        base + "/domain-types/host_config/collections/clusters",
        params='{"host_name": "bazfoo", "folder": "/", "nodes": ["foobar"]}',
        status=200,
        headers={"Accept": "application/json"},
        content_type='application/json; charset="utf-8"',
    )

    aut_user_auth_wsgi_app.call_method(
        "get",
        base + "/objects/host_config/bazfoozle",
        status=404,
        headers={"Accept": "application/json"},
    )

    resp = aut_user_auth_wsgi_app.call_method(
        "get",
        base + "/objects/host_config/bazfoo",
        status=200,
        headers={"Accept": "application/json"},
    )

    aut_user_auth_wsgi_app.call_method(
        "put",
        base + "/objects/host_config/bazfoo/properties/nodes",
        params='{"nodes": ["not_existing"]}',
        status=400,
        headers={"Accept": "application/json", "If-Match": resp.headers["ETag"]},
        content_type="application/json",
    )

    aut_user_auth_wsgi_app.call_method(
        "put",
        base + "/objects/host_config/bazfoo/properties/nodes",
        params='{"nodes": ["example.com", "bazfoo"]}',
        status=400,
        headers={"Accept": "application/json", "If-Match": resp.headers["ETag"]},
        content_type="application/json",
    )

    aut_user_auth_wsgi_app.call_method(
        "put",
        base + "/objects/host_config/bazfoo/properties/nodes",
        params='{"nodes": ["example.com"]}',
        status=200,
        headers={"Accept": "application/json", "If-Match": resp.headers["ETag"]},
        content_type="application/json",
    )

    resp = aut_user_auth_wsgi_app.call_method(
        "get",
        base + "/objects/host_config/bazfoo",
        status=200,
        headers={"Accept": "application/json"},
    )
    assert resp.json["extensions"]["cluster_nodes"] == ["example.com"]


@pytest.fixture(name="try_bake_agents_for_hosts")
def fixture_try_bake_agents_for_hosts(mocker: MockerFixture) -> MagicMock:
    return mocker.patch(
        "cmk.gui.watolib.hosts_and_folders.try_bake_agents_for_hosts",
        side_effect=lambda _hosts: None,
    )


@pytest.mark.parametrize(
    "query,called",
    [
        ("?bake_agent=1", True),
        ("?bake_agent=0", False),
        ("", False),
    ],
)
def test_openapi_add_host_bake_agent_parameter(
    base: str,
    query: str,
    called: bool,
    aut_user_auth_wsgi_app: WebTestAppForCMK,
    try_bake_agents_for_hosts: MagicMock,
) -> None:
    aut_user_auth_wsgi_app.call_method(
        "post",
        f"{base}/domain-types/host_config/collections/all{query}",
        params='{"host_name": "foobar", "folder": "/"}',
        status=200,
        headers={"Accept": "application/json"},
        content_type="application/json; charset=utf-8",
    )
    if called:
        try_bake_agents_for_hosts.assert_called_once_with(["foobar"])
    else:
        try_bake_agents_for_hosts.assert_not_called()


@pytest.mark.parametrize(
    "query,called",
    [
        ("?bake_agent=1", True),
        ("?bake_agent=0", False),
        ("", False),
    ],
)
def test_openapi_add_cluster_bake_agent_parameter(
    base: str,
    query: str,
    called: bool,
    aut_user_auth_wsgi_app: WebTestAppForCMK,
    try_bake_agents_for_hosts: MagicMock,
) -> None:
    aut_user_auth_wsgi_app.call_method(
        "post",
        f"{base}/domain-types/host_config/collections/all{query}",
        params='{"host_name": "foobar", "folder": "/"}',
        status=200,
        headers={"Accept": "application/json"},
        content_type="application/json; charset=utf-8",
    )

    if called:
        try_bake_agents_for_hosts.assert_called_once_with(["foobar"])
    else:
        try_bake_agents_for_hosts.assert_not_called()
    try_bake_agents_for_hosts.reset_mock()

    aut_user_auth_wsgi_app.call_method(
        "post",
        f"{base}/domain-types/host_config/collections/clusters{query}",
        params='{"host_name": "bazfoo", "folder": "/", "nodes": ["foobar"]}',
        status=200,
        headers={"Accept": "application/json"},
        content_type='application/json; charset="utf-8"',
    )

    if called:
        try_bake_agents_for_hosts.assert_called_once_with(["bazfoo"])
    else:
        try_bake_agents_for_hosts.assert_not_called()


@pytest.mark.parametrize(
    "query,called",
    [
        ("?bake_agent=1", True),
        ("?bake_agent=0", False),
        ("", False),
    ],
)
def test_openapi_bulk_add_hosts_bake_agent_parameter(
    base: str,
    query: str,
    called: bool,
    aut_user_auth_wsgi_app: WebTestAppForCMK,
    try_bake_agents_for_hosts: MagicMock,
) -> None:
    resp = aut_user_auth_wsgi_app.call_method(
        "post",
        f"{base}/domain-types/host_config/actions/bulk-create/invoke{query}",
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
        headers={"Accept": "application/json"},
        content_type="application/json",
    )
    assert len(resp.json["value"]) == 2

    if called:
        try_bake_agents_for_hosts.assert_called_once_with(["foobar", "sample"])
    else:
        try_bake_agents_for_hosts.assert_not_called()


def test_openapi_hosts(
    base: str,
    monkeypatch: pytest.MonkeyPatch,
    aut_user_auth_wsgi_app: WebTestAppForCMK,
) -> None:
    resp = aut_user_auth_wsgi_app.call_method(
        "post",
        base + "/domain-types/host_config/collections/all",
        params='{"host_name": "foobar", "folder": "/"}',
        status=200,
        headers={"Accept": "application/json"},
        content_type="application/json",
    )
    assert isinstance(resp.json["extensions"]["attributes"]["meta_data"]["created_at"], str)
    assert isinstance(resp.json["extensions"]["attributes"]["meta_data"]["updated_at"], str)

    resp = aut_user_auth_wsgi_app.follow_link(
        resp,
        "self",
        status=200,
        headers={"Accept": "application/json"},
    )

    attributes = {
        "ipaddress": "127.0.0.1",
        "snmp_community": {
            "type": "v1_v2_community",
            "community": "blah",
        },
    }
    resp = aut_user_auth_wsgi_app.follow_link(
        resp,
        ".../update",
        status=200,
        params=json.dumps({"attributes": attributes}),
        headers={"If-Match": resp.headers["ETag"], "Accept": "application/json"},
        content_type="application/json",
    )
    got_attributes = resp.json["extensions"]["attributes"]
    assert list(attributes.items()) <= list(got_attributes.items())

    resp = aut_user_auth_wsgi_app.follow_link(
        resp,
        ".../update",
        status=200,
        params='{"update_attributes": {"alias": "bar"}}',
        headers={"If-Match": resp.headers["ETag"], "Accept": "application/json"},
        content_type="application/json",
    )
    assert resp.json["extensions"]["attributes"]["alias"] == "bar"

    resp = aut_user_auth_wsgi_app.follow_link(
        resp,
        ".../update",
        status=200,
        params='{"remove_attributes": ["alias"]}',
        headers={"If-Match": resp.headers["ETag"], "Accept": "application/json"},
        content_type="application/json",
    )
    assert list(resp.json["extensions"]["attributes"].items()) >= list(
        {"ipaddress": "127.0.0.1"}.items()
    )
    assert "alias" not in resp.json["extensions"]["attributes"]

    # make sure changes are written to disk:
    resp = aut_user_auth_wsgi_app.follow_link(
        resp,
        "self",
        status=200,
        headers={"Accept": "application/json"},
    )
    assert list(resp.json["extensions"]["attributes"].items()) >= list(
        {"ipaddress": "127.0.0.1"}.items()
    )

    # also try to update with wrong attribute
    aut_user_auth_wsgi_app.follow_link(
        resp,
        ".../update",
        status=400,
        params='{"attributes": {"foobaz": "bar"}}',
        headers={"If-Match": resp.headers["ETag"], "Accept": "application/json"},
        content_type="application/json",
    )

    monkeypatch.setattr(
        "cmk.gui.watolib.hosts_and_folders.delete_hosts",
        lambda *args, **kwargs: DeleteHostsResult(),
    )
    aut_user_auth_wsgi_app.follow_link(
        resp,
        ".../delete",
        status=204,
        headers={"Accept": "application/json"},
        content_type="application/json",
    )


def test_openapi_host_update_after_move(
    aut_user_auth_wsgi_app: WebTestAppForCMK,
    with_host,
):

    aut_user_auth_wsgi_app.post(
        "/NO_SITE/check_mk/api/1.0/domain-types/folder_config/collections/all",
        params='{"name": "new_folder", "title": "bar", "parent": "/"}',
        status=200,
        content_type="application/json",
        headers={
            "Accept": "application/json",
        },
    )

    heute = aut_user_auth_wsgi_app.call_method(
        "get",
        "/NO_SITE/check_mk/api/1.0/objects/host_config/heute",
        headers={
            "Accept": "application/json",
        },
    )

    aut_user_auth_wsgi_app.call_method(
        "post",
        "/NO_SITE/check_mk/api/1.0/objects/host_config/heute/actions/move/invoke",
        params='{"target_folder": "/new_folder"}',
        headers={
            "If-Match": heute.headers["ETag"],
            "Accept": "application/json",
        },
        content_type="application/json",
        status=200,
    )

    example = aut_user_auth_wsgi_app.call_method(
        "get",
        "/NO_SITE/check_mk/api/1.0/objects/host_config/example.com",
        headers={
            "Accept": "application/json",
        },
    )

    moved_example = aut_user_auth_wsgi_app.call_method(
        "post",
        "/NO_SITE/check_mk/api/1.0/objects/host_config/example.com/actions/move/invoke",
        params='{"target_folder": "/new_folder"}',
        headers={
            "If-Match": example.headers["ETag"],
            "Accept": "application/json",
        },
        content_type="application/json",
        status=200,
    )

    moved_example_updated = aut_user_auth_wsgi_app.follow_link(
        moved_example,
        ".../update",
        status=200,
        params=json.dumps({"attributes": {"alias": "foo"}}),
        headers={
            "If-Match": moved_example.headers["ETag"],
            "Accept": "application/json",
        },
        content_type="application/json",
    )

    aut_user_auth_wsgi_app.follow_link(
        moved_example_updated,
        ".../update",
        status=200,
        params=json.dumps({"attributes": {"alias": "foo"}}),
        headers={
            "If-Match": moved_example_updated.headers["ETag"],
            "Accept": "application/json",
        },
        content_type="application/json",
    )


def test_openapi_bulk_hosts(
    monkeypatch: pytest.MonkeyPatch,
    aut_user_auth_wsgi_app: WebTestAppForCMK,
):
    monkeypatch.setattr(
        "cmk.gui.watolib.hosts_and_folders.delete_hosts",
        lambda *args, **kwargs: DeleteHostsResult(),
    )

    base = "/NO_SITE/check_mk/api/1.0"

    resp = aut_user_auth_wsgi_app.call_method(
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
        headers={"Accept": "application/json"},
        content_type="application/json",
    )
    assert len(resp.json["value"]) == 2

    _resp = aut_user_auth_wsgi_app.call_method(
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
        headers={"Accept": "application/json"},
        content_type="application/json",
    )

    # verify attribute ipaddress is set corretly
    resp = aut_user_auth_wsgi_app.call_method(
        "get",
        base + "/objects/host_config/foobar",
        status=200,
        headers={"Accept": "application/json"},
    )
    assert resp.json["extensions"]["attributes"]["ipaddress"] == "192.168.1.1"

    # remove attribute ipaddress via bulk request
    aut_user_auth_wsgi_app.call_method(
        "put",
        base + "/domain-types/host_config/actions/bulk-update/invoke",
        params=json.dumps(
            {
                "entries": [{"host_name": "foobar", "remove_attributes": ["ipaddress"]}],
            }
        ),
        status=200,
        headers={"Accept": "application/json"},
        content_type="application/json",
    )

    # verify attribute ipaddress was removed correctly
    resp = aut_user_auth_wsgi_app.call_method(
        "get",
        base + "/objects/host_config/foobar",
        status=200,
        headers={"Accept": "application/json"},
    )
    assert "ipaddress" not in resp.json["extensions"]["attributes"]

    # adding invalid attribute should fail
    _resp = aut_user_auth_wsgi_app.call_method(
        "put",
        base + "/domain-types/host_config/actions/bulk-update/invoke",
        params=json.dumps(
            {
                "entries": [{"host_name": "foobar", "attributes": {"foobaz": "bar"}}],
            }
        ),
        status=400,
        headers={"Accept": "application/json"},
        content_type="application/json",
    )

    _resp = aut_user_auth_wsgi_app.call_method(
        "post",
        base + "/domain-types/host_config/actions/bulk-delete/invoke",
        params=json.dumps({"entries": ["foobar", "sample"]}),
        status=204,
        headers={"Accept": "application/json"},
        content_type="application/json",
    )


@pytest.mark.usefixtures("suppress_remote_automation_calls")
def test_openapi_bulk_simple(aut_user_auth_wsgi_app: WebTestAppForCMK):
    base = "/NO_SITE/check_mk/api/1.0"
    aut_user_auth_wsgi_app.call_method(
        "post",
        base + "/domain-types/host_config/actions/bulk-create/invoke",
        params=json.dumps(
            {"entries": [{"host_name": "example.com", "folder": "/", "attributes": {}}]}
        ),
        status=200,
        headers={"Accept": "application/json"},
        content_type="application/json",
    )


@pytest.fixture(name="custom_host_attribute")
def _custom_host_attribute():
    try:
        attr: CustomAttr = {
            "name": "foo",
            "title": "bar",
            "help": "foo",
            "topic": "topic",
            "type": "TextAscii",
            "add_custom_macro": False,
            "show_in_table": False,
        }
        save_custom_attrs_to_mk_file({"host": [attr]})
        yield
    finally:
        save_custom_attrs_to_mk_file({})


def test_openapi_host_custom_attributes(
    aut_user_auth_wsgi_app: WebTestAppForCMK,
    with_host,
    custom_host_attribute,
):
    base = "/NO_SITE/check_mk/api/1.0"

    # Known custom attribute

    resp = aut_user_auth_wsgi_app.call_method(
        "get",
        base + "/objects/host_config/example.com",
        status=200,
        headers={
            "Accept": "application/json",
        },
    )

    aut_user_auth_wsgi_app.call_method(
        "put",
        base + "/objects/host_config/example.com",
        status=200,
        params='{"attributes": {"foo": "bar"}}',
        headers={
            "If-Match": resp.headers["ETag"],
            "Accept": "application/json",
        },
        content_type="application/json",
    )

    # Unknown custom attribute

    resp = aut_user_auth_wsgi_app.call_method(
        "get",
        base + "/objects/host_config/example.com",
        status=200,
        headers={
            "Accept": "application/json",
        },
    )

    aut_user_auth_wsgi_app.call_method(
        "put",
        base + "/objects/host_config/example.com",
        status=400,
        params='{"attributes": {"foo2": "bar"}}',
        headers={
            "If-Match": resp.headers["ETag"],
            "Accept": "application/json",
        },
        content_type="application/json",
    )


def test_openapi_host_collection(
    aut_user_auth_wsgi_app: WebTestAppForCMK,
    with_host,
):
    base = "/NO_SITE/check_mk/api/1.0"

    resp = aut_user_auth_wsgi_app.call_method(
        "get",
        base + "/domain-types/host_config/collections/all",
        status=200,
        headers={"Accept": "application/json"},
    )
    for host in resp.json["value"]:
        # Check that all entries are domain objects
        assert "extensions" in host
        assert "links" in host
        assert "members" in host
        assert "title" in host
        assert "id" in host


def test_openapi_host_rename(
    aut_user_auth_wsgi_app: WebTestAppForCMK,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr("cmk.gui.watolib.activate_changes.get_pending_changes_info", lambda: [])
    monkeypatch.setattr(
        "cmk.gui.watolib.host_rename.rename_hosts",
        lambda *args, **kwargs: RenameHostsResult({}),
    )

    base = "/NO_SITE/check_mk/api/1.0"

    aut_user_auth_wsgi_app.call_method(
        "post",
        base + "/domain-types/host_config/collections/all",
        params='{"host_name": "foobar", "folder": "/"}',
        status=200,
        headers={"Accept": "application/json"},
        content_type="application/json",
    )

    resp = aut_user_auth_wsgi_app.call_method(
        "get",
        base + "/objects/host_config/foobar",
        status=200,
        headers={"Accept": "application/json"},
    )

    _resp = aut_user_auth_wsgi_app.call_method(
        "put",
        base + "/objects/host_config/foobar/actions/rename/invoke",
        params='{"new_name": "foobaz"}',
        content_type="application/json",
        status=200,
        headers={"Accept": "application/json", "If-Match": resp.headers["ETag"]},
    )

    _resp = aut_user_auth_wsgi_app.call_method(
        "get",
        base + "/objects/host_config/foobaz",
        status=200,
        headers={"Accept": "application/json"},
    )


@pytest.mark.usefixtures("suppress_remote_automation_calls")
def test_openapi_host_rename_error_on_not_existing_host(
    aut_user_auth_wsgi_app: WebTestAppForCMK,
    monkeypatch,
):
    monkeypatch.setattr("cmk.gui.watolib.activate_changes.get_pending_changes_info", lambda: [])

    base = "/NO_SITE/check_mk/api/1.0"

    aut_user_auth_wsgi_app.call_method(
        "post",
        base + "/domain-types/host_config/collections/all",
        params='{"host_name": "foobar", "folder": "/"}',
        status=200,
        headers={"Accept": "application/json"},
        content_type="application/json",
    )

    resp = aut_user_auth_wsgi_app.call_method(
        "get",
        base + "/objects/host_config/foobar",
        status=200,
        headers={"Accept": "application/json"},
    )

    _resp = aut_user_auth_wsgi_app.call_method(
        "put",
        base + "/objects/host_config/fooba/actions/rename/invoke",
        params='{"new_name": "foobaz"}',
        content_type="application/json",
        headers={"If-Match": resp.headers["ETag"], "Accept": "application/json"},
        status=404,
    )


@pytest.mark.usefixtures("suppress_remote_automation_calls")
def test_openapi_host_rename_on_invalid_hostname(
    aut_user_auth_wsgi_app: WebTestAppForCMK,
    monkeypatch,
):
    monkeypatch.setattr("cmk.gui.watolib.activate_changes.get_pending_changes_info", lambda: [])

    base = "/NO_SITE/check_mk/api/1.0"

    aut_user_auth_wsgi_app.call_method(
        "post",
        base + "/domain-types/host_config/collections/all",
        params='{"host_name": "foobar", "folder": "/"}',
        status=200,
        headers={"Accept": "application/json"},
        content_type="application/json",
    )

    resp = aut_user_auth_wsgi_app.call_method(
        "get",
        base + "/objects/host_config/foobar",
        status=200,
        headers={"Accept": "application/json"},
    )

    _resp = aut_user_auth_wsgi_app.call_method(
        "put",
        base + "/objects/host_config/foobar/actions/rename/invoke",
        params='{"new_name": "foobar"}',
        content_type="application/json",
        headers={"If-Match": resp.headers["ETag"], "Accept": "application/json"},
        status=400,
    )


@pytest.mark.usefixtures("suppress_remote_automation_calls")
def test_openapi_host_rename_with_pending_activate_changes(
    aut_user_auth_wsgi_app: WebTestAppForCMK,
):
    base = "/NO_SITE/check_mk/api/1.0"

    aut_user_auth_wsgi_app.call_method(
        "post",
        base + "/domain-types/host_config/collections/all",
        params='{"host_name": "foobar", "folder": "/"}',
        status=200,
        headers={"Accept": "application/json"},
        content_type="application/json",
    )

    resp = aut_user_auth_wsgi_app.call_method(
        "get",
        base + "/objects/host_config/foobar",
        status=200,
        headers={"Accept": "application/json"},
    )

    _resp = aut_user_auth_wsgi_app.call_method(
        "put",
        base + "/objects/host_config/foobar/actions/rename/invoke",
        params='{"new_name": "foobaz"}',
        content_type="application/json",
        headers={"If-Match": resp.headers["ETag"], "Accept": "application/json"},
        status=409,
    )


@pytest.mark.usefixtures("suppress_remote_automation_calls")
def test_openapi_host_move(aut_user_auth_wsgi_app: WebTestAppForCMK):
    base = "/NO_SITE/check_mk/api/1.0"

    resp = aut_user_auth_wsgi_app.call_method(
        "post",
        base + "/domain-types/host_config/collections/all",
        params='{"host_name": "foobar", "folder": "/"}',
        status=200,
        headers={"Accept": "application/json"},
        content_type="application/json",
    )

    aut_user_auth_wsgi_app.call_method(
        "post",
        base + "/domain-types/folder_config/collections/all",
        params='{"name": "new_folder", "title": "foo", "parent": "/"}',
        content_type="application/json",
        status=200,
        headers={"Accept": "application/json"},
    )

    _resp = aut_user_auth_wsgi_app.call_method(
        "post",
        base + "/objects/host_config/foobar/actions/move/invoke",
        params='{"target_folder": "/new_folder"}',
        headers={"If-Match": resp.headers["ETag"], "Accept": "application/json"},
        content_type="application/json",
        status=200,
    )


@pytest.mark.usefixtures("suppress_remote_automation_calls")
def test_openapi_host_move_to_non_valid_folder(aut_user_auth_wsgi_app: WebTestAppForCMK):
    base = "/NO_SITE/check_mk/api/1.0"

    resp = aut_user_auth_wsgi_app.call_method(
        "post",
        base + "/domain-types/host_config/collections/all",
        params='{"host_name": "foobar", "folder": "/"}',
        status=200,
        headers={"Accept": "application/json"},
        content_type="application/json",
    )

    aut_user_auth_wsgi_app.call_method(
        "post",
        base + "/domain-types/folder_config/collections/all",
        params='{"name": "new_folder", "title": "foo", "parent": "/"}',
        content_type="application/json",
        status=200,
        headers={"Accept": "application/json"},
    )

    aut_user_auth_wsgi_app.call_method(
        "post",
        base + "/objects/host_config/foobar/actions/move/invoke",
        params='{"target_folder": "/"}',
        headers={"If-Match": resp.headers["ETag"], "Accept": "application/json"},
        content_type="application/json",
        status=400,
    )


@pytest.mark.usefixtures("suppress_remote_automation_calls")
def test_openapi_host_move_of_non_existing_host(aut_user_auth_wsgi_app: WebTestAppForCMK):
    base = "/NO_SITE/check_mk/api/1.0"
    _resp = aut_user_auth_wsgi_app.call_method(
        "post",
        base + "/objects/host_config/foobaz/actions/move/invoke",
        params='{"target_folder": "/"}',
        content_type="application/json",
        status=404,
        headers={"Accept": "application/json"},
    )


@pytest.mark.usefixtures("suppress_remote_automation_calls")
def test_openapi_host_update_invalid(aut_user_auth_wsgi_app: WebTestAppForCMK):
    base = "/NO_SITE/check_mk/api/1.0"

    resp = aut_user_auth_wsgi_app.call_method(
        "post",
        base + "/domain-types/host_config/collections/all",
        params='{"host_name": "example.com", "folder": "/"}',
        status=200,
        headers={"Accept": "application/json"},
        content_type="application/json",
    )

    aut_user_auth_wsgi_app.follow_link(
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
        headers={"If-Match": resp.headers["ETag"], "Accept": "application/json"},
        content_type="application/json",
    )


@managedtest
def test_openapi_create_host_with_contact_group(aut_user_auth_wsgi_app: WebTestAppForCMK):
    base = "/NO_SITE/check_mk/api/1.0"

    group = {"name": "code_monkeys", "alias": "banana team", "customer": "global"}
    _resp = aut_user_auth_wsgi_app.call_method(
        "post",
        base + "/domain-types/contact_group_config/collections/all",
        params=json.dumps(group),
        status=200,
        content_type="application/json",
        headers={"Accept": "application/json"},
    )

    json_data = {
        "folder": "/",
        "host_name": "example.com",
        "attributes": {
            "ipaddress": "192.168.0.123",
            "contactgroups": {
                "groups": ["code_monkeys"],
                "use": False,
                "use_for_services": False,
                "recurse_use": False,
                "recurse_perms": False,
            },
        },
    }
    aut_user_auth_wsgi_app.call_method(
        "post",
        base + "/domain-types/host_config/collections/all",
        params=json.dumps(json_data),
        status=200,
        content_type="application/json",
        headers={"Accept": "application/json"},
    )


@managedtest
@pytest.mark.skip("Doesn't work until MultiNested with merged=True is active.")
def test_openapi_create_host_with_custom_attributes(
    aut_user_auth_wsgi_app: WebTestAppForCMK,
    custom_host_attribute,
):
    base = "/NO_SITE/check_mk/api/1.0"

    json_data = {
        "folder": "/",
        "host_name": "example.com",
        "attributes": {
            "ipaddress": "192.168.0.123",
            "foo": "abc",
        },
    }
    aut_user_auth_wsgi_app.call_method(
        "post",
        base + "/domain-types/host_config/collections/all",
        params=json.dumps(json_data),
        status=200,
        content_type="application/json",
        headers={"Accept": "application/json"},
    )
