#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from functools import partial

import pytest

from tests.unit.cmk.gui.conftest import WebTestAppForCMK


@pytest.fixture(name="object_base")
def user_role_object_base(base: str) -> str:
    return f"{base}/objects/user_role/"


@pytest.fixture(name="collection_base")
def user_role_collection_base(base: str) -> str:
    return f"{base}/domain-types/user_role/collections/all"


def test_get_userrole_endpoint(object_base: str, aut_user_auth_wsgi_app: WebTestAppForCMK) -> None:
    resp = aut_user_auth_wsgi_app.get(
        object_base + "admin",
        status=200,
        headers={"Accept": "application/json"},
    )

    assert resp.json["extensions"].keys() == {"alias", "permissions", "builtin"}
    assert {link["method"] for link in resp.json["links"]} == {"GET", "PUT"}


def test_get_userroles_endpoint(
    collection_base: str, aut_user_auth_wsgi_app: WebTestAppForCMK
) -> None:
    resp = aut_user_auth_wsgi_app.get(
        collection_base,
        status=200,
        headers={"Accept": "application/json"},
    )

    assert {user_role["id"] for user_role in resp.json["value"]} == {"user", "admin", "guest"}


def test_post_userrole_endpoint(
    collection_base: str, object_base: str, aut_user_auth_wsgi_app: WebTestAppForCMK
) -> None:
    aut_user_auth_wsgi_app.post(
        collection_base,
        status=200,
        params=json.dumps({"role_id": "admin"}),
        headers={"Accept": "application/json"},
        content_type="application/json",
    )

    resp = aut_user_auth_wsgi_app.get(
        object_base + "adminx",
        status=200,
        headers={"Accept": "application/json"},
    )

    assert resp.json["extensions"].keys() == {"alias", "permissions", "builtin", "basedon"}
    assert resp.json["id"] == "adminx"
    assert {link["method"] for link in resp.json["links"]} == {"GET", "PUT", "DELETE"}


def test_delete_userrole_endpoint(
    collection_base: str, object_base: str, aut_user_auth_wsgi_app: WebTestAppForCMK
) -> None:
    aut_user_auth_wsgi_app.post(
        collection_base,
        status=200,
        params=json.dumps({"role_id": "admin"}),
        headers={"Accept": "application/json"},
        content_type="application/json",
    )

    aut_user_auth_wsgi_app.delete(
        object_base + "adminx",
        status=204,
        headers={"Accept": "application/json"},
    )


def test_delete_non_existing_userrole_endpoint(
    object_base: str, aut_user_auth_wsgi_app: WebTestAppForCMK
) -> None:
    aut_user_auth_wsgi_app.delete(
        object_base + "non-existing-user-role",
        status=404,
        headers={"Accept": "application/json"},
    )


def test_delete_builtin_userrole(
    object_base: str, aut_user_auth_wsgi_app: WebTestAppForCMK
) -> None:
    aut_user_auth_wsgi_app.delete(
        object_base + "admin",
        status=404,
        headers={"Accept": "application/json"},
    )


def test_edit_cloned_userrole_with_valid_data(
    collection_base: str, object_base: str, aut_user_auth_wsgi_app: WebTestAppForCMK
) -> None:
    aut_user_auth_wsgi_app.post(
        collection_base,
        status=200,
        params=json.dumps({"role_id": "admin"}),
        headers={"Accept": "application/json"},
        content_type="application/json",
    )

    put = partial(
        aut_user_auth_wsgi_app.put,
        object_base + "adminx",
        status=200,
        headers={"Accept": "application/json"},
        content_type="application/json",
    )

    # Verify basedon can be changed
    resp = put(params=json.dumps({"new_basedon": "user"}))
    assert resp.json["extensions"]["basedon"] == "user"

    # Verify alias can be changed
    resp = put(params=json.dumps({"new_alias": "yonsemite sam"}))
    assert resp.json["extensions"]["alias"] == "yonsemite sam"

    # Verify permissions can be changed - Change to opposite
    resp = put(
        params=json.dumps(
            {"new_permissions": {"general.server_side_requests": "yes", "general.use": "no"}}
        )
    )

    assert "general.server_side_requests" in resp.json["extensions"]["permissions"]
    assert "general.use" not in resp.json["extensions"]["permissions"]

    # Verify permissions can be changed to default
    resp = put(
        params=json.dumps(
            {
                "new_permissions": {
                    "general.server_side_requests": "default",
                    "general.use": "default",
                }
            }
        )
    )

    assert "general.server_side_requests" not in resp.json["extensions"]["permissions"]
    assert "general.use" in resp.json["extensions"]["permissions"]

    # Verify the id can be changed
    resp = put(params=json.dumps({"new_role_id": "sam"}))
    assert resp.json["id"] == "sam"


def test_edit_cloned_userrole_with_invalid_data(
    collection_base: str, object_base: str, aut_user_auth_wsgi_app: WebTestAppForCMK
) -> None:
    aut_user_auth_wsgi_app.post(
        collection_base,
        status=200,
        params=json.dumps({"role_id": "admin"}),
        headers={"Accept": "application/json"},
        content_type="application/json",
    )

    put = partial(
        aut_user_auth_wsgi_app.put,
        object_base + "adminx",
        status=400,
        headers={"Accept": "application/json"},
        content_type="application/json",
    )

    # admin id already exists
    put(params=json.dumps({"new_role_id": "admin"}))

    # invalid basedon - has to be a builtin role
    put(params=json.dumps({"new_basedon": "sam"}))

    # alias already exists
    put(params=json.dumps({"new_alias": "Administrator"}))

    # permissions don't exist
    put(params=json.dumps({"new_permissions": ["permission_a", "permission_b"]}))


def test_edit_builtin_userrole(object_base: str, aut_user_auth_wsgi_app: WebTestAppForCMK) -> None:
    put = partial(
        aut_user_auth_wsgi_app.put,
        object_base + "admin",
        status=400,
        headers={"Accept": "application/json"},
        content_type="application/json",
    )

    # builtin role ids can't be edited
    put(params=json.dumps({"new_role_id": "edited_admin"}))

    # builtin basedon can't be edited
    put(params=json.dumps({"new_basedon": "something_else"}))

    # builtin alias can be edited
    resp = put(params=json.dumps({"new_alias": "something_else"}), status=200)

    # Verify alias has changed
    assert resp.json["extensions"]["alias"] == "something_else"


def test_permission_change_when_builtin_changes(
    object_base: str, collection_base: str, aut_user_auth_wsgi_app: WebTestAppForCMK
) -> None:
    get = partial(
        aut_user_auth_wsgi_app.get,
        status=200,
        headers={"Accept": "application/json"},
    )

    admin_permissions = set(get(url=object_base + "admin").json["extensions"]["permissions"])
    guest_permissions = set(get(url=object_base + "guest").json["extensions"]["permissions"])
    user_permissions = set(get(url=object_base + "user").json["extensions"]["permissions"])

    resp = aut_user_auth_wsgi_app.post(
        collection_base,
        status=200,
        params=json.dumps({"role_id": "admin"}),
        headers={"Accept": "application/json"},
        content_type="application/json",
    )

    # Cloned user should have admin permissions.
    assert set(resp.json["extensions"]["permissions"]) == admin_permissions

    put = partial(
        aut_user_auth_wsgi_app.put,
        object_base + "adminx",
        status=200,
        headers={"Accept": "application/json"},
        content_type="application/json",
    )

    # Change basedon to guest and check permissions match a guest's permissions
    resp = put(params=json.dumps({"new_basedon": "guest"}))
    assert set(resp.json["extensions"]["permissions"]) == guest_permissions

    # Change basedon to user and check permissions match a user's permissions
    resp = put(params=json.dumps({"new_basedon": "user"}))
    assert set(resp.json["extensions"]["permissions"]) == user_permissions
