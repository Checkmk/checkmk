#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from collections.abc import Callable
from functools import partial

import pytest

from tests.unit.cmk.gui.conftest import WebTestAppForCMK

from cmk.gui.config import builtin_role_ids


@pytest.fixture(name="object_base")
def user_role_object_base(base: str) -> str:
    return f"{base}/objects/user_role/"


@pytest.fixture(name="collection_base")
def user_role_collection_base(base: str) -> str:
    return f"{base}/domain-types/user_role/collections/all"


@pytest.fixture(name="get_userrole")
def partial_get(aut_user_auth_wsgi_app: WebTestAppForCMK, object_base: str) -> Callable:
    return partial(
        aut_user_auth_wsgi_app.get,
        url=object_base + "adminx",
        status=200,
        headers={"Accept": "application/json"},
    )


@pytest.fixture(name="get_userroles")
def partial_list(
    aut_user_auth_wsgi_app: WebTestAppForCMK, collection_base: str, get_userrole: Callable
) -> Callable:
    return partial(
        aut_user_auth_wsgi_app.get,
        url=collection_base,
        status=200,
        headers={"Accept": "application/json"},
    )


@pytest.fixture(name="clone_userrole")
def partial_post(aut_user_auth_wsgi_app: WebTestAppForCMK, collection_base: str) -> Callable:
    return partial(
        aut_user_auth_wsgi_app.post,
        url=collection_base,
        status=200,
        params=json.dumps({"role_id": "admin"}),
        headers={"Accept": "application/json"},
        content_type="application/json",
    )


@pytest.fixture(name="delete_userrole")
def partial_delete(aut_user_auth_wsgi_app: WebTestAppForCMK, object_base: str) -> Callable:
    return partial(
        aut_user_auth_wsgi_app.delete,
        url=object_base + "adminx",
        status=204,
        headers={"Accept": "application/json"},
    )


@pytest.fixture(name="edit_userrole")
def partial_put(aut_user_auth_wsgi_app: WebTestAppForCMK, object_base: str) -> Callable:
    return partial(
        aut_user_auth_wsgi_app.put,
        url=object_base + "adminx",
        status=200,
        headers={"Accept": "application/json"},
        content_type="application/json",
    )


def test_get_userrole_endpoint(object_base: str, get_userrole: Callable) -> None:
    resp = get_userrole(url=object_base + "admin")
    assert resp.json["extensions"].keys() == {"alias", "permissions", "builtin"}
    assert {link["method"] for link in resp.json["links"]} == {"GET", "PUT"}


def test_get_userroles_endpoint(get_userroles: Callable) -> None:
    resp = get_userroles()
    assert {user_role["id"] for user_role in resp.json["value"]} == set(builtin_role_ids)


def test_post_userrole_endpoint(clone_userrole: Callable, get_userrole: Callable) -> None:
    clone_userrole()
    resp = get_userrole()
    assert resp.json["extensions"].keys() == {"alias", "permissions", "builtin", "basedon"}
    assert resp.json["id"] == "adminx"
    assert {link["method"] for link in resp.json["links"]} == {"GET", "PUT", "DELETE"}


def test_post_clone_userrole_new_id(
    object_base: str, clone_userrole: Callable, get_userrole: Callable
) -> None:
    clone_userrole(params=json.dumps({"role_id": "admin", "new_role_id": "megatron"}))
    get_userrole(url=object_base + "megatron")


def test_post_clone_userrole_new_alias(
    object_base: str, clone_userrole: Callable, get_userrole: Callable
) -> None:
    clone_userrole(params=json.dumps({"role_id": "admin", "new_alias": "mr_silly"}))
    resp = get_userrole()
    assert resp.json["extensions"]["alias"] == "mr_silly"


def test_delete_cloned_userrole(clone_userrole: Callable, delete_userrole: Callable) -> None:
    clone_userrole()
    delete_userrole()


def test_delete_non_existing_userrole_endpoint(object_base: str, delete_userrole: Callable) -> None:
    resp = delete_userrole(url=object_base + "non-existing-user-role", status=404)
    assert (
        "The role should exist but it doesn't: 'non-existing-user-role'"
        in resp.json["fields"]["role_id"]
    )


def test_delete_builtin_userrole(object_base: str, delete_userrole: Callable) -> None:
    resp = delete_userrole(url=object_base + "admin", status=404)
    assert (
        "The role should be a custom role but it's not: 'admin'" in resp.json["fields"]["role_id"]
    )


def test_edit_cloned_userrole_basedon(clone_userrole: Callable, edit_userrole: Callable) -> None:
    clone_userrole()
    resp = edit_userrole(params=json.dumps({"new_basedon": "user"}))
    assert resp.json["extensions"]["basedon"] == "user"


def test_edit_cloned_userrole_alias(clone_userrole: Callable, edit_userrole: Callable) -> None:
    clone_userrole()
    resp = edit_userrole(params=json.dumps({"new_alias": "yonsemite sam"}))
    assert resp.json["extensions"]["alias"] == "yonsemite sam"


def test_edit_cloned_userrole_id(clone_userrole: Callable, edit_userrole: Callable) -> None:
    clone_userrole()
    resp = edit_userrole(params=json.dumps({"new_role_id": "sam"}))
    assert resp.json["id"] == "sam"


def test_edit_cloned_userrole_permissions(
    clone_userrole: Callable, edit_userrole: Callable
) -> None:
    clone_userrole()
    resp = edit_userrole(
        params=json.dumps(
            {"new_permissions": {"general.server_side_requests": "no", "general.use": "no"}}
        )
    )

    assert "general.server_side_requests" not in resp.json["extensions"]["permissions"]
    assert "general.use" not in resp.json["extensions"]["permissions"]

    resp = edit_userrole(
        params=json.dumps(
            {
                "new_permissions": {
                    "general.server_side_requests": "default",
                    "general.use": "default",
                }
            }
        )
    )

    assert "general.server_side_requests" in resp.json["extensions"]["permissions"]
    assert "general.use" in resp.json["extensions"]["permissions"]


def test_userrole_invalid_permission_value(object_base: str, edit_userrole: Callable) -> None:
    edit_userrole(
        url=object_base + "admin",
        status=400,
        params=json.dumps({"new_permissions": {"general.server_side_requests": "abc"}}),
    )


def test_userrole_invalid_permission_name(object_base: str, edit_userrole: Callable) -> None:
    edit_userrole(
        url=object_base + "admin",
        status=400,
        params=json.dumps({"new_permissions": {"general.made_up_permission": "yes"}}),
    )


def test_edit_cloned_userrole_invalid_roleid(
    clone_userrole: Callable, edit_userrole: Callable
) -> None:
    clone_userrole()
    edit_userrole(status=400, params=json.dumps({"new_role_id": "admin"}))


def test_edit_cloned_userrole_invalid_basedon(
    clone_userrole: Callable, edit_userrole: Callable
) -> None:
    clone_userrole()
    edit_userrole(status=400, params=json.dumps({"new_basedon": "sam"}))


def test_edit_cloned_userrole_invalid_alias(
    clone_userrole: Callable, edit_userrole: Callable
) -> None:
    clone_userrole()
    edit_userrole(status=400, params=json.dumps({"new_alias": "Administrator"}))


def test_edit_cloned_userrole_invalid_permissions(
    clone_userrole: Callable, edit_userrole: Callable
) -> None:
    clone_userrole()
    edit_userrole(
        status=400,
        params=json.dumps({"new_permissions": {"permission_a": "default", "permission_b": "yes"}}),
    )


def test_edit_builtin_role_id(object_base: str, edit_userrole: Callable) -> None:
    edit_userrole(
        url=object_base + "admin", status=400, params=json.dumps({"new_role_id": "edited_admin"})
    )


def test_edit_builtin_basedon(object_base: str, edit_userrole: Callable) -> None:
    edit_userrole(
        url=object_base + "admin", status=400, params=json.dumps({"new_basedon": "something_else"})
    )


def test_edit_builtin_alias(object_base: str, edit_userrole: Callable) -> None:
    resp = edit_userrole(
        url=object_base + "admin", params=json.dumps({"new_alias": "something_else"})
    )
    assert resp.json["extensions"]["alias"] == "something_else"


def test_permission_change_when_builtin_changes(
    get_userrole: Callable, clone_userrole: Callable, edit_userrole: Callable, object_base: str
) -> None:
    admin_permissions = get_userrole(url=object_base + "admin").json["extensions"]["permissions"]
    guest_permissions = get_userrole(url=object_base + "guest").json["extensions"]["permissions"]
    user_permissions = get_userrole(url=object_base + "user").json["extensions"]["permissions"]

    # Clone admin and check the clone has admin permissions.
    resp = clone_userrole()
    assert set(resp.json["extensions"]["permissions"]) == set(admin_permissions)

    # Change basedon to guest and check permissions match a guest's permissions
    resp = edit_userrole(params=json.dumps({"new_basedon": "guest"}))
    assert set(resp.json["extensions"]["permissions"]) == set(guest_permissions)

    # Change basedon to user and check permissions match a user's permissions
    resp = edit_userrole(params=json.dumps({"new_basedon": "user"}))
    assert set(resp.json["extensions"]["permissions"]) == set(user_permissions)
