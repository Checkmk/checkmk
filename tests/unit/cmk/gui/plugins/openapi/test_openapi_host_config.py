#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import contextlib
import json
from collections.abc import Iterator, Sequence
from typing import Tuple
from unittest.mock import MagicMock

import pytest
from freezegun import freeze_time
from pytest_mock import MockerFixture

from tests.testlib.rest_api_client import ClientRegistry

from tests.unit.cmk.gui.conftest import WebTestAppForCMK

from cmk.utils import version

from cmk.automations.results import DeleteHostsResult, RenameHostsResult

import cmk.gui.watolib.bakery as bakery
from cmk.gui.exceptions import MKUserError
from cmk.gui.type_defs import CustomAttr
from cmk.gui.watolib.custom_attributes import save_custom_attrs_to_mk_file
from cmk.gui.watolib.hosts_and_folders import CREFolder, CREHost, Folder, Host

managedtest = pytest.mark.skipif(not version.is_managed_edition(), reason="see #7213")


def test_openapi_missing_host(clients: ClientRegistry) -> None:
    resp = clients.HostConfig.get("foobar", expect_ok=False)
    resp.assert_status_code(404)
    assert resp.json == {
        "detail": "These fields have problems: host_name",
        "fields": {"host_name": ["Host not found: 'foobar'"]},
        "status": 404,
        "title": "Not Found",
    }


@pytest.mark.usefixtures("with_host")
def test_openapi_cluster_host(clients: ClientRegistry) -> None:
    clients.HostConfig.create(host_name="foobar")
    clients.HostConfig.create_cluster(host_name="bazfoo", nodes=["foobar"])
    clients.HostConfig.create(
        host_name="foobaz", attributes={"ipv6address": "xxx.myfritz.net"}
    ).assert_status_code(200)

    clients.HostConfig.get("bazfoozle", expect_ok=False).assert_status_code(404)
    clients.HostConfig.get("bazfoo")

    clients.HostConfig.edit_property(
        "bazfoo", "nodes", {"nodes": ["not_existing"]}, expect_ok=False
    ).assert_status_code(400)
    clients.HostConfig.edit_property(
        "bazfoo", "nodes", {"nodes": ["example.com", "bazfoo"]}, expect_ok=False
    ).assert_status_code(400)

    clients.HostConfig.edit_property(
        "bazfoo", "nodes", {"nodes": ["example.com"]}
    ).assert_status_code(200)

    resp = clients.HostConfig.get("bazfoo")
    assert resp.json["extensions"]["cluster_nodes"] == ["example.com"]


@pytest.fixture(name="try_bake_agents_for_hosts")
def fixture_try_bake_agents_for_hosts(mocker: MockerFixture) -> MagicMock:
    return mocker.patch.object(
        bakery,
        "try_bake_agents_for_hosts",
        side_effect=lambda *args, **kw: None,
    )


@pytest.mark.parametrize(
    "bake_agent,called",
    [
        (True, True),
        (False, False),
        (None, False),
    ],
)
def test_openapi_add_host_bake_agent_parameter(
    bake_agent: bool | None,
    called: bool,
    try_bake_agents_for_hosts: MagicMock,
    clients: ClientRegistry,
) -> None:
    clients.HostConfig.create(host_name="foobar", bake_agent=bake_agent)

    if called:
        try_bake_agents_for_hosts.assert_called_once_with(["foobar"])
    else:
        try_bake_agents_for_hosts.assert_not_called()


def test_openapi_add_host_with_attributes(clients: ClientRegistry) -> None:
    response = clients.HostConfig.create(
        host_name="foobar",
        attributes={
            "alias": "ALIAS",
            "locked_by": {
                "site_id": "site_id",
                "program_id": "dcd",
                "instance_id": "connection_id",
            },
            "locked_attributes": ["alias"],
        },
    ).assert_status_code(200)

    api_attributes = response.json["extensions"]["attributes"]
    assert api_attributes["alias"] == "ALIAS"
    assert api_attributes["locked_by"] == {
        "instance_id": "connection_id",
        "program_id": "dcd",
        "site_id": "site_id",
    }
    assert api_attributes["locked_attributes"] == ["alias"]

    # Ensure that the attributes were stored as expected
    hosts_config = Folder.root_folder()._load_hosts_file()
    assert hosts_config is not None
    assert hosts_config["host_attributes"]["foobar"]["locked_attributes"] == ["alias"]
    assert hosts_config["host_attributes"]["foobar"]["locked_by"] == (
        "site_id",
        "dcd",
        "connection_id",
    )


def test_openapi_bulk_add_hosts_with_attributes(
    clients: ClientRegistry,
) -> None:
    response = clients.HostConfig.bulk_create(
        {
            "host_name": "ding",
            "folder": "/",
            "attributes": {"ipaddress": "127.0.0.2"},
        },
        {
            "host_name": "dong",
            "folder": "/",
            "attributes": {
                "ipaddress": "127.0.0.2",
                "site": "NO_SITE",
            },
        },
    ).assert_status_code(200)
    assert len(response.json["value"]) == 2

    clients.HostConfig.bulk_edit(
        {
            "host_name": "ding",
            "update_attributes": {
                "locked_by": {
                    "site_id": "site_id",
                    "program_id": "dcd",
                    "instance_id": "connection_id",
                },
                "locked_attributes": ["alias"],
            },
        }
    ).assert_status_code(200)

    # verify attribute ipaddress is set corretly
    response = clients.HostConfig.get(host_name="ding")

    api_attributes = response.json["extensions"]["attributes"]
    assert api_attributes["locked_by"] == {
        "instance_id": "connection_id",
        "program_id": "dcd",
        "site_id": "site_id",
    }
    assert api_attributes["locked_attributes"] == ["alias"]


@pytest.mark.parametrize(
    "bake_agent,called",
    [
        (True, True),
        (False, False),
        (None, False),
    ],
)
def test_openapi_add_cluster_bake_agent_parameter(
    bake_agent: bool,
    called: bool,
    try_bake_agents_for_hosts: MagicMock,
    clients: ClientRegistry,
) -> None:
    clients.HostConfig.create(host_name="foobar", bake_agent=bake_agent).assert_status_code(200)

    if called:
        try_bake_agents_for_hosts.assert_called_once_with(["foobar"])
    else:
        try_bake_agents_for_hosts.assert_not_called()
    try_bake_agents_for_hosts.reset_mock()

    clients.HostConfig.create_cluster(
        host_name="bazfoo", nodes=["foobar"], bake_agent=bake_agent
    ).assert_status_code(200)

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
    monkeypatch: pytest.MonkeyPatch,
    clients: ClientRegistry,
) -> None:
    resp = clients.HostConfig.create(host_name="foobar").assert_status_code(200)

    assert isinstance(resp.json["extensions"]["attributes"]["meta_data"]["created_at"], str)
    assert isinstance(resp.json["extensions"]["attributes"]["meta_data"]["updated_at"], str)

    resp = clients.HostConfig.follow_link(resp.json, "self")
    resp.assert_status_code(200)

    attributes = {
        "ipaddress": "127.0.0.1",
        "snmp_community": {
            "type": "v1_v2_community",
            "community": "blah",
        },
    }
    resp = clients.HostConfig.follow_link(
        resp.json,
        ".../update",
        extra_params={"attributes": attributes},
        headers={"If-Match": resp.headers["ETag"]},
    )

    got_attributes = resp.json["extensions"]["attributes"]
    assert list(attributes.items()) <= list(got_attributes.items())

    resp = clients.HostConfig.follow_link(
        resp.json,
        ".../update",
        extra_params={"update_attributes": {"alias": "bar"}},
        headers={"If-Match": resp.headers["ETag"], "Accept": "application/json"},
    )
    resp.assert_status_code(200)
    assert resp.json["extensions"]["attributes"]["alias"] == "bar"

    resp = clients.HostConfig.follow_link(
        resp.json,
        ".../update",
        extra_params={"remove_attributes": ["alias"]},
        headers={"If-Match": resp.headers["ETag"]},
    )

    assert list(resp.json["extensions"]["attributes"].items()) >= list(
        {"ipaddress": "127.0.0.1"}.items()
    )
    assert "alias" not in resp.json["extensions"]["attributes"]

    # make sure changes are written to disk:
    clients.HostConfig.follow_link(resp.json, "self").assert_status_code(200)
    assert list(resp.json["extensions"]["attributes"].items()) >= list(
        {"ipaddress": "127.0.0.1"}.items()
    )

    # also try to update with wrong attribute
    clients.HostConfig.follow_link(
        resp.json,
        ".../update",
        extra_params={"attributes": {"foobaz": "bar"}},
        headers={"If-Match": resp.headers["ETag"]},
        expect_ok=False,
    ).assert_status_code(400)

    monkeypatch.setattr(
        "cmk.gui.plugins.openapi.endpoints.host_config.delete_hosts",
        lambda *args, **kwargs: DeleteHostsResult(),
    )
    clients.HostConfig.follow_link(resp.json, ".../delete").assert_status_code(204)


def test_openapi_host_update_after_move(
    clients: ClientRegistry,
) -> None:
    clients.ContactGroup.create(
        name="all",
        alias="all_alias",
    )
    clients.Folder.create(
        folder_name="source_folder",
        title="source_folder",
        parent="/",
        attributes={"contactgroups": {"groups": ["all"]}},
    )
    clients.Folder.create(
        folder_name="target_folder",
        title="target_folder",
        parent="/",
        attributes={"contactgroups": {"groups": ["all"]}},
    )
    clients.HostConfig.create(
        host_name="TestHost1",
        folder="/source_folder",
    )
    clients.HostConfig.move(
        host_name="TestHost1",
        target_folder="/target_folder",
    )
    clients.HostConfig.edit(
        host_name="TestHost1",
        attributes={"alias": "foo"},
    )


def test_openapi_bulk_hosts(
    monkeypatch: pytest.MonkeyPatch,
    aut_user_auth_wsgi_app: WebTestAppForCMK,
) -> None:
    monkeypatch.setattr(
        "cmk.gui.plugins.openapi.endpoints.host_config.delete_hosts",
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
def test_openapi_bulk_simple(aut_user_auth_wsgi_app: WebTestAppForCMK) -> None:
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


@pytest.mark.usefixtures("suppress_remote_automation_calls")
def test_openapi_bulk_with_failed(
    base: str,
    monkeypatch: pytest.MonkeyPatch,
    aut_user_auth_wsgi_app: WebTestAppForCMK,
) -> None:
    def _raise(_self, _host_name, _attributes):
        if _host_name == "foobar":
            raise MKUserError(None, "fail")
        return _attributes

    monkeypatch.setattr(
        "cmk.gui.watolib.hosts_and_folders.CREFolder.verify_and_update_host_details", _raise
    )

    resp = aut_user_auth_wsgi_app.call_method(
        "post",
        base + "/domain-types/host_config/actions/bulk-create/invoke",
        params=json.dumps(
            {
                "entries": [
                    {"host_name": "foobar", "folder": "/", "attributes": {}},
                    {"host_name": "example.com", "folder": "/", "attributes": {}},
                ]
            }
        ),
        status=400,
        headers={"Accept": "application/json"},
        content_type="application/json",
    )
    assert resp.json["ext"]["failed_hosts"] == {"foobar": "Validation failed: fail"}
    assert [e["id"] for e in resp.json["ext"]["succeeded_hosts"]["value"]] == ["example.com"]


@pytest.fixture(name="custom_host_attribute")
def _custom_host_attribute():
    attr: CustomAttr = {
        "name": "foo",
        "title": "bar",
        "help": "foo",
        "topic": "topic",
        "type": "TextAscii",
        "add_custom_macro": False,
        "show_in_table": False,
    }
    with custom_host_attribute_ctx({"host": [attr]}):
        yield


@pytest.fixture(name="custom_host_attribute_basic_topic")
def _custom_host_attribute_with_basic_topic():
    attr: CustomAttr = {
        "name": "foo",
        "title": "bar",
        "help": "foo",
        "topic": "basic",
        "type": "TextAscii",
        "add_custom_macro": False,
        "show_in_table": False,
    }
    with custom_host_attribute_ctx({"host": [attr]}):
        yield


@contextlib.contextmanager
def custom_host_attribute_ctx(attrs: dict[str, list[CustomAttr]]) -> Iterator[None]:
    try:
        save_custom_attrs_to_mk_file(attrs)
        yield
    finally:
        save_custom_attrs_to_mk_file({})


def test_openapi_host_created_timestamp(
    base: str, aut_user_auth_wsgi_app: WebTestAppForCMK
) -> None:
    json_data = {
        "folder": "/",
        "host_name": "foobar.com",
        "attributes": {
            "ipaddress": "192.168.0.123",
        },
    }

    resp_post = aut_user_auth_wsgi_app.call_method(
        "post",
        base + "/domain-types/host_config/collections/all",
        params=json.dumps(json_data),
        status=200,
        content_type="application/json",
        headers={"Accept": "application/json"},
    )

    created_at_post = resp_post.json["extensions"]["attributes"]["meta_data"]["created_at"]

    resp_get = aut_user_auth_wsgi_app.call_method(
        "get",
        base + "/objects/host_config/foobar.com",
        status=200,
        headers={"Accept": "application/json"},
    )

    created_at_get = resp_get.json["extensions"]["attributes"]["meta_data"]["created_at"]

    resp_put = aut_user_auth_wsgi_app.call_method(
        "put",
        base + "/objects/host_config/foobar.com",
        status=200,
        params='{"attributes": {"ipaddress": "192.168.0.124"}}',
        content_type="application/json",
        headers={"If-Match": resp_get.headers["ETag"], "Accept": "application/json"},
    )

    created_at_put = resp_put.json["extensions"]["attributes"]["meta_data"]["created_at"]
    assert created_at_post == created_at_get == created_at_put


@pytest.mark.usefixtures("custom_host_attribute")
@pytest.mark.usefixtures("with_host")
def test_openapi_host_has_deleted_custom_attributes(
    base: str,
    aut_user_auth_wsgi_app: WebTestAppForCMK,
) -> None:
    # Known custom attribute
    resp = aut_user_auth_wsgi_app.call_method(
        "get",
        base + "/objects/host_config/example.com",
        status=200,
        headers={
            "Accept": "application/json",
        },
    )

    # Set the attribute on the host
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

    # Try to get it with the attribute already deleted
    with custom_host_attribute_ctx({}):
        resp = aut_user_auth_wsgi_app.call_method(
            "get",
            base + "/objects/host_config/example.com",
            status=200,
            headers={
                "Accept": "application/json",
            },
        )
        # foo will still show up in the response, even though it is deleted.
        assert "foo" in resp.json["extensions"]["attributes"]


@pytest.mark.usefixtures("custom_host_attribute")
@pytest.mark.usefixtures("with_host")
def test_openapi_host_custom_attributes(
    base: str,
    aut_user_auth_wsgi_app: WebTestAppForCMK,
) -> None:
    # Known custom attribute
    resp = aut_user_auth_wsgi_app.call_method(
        "get",
        base + "/objects/host_config/example.com",
        status=200,
        headers={
            "Accept": "application/json",
        },
    )

    update1 = aut_user_auth_wsgi_app.call_method(
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

    # Internal, non-editable attributes shall not be settable.
    aut_user_auth_wsgi_app.call_method(
        "put",
        base + "/objects/host_config/example.com",
        status=400,
        params='{"attributes": {"meta_data": "bar"}}',
        headers={
            "If-Match": update1.headers["ETag"],
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


@pytest.mark.usefixtures("with_host")
def test_openapi_host_collection(
    base: str,
    aut_user_auth_wsgi_app: WebTestAppForCMK,
) -> None:
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


@pytest.mark.usefixtures("with_host")
def test_openapi_host_collection_effective_attributes(
    base: str,
    aut_user_auth_wsgi_app: WebTestAppForCMK,
) -> None:
    resp = aut_user_auth_wsgi_app.call_method(
        "get",
        base + "/domain-types/host_config/collections/all?effective_attributes=true",
        status=200,
        headers={"Accept": "application/json"},
    )
    for host in resp.json["value"]:
        assert isinstance(host["extensions"]["effective_attributes"], dict)

    resp = aut_user_auth_wsgi_app.call_method(
        "get",
        base + "/domain-types/host_config/collections/all?effective_attributes=false",
        status=200,
        headers={"Accept": "application/json"},
    )
    for host in resp.json["value"]:
        assert host["extensions"]["effective_attributes"] is None


def test_openapi_host_rename(
    aut_user_auth_wsgi_app: WebTestAppForCMK,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "cmk.gui.plugins.openapi.endpoints.host_config.has_pending_changes", lambda: False
    )
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
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "cmk.gui.plugins.openapi.endpoints.host_config.has_pending_changes", lambda: False
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
        base + "/objects/host_config/fooba/actions/rename/invoke",
        params='{"new_name": "foobaz"}',
        content_type="application/json",
        headers={"If-Match": resp.headers["ETag"], "Accept": "application/json"},
        status=404,
    )


@pytest.mark.usefixtures("suppress_remote_automation_calls")
def test_openapi_host_rename_on_invalid_hostname(
    aut_user_auth_wsgi_app: WebTestAppForCMK,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "cmk.gui.plugins.openapi.endpoints.host_config.has_pending_changes", lambda: False
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
        params='{"new_name": "foobar"}',
        content_type="application/json",
        headers={"If-Match": resp.headers["ETag"], "Accept": "application/json"},
        status=400,
    )


@pytest.mark.usefixtures("suppress_remote_automation_calls")
def test_openapi_host_folder_config_normalization(
    aut_user_auth_wsgi_app: WebTestAppForCMK,
) -> None:
    base = "/NO_SITE/check_mk/api/1.0"

    def _create_folder(fname: str, parent: str) -> None:
        params = f'{{"name": "{fname}", "title": "{fname}", "parent": "{parent}"}}'
        aut_user_auth_wsgi_app.call_method(
            "post",
            base + "/domain-types/folder_config/collections/all",
            params=params,
            status=200,
            headers={"Accept": "application/json"},
            content_type="application/json",
        )
        parent += f"{fname}~"

    def _create_folders_recursive(folders: Sequence[str]) -> None:
        _create_folder(folders[0], "~")
        parent = f"~{folders[0]}"
        for fname in folders[1:]:
            _create_folder(fname, parent)
            parent += f"~{fname}"

    _create_folders_recursive(["I", "want", "those"])

    aut_user_auth_wsgi_app.call_method(
        "post",
        base + "/domain-types/host_config/collections/all",
        params='{"host_name": "foobar", "folder": "/I/want/those"}',
        status=200,
        headers={"Accept": "application/json"},
        content_type="application/json",
    )

    response = aut_user_auth_wsgi_app.call_method(
        "get",
        base + "/objects/host_config/foobar",
        status=200,
        headers={"Accept": "application/json"},
    )
    assert response.json["extensions"]["folder"] == "/I/want/those"


@pytest.mark.usefixtures("suppress_remote_automation_calls")
def test_openapi_host_rename_with_pending_activate_changes(
    aut_user_auth_wsgi_app: WebTestAppForCMK,
) -> None:
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
def test_openapi_host_move(clients: ClientRegistry) -> None:
    clients.ContactGroup.create(
        name="all",
        alias="all_alias",
    )
    clients.Folder.create(
        folder_name="source_folder",
        title="source_folder",
        parent="/",
        attributes={"contactgroups": {"groups": ["all"]}},
    )
    clients.Folder.create(
        folder_name="target_folder",
        title="target_folder",
        parent="/",
        attributes={"contactgroups": {"groups": ["all"]}},
    )
    clients.HostConfig.create(
        host_name="TestHost1",
        folder="/source_folder",
    )
    clients.HostConfig.move(
        host_name="TestHost1",
        target_folder="/target_folder",
    )


@pytest.mark.usefixtures("suppress_remote_automation_calls")
def test_openapi_host_move_to_non_valid_folder(clients: ClientRegistry) -> None:
    clients.HostConfig.create(
        host_name="TestHost1",
        folder="/",
    )
    clients.HostConfig.move(
        host_name="TestHost1", target_folder="/folder-that-does-not-exist", expect_ok=False
    ).assert_status_code(400)


@pytest.mark.usefixtures("suppress_remote_automation_calls")
def test_openapi_host_move_of_non_existing_host(aut_user_auth_wsgi_app: WebTestAppForCMK) -> None:
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
def test_openapi_host_update_invalid(aut_user_auth_wsgi_app: WebTestAppForCMK) -> None:
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
def test_openapi_create_host_with_contact_group(aut_user_auth_wsgi_app: WebTestAppForCMK) -> None:
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
def test_openapi_host_with_custom_attributes(  # type: ignore[no-untyped-def]
    clients: ClientRegistry,
    custom_host_attribute_basic_topic,
):
    resp = clients.HostConfig.create(
        host_name="example.com",
        attributes={
            "ipaddress": "192.168.0.123",
            "foo": "abc",
        },
    )
    assert "ipaddress" in resp.json["extensions"]["attributes"]
    assert "foo" in resp.json["extensions"]["attributes"]

    # remove custom attribute
    resp = clients.HostConfig.edit(
        host_name="example.com",
        remove_attributes=["foo"],
    )
    assert "foo" not in resp.json["extensions"]["attributes"]


@managedtest
def test_openapi_host_with_inventory_failed(
    base: str,
    aut_user_auth_wsgi_app: WebTestAppForCMK,
) -> None:
    json_data = {
        "folder": "/",
        "host_name": "example.com",
        "attributes": {
            "ipaddress": "192.168.0.123",
            "inventory_failed": True,
        },
    }
    resp = aut_user_auth_wsgi_app.call_method(
        "post",
        f"{base}/domain-types/host_config/collections/all",
        params=json.dumps(json_data),
        status=200,
        content_type="application/json",
        headers={"Accept": "application/json"},
    )
    assert resp.json["extensions"]["attributes"]["inventory_failed"] is True


def test_openapi_host_with_invalid_labels(
    base: str, aut_user_auth_wsgi_app: WebTestAppForCMK
) -> None:
    json_data = {
        "folder": "/",
        "host_name": "example.com",
        "attributes": {"labels": {"label": ["invalid_label_entry", "another_one"]}},
    }
    aut_user_auth_wsgi_app.call_method(
        "post",
        f"{base}/domain-types/host_config/collections/all",
        params=json.dumps(json_data),
        status=400,
        content_type="application/json",
        headers={"Accept": "application/json"},
    )


def test_openapi_host_with_labels(base: str, aut_user_auth_wsgi_app: WebTestAppForCMK) -> None:
    json_data = {
        "folder": "/",
        "host_name": "example.com",
        "attributes": {
            "labels": {
                "label": "value",
            }
        },
    }
    resp = aut_user_auth_wsgi_app.call_method(
        "post",
        f"{base}/domain-types/host_config/collections/all",
        params=json.dumps(json_data),
        status=200,
        content_type="application/json",
        headers={"Accept": "application/json"},
    )
    assert resp.json["extensions"]["attributes"]["labels"] == {"label": "value"}


def test_openapi_host_with_invalid_snmp_community_option(
    base: str, aut_user_auth_wsgi_app: WebTestAppForCMK
) -> None:
    json_data = {
        "folder": "/",
        "host_name": "example.com",
        "attributes": {
            "snmp_community": {
                "type": "v1_v2_community",
            }
        },
    }
    aut_user_auth_wsgi_app.call_method(
        "post",
        f"{base}/domain-types/host_config/collections/all",
        params=json.dumps(json_data),
        status=400,
        content_type="application/json",
        headers={"Accept": "application/json"},
    )


def test_openapi_all_hosts_with_non_existing_site(
    base: str,
    aut_user_auth_wsgi_app: WebTestAppForCMK,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def mock_all_hosts_recursively(_cls):
        return {
            "foo": CREHost(
                folder=CREFolder.root_folder(),
                host_name="foo",
                attributes={"site": "a_non_existing_site"},
                cluster_nodes=None,
            )
        }

    monkeypatch.setattr(CREFolder, "all_hosts_recursively", mock_all_hosts_recursively)

    aut_user_auth_wsgi_app.get(
        f"{base}/domain-types/host_config/collections/all",
        status=200,
        headers={"Accept": "application/json"},
    )


def test_openapi_host_with_non_existing_site(
    base: str,
    aut_user_auth_wsgi_app: WebTestAppForCMK,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def mock_host(_hostname):
        return CREHost(
            folder=CREFolder.root_folder(),
            host_name="foo",
            attributes={"site": "a_non_existing_site"},
            cluster_nodes=None,
        )

    monkeypatch.setattr(Host, "host", mock_host)

    resp = aut_user_auth_wsgi_app.get(
        f"{base}/objects/host_config/foo",
        status=200,
        headers={"Accept": "application/json"},
    )

    assert resp.json["extensions"]["attributes"]["site"] == "Unknown Site: a_non_existing_site"


def test_openapi_host_config_attributes_as_string_crash_regression(
    aut_user_auth_wsgi_app: WebTestAppForCMK, base: str
) -> None:
    resp = aut_user_auth_wsgi_app.post(
        f"{base}/domain-types/host_config/collections/all",
        content_type="application/json",
        headers={"Accept": "application/json"},
        params=json.dumps(
            {
                "folder": "/",
                "host_name": "example.com",
                "attributes": "{'ipaddress':'192.168.0.123'}",  # note that this is a str
            }
        ),
        status=400,
    )
    assert resp.json["fields"]["attributes"] == [
        "Incompatible data type. Received a(n) 'str', but an associative value is required. Maybe you quoted a value that is meant to be an object?"
    ]


@pytest.mark.usefixtures("with_host")
def test_openapi_host_config_effective_attributes_schema_regression(
    clients: ClientRegistry,
) -> None:
    resp = clients.HostConfig.get("heute", effective_attributes=True)
    assert isinstance(
        resp.json["extensions"]["effective_attributes"]["meta_data"]["created_at"], str
    )
    assert isinstance(
        resp.json["extensions"]["effective_attributes"]["meta_data"]["updated_at"], str
    )


@pytest.mark.usefixtures("with_host")
def test_openapi_host_config_show_host_disregards_contact_groups(clients: ClientRegistry) -> None:
    """This test makes sure a user cannot see the config of a host that is not assigned to their contact groups."""
    clients.ContactGroup.create("no_hosts_in_here", alias="no_hosts_in_here")
    clients.ContactGroup.create("all_hosts_in_here", alias="all_hosts_in_here")

    clients.User.create(
        username="unable_to_see_host",
        fullname="unable_to_see_host",
        contactgroups=["no_hosts_in_here"],
        auth_option={"auth_type": "password", "password": "supersecret"},
    )

    clients.Rule.create(
        "host_contactgroups",
        value_raw="'all_hosts_in_here'",
        folder="/",
        conditions={},
    )

    clients.HostConfig.set_credentials("unable_to_see_host", "supersecret")

    resp = clients.HostConfig.get("heute", expect_ok=False).assert_status_code(403)
    assert resp.json["title"] == "Forbidden"
    assert "heute" in resp.json["detail"]


def test_openapi_list_hosts_does_not_show_inaccessible_hosts(clients: ClientRegistry) -> None:
    clients.ContactGroup.create(name="does_not_see_everything", alias="does_not_see_everything")
    clients.User.create(
        username="unable_to_see_all_host",
        fullname="unable_to_see_all_host",
        contactgroups=["does_not_see_everything"],
        auth_option={"auth_type": "password", "password": "supersecret"},
    )

    clients.HostConfig.create(
        host_name="should_be_visible",
        attributes={"contactgroups": {"groups": ["does_not_see_everything"], "use": True}},
    )
    clients.HostConfig.create(
        host_name="should_not_be_invisible",
    )

    clients.HostConfig.set_credentials("unable_to_see_all_host", "supersecret")
    resp = clients.HostConfig.get_all()
    host_names = [entry["id"] for entry in resp.json["value"]]
    assert "should_be_visible" in host_names
    assert "should_not_be_invisible" not in host_names


@freeze_time("1998-02-09")
def test_openapi_effective_attributes_are_transformed_on_their_way_out_regression(
    clients: ClientRegistry, with_admin: Tuple[str, str]
) -> None:
    """We take 'meta_data' as the example attributes, it's a CheckmkTuple type that is stored as a
    tuple in the .mk files, but read and written as a dict in the REST API."""

    username, password = with_admin
    # We can't use the 'with_host' fixture, because time won't be frozen when it's created.
    clients.HostConfig.set_credentials(username, password)

    clients.HostConfig.create("test_host")

    resp_with_effective_attributes = clients.HostConfig.get(
        host_name="test_host", effective_attributes=True
    )
    resp_without_effective_attributes = clients.HostConfig.get(host_name="test_host")
    assert resp_with_effective_attributes.json["extensions"]["effective_attributes"][
        "meta_data"
    ] == {
        "created_at": "1998-02-09T00:00:00+00:00",
        "updated_at": "1998-02-09T00:00:00+00:00",
        "created_by": username,
    }  # should not be the tuple stored in the .mk files, but a nice, readable dict
    assert (
        resp_with_effective_attributes.json["extensions"]["effective_attributes"]["meta_data"]
        == resp_without_effective_attributes.json["extensions"]["attributes"]["meta_data"]
    )

    resp_with_effective_attributes = clients.HostConfig.get_all(effective_attributes=True)
    resp_without_effective_attributes = clients.HostConfig.get_all()
    assert resp_with_effective_attributes.json["value"][0]["extensions"]["effective_attributes"][
        "meta_data"
    ] == {
        "created_at": "1998-02-09T00:00:00+00:00",
        "updated_at": "1998-02-09T00:00:00+00:00",
        "created_by": username,
    }  # should not be the tuple stored in the .mk files, but a nice, readable dict
    assert (
        resp_with_effective_attributes.json["value"][0]["extensions"]["effective_attributes"][
            "meta_data"
        ]
        == resp_without_effective_attributes.json["value"][0]["extensions"]["attributes"][
            "meta_data"
        ]
    )


def test_move_to_folder_with_different_contact_group(clients: ClientRegistry) -> None:
    clients.ContactGroup.create(
        name="test_contact_group",
        alias="cg_alias",
    )

    clients.User.create(
        username="user1",
        fullname="user1_fullname",
        contactgroups=["test_contact_group"],
        auth_option={"auth_type": "password", "password": "asflkjas^asf@adf%5Ah!@%^sfadf"},
        roles=["admin"],
    )

    clients.Folder.create(
        folder_name="Folder1",
        title="Folder1",
        parent="/",
        attributes={"contactgroups": {"groups": ["test_contact_group"]}},
    )

    clients.Folder.create(
        folder_name="Folder2",
        title="Folder2",
        parent="/",
    )  # no contact group set

    clients.HostConfig.create(
        host_name="TestHost1",
        folder="/Folder1",
    )

    clients.HostConfig.set_credentials(
        username="user1",
        password="asflkjas^asf@adf%5Ah!@%^sfadf",
    )

    resp = clients.HostConfig.move(
        host_name="TestHost1",
        target_folder="/Folder2",
        expect_ok=False,
    )

    resp.assert_status_code(403)
    assert resp.json["title"] == "Permission denied"
    assert (
        resp.json["detail"]
        == "The user doesn't belong to the required contact groups of the following objects to perform this action: Folder('Folder2', 'Folder2')"
    )


def test_move_from_folder_with_different_contact_group(clients: ClientRegistry) -> None:
    clients.ContactGroup.create(
        name="test_contact_group",
        alias="cg_alias",
    )

    clients.User.create(
        username="user1",
        fullname="user1_fullname",
        contactgroups=["test_contact_group"],
        auth_option={"auth_type": "password", "password": "asflkjas^asf@adf%5Ah!@%^sfadf"},
        roles=["admin"],
    )

    clients.Folder.create(
        folder_name="Folder1",
        title="Folder1",
        parent="/",
    )  # no contact group set

    clients.Folder.create(
        folder_name="Folder2",
        title="Folder2",
        parent="/",
        attributes={"contactgroups": {"groups": ["test_contact_group"]}},
    )

    clients.HostConfig.create(
        host_name="TestHost1",
        folder="/Folder1",
    )

    clients.HostConfig.set_credentials(
        username="user1",
        password="asflkjas^asf@adf%5Ah!@%^sfadf",
    )

    resp = clients.HostConfig.move(
        host_name="TestHost1",
        target_folder="/Folder2",
        expect_ok=False,
    )

    resp.assert_status_code(403)
    assert resp.json["title"] == "Permission denied"
    assert (
        resp.json["detail"]
        == "The user doesn't belong to the required contact groups of the following objects to perform this action: Folder('Folder1', 'Folder1'), Host('TestHost1')"
    )


def test_move_host_different_contact_group(clients: ClientRegistry) -> None:
    clients.ContactGroup.create(
        name="test_contact_group_1",
        alias="cg_alias1",
    )
    clients.ContactGroup.create(
        name="test_contact_group2",
        alias="cg_alias2",
    )
    clients.Folder.create(
        folder_name="Folder1",
        title="Folder1",
        parent="/",
        attributes={"contactgroups": {"groups": ["test_contact_group_1"]}},
    )

    clients.Folder.create(
        folder_name="Folder2",
        title="Folder2",
        parent="/",
        attributes={"contactgroups": {"groups": ["test_contact_group_1"]}},
    )
    # User has access to both folders (same contact group)
    clients.User.create(
        username="user1",
        fullname="user1_fullname",
        contactgroups=["test_contact_group_1"],
        auth_option={"auth_type": "password", "password": "asflkjas^asf@adf%5Ah!@%^sfadf"},
        roles=["admin"],
    )

    # As admin api user, create a host in test_contact_group2
    clients.HostConfig.create(
        host_name="TestHost1",
        folder="/Folder1",
        attributes={"contactgroups": {"groups": ["test_contact_group2"]}},
    )

    # Switch to the test user created above who only has access to test_contact_group1
    clients.HostConfig.set_credentials(
        username="user1",
        password="asflkjas^asf@adf%5Ah!@%^sfadf",
    )

    # Try to move the Host
    resp = clients.HostConfig.move(
        host_name="TestHost1",
        target_folder="/Folder2",
        expect_ok=False,
    )

    resp.assert_status_code(403)
    assert resp.json["title"] == "Permission denied"
    assert (
        resp.json["detail"]
        == "The user doesn't belong to the required contact groups of the following objects to perform this action: Host('TestHost1')"
    )


@pytest.mark.usefixtures("custom_host_attribute")
def test_openapi_host_config_effective_attributes_includes_custom_attributes_regression(
    clients: ClientRegistry,
) -> None:
    clients.HostConfig.create(host_name="test_host", attributes={"foo": "blub"})

    resp = clients.HostConfig.get("test_host", effective_attributes=True)
    assert resp.json["extensions"]["effective_attributes"]["foo"] == "blub"


def test_openapi_host_config_effective_attributes_includes_tags_regression(
    clients: ClientRegistry,
) -> None:
    clients.HostTagGroup.create(ident="foo", title="foo", tags=[{"ident": "bar", "title": "bar"}])
    clients.HostConfig.create(host_name="test_host", attributes={"tag_foo": "bar"})

    resp = clients.HostConfig.get("test_host", effective_attributes=True)
    assert resp.json["extensions"]["effective_attributes"]["tag_foo"] == "bar"


@freeze_time("2022-11-05")
def test_openapi_host_config_effective_attributes_includes_all_host_attributes_regression(
    clients: ClientRegistry, with_admin: Tuple[str, str]
) -> None:
    username, password = with_admin
    clients.HostConfig.set_credentials(username, password)

    clients.HostConfig.create(host_name="heute")
    resp = clients.HostConfig.get(host_name="heute", effective_attributes=True)

    # all keys in 'attributes' have to be present in 'effective_attributes' as well
    assert set(resp.json["extensions"]["attributes"]) <= set(
        resp.json["extensions"]["effective_attributes"]
    )

    assert (
        resp.json["extensions"]["effective_attributes"]
        == {
            "additional_ipv4addresses": [],
            "additional_ipv6addresses": [],
            "alias": "",
            "bake_agent_package": False,
            "cmk_agent_connection": "pull-agent",
            "contactgroups": {},
            "inventory_failed": False,
            "ipaddress": "",
            "ipv6address": "",
            "labels": {},
            "locked_attributes": [],
            "locked_by": {"instance_id": "", "program_id": "", "site_id": "NO_SITE"},
            "management_address": "",
            "management_ipmi_credentials": None,
            "management_protocol": "none",
            "management_snmp_community": None,
            "meta_data": {
                "created_at": "2022-11-05T00:00:00+00:00",
                "created_by": username,
                "updated_at": "2022-11-05T00:00:00+00:00",
            },
            "network_scan": {
                "addresses": [],
                "exclude_addresses": [],
                "run_as": username,
                "scan_interval": 86400,
                "set_ip_address": True,
                "time_allowed": [{"end": "23:59:59", "start": "00:00:00"}],
            },
            "network_scan_result": {"end": None, "output": "", "start": None, "state": "running"},
            "parents": [],
            "site": "NO_SITE",
            "snmp_community": None,
            "tag_address_family": "ip-v4-only",
            "tag_agent": "cmk-agent",
            "tag_piggyback": "auto-piggyback",
            "tag_snmp_ds": "no-snmp",
        }
        != {
            "additional_ipv4addresses": [],
            "additional_ipv6addresses": [],
            "alias": "",
            "bake_agent_package": False,
            "cmk_agent_connection": "pull-agent",
            "contactgroups": {},
            "inventory_failed": False,
            "ipaddress": "",
            "ipv6address": "",
            "labels": {},
            "locked_attributes": [],
            "locked_by": {"instance_id": "", "program_id": "", "site_id": "NO_SITE"},
            "management_address": "",
            "management_ipmi_credentials": None,
            "management_protocol": "none",
            "management_snmp_community": None,
            "meta_data": {
                "created_at": "2022-11-05T10:01:41.212124+00:00",
                "created_by": username,
                "updated_at": "2023-06-09T10:01:41.259554+00:00",
            },
            "network_scan": {
                "addresses": [],
                "exclude_addresses": [],
                "run_as": username,
                "scan_interval": 86400,
                "set_ip_address": True,
                "time_allowed": [{"end": "23:59:59", "start": "00:00:00"}],
            },
            "network_scan_result": {"end": None, "output": "", "start": None, "state": "running"},
            "parents": [],
            "site": "NO_SITE",
            "snmp_community": None,
            "tag_address_family": "ip-v4-only",
            "tag_agent": "cmk-agent",
            "tag_piggyback": "auto-piggyback",
            "tag_snmp_ds": "no-snmp",
        }
    )
