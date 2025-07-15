#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import random
import string

import pytest
from pytest import FixtureRequest

from cmk.ccc import version
from cmk.gui.openapi.endpoints.contact_group_config.common import APIInventoryPaths
from cmk.utils import paths
from tests.testlib.unit.rest_api_client import ClientRegistry, GroupConfig
from tests.unit.cmk.web_test_app import WebTestAppForCMK

managedtest = pytest.mark.skipif(
    version.edition(paths.omd_root) is not version.Edition.CME, reason="see #7213"
)

ESCAPED_GROUP_NAME_PATTERN = "^(?!\\\\.\\\\.$|\\\\.$)[-a-zA-Z0-9_\\\\.]*\\\\Z"


@pytest.fixture(name="group_type", params=["host", "contact", "service"])
def fixture_group_type(request: FixtureRequest) -> str:
    return request.param


@pytest.fixture(name="group_client")
def fixture_group_client(clients: ClientRegistry, group_type: str) -> GroupConfig:
    return getattr(clients, f"{group_type.title()}Group")


@managedtest
def test_required_alias_field_create(group_client: GroupConfig) -> None:
    group_client.create(name="RandleMcMurphy", alias="", expect_ok=False).assert_status_code(400)


@managedtest
@pytest.mark.parametrize("group_type", ["host", "contact", "service"])
def test_openapi_groups(
    base: str,
    monkeypatch: pytest.MonkeyPatch,
    group_type: str,
    aut_user_auth_wsgi_app: WebTestAppForCMK,
) -> None:
    aut_user_auth_wsgi_app.call_method(
        "post",
        base + f"/domain-types/{group_type}_group_config/collections/all",
        params=json.dumps({"name": "Invalid%&name", "alias": "Invalid", "customer": "provider"}),
        status=400,
        headers={"Accept": "application/json"},
        content_type="application/json",
    )

    name = _random_string(10)
    alias = _random_string(10)

    group = {"name": name, "alias": alias, "customer": "provider"}

    base = "/NO_SITE/check_mk/api/1.0"
    resp = aut_user_auth_wsgi_app.call_method(
        "post",
        base + f"/domain-types/{group_type}_group_config/collections/all",
        params=json.dumps(group),
        status=200,
        headers={"Accept": "application/json"},
        content_type="application/json",
    )

    _ = aut_user_auth_wsgi_app.call_method(
        "get",
        base + f"/domain-types/{group_type}_group_config/collections/all",
        status=200,
        headers={"Accept": "application/json"},
    )

    resp = aut_user_auth_wsgi_app.follow_link(
        resp,
        "self",
        status=200,
        headers={"Accept": "application/json"},
    )

    update_group = {"alias": f"{alias} update"}

    aut_user_auth_wsgi_app.follow_link(
        resp,
        ".../update",
        params=json.dumps(update_group),
        headers={"If-Match": "foo bar", "Accept": "application/json"},
        status=412,
        content_type="application/json",
    )

    resp = aut_user_auth_wsgi_app.follow_link(
        resp,
        ".../update",
        params=json.dumps(update_group),
        headers={"If-Match": resp.headers["ETag"], "Accept": "application/json"},
        status=200,
        content_type="application/json",
    )

    monkeypatch.setattr("cmk.gui.mkeventd.wato._get_rule_stats_from_ec", lambda: {})
    aut_user_auth_wsgi_app.follow_link(
        resp,
        ".../delete",
        status=204,
        headers={"Accept": "application/json"},
        content_type="application/json",
    )


@managedtest
@pytest.mark.parametrize("group_type", ["host", "service", "contact"])
def test_openapi_bulk_groups(
    monkeypatch: pytest.MonkeyPatch,
    group_type: str,
    aut_user_auth_wsgi_app: WebTestAppForCMK,
) -> None:
    groups = [
        {"name": _random_string(10), "alias": _random_string(10), "customer": "provider"}
        for _i in range(2)
    ]

    base = "/NO_SITE/check_mk/api/1.0"
    resp = aut_user_auth_wsgi_app.call_method(
        "post",
        base + f"/domain-types/{group_type}_group_config/actions/bulk-create/invoke",
        params=json.dumps({"entries": groups}),
        headers={"Accept": "application/json"},
        status=200,
        content_type="application/json",
    )
    assert len(resp.json["value"]) == 2

    resp = aut_user_auth_wsgi_app.call_method(
        "get",
        base + f"/objects/{group_type}_group_config/{groups[0]['name']}",
        status=200,
        headers={"Accept": "application/json"},
    )
    assert resp.json_body["extensions"]["customer"] == "provider"

    _resp = aut_user_auth_wsgi_app.call_method(
        "post",
        base + f"/domain-types/{group_type}_group_config/actions/bulk-create/invoke",
        params=json.dumps({"entries": groups}),
        headers={"Accept": "application/json"},
        status=400,
        content_type="application/json",
    )

    update_groups = [
        {
            "name": group["name"],
            "attributes": {"alias": group["alias"], "customer": "global"},
        }
        for group in groups
    ]

    _resp = aut_user_auth_wsgi_app.call_method(
        "put",
        base + f"/domain-types/{group_type}_group_config/actions/bulk-update/invoke",
        params=json.dumps({"entries": update_groups}),
        headers={"Accept": "application/json"},
        status=200,
        content_type="application/json",
    )

    resp = aut_user_auth_wsgi_app.call_method(
        "get",
        base + f"/objects/{group_type}_group_config/{groups[0]['name']}",
        status=200,
        headers={"Accept": "application/json"},
    )
    assert resp.json_body["extensions"]["customer"] == "global"

    partial_update_groups = [
        {
            "name": group["name"],
            "attributes": {
                "alias": f"{group['alias']} partial",
            },
        }
        for group in groups
    ]

    _resp = aut_user_auth_wsgi_app.call_method(
        "put",
        base + f"/domain-types/{group_type}_group_config/actions/bulk-update/invoke",
        params=json.dumps({"entries": partial_update_groups}),
        headers={"Accept": "application/json"},
        status=200,
        content_type="application/json",
    )

    resp = aut_user_auth_wsgi_app.call_method(
        "get",
        base + f"/objects/{group_type}_group_config/{groups[0]['name']}",
        headers={"Accept": "application/json"},
        status=200,
    )
    assert resp.json_body["extensions"]["customer"] == "global"

    monkeypatch.setattr("cmk.gui.mkeventd.wato._get_rule_stats_from_ec", lambda: {})
    _resp = aut_user_auth_wsgi_app.call_method(
        "post",
        base + f"/domain-types/{group_type}_group_config/actions/bulk-delete/invoke",
        params=json.dumps({"entries": [group["name"] for group in groups]}),
        headers={"Accept": "application/json"},
        status=204,
        content_type="application/json",
    )


@managedtest
@pytest.mark.parametrize("group_type", ["host", "contact", "service"])
def test_openapi_groups_with_customer(
    monkeypatch: pytest.MonkeyPatch,
    group_type: str,
    aut_user_auth_wsgi_app: WebTestAppForCMK,
) -> None:
    name = _random_string(10)
    alias = _random_string(10)

    group = {"name": name, "alias": alias, "customer": "global"}

    base = "/NO_SITE/check_mk/api/1.0"
    _resp = aut_user_auth_wsgi_app.call_method(
        "post",
        base + f"/domain-types/{group_type}_group_config/collections/all",
        params=json.dumps(group),
        headers={"Accept": "application/json"},
        status=200,
        content_type="application/json",
    )

    resp = aut_user_auth_wsgi_app.call_method(
        "get",
        base + f"/objects/{group_type}_group_config/{name}",
        headers={"Accept": "application/json"},
        status=200,
    )
    assert resp.json_body["extensions"]["customer"] == "global"

    resp = aut_user_auth_wsgi_app.call_method(
        "put",
        base + f"/objects/{group_type}_group_config/{name}",
        headers={"If-Match": resp.headers["ETag"], "Accept": "application/json"},
        params=json.dumps(
            {
                "alias": f"{alias}+",
            }
        ),
        status=200,
        content_type="application/json",
    )
    assert resp.json_body["extensions"]["customer"] == "global"

    resp = aut_user_auth_wsgi_app.call_method(
        "put",
        base + f"/objects/{group_type}_group_config/{name}",
        headers={"If-Match": resp.headers["ETag"], "Accept": "application/json"},
        params=json.dumps({"alias": alias, "customer": "provider"}),
        status=200,
        content_type="application/json",
    )
    assert resp.json_body["extensions"]["customer"] == "provider"

    monkeypatch.setattr("cmk.gui.mkeventd.wato._get_rule_stats_from_ec", lambda: {})
    aut_user_auth_wsgi_app.delete(
        base + f"/objects/{group_type}_group_config/{name}",
        headers={"If-Match": resp.headers["ETag"], "Accept": "application/json"},
        status=204,
        content_type="application/json",
    )


@managedtest
def test_openapi_group_values_are_links(group_client: GroupConfig, group_type: str) -> None:
    response = group_client.list()
    assert len(response.json["value"]) == 0

    group_client.create(
        name=f"{group_type}_foo_bar",
        alias=f"{group_type} foo bar",
        customer="global",
    )

    response = group_client.list()

    assert len(response.json["value"]) == 1
    assert response.json["value"][0]["links"][0]["domainType"] == "link"


def _random_string(size):
    return "".join(random.choice(string.ascii_letters + string.digits) for _ in range(size))


@managedtest
@pytest.mark.parametrize("group_type", ["host", "contact", "service"])
def test_delete_non_existing_group_types(
    aut_user_auth_wsgi_app: WebTestAppForCMK,
    group_type: str,
    base: str,
) -> None:
    aut_user_auth_wsgi_app.delete(
        base + f"/objects/{group_type}_group_config/I_dont_exist",
        headers={"Accept": "application/json"},
        status=404,
        content_type="application/json",
    )


@managedtest
@pytest.mark.parametrize("group_type", ["host", "contact", "service"])
def test_bulk_delete_non_existing_group_types(
    aut_user_auth_wsgi_app: WebTestAppForCMK,
    group_type: str,
    base: str,
) -> None:
    groups = [
        {
            "name": _random_string(10),
            "alias": _random_string(10),
            "customer": "provider",
        }
        for _ in range(2)
    ]

    aut_user_auth_wsgi_app.call_method(
        "post",
        base + f"/domain-types/{group_type}_group_config/actions/bulk-delete/invoke",
        params=json.dumps({"entries": [group["name"] for group in groups]}),
        headers={"Accept": "application/json"},
        status=404,
        content_type="application/json",
    )


@managedtest
@pytest.mark.parametrize("group_type", ["host", "service", "contact"])
def test_openapi_bulk_group_schema(
    aut_user_auth_wsgi_app: WebTestAppForCMK,
    group_type: str,
    base: str,
) -> None:
    groups = [
        {"name": _random_string(10), "alias": _random_string(10), "customer": "provider"}
        for _i in range(2)
    ]

    # ------------------- bulk create -------------------
    resp = aut_user_auth_wsgi_app.call_method(
        "post",
        base + f"/domain-types/{group_type}_group_config/actions/bulk-create/invoke",
        params=json.dumps({"entries": groups}),
        headers={"Accept": "application/json"},
        status=200,
        content_type="application/json",
    )
    assert set(resp.json["value"][0]) == {
        "links",
        "domainType",
        "id",
        "title",
        "members",
        "extensions",
    }
    assert resp.json["value"][0]["domainType"] == f"{group_type}_group_config"

    # ------------------- get collection -------------------
    resp = aut_user_auth_wsgi_app.call_method(
        "get",
        base + f"/domain-types/{group_type}_group_config/collections/all",
        status=200,
        headers={"Accept": "application/json"},
    )
    assert set(resp.json["value"][0]) == {
        "links",
        "domainType",
        "id",
        "title",
        "members",
        "extensions",
    }
    assert resp.json["value"][0]["domainType"] == f"{group_type}_group_config"

    # ------------------- bulk update -------------------
    updated_groups = [
        {
            "name": group["name"],
            "attributes": {"alias": group["alias"], "customer": "global"},
        }
        for group in groups
    ]
    resp = aut_user_auth_wsgi_app.call_method(
        "put",
        base + f"/domain-types/{group_type}_group_config/actions/bulk-update/invoke",
        params=json.dumps({"entries": updated_groups}),
        headers={"Accept": "application/json"},
        status=200,
        content_type="application/json",
    )

    assert set(resp.json["value"][0]) == {
        "links",
        "domainType",
        "id",
        "title",
        "members",
        "extensions",
    }
    assert resp.json["value"][0]["domainType"] == f"{group_type}_group_config"


invalid_group_ids = (
    "test_group_id\\n",
    "test_group_id\n",
    "test_gr\noup_id",
    "\test_group_id",
    "..",
    ".",
    "./.",
    "./..",
    "../.",
    "../..",
)


@managedtest
@pytest.mark.parametrize("group_id", invalid_group_ids)
def test_host_group_id_with_newline(
    clients: ClientRegistry,
    group_id: str,
) -> None:
    resp = clients.HostGroup.create(name=group_id, alias="not_important", expect_ok=False)
    resp.assert_status_code(400)
    assert (
        resp.json["fields"]["name"][0]
        == f"{group_id!r} does not match pattern '{ESCAPED_GROUP_NAME_PATTERN}'."
    )


@managedtest
@pytest.mark.parametrize("group_id", invalid_group_ids)
def test_contact_group_id_with_newline(
    clients: ClientRegistry,
    group_id: str,
) -> None:
    resp = clients.ContactGroup.create(name=group_id, alias="not_important", expect_ok=False)
    resp.assert_status_code(400)
    assert (
        resp.json["fields"]["name"][0]
        == f"{group_id!r} does not match pattern '{ESCAPED_GROUP_NAME_PATTERN}'."
    )


@managedtest
@pytest.mark.parametrize("group_id", invalid_group_ids)
def test_service_group_id_with_newline(
    clients: ClientRegistry,
    group_id: str,
) -> None:
    resp = clients.ServiceGroup.create(name=group_id, alias="not_important", expect_ok=False)
    resp.assert_status_code(400)
    assert (
        resp.json["fields"]["name"][0]
        == f"{group_id!r} does not match pattern '{ESCAPED_GROUP_NAME_PATTERN}'."
    )


@managedtest
def test_group_attributes_required(
    group_client: GroupConfig,
) -> None:
    group_name = "test_name"
    group_client.create(name=group_name, alias="test_alias")
    resp = group_client.bulk_edit(
        groups=({"name": group_name},),
        expect_ok=False,
    )
    resp.assert_status_code(400)
    assert resp.json["fields"]["entries"]["0"] == {
        "attributes": ["Missing data for required field."]
    }


@managedtest
def test_contact_group_dot_names(
    clients: ClientRegistry,
) -> None:
    contact_group_dot_response = clients.ContactGroup.create(
        name=".", alias="not_important", expect_ok=False
    )
    contact_group_double_dot_response = clients.ContactGroup.create(
        name="..", alias="not_important", expect_ok=False
    )

    host_group_dot_response = clients.HostGroup.create(
        name=".", alias="not_important", expect_ok=False
    )
    host_group_double_dot_response = clients.HostGroup.create(
        name="..", alias="not_important", expect_ok=False
    )

    service_group_dot_response = clients.ServiceGroup.create(
        name=".", alias="not_important", expect_ok=False
    )
    service_group_double_dot_response = clients.ServiceGroup.create(
        name="..", alias="not_important", expect_ok=False
    )

    assert contact_group_dot_response.status_code == 400
    assert "name" in contact_group_dot_response.json["fields"]
    assert "name" in contact_group_dot_response.json["detail"]

    assert contact_group_double_dot_response.status_code == 400
    assert "name" in contact_group_double_dot_response.json["fields"]
    assert "name" in contact_group_double_dot_response.json["detail"]

    assert host_group_dot_response.status_code == 400
    assert "name" in host_group_dot_response.json["fields"]
    assert "name" in host_group_dot_response.json["detail"]

    assert host_group_double_dot_response.status_code == 400
    assert "name" in host_group_double_dot_response.json["fields"]
    assert "name" in host_group_double_dot_response.json["detail"]

    assert service_group_dot_response.status_code == 400
    assert "name" in service_group_dot_response.json["fields"]
    assert "name" in service_group_dot_response.json["detail"]

    assert service_group_double_dot_response.status_code == 400
    assert "name" in service_group_double_dot_response.json["fields"]
    assert "name" in service_group_double_dot_response.json["detail"]


@pytest.mark.parametrize(
    "inventory_paths",
    [
        {
            "type": "allow_all",
        },
        {
            "type": "forbid_all",
        },
        {
            "type": "specific_paths",
            "paths": [
                {
                    "path": "path1",
                },
                {
                    "path": "path2",
                    "attributes": {"type": "restrict_all"},
                    "columns": {"type": "restrict_values", "values": ["col1", "col2"]},
                    "nodes": {"type": "no_restriction"},
                },
            ],
        },
    ],
)
def test_contact_group_inventory_paths(
    clients: ClientRegistry, inventory_paths: APIInventoryPaths
) -> None:
    group = clients.ContactGroup.create(
        name="test_group",
        alias="test_alias",
        inventory_paths=inventory_paths,
    )
    if inventory_paths["type"] == "specific_paths":
        for path in inventory_paths["paths"]:
            path.setdefault("attributes", {"type": "no_restriction"})
            path.setdefault("columns", {"type": "no_restriction"})
            path.setdefault("nodes", {"type": "no_restriction"})

    assert group.json["extensions"]["inventory_paths"] == inventory_paths
