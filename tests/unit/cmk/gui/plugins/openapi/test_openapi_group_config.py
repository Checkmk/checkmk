#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import random
import string

import pytest
from pytest import FixtureRequest

from tests.testlib.rest_api_client import (
    ClientRegistry,
    ContactGroupClient,
    HostGroupClient,
    ServiceGroupClient,
)

from tests.unit.cmk.gui.conftest import WebTestAppForCMK

from cmk.utils import version
from cmk.utils.type_defs.user_id import UserId

managedtest = pytest.mark.skipif(not version.is_managed_edition(), reason="see #7213")


@pytest.fixture
def host(clients: ClientRegistry) -> HostGroupClient:
    return clients.HostGroup


@pytest.fixture
def contact(clients: ClientRegistry) -> ContactGroupClient:
    return clients.ContactGroup


@pytest.fixture
def service(clients: ClientRegistry) -> ServiceGroupClient:
    return clients.ServiceGroup


@managedtest
@pytest.mark.parametrize("group_type", ["host", "contact", "service"])
def test_required_alias_field_create(group_type: str, request: FixtureRequest) -> None:
    client = request.getfixturevalue(group_type)
    client.create(name="RandleMcMurphy", expect_ok=False).assert_status_code(400)


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

    monkeypatch.setattr("cmk.gui.watolib.mkeventd._get_rule_stats_from_ec", lambda: {})
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

    monkeypatch.setattr("cmk.gui.watolib.mkeventd._get_rule_stats_from_ec", lambda: {})
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

    monkeypatch.setattr("cmk.gui.watolib.mkeventd._get_rule_stats_from_ec", lambda: {})
    aut_user_auth_wsgi_app.delete(
        base + f"/objects/{group_type}_group_config/{name}",
        headers={"If-Match": resp.headers["ETag"], "Accept": "application/json"},
        status=204,
        content_type="application/json",
    )


@managedtest
@pytest.mark.parametrize("group_type", ["host", "contact", "service"])
def test_openapi_group_values_are_links(
    group_type: str, wsgi_app: WebTestAppForCMK, with_automation_user: tuple[UserId, str], base: str
) -> None:
    username, secret = with_automation_user
    wsgi_app.set_authorization(("Bearer", username + " " + secret))

    collection_url = f"{base}/domain-types/{group_type}_group_config/collections/all"
    response = wsgi_app.call_method(
        url=collection_url,
        method="GET",
        headers={"Accept": "application/json"},
    )
    json_data = response.json
    assert len(json_data["value"]) == 0

    group = {
        "name": f"{group_type}_foo_bar",
        "alias": f"{group_type} foo bar",
        "customer": "global",
    }
    _response = wsgi_app.call_method(
        "post",
        base + f"/domain-types/{group_type}_group_config/collections/all",
        params=json.dumps(group),
        headers={"Accept": "application/json"},
        status=200,
        content_type="application/json",
    )

    response = wsgi_app.call_method(
        url=collection_url,
        method="GET",
        headers={"Accept": "application/json"},
    )
    assert response.status_code == 200

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
