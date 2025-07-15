#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.config import builtin_role_ids

from tests.testlib.unit.rest_api_client import ClientRegistry


def test_get_userrole_endpoint(clients: ClientRegistry) -> None:
    resp = clients.UserRole.get(role_id="admin")
    assert resp.json["extensions"].keys() == {
        "alias",
        "permissions",
        "builtin",
        "enforce_two_factor_authentication",
    }
    assert {link["method"] for link in resp.json["links"]} == {"GET", "PUT"}


def test_get_userroles_endpoint(clients: ClientRegistry) -> None:
    resp = clients.UserRole.get_all()
    assert {user_role["id"] for user_role in resp.json["value"]} == set(builtin_role_ids)


def test_post_userrole_endpoint(clients: ClientRegistry) -> None:
    clients.UserRole.clone(body={"role_id": "admin"})
    resp = clients.UserRole.get(role_id="adminx")
    assert resp.json["extensions"].keys() == {
        "alias",
        "permissions",
        "builtin",
        "basedon",
        "enforce_two_factor_authentication",
    }
    assert resp.json["id"] == "adminx"
    assert {link["method"] for link in resp.json["links"]} == {"GET", "PUT", "DELETE"}


def test_post_clone_userrole_new_id(clients: ClientRegistry) -> None:
    clients.UserRole.clone(body={"role_id": "admin", "new_role_id": "megatron"})
    clients.UserRole.get(role_id="megatron")


def test_post_clone_userrole_new_alias(clients: ClientRegistry) -> None:
    clients.UserRole.clone(body={"role_id": "admin", "new_alias": "mr_silly"})
    resp = clients.UserRole.get(role_id="adminx")
    assert resp.json["extensions"]["alias"] == "mr_silly"


def test_post_clone_userrole_new_two_factor(clients: ClientRegistry) -> None:
    clients.UserRole.clone(body={"role_id": "admin", "enforce_two_factor_authentication": True})
    resp = clients.UserRole.get(role_id="adminx")
    assert resp.json["extensions"]["enforce_two_factor_authentication"] is True


def test_delete_cloned_userrole(clients: ClientRegistry) -> None:
    clients.UserRole.clone(body={"role_id": "admin"})
    clients.UserRole.delete(role_id="adminx")


def test_delete_non_existing_userrole_endpoint(clients: ClientRegistry) -> None:
    resp = clients.UserRole.delete(role_id="non-existing-user-role", expect_ok=False)
    assert (
        "The role should exist but it doesn't: 'non-existing-user-role'"
        in resp.json["fields"]["role_id"]
    )


def test_delete_builtin_userrole(clients: ClientRegistry) -> None:
    resp = clients.UserRole.delete(role_id="admin", expect_ok=False)
    resp.assert_status_code(404)
    assert (
        "The role should be a custom role but it's not: 'admin'" in resp.json["fields"]["role_id"]
    )


def test_edit_cloned_userrole_two_factor(clients: ClientRegistry) -> None:
    clients.UserRole.clone(body={"role_id": "admin"})
    resp = clients.UserRole.edit(role_id="adminx", body={"enforce_two_factor_authentication": True})
    assert resp.json["extensions"]["enforce_two_factor_authentication"] is True


def test_edit_cloned_userrole_basedon(clients: ClientRegistry) -> None:
    clients.UserRole.clone(body={"role_id": "admin"})
    resp = clients.UserRole.edit(role_id="adminx", body={"new_basedon": "user"})
    assert resp.json["extensions"]["basedon"] == "user"


def test_edit_cloned_userrole_alias(clients: ClientRegistry) -> None:
    clients.UserRole.clone(body={"role_id": "admin"})
    resp = clients.UserRole.edit(role_id="adminx", body={"new_alias": "yonsemite sam"})
    assert resp.json["extensions"]["alias"] == "yonsemite sam"


def test_edit_cloned_userrole_id(clients: ClientRegistry) -> None:
    clients.UserRole.clone(body={"role_id": "admin"})
    resp = clients.UserRole.edit(role_id="adminx", body={"new_role_id": "sam"})
    assert resp.json["id"] == "sam"


def test_edit_cloned_userrole_permissions(clients: ClientRegistry) -> None:
    clients.UserRole.clone(body={"role_id": "admin"})
    resp = clients.UserRole.edit(
        role_id="adminx",
        body={"new_permissions": {"general.server_side_requests": "no", "general.use": "no"}},
    )

    assert "general.server_side_requests" not in resp.json["extensions"]["permissions"]
    assert "general.use" not in resp.json["extensions"]["permissions"]

    resp = clients.UserRole.edit(
        role_id="adminx",
        body={
            "new_permissions": {"general.server_side_requests": "default", "general.use": "default"}
        },
    )

    assert "general.server_side_requests" in resp.json["extensions"]["permissions"]
    assert "general.use" in resp.json["extensions"]["permissions"]


def test_userrole_invalid_permission_value(clients: ClientRegistry) -> None:
    clients.UserRole.edit(
        role_id="admin",
        body={"new_permissions": {"general.server_side_requests": "abc"}},
        expect_ok=False,
    ).assert_status_code(400)


def test_userrole_invalid_permission_name(clients: ClientRegistry) -> None:
    clients.UserRole.edit(
        role_id="admin",
        body={"new_permissions": {"new_permissions": {"general.made_up_permission": "yes"}}},
        expect_ok=False,
    ).assert_status_code(400)


def test_edit_cloned_userrole_invalid_roleid(clients: ClientRegistry) -> None:
    clients.UserRole.clone(body={"role_id": "admin"})
    clients.UserRole.edit(
        role_id="adminx",
        body={"new_role_id": "admin"},
        expect_ok=False,
    ).assert_status_code(400)


def test_edit_cloned_userrole_invalid_basedon(clients: ClientRegistry) -> None:
    clients.UserRole.clone(body={"role_id": "admin"})
    clients.UserRole.edit(
        role_id="adminx",
        body={"new_basedon": "sam"},
        expect_ok=False,
    ).assert_status_code(400)


def test_edit_cloned_userrole_invalid_alias(clients: ClientRegistry) -> None:
    clients.UserRole.clone(body={"role_id": "admin"})
    clients.UserRole.edit(
        role_id="adminx",
        body={"new_alias": "Administrator"},
        expect_ok=False,
    ).assert_status_code(400)


def test_edit_cloned_userrole_invalid_permissions(clients: ClientRegistry) -> None:
    clients.UserRole.clone(body={"role_id": "admin"})
    clients.UserRole.edit(
        role_id="adminx",
        body={"new_permissions": {"permission_a": "default", "permission_b": "yes"}},
        expect_ok=False,
    ).assert_status_code(400)


def test_edit_builtin_role_id(clients: ClientRegistry) -> None:
    clients.UserRole.edit(
        role_id="admin",
        body={"new_role_id": "edited_admin"},
        expect_ok=False,
    ).assert_status_code(400)


def test_edit_builtin_basedon(clients: ClientRegistry) -> None:
    clients.UserRole.edit(
        role_id="admin",
        body={"new_basedon": "something_else"},
        expect_ok=False,
    ).assert_status_code(400)


def test_edit_builtin_alias(clients: ClientRegistry) -> None:
    resp = clients.UserRole.edit(
        role_id="admin",
        body={"new_alias": "something_else"},
    )
    assert resp.json["extensions"]["alias"] == "something_else"


def test_permission_change_when_builtin_changes(clients: ClientRegistry) -> None:
    admin_permissions = clients.UserRole.get(role_id="admin").json["extensions"]["permissions"]
    guest_permissions = clients.UserRole.get(role_id="guest").json["extensions"]["permissions"]
    user_permissions = clients.UserRole.get(role_id="user").json["extensions"]["permissions"]

    # Clone admin and check the clone has admin permissions.
    resp = clients.UserRole.clone(body={"role_id": "admin"})
    assert set(resp.json["extensions"]["permissions"]) == set(admin_permissions)

    # Change basedon to guest and check permissions match a guest's permissions
    resp = clients.UserRole.edit(
        role_id="adminx",
        body={"new_basedon": "guest"},
    )
    assert set(resp.json["extensions"]["permissions"]) == set(guest_permissions)

    # Change basedon to user and check permissions match a user's permissions
    resp = clients.UserRole.edit(
        role_id="adminx",
        body={"new_basedon": "user"},
    )
    assert set(resp.json["extensions"]["permissions"]) == set(user_permissions)
