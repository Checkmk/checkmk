#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import contextlib
import datetime
from collections.abc import Iterator, Sequence
from typing import Literal
from unittest.mock import MagicMock

import pytest
import time_machine
from pytest_mock import MockerFixture

from tests.testlib.unit.rest_api_client import ClientRegistry

from tests.unit.cmk.web_test_app import WebTestAppForCMK

from cmk.ccc import version
from cmk.ccc.hostaddress import HostName
from cmk.ccc.site import SiteId

from cmk.utils import paths
from cmk.utils.global_ident_type import PROGRAM_ID_QUICK_SETUP
from cmk.utils.tags import BuiltinTagConfig

from cmk.automations.results import DeleteHostsResult

from cmk.gui.exceptions import MKUserError
from cmk.gui.logged_in import user
from cmk.gui.openapi.endpoints._common.host_attribute_schemas import (
    BaseHostAttribute,
    BaseHostTagGroup,
)
from cmk.gui.type_defs import CustomHostAttrSpec
from cmk.gui.watolib.configuration_bundle_store import BundleId, ConfigBundleStore
from cmk.gui.watolib.configuration_bundles import create_config_bundle, CreateBundleEntities
from cmk.gui.watolib.custom_attributes import CustomAttrSpecs, save_custom_attrs_to_mk_file
from cmk.gui.watolib.host_attributes import (
    BuiltInHostAttributes,
    BuiltInHostTagGroups,
    HostAttributes,
)
from cmk.gui.watolib.hosts_and_folders import Folder, folder_tree, Host

managedtest = pytest.mark.skipif(
    version.edition(paths.omd_root) is not version.Edition.CME, reason="see #7213"
)


@pytest.fixture()
def quick_setup_config_bundle() -> Iterator[tuple[BundleId, str]]:
    bundle_id = BundleId("bundle_id")
    program_id = PROGRAM_ID_QUICK_SETUP
    create_config_bundle(
        bundle_id=bundle_id,
        bundle={
            "title": "bundle_title",
            "comment": "bundle_comment",
            "owned_by": "cmkadmin",
            "group": "bundle_group",
            "program_id": program_id,
        },
        entities=CreateBundleEntities(),
        user_id=user.id,
        pprint_value=False,
        use_git=False,
        debug=False,
    )
    yield bundle_id, program_id
    store = ConfigBundleStore()
    all_bundles = store.load_for_modification()
    all_bundles.pop(bundle_id)
    store.save(all_bundles, pprint_value=False)


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
    suppress_bake_agents_in_background: MagicMock,
    clients: ClientRegistry,
) -> None:
    clients.HostConfig.create(host_name="foobar", bake_agent=bake_agent)

    if called:
        suppress_bake_agents_in_background.assert_called_once_with(["foobar"], debug=False)
    else:
        suppress_bake_agents_in_background.assert_not_called()


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
    hosts_config = folder_tree().root_folder()._load_hosts_file()
    assert hosts_config is not None
    assert hosts_config["host_attributes"]["foobar"]["locked_attributes"] == ["alias"]
    assert hosts_config["host_attributes"]["foobar"]["locked_by"] == (
        "site_id",
        "dcd",
        "connection_id",
    )


def test_openapi_bulk_add_hosts_with_attributes(clients: ClientRegistry) -> None:
    response = clients.HostConfig.bulk_create(
        entries=[
            {
                "host_name": "ding",
                "folder": "/",
                "attributes": {"ipaddress": "127.0.0.2"},
            },
            {
                "host_name": "dong",
                "folder": "/",
                "attributes": {"ipaddress": "127.0.0.2", "site": "NO_SITE"},
            },
        ]
    ).assert_status_code(200)
    assert len(response.json["value"]) == 2

    clients.HostConfig.bulk_edit(
        entries=[
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
            },
        ]
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
    suppress_bake_agents_in_background: MagicMock,
    clients: ClientRegistry,
) -> None:
    clients.HostConfig.create(host_name="foobar", bake_agent=bake_agent).assert_status_code(200)

    if called:
        suppress_bake_agents_in_background.assert_called_once_with(["foobar"], debug=False)
    else:
        suppress_bake_agents_in_background.assert_not_called()
    suppress_bake_agents_in_background.reset_mock()

    clients.HostConfig.create_cluster(
        host_name="bazfoo", nodes=["foobar"], bake_agent=bake_agent
    ).assert_status_code(200)

    if called:
        suppress_bake_agents_in_background.assert_called_once_with(["bazfoo"], debug=False)
    else:
        suppress_bake_agents_in_background.assert_not_called()


@pytest.mark.parametrize(
    "bake_agent,called",
    [
        ("1", True),
        ("0", False),
        (None, False),
    ],
)
def test_openapi_bulk_add_hosts_bake_agent_parameter(
    clients: ClientRegistry,
    bake_agent: Literal["0", "1"] | None,
    called: bool,
    suppress_bake_agents_in_background: MagicMock,
) -> None:
    resp = clients.HostConfig.bulk_create(
        entries=[
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
        ],
        bake_agent=bake_agent,
    )

    assert len(resp.json["value"]) == 2

    if called:
        suppress_bake_agents_in_background.assert_called_once_with(
            ["foobar", "sample"], debug=False
        )
    else:
        suppress_bake_agents_in_background.assert_not_called()


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
        "cmk.gui.openapi.endpoints.host_config.delete_hosts",
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


def test_move_host(clients: ClientRegistry) -> None:
    clients.Folder.create(
        folder_name="Folder1",
        title="folder1",
        parent="/",
    )
    clients.HostConfig.create(
        host_name="TestHost1",
        folder="/",
    )
    clients.HostConfig.move(
        host_name="TestHost1",
        target_folder="/Folder1",
    )


def test_openapi_bulk_hosts(
    clients: ClientRegistry,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "cmk.gui.openapi.endpoints.host_config.delete_hosts",
        lambda *args, **kwargs: DeleteHostsResult(),
    )

    resp = clients.HostConfig.bulk_create(
        entries=[
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
    )
    assert len(resp.json["value"]) == 2

    clients.HostConfig.bulk_edit(
        entries=[
            {
                "host_name": "foobar",
                "attributes": {
                    "ipaddress": "192.168.1.1",
                    "tag_address_family": "ip-v4-only",
                },
            }
        ]
    )

    # verify attribute ipaddress is set correctly
    resp2 = clients.HostConfig.get(host_name="foobar")
    assert resp2.json["extensions"]["attributes"]["ipaddress"] == "192.168.1.1"

    # remove attribute ipaddress via bulk request
    clients.HostConfig.bulk_edit(
        entries=[{"host_name": "foobar", "remove_attributes": ["ipaddress"]}],
    )

    # verify attribute ipaddress was removed correctly
    resp3 = clients.HostConfig.get(host_name="foobar")
    assert "ipaddress" not in resp3.json["extensions"]["attributes"]

    # adding invalid attribute should fail
    clients.HostConfig.bulk_edit(
        entries=[{"host_name": "foobar", "attributes": {"foobaz": "bar"}}],
        expect_ok=False,
    ).assert_status_code(400)

    # delete host with bulk delete
    clients.HostConfig.bulk_delete(entries=["foobar", "sample"])


@pytest.mark.usefixtures("suppress_remote_automation_calls")
def test_openapi_bulk_simple(clients: ClientRegistry) -> None:
    clients.HostConfig.bulk_create(
        entries=[{"host_name": "example.com", "folder": "/", "attributes": {}}],
    )


@pytest.mark.usefixtures("suppress_remote_automation_calls")
def test_openapi_bulk_with_failed(
    clients: ClientRegistry,
    base: str,
    monkeypatch: pytest.MonkeyPatch,
    aut_user_auth_wsgi_app: WebTestAppForCMK,
) -> None:
    def _raise(_self, _host_name, _attributes):
        if _host_name == "foobar":
            raise MKUserError(None, "fail")
        return _attributes

    monkeypatch.setattr(
        "cmk.gui.watolib.hosts_and_folders.Folder.verify_and_update_host_details",
        _raise,
    )

    resp = clients.HostConfig.bulk_create(
        entries=[
            {"host_name": "foobar", "folder": "/", "attributes": {}},
            {"host_name": "example.com", "folder": "/", "attributes": {}},
        ],
        expect_ok=False,
    ).assert_status_code(400)

    assert resp.json["ext"]["failed_hosts"] == {"foobar": "Validation failed: fail"}
    assert [e["id"] for e in resp.json["ext"]["succeeded_hosts"]["value"]] == ["example.com"]


@pytest.fixture(name="custom_host_attribute")
def _custom_host_attribute() -> Iterator[None]:
    attr = CustomHostAttrSpec(
        {
            "name": "foo",
            "title": "bar",
            "help": "foo",
            "topic": "basic",
            "type": "TextAscii",
            "add_custom_macro": False,
            "show_in_table": False,
        }
    )
    with custom_host_attribute_ctx({"user": [], "host": [attr]}):
        yield


@pytest.fixture(name="custom_host_attribute_basic_topic")
def _custom_host_attribute_with_basic_topic() -> Iterator[None]:
    attr = CustomHostAttrSpec(
        {
            "name": "foo",
            "title": "bar",
            "help": "foo",
            "topic": "basic",
            "type": "TextAscii",
            "add_custom_macro": False,
            "show_in_table": False,
        }
    )
    with custom_host_attribute_ctx({"user": [], "host": [attr]}):
        yield


@contextlib.contextmanager
def custom_host_attribute_ctx(attrs: CustomAttrSpecs) -> Iterator[None]:
    try:
        save_custom_attrs_to_mk_file(attrs)
        yield
    finally:
        save_custom_attrs_to_mk_file({"user": [], "host": []})


def test_openapi_host_created_timestamp(clients: ClientRegistry) -> None:
    HOSTNAME = "foobar.com"

    # Create host
    response = clients.HostConfig.create(
        host_name=HOSTNAME, folder="/", attributes={"ipaddress": "192.168.0.123"}
    )
    created_at_create = response.json["extensions"]["attributes"]["meta_data"]["created_at"]

    # Get host
    response = clients.HostConfig.get(host_name=HOSTNAME)
    created_at_get = response.json["extensions"]["attributes"]["meta_data"]["created_at"]

    # Update host
    response = clients.HostConfig.edit(
        host_name=HOSTNAME, attributes={"ipaddress": "192.168.0.124"}
    )
    created_at_update = response.json["extensions"]["attributes"]["meta_data"]["created_at"]

    assert created_at_create == created_at_get == created_at_update


@pytest.mark.usefixtures("custom_host_attribute")
@pytest.mark.usefixtures("with_host")
def test_openapi_host_has_deleted_custom_attributes(clients: ClientRegistry) -> None:
    # Known custom attribute
    clients.HostConfig.get(host_name="example.com")

    # Set the attribute on the host
    clients.HostConfig.edit(host_name="example.com", attributes={"foo": "bar"})

    # Try to get it with the attribute already deleted
    with custom_host_attribute_ctx({"user": [], "host": []}):
        resp = clients.HostConfig.get(host_name="example.com")

        # foo will still show up in the response, even though it is deleted.
        assert "foo" in resp.json["extensions"]["attributes"]


@pytest.mark.usefixtures("custom_host_attribute")
@pytest.mark.usefixtures("with_host")
def test_openapi_host_custom_attributes(clients: ClientRegistry) -> None:
    # Known custom attribute
    clients.HostConfig.get(
        host_name="example.com",
    )

    clients.HostConfig.edit(
        host_name="example.com",
        attributes={"foo": "bar"},
    )

    # Internal, non-editable attributes shall not be settable.
    clients.HostConfig.edit(
        host_name="example.com",
        attributes={"meta_data": "bar"},
        expect_ok=False,
    ).assert_status_code(400)

    # Unknown custom attribute
    clients.HostConfig.get(
        host_name="example.com",
    )

    clients.HostConfig.edit(
        host_name="example.com",
        attributes={"foo2": "bar"},
        expect_ok=False,
    ).assert_status_code(400)


@pytest.mark.usefixtures("with_host")
def test_openapi_host_collection(clients: ClientRegistry) -> None:
    resp = clients.HostConfig.get_all()

    for host in resp.json["value"]:
        # Check that all entries are domain objects
        assert "extensions" in host
        assert "members" in host
        assert "title" in host
        assert "id" in host


@pytest.mark.usefixtures("with_host")
def test_openapi_host_collection_effective_attributes(clients: ClientRegistry) -> None:
    resp1 = clients.HostConfig.get_all(effective_attributes=True)
    for host in resp1.json["value"]:
        assert isinstance(host["extensions"]["effective_attributes"], dict)

    resp2 = clients.HostConfig.get_all(effective_attributes=False)
    for host in resp2.json["value"]:
        assert "effective_attributes" not in host["extensions"]


@pytest.mark.usefixtures("with_host")
def test_host_collection_fields(clients: ClientRegistry) -> None:
    resp = clients.HostConfig.get_all(fields="(id)")
    # TODO: update response models to not automatically add fields
    # assert resp.json == {"id": "host"}, "Expected only the id field to be returned"
    assert resp.json == {"id": "host", "domainType": "host_config"}

    resp = clients.HostConfig.get_all(fields="!(value~extensions)")
    assert "value" in resp.json, "Expected the value field to be returned"
    for host in resp.json["value"]:
        assert host.get("links"), "Expected the links field to be returned and computed"
        assert "extensions" not in host, "Expected the extensions field to not be returned"


def test_host_collection_invalid_fields(clients: ClientRegistry) -> None:
    clients.HostConfig.get_all(fields="invalid_filter", expect_ok=False).assert_status_code(400)


@pytest.mark.usefixtures("with_host")
def test_openapi_list_hosts_include_links(clients: ClientRegistry) -> None:
    default_response = clients.HostConfig.get_all()
    enabled_response = clients.HostConfig.get_all(include_links=True)
    disabled_response = clients.HostConfig.get_all(include_links=False)

    assert len(default_response.json["value"]) > 0

    assert default_response.json == disabled_response.json
    assert any(bool(value["links"]) for value in enabled_response.json["value"])
    assert all("links" not in value for value in disabled_response.json["value"])


@pytest.mark.usefixtures("inline_background_jobs")
def test_openapi_host_rename(
    clients: ClientRegistry,
    monkeypatch: pytest.MonkeyPatch,
    mocker: MockerFixture,
) -> None:
    monkeypatch.setattr("cmk.gui.openapi.endpoints.host_config.has_pending_changes", lambda: False)
    automation = mocker.patch("cmk.gui.watolib.host_rename.rename_hosts")

    clients.HostConfig.create(
        host_name="foobar",
        folder="/",
    )
    clients.HostConfig.rename(
        host_name="foobar",
        new_name="foobaz",
    ).assert_status_code(204)
    automation.assert_called_once()


def test_openapi_host_rename_wait_for_completion_without_job(
    clients: ClientRegistry,
) -> None:
    clients.HostConfig.rename_wait_for_completion(
        expect_ok=False, follow_redirects=False
    ).assert_status_code(404)


@pytest.mark.usefixtures("suppress_remote_automation_calls")
def test_openapi_host_rename_error_on_not_existing_host(
    clients: ClientRegistry,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("cmk.gui.openapi.endpoints.host_config.has_pending_changes", lambda: False)

    clients.HostConfig.create(
        host_name="foobar",
        folder="/",
    )
    clients.HostConfig.get("foobar")
    clients.HostConfig.rename(
        host_name="fooba",
        new_name="foobaz",
        follow_redirects=False,
        expect_ok=False,
    )


@pytest.mark.usefixtures("suppress_remote_automation_calls")
def test_openapi_host_rename_on_invalid_hostname(
    clients: ClientRegistry,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("cmk.gui.openapi.endpoints.host_config.has_pending_changes", lambda: False)

    clients.HostConfig.create(
        host_name="foobar",
        folder="/",
    )
    clients.HostConfig.get("foobar")
    clients.HostConfig.rename(
        host_name="foobar",
        new_name="foobar",
        expect_ok=False,
    ).assert_status_code(400)


@pytest.mark.usefixtures("suppress_remote_automation_calls")
def test_openapi_host_rename_locked_by_quick_setup(
    clients: ClientRegistry,
    quick_setup_config_bundle: tuple[BundleId, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("cmk.gui.openapi.endpoints.host_config.has_pending_changes", lambda: False)

    bundle_id, program_id = quick_setup_config_bundle
    clients.HostConfig.create(
        host_name="foobar",
        folder="/",
        attributes={
            "locked_by": {
                "site_id": "heute",
                "program_id": program_id,
                "instance_id": bundle_id,
            }
        },
    )
    clients.HostConfig.rename(
        host_name="foobar",
        new_name="foobar123",
        expect_ok=False,
    ).assert_status_code(400)


@pytest.mark.usefixtures("suppress_remote_automation_calls")
def test_openapi_host_delete_locked_by_quick_setup(
    clients: ClientRegistry,
    quick_setup_config_bundle: tuple[BundleId, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bundle_id, program_id = quick_setup_config_bundle
    clients.HostConfig.create(
        host_name="foobar",
        folder="/",
        attributes={
            "locked_by": {
                "site_id": "heute",
                "program_id": program_id,
                "instance_id": bundle_id,
            }
        },
    )
    clients.HostConfig.delete(
        host_name="foobar",
        expect_ok=False,
    ).assert_status_code(400)


@pytest.mark.usefixtures("suppress_remote_automation_calls")
def test_openapi_host_update_locked_by_quick_setup(
    clients: ClientRegistry,
    quick_setup_config_bundle: tuple[BundleId, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bundle_id, program_id = quick_setup_config_bundle
    clients.HostConfig.create(
        host_name="foobar",
        folder="/",
        attributes={
            "tag_address_family": "no-ip",
            "locked_attributes": ["tag_address_family"],
            "locked_by": {
                "site_id": "heute",
                "program_id": program_id,
                "instance_id": bundle_id,
            },
        },
    )
    clients.HostConfig.edit(
        host_name="foobar",
        attributes={"tag_address_family": "no-ip"},  # should fail because we remove the lock
        expect_ok=False,
    ).assert_status_code(400)

    clients.HostConfig.edit(
        host_name="foobar",
        update_attributes={"tag_address_family": "ip-v4-only"},
        expect_ok=False,
    ).assert_status_code(400)

    clients.HostConfig.edit(
        host_name="foobar",
        remove_attributes=["tag_address_family"],
        expect_ok=False,
    ).assert_status_code(400)


@pytest.mark.usefixtures("suppress_remote_automation_calls")
def test_openapi_host_folder_config_normalization(clients: ClientRegistry) -> None:
    def _create_folder(fname: str, parent: str) -> None:
        clients.Folder.create(folder_name=fname, title=fname, parent=parent)
        parent += f"{fname}~"

    def _create_folders_recursive(folders: Sequence[str]) -> None:
        _create_folder(folders[0], "~")
        parent = f"~{folders[0]}"
        for fname in folders[1:]:
            _create_folder(fname, parent)
            parent += f"~{fname}"

    _create_folders_recursive(["I", "want", "those"])

    clients.HostConfig.create(host_name="foobar", folder="/I/want/those")
    resp = clients.HostConfig.get(host_name="foobar")
    assert resp.json["extensions"]["folder"] == "/I/want/those"


@pytest.mark.usefixtures("suppress_remote_automation_calls")
def test_openapi_host_rename_with_pending_activate_changes(
    clients: ClientRegistry,
) -> None:
    clients.HostConfig.create(
        host_name="foobar",
        folder="/",
    )
    clients.HostConfig.get(
        host_name="foobar",
    )
    clients.HostConfig.rename(
        host_name="foobar",
        new_name="foobaz",
        expect_ok=False,
    ).assert_status_code(409)


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
        host_name="TestHost1",
        target_folder="/folder-that-does-not-exist",
        expect_ok=False,
    ).assert_status_code(400)


@pytest.mark.usefixtures("suppress_remote_automation_calls")
def test_openapi_host_move_of_non_existing_host(clients: ClientRegistry) -> None:
    clients.HostConfig.move(
        host_name="foobaz",
        target_folder="/",
        expect_ok=False,
    ).assert_status_code(404)


@pytest.mark.usefixtures("suppress_remote_automation_calls")
def test_openapi_host_update_invalid(clients: ClientRegistry) -> None:
    clients.HostConfig.create(
        host_name="example.com",
        folder="/",
    )
    clients.HostConfig.edit(
        host_name="example.com",
        attributes={"ipaddress": "192.168.0.123"},
        update_attributes={"ipaddress": "192.168.0.123"},
        remove_attributes=["tag_foobar"],
        expect_ok=False,
    ).assert_status_code(400)


@managedtest
def test_openapi_create_host_with_contact_group(clients: ClientRegistry) -> None:
    clients.ContactGroup.create(
        name="code_monkeys",
        alias="banana_team",
        customer="global",
    )
    clients.HostConfig.create(
        host_name="example.com",
        folder="/",
        attributes={
            "ipaddress": "192.168.0.123",
            "contactgroups": {
                "groups": ["code_monkeys"],
                "use": False,
                "use_for_services": False,
                "recurse_use": False,
                "recurse_perms": False,
            },
        },
    )


@managedtest
def test_openapi_host_with_custom_attributes(
    clients: ClientRegistry,
    custom_host_attribute_basic_topic: None,
) -> None:
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
def test_openapi_host_with_inventory_failed(clients: ClientRegistry) -> None:
    resp = clients.HostConfig.create(
        host_name="example.com",
        folder="/",
        attributes={
            "ipaddress": "192.168.0.123",
            "inventory_failed": True,
        },
    )
    assert resp.json["extensions"]["attributes"]["inventory_failed"] is True


@managedtest
def test_openapi_host_with_waiting_for_discovery(clients: ClientRegistry) -> None:
    resp = clients.HostConfig.create(
        host_name="example.com",
        folder="/",
        attributes={
            "ipaddress": "192.168.0.123",
            "waiting_for_discovery": True,
        },
    )
    assert resp.json["extensions"]["attributes"]["waiting_for_discovery"] is True


def test_openapi_host_with_invalid_labels(clients: ClientRegistry) -> None:
    clients.HostConfig.create(
        folder="/",
        host_name="example.com",
        attributes={"labels": {"label": ["invalid_label_entry", "another_one"]}},
        expect_ok=False,
    ).assert_status_code(400)

    clients.HostConfig.create(
        folder="/",
        host_name="example.com",
        attributes={"labels": {"label": "va:lue"}},
        expect_ok=False,
    ).assert_status_code(400)

    clients.HostConfig.create(
        folder="/",
        host_name="example.com",
        attributes={"labels": {"la:bel": "value"}},
        expect_ok=False,
    ).assert_status_code(400)


def test_openapi_host_non_existent_site(clients: ClientRegistry) -> None:
    non_existing_site_name = "i_am_not_existing"
    resp = clients.HostConfig.create(
        folder="/",
        host_name="example.com",
        attributes={"site": non_existing_site_name},
        expect_ok=False,
    )
    resp.assert_status_code(400)
    assert "site" in resp.json["fields"]["attributes"]


def test_openapi_host_with_labels(clients: ClientRegistry) -> None:
    resp = clients.HostConfig.create(
        folder="/",
        host_name="example.com",
        attributes={"labels": {"label": "value"}},
    )
    assert resp.json["extensions"]["attributes"]["labels"] == {"label": "value"}


def test_openapi_host_with_invalid_snmp_community_option(
    clients: ClientRegistry,
) -> None:
    clients.HostConfig.create(
        folder="/",
        host_name="example.com",
        attributes={"snmp_community": {"type": "v1_v2_community"}},
        expect_ok=False,
    ).assert_status_code(400)


def test_openapi_all_hosts_with_non_existing_site(
    clients: ClientRegistry,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def mock_all_hosts_recursively(_cls):
        return {
            "foo": Host(
                folder=folder_tree().root_folder(),
                host_name=HostName("foo"),
                attributes=HostAttributes({"site": SiteId("a_non_existing_site")}),
                cluster_nodes=None,
            )
        }

    monkeypatch.setattr(Folder, "all_hosts_recursively", mock_all_hosts_recursively)
    clients.HostConfig.get_all()


def test_openapi_host_with_non_existing_site(
    clients: ClientRegistry,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def mock_host(_hostname):
        return Host(
            folder=folder_tree().root_folder(),
            host_name=HostName("foo"),
            attributes=HostAttributes({"site": SiteId("a_non_existing_site")}),
            cluster_nodes=None,
        )

    monkeypatch.setattr(Host, "host", mock_host)
    resp = clients.HostConfig.get(host_name="foo")
    assert resp.json["extensions"]["attributes"]["site"] == "Unknown Site: a_non_existing_site"


def test_openapi_bulk_create_permission_missmatch_regression(
    clients: ClientRegistry,
) -> None:
    clients.HostConfig.bulk_create(entries=[])


def test_openapi_host_config_attributes_as_string_crash_regression(
    clients: ClientRegistry,
) -> None:
    attributes = "{'ipaddress':'192.168.0.123'}"  # note that this is a str
    resp = clients.HostConfig.create(
        folder="/",
        host_name="example.com",
        attributes=attributes,
        expect_ok=False,
    )
    resp.assert_status_code(400)

    resp.json["fields"]["attributes"] == [f"Data type is invalid: {attributes}"]


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


def test_openapi_host_config_ipmi_credentials_empty(
    clients: ClientRegistry,
) -> None:
    clients.HostConfig.create(
        folder="/",
        host_name="heute",
        attributes={
            "management_ipmi_credentials": None,
            "management_snmp_community": None,
        },
    ).assert_status_code(200)
    resp = clients.HostConfig.get("heute")
    resp.assert_status_code(200)
    assert resp.json["extensions"]["attributes"]["management_ipmi_credentials"] is None
    assert resp.json["extensions"]["attributes"]["management_snmp_community"] is None


@managedtest
@pytest.mark.usefixtures("with_host")
def test_openapi_host_config_show_host_disregards_contact_groups(
    clients: ClientRegistry,
) -> None:
    """This test makes sure a user cannot see the config of a host that is not assigned to their contact groups."""
    clients.ContactGroup.create("no_hosts_in_here", alias="no_hosts_in_here")
    clients.ContactGroup.create("all_hosts_in_here", alias="all_hosts_in_here")

    clients.User.create(
        username="unable_to_see_host",
        fullname="unable_to_see_host",
        customer="provider",
        contactgroups=["no_hosts_in_here"],
        auth_option={"auth_type": "password", "password": "supersecretish"},
    )

    clients.Rule.create(
        "host_contactgroups",
        value_raw="'all_hosts_in_here'",
        folder="/",
        conditions={},
    )

    clients.Host.set_credentials("unable_to_see_host", "supersecretish")

    resp = clients.HostConfig.get("heute", expect_ok=False).assert_status_code(403)
    assert resp.json["title"] == "Forbidden"
    assert "heute" in resp.json["detail"]


@managedtest
def test_openapi_list_hosts_does_not_show_inaccessible_hosts(
    clients: ClientRegistry,
) -> None:
    clients.ContactGroup.create(name="does_not_see_everything", alias="does_not_see_everything")
    clients.User.create(
        username="unable_to_see_all_host",
        fullname="unable_to_see_all_host",
        customer="provider",
        contactgroups=["does_not_see_everything"],
        auth_option={"auth_type": "password", "password": "supersecretish"},
    )

    clients.HostConfig.create(
        host_name="should_be_visible",
        attributes={"contactgroups": {"groups": ["does_not_see_everything"], "use": True}},
    )
    clients.HostConfig.create(
        host_name="should_not_be_invisible",
    )

    clients.Host.set_credentials("unable_to_see_all_host", "supersecretish")
    resp = clients.HostConfig.get_all()
    host_names = [entry["id"] for entry in resp.json["value"]]
    assert "should_be_visible" in host_names
    assert "should_not_be_invisible" not in host_names


@time_machine.travel(datetime.datetime.fromisoformat("1998-02-09T00:00:00+00:00"), tick=False)
def test_openapi_effective_attributes_are_transformed_on_their_way_out_regression(
    clients: ClientRegistry, with_admin: tuple[str, str]
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


@managedtest
def test_move_to_folder_with_different_contact_group(clients: ClientRegistry) -> None:
    clients.ContactGroup.create(
        name="test_contact_group",
        alias="cg_alias",
    )

    clients.User.create(
        username="user1",
        fullname="user1_fullname",
        customer="provider",
        contactgroups=["test_contact_group"],
        auth_option={
            "auth_type": "password",
            "password": "asflkjas^asf@adf%5Ah!@%^sfadf",
        },
        roles=["user"],
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
    assert resp.json["detail"] == "You lack the permissions to move host TestHost1 to ~Folder2."


@managedtest
def test_move_from_folder_with_different_contact_group(clients: ClientRegistry) -> None:
    # Create test contact group
    clients.ContactGroup.create(
        name="test_contact_group",
        alias="cg_alias",
    )

    # Create folder, no contact group
    clients.Folder.create(
        folder_name="Folder1",
        title="Folder1",
        parent="/",
    )  # no contact group set

    # Create folder with test contact group
    clients.Folder.create(
        folder_name="Folder2",
        title="Folder2",
        parent="/",
        attributes={"contactgroups": {"groups": ["test_contact_group"]}},
    )

    # Create host in Folder 1, no contact group
    clients.HostConfig.create(
        host_name="TestHost1",
        folder="/Folder1",
    )

    # Create test user with role = user
    clients.User.create(
        username="user1",
        fullname="user1_fullname",
        customer="provider",
        contactgroups=["test_contact_group"],
        auth_option={
            "auth_type": "password",
            "password": "asflkjas^asf@adf%5Ah!@%^sfadf",
        },
        roles=["user"],
    )

    # Set test client's credentials to test user
    clients.User.set_credentials(
        username="user1",
        password="asflkjas^asf@adf%5Ah!@%^sfadf",
    )

    # Try to move the test host to folder2
    resp = clients.HostConfig.move(
        host_name="TestHost1",
        target_folder="/Folder2",
        expect_ok=False,
    )

    resp.assert_status_code(403)
    assert resp.json["title"] == "Permission denied"
    assert resp.json["detail"] == "You lack the permissions to move host TestHost1 to ~Folder2."


@managedtest
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
        customer="provider",
        contactgroups=["test_contact_group_1"],
        auth_option={
            "auth_type": "password",
            "password": "asflkjas^asf@adf%5Ah!@%^sfadf",
        },
        roles=["user"],
    )

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

    # Move the Host
    clients.HostConfig.move(
        host_name="TestHost1",
        target_folder="/Folder2",
    )


@managedtest
def test_move_host_to_the_same_folder(clients: ClientRegistry) -> None:
    clients.Folder.create(
        folder_name="Folder1",
        title="Folder1",
        parent="/",
    )
    clients.HostConfig.create(
        host_name="TestHost1",
        folder="/Folder1",
    )

    resp = clients.HostConfig.move(
        host_name="TestHost1",
        target_folder="/Folder1",
        expect_ok=False,
    )
    resp.assert_status_code(400)
    resp.json["title"] = "Invalid move action"


@pytest.mark.usefixtures("request_context", "custom_host_attribute")
def test_openapi_host_config_effective_attributes_includes_custom_attributes_regression(
    clients: ClientRegistry,
) -> None:
    clients.HostConfig.create(host_name="test_host", attributes={"foo": "blub"})

    resp = clients.HostConfig.get("test_host", effective_attributes=True)
    assert resp.json["extensions"]["effective_attributes"]["foo"] == "blub"


@pytest.mark.usefixtures("suppress_spec_generation_in_background")
def test_openapi_host_config_effective_attributes_includes_tags_regression(
    clients: ClientRegistry,
) -> None:
    clients.HostTagGroup.create(ident="foo", title="foo", tags=[{"id": "bar", "title": "bar"}])
    clients.HostConfig.create(host_name="test_host", attributes={"tag_foo": "bar"})

    resp = clients.HostConfig.get("test_host", effective_attributes=True)
    assert resp.json["extensions"]["effective_attributes"]["tag_foo"] == "bar"


def test_openapi_host_config_effective_attributes_labels_from_parent_folder(
    clients: ClientRegistry,
) -> None:
    """Tests inheritance of host labels from parent folder"""
    clients.Folder.create(
        folder_name="test_folder",
        title="Test folder",
        parent="/",
        attributes={"labels": {"foo1": "bar1"}},
    )
    clients.HostConfig.create(
        host_name="test_host",
        attributes={"labels": {"foo2": "bar2"}},
        folder="/test_folder",
    )

    resp = clients.HostConfig.get("test_host", effective_attributes=True)
    assert resp.json["extensions"]["effective_attributes"]["labels"] == {
        "foo1": "bar1",
        "foo2": "bar2",
    }
    assert resp.json["extensions"]["attributes"]["labels"] == {
        "foo2": "bar2",
    }


@managedtest
def test_openapi_host_config_correct_contactgroup_default(
    clients: ClientRegistry, with_admin: tuple[str, str]
) -> None:
    username, password = with_admin
    clients.HostConfig.set_credentials(username, password)

    clients.HostConfig.create(host_name="localhost")
    resp = clients.HostConfig.get(host_name="localhost", effective_attributes=True)

    assert "contactgroups" not in resp.json["extensions"]["attributes"]
    assert resp.json["extensions"]["effective_attributes"]["contactgroups"] == {
        "groups": [],
        "recurse_perms": False,
        "recurse_use": False,
        "use": False,
        "use_for_services": False,
    }


@managedtest
@time_machine.travel(datetime.datetime.fromisoformat("2022-11-05T00:00:00+00:00"), tick=False)
def test_openapi_host_config_effective_attributes_includes_all_host_attributes_regression(
    clients: ClientRegistry, with_admin: tuple[str, str]
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
            "contactgroups": {
                "groups": [],
                "recurse_perms": False,
                "recurse_use": False,
                "use": False,
                "use_for_services": False,
            },
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
            "network_scan_result": {
                "end": None,
                "output": "",
                "start": None,
                "state": "running",
            },
            "parents": [],
            "site": "NO_SITE",
            "snmp_community": None,
            "tag_address_family": "ip-v4-only",
            "tag_agent": "cmk-agent",
            "tag_piggyback": "auto-piggyback",
            "tag_snmp_ds": "no-snmp",
            "waiting_for_discovery": False,
        }
        != {
            "additional_ipv4addresses": [],
            "additional_ipv6addresses": [],
            "alias": "",
            "bake_agent_package": False,
            "cmk_agent_connection": "pull-agent",
            "contactgroups": {
                "groups": [],
                "recurse_perms": False,
                "recurse_use": False,
                "use": False,
                "use_for_services": False,
            },
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
            "network_scan_result": {
                "end": None,
                "output": "",
                "start": None,
                "state": "running",
            },
            "parents": [],
            "site": "NO_SITE",
            "snmp_community": None,
            "tag_address_family": "ip-v4-only",
            "tag_agent": "cmk-agent",
            "tag_piggyback": "auto-piggyback",
            "tag_snmp_ds": "no-snmp",
            "waiting_for_discovery": False,
        }
    )


@managedtest
def test_openapi_only_one_edit_action(clients: ClientRegistry) -> None:
    clients.HostConfig.create(
        host_name="test_host",
        folder="/",
        attributes={"ipaddress": "192.168.0.123"},
    )

    expected_error_msg = (
        "This endpoint only allows 1 action (set/update/remove) per call, you specified"
    )

    resp1 = clients.HostConfig.edit(
        host_name="test_host",
        attributes={"ipaddress": "192.168.0.123"},
        update_attributes={"ipaddress": "192.168.0.124"},
        remove_attributes=["tag_foobar"],
        etag=None,
        expect_ok=False,
    )
    resp1.assert_status_code(400)
    assert expected_error_msg in resp1.json["fields"]["_schema"][0]

    resp2 = clients.HostConfig.edit(
        host_name="test_host",
        update_attributes={"ipaddress": "192.168.0.124"},
        remove_attributes=["tag_foobar"],
        etag=None,
        expect_ok=False,
    )
    resp2.assert_status_code(400)
    assert expected_error_msg in resp2.json["fields"]["_schema"][0]

    resp3 = clients.HostConfig.edit(
        host_name="test_host",
        attributes={"ipaddress": "192.168.0.124"},
        update_attributes={"ipaddress": "192.168.0.125"},
        etag=None,
        expect_ok=False,
    )
    resp3.assert_status_code(400)
    assert expected_error_msg in resp3.json["fields"]["_schema"][0]

    resp4 = clients.HostConfig.edit(
        host_name="test_host",
        attributes={"ipaddress": "192.168.0.123"},
        remove_attributes=["tag_foobar"],
        etag=None,
        expect_ok=False,
    )
    resp4.assert_status_code(400)
    assert expected_error_msg in resp4.json["fields"]["_schema"][0]


invalid_host_names = (
    "test_host\\n",
    "test_host\n",
    "test_\nhost",
    "\ntest_host",
)


@managedtest
@pytest.mark.parametrize("host_name", invalid_host_names)
def test_create_host_with_newline_in_the_name(
    clients: ClientRegistry,
    host_name: str,
) -> None:
    resp = clients.HostConfig.create(
        host_name=host_name,
        folder="/",
        attributes={"ipaddress": "192.168.0.123"},
        expect_ok=False,
    )
    resp.assert_status_code(400)
    assert (
        resp.json["fields"]["host_name"][0]
        == f"{host_name!r} does not match pattern '^[-0-9a-zA-Z_.]+\\\\Z'."
    )


def test_create_host_with_too_long_of_a_name(
    clients: ClientRegistry,
) -> None:
    resp = clients.HostConfig.create(
        host_name=255 * "a",
        expect_ok=False,
    )
    resp.assert_status_code(400)
    assert resp.json["fields"]["host_name"][0] == f"host address too long: {16 * 'a' + '…'!r}"


@managedtest
def test_bulk_delete_no_entries(clients: ClientRegistry) -> None:
    r = clients.HostConfig.bulk_delete(entries=[], expect_ok=False)
    r.assert_status_code(400)
    assert r.json["fields"] == {"entries": ["At least one entry is required"]}


@managedtest
def test_move_host_between_nested_folders(clients: ClientRegistry) -> None:
    clients.Folder.create(
        folder_name="F1",
        title="f1",
        parent="/",
    )

    clients.Folder.create(
        folder_name="F11",
        title="f11",
        parent="/F1",
    )

    clients.Folder.create(
        folder_name="F111",
        title="f111",
        parent="/F1/F11",
    )

    clients.Folder.create(
        folder_name="F1111",
        title="f1111",
        parent="/F1/F11/F111",
    )

    clients.HostConfig.create(host_name="host1", folder="/")
    clients.HostConfig.move(host_name="host1", target_folder="~F1")
    clients.HostConfig.move(host_name="host1", target_folder="~F1~F11")
    clients.HostConfig.move(host_name="host1", target_folder="~F1~F11~F111")
    clients.HostConfig.move(host_name="host1", target_folder="~F1~F11~F111~F1111")
    clients.HostConfig.move(host_name="host1", target_folder="~F1~F11~F111")
    clients.HostConfig.move(host_name="host1", target_folder="~F1~F11")
    clients.HostConfig.move(host_name="host1", target_folder="~F1")


@managedtest
def test_update_host_parent_must_exist(clients: ClientRegistry) -> None:
    clients.HostConfig.create(host_name="test_host")
    clients.HostConfig.create(host_name="parent_host", attributes={"parents": ["test_host"]})
    resp = clients.HostConfig.edit(
        host_name="test_host",
        update_attributes={"parents": ["non-existent"]},
        expect_ok=False,
    )
    resp.assert_status_code(400)
    assert resp.json["detail"] == "These fields have problems: update_attributes"
    assert (
        resp.json["fields"]["update_attributes"]["parents"]["0"][0]
        == "Host not found: 'non-existent'"
    )


@managedtest
def test_update_host_parent_must_be_list_of_strings(clients: ClientRegistry) -> None:
    clients.HostConfig.create(host_name="test_host")
    resp = clients.HostConfig.edit(
        host_name="test_host",
        update_attributes={"parents": "wrong-type"},
        expect_ok=False,
    )
    resp.assert_status_code(400)
    assert resp.json["detail"] == "These fields have problems: update_attributes"
    assert "Not a valid list." in resp.json["fields"]["update_attributes"]["parents"]


def test_openapi_create_host_in_folder_with_umlaut(clients: ClientRegistry) -> None:
    folder_name = "ümlaut"
    clients.Folder.create(
        parent="/",
        folder_name=folder_name,
        title=folder_name,
    )
    response = clients.HostConfig.create(host_name="host1", folder=f"~{folder_name}")
    assert response.status_code == 200


def test_openapi_list_hosts_with_include_links(clients: ClientRegistry) -> None:
    clients.HostConfig.create(host_name="host1")
    resp = clients.HostConfig.get_all(include_links=True)
    assert len(resp.json["value"][0]["links"])


class TestHostsFilters:
    """Test cases for filtering hosts by various attributes."""

    def test_openapi_hostnames_filter(self, clients: ClientRegistry) -> None:
        clients.HostConfig.bulk_create(
            entries=[
                {"host_name": "host1", "folder": "/"},
                {"host_name": "host2", "folder": "/"},
                {"host_name": "host3", "folder": "/"},
            ]
        )

        resp = clients.HostConfig.get_all(search={"hostnames": ["host1", "host2"]})
        assert {entry["id"] for entry in resp.json["value"]} == {"host1", "host2"}

    def test_openapi_not_matching_site_filter(self, clients: ClientRegistry) -> None:
        clients.HostConfig.bulk_create(
            entries=[
                {
                    "host_name": "host1",
                    "folder": "/",
                    "attributes": {"site": "NO_SITE"},
                },
            ]
        )
        resp = clients.HostConfig.get_all(search={"site": "INVALID_SITE"})
        assert not resp.json["value"]


def test_openapi_built_in_host_attributes_in_sync() -> None:
    known_exceptions = ["meta_data", "network_scan_result"]
    if version.edition(paths.omd_root) is version.Edition.CRE:
        known_exceptions.append("bake_agent_package")
    if version.edition(paths.omd_root) not in [
        version.Edition.CME,
        version.Edition.CCE,
    ]:
        known_exceptions.append("cmk_agent_connection")

    assert set(BuiltInHostAttributes.__annotations__) == set(
        list(BaseHostAttribute().fields.keys()) + known_exceptions
    )


def test_openapi_built_in_tag_groups_in_sync() -> None:
    built_in_tag_group_keys = {
        "tag_" + tag_group.id for tag_group in BuiltinTagConfig().get_tag_groups()
    }
    assert built_in_tag_group_keys == set(BuiltInHostTagGroups.__annotations__)
    assert built_in_tag_group_keys == set(BaseHostTagGroup().fields.keys())
