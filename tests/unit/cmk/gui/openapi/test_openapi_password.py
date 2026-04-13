#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui.watolib.password_store import PasswordStore
from cmk.utils import password_store
from cmk.utils.password_store import PasswordConfig
from tests.testlib.unit.rest_api_client import ClientRegistry


@pytest.mark.usefixtures("suppress_remote_automation_calls", "mock_password_file_regeneration")
def test_openapi_password(clients: ClientRegistry) -> None:
    clients.Password.create(
        ident="invalid%$",
        title="foobar",
        password="tt",
        shared=["all"],
        editable_by="admin",
        expect_ok=False,
    ).assert_status_code(400)

    clients.Password.create(
        ident="foo:invalid",
        title="foobar",
        password="tt",
        shared=["all"],
        editable_by="admin",
        expect_ok=False,
    ).assert_status_code(400)

    clients.Password.create(
        ident="foo",
        title="foobar",
        password="tt",
        shared=["all"],
        editable_by="admin",
    )

    clients.Password.edit("fooz", expect_ok=False).assert_status_code(404)
    clients.Password.edit("foo", title="foobu", comment="Something but nothing random")

    resp = clients.Password.get("foo")
    extensions = resp.json["extensions"]
    assert extensions["comment"] == "Something but nothing random"
    assert extensions["documentation_url"] == ""
    assert extensions["owned_by"] == "admin"
    assert extensions["editable_by"] == "admin"
    assert extensions["shared"] == ["all"]


@pytest.mark.usefixtures("suppress_remote_automation_calls", "mock_password_file_regeneration")
def test_openapi_password_editable_by(clients: ClientRegistry) -> None:
    clients.ContactGroup.create("group1", "group1")

    clients.Password.create(
        ident="test",
        title="Checkmk",
        password="tt",
        shared=[],
        editable_by="group1",
        _owner="group1",
        expect_ok=False,
    ).assert_status_code(400)

    resp = clients.Password.create(
        ident="test_1",
        title="Checkmk",
        password="tt",
        shared=[],
        _owner="group1",
    )
    assert resp.json["extensions"]["editable_by"] == "group1"
    assert resp.json["extensions"]["owned_by"] == "group1"

    resp = clients.Password.create(
        ident="test_2",
        title="Checkmk",
        password="tt",
        shared=[],
        editable_by="group1",
    )
    assert resp.json["extensions"]["editable_by"] == "group1"
    assert resp.json["extensions"]["owned_by"] == "group1"

    resp = clients.Password.create(
        ident="test_3",
        title="Checkmk",
        password="tt",
        shared=[],
        editable_by=None,  # default should be admin
    )
    assert resp.json["extensions"]["editable_by"] == "admin"
    assert resp.json["extensions"]["owned_by"] == "admin"

    resp = clients.Password.edit("test_3", editable_by="group1")
    assert resp.json["extensions"]["editable_by"] == "group1"
    assert resp.json["extensions"]["owned_by"] == "group1"


@pytest.mark.usefixtures("suppress_remote_automation_calls", "mock_password_file_regeneration")
def test_openapi_password_delete(clients: ClientRegistry) -> None:
    clients.Password.create(
        ident="test",
        title="Checkmk",
        password="tt",
        shared=[],
        editable_by="admin",
    )
    resp = clients.Password.get_all()
    assert len(resp.json["value"]) == 1

    clients.Password.delete("invalid", expect_ok=False).assert_status_code(404)
    clients.Password.delete("test").assert_status_code(204)

    clients.Password.get("test", expect_ok=False).assert_status_code(404)
    resp = clients.Password.get_all()
    assert len(resp.json["value"]) == 0


@pytest.mark.usefixtures("suppress_remote_automation_calls", "mock_password_file_regeneration")
def test_openapi_password_etag(clients: ClientRegistry) -> None:
    ident = "test_etag"
    clients.Password.create(
        ident=ident,
        title="Checkmk",
        password="tt",
        shared=[],
        editable_by="admin",
    )

    clients.Password.edit(
        ident, title="Updated", expect_ok=False, etag="invalid_etag"
    ).assert_status_code(412)
    clients.Password.delete(ident, expect_ok=False, etag="invalid_etag").assert_status_code(412)

    clients.Password.edit(ident, title="Updated", etag="valid_etag")
    clients.Password.delete(ident, etag="valid_etag")


@pytest.mark.usefixtures("mock_password_file_regeneration")
def test_password_with_newlines(clients: ClientRegistry) -> None:
    credentials_with_newlines = """{
        "type": "service_account",
        "project_id": "myCoolProject",
        "private_key_id": "foobar",
        "private_key": "I\\nhave\\nnewlines\\n",
        "client_email": "me@example.com",
        "client_id": "123456789",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/me@example.com"
    }"""

    clients.Password.create(
        ident="gcp",
        title="gcp",
        password=credentials_with_newlines,
        shared=[],
        editable_by="admin",
    )

    loaded = password_store.load(password_store.password_store_path())
    assert loaded["gcp"] == credentials_with_newlines.replace("\n", "")


@pytest.mark.usefixtures("mock_password_file_regeneration")
def test_openapi_password_without_owner_regression(clients: ClientRegistry) -> None:
    clients.Password.create(
        ident="so_secret",
        title="so_secret",
        password="no_one_can_know",
        shared=["all"],
        editable_by="admin",
    )

    resp = clients.Password.get("so_secret")
    assert resp.json["extensions"].get("owned_by") is not None


def test_password_min_length_create(clients: ClientRegistry) -> None:
    resp = clients.Password.create(
        ident="so_secret",
        title="so_secret",
        password="",
        shared=["all"],
        editable_by="admin",
        expect_ok=False,
    )

    resp.assert_status_code(400)
    assert resp.json["fields"]["body.password"]["type"] == "string_too_short"


@pytest.mark.usefixtures("mock_password_file_regeneration")
def test_password_min_length_update(clients: ClientRegistry) -> None:
    clients.Password.create(
        ident="so_secret",
        title="so_secret",
        password="no_one_can_know",
        shared=["all"],
        editable_by="admin",
    )
    resp = clients.Password.edit(
        ident="so_secret",
        title="so_secret",
        editable_by="admin",
        password="",
        shared=["all"],
        expect_ok=False,
    )

    resp.assert_status_code(400)
    assert resp.json["fields"]["body.password.constrained-str"]["type"] == "string_too_short"


def test_password_identifier_regex(clients: ClientRegistry) -> None:
    resp = clients.Password.create(
        ident="abcℕ",
        title="so_secret",
        password="no_one_can_know",
        shared=["all"],
        editable_by="admin",
        expect_ok=False,
    )

    resp.assert_status_code(400)
    assert (
        resp.json["fields"]["body.ident"]["msg"]
        == "Value error, 'abcℕ' does not match pattern. An identifier must only consist of letters, digits, dash and underscore and it must start with a letter or underscore."
    )


@pytest.mark.usefixtures("mock_password_file_regeneration")
def test_delete_own_password_does_not_delete_other_passwords(
    clients: ClientRegistry,
    with_automation_user: tuple[str, str],
    with_automation_user_not_admin: tuple[str, str],
) -> None:
    """Regression test: deleting a user's own password must not delete other users' passwords.

    Steps to reproduce the bug:
    1. Admin creates a password.
    2. A normal monitoring user (in a contact group) creates their own password.
    3. The normal user deletes their own password.
    4. The admin's password was also deleted as a side effect (bug).
    """
    # Seed the password store directly to avoid managed-edition customer validation.
    # The admin's password is owned by "admin" (not editable by normal users).
    # The user's password is owned by "all" (editable by the non-admin automation user
    # which has contactgroups=["all"]).
    PasswordStore().save(
        {
            "admin_pw": PasswordConfig(
                title="Admin Password",
                comment="",
                docu_url="",
                password="admin_secret",
                owned_by="admin",
                shared_with=[],
            ),
            "user_pw": PasswordConfig(
                title="User Password",
                comment="",
                docu_url="",
                password="user_secret",
                owned_by="all",
                shared_with=[],
            ),
        },
        pprint_value=False,
    )

    # Switch to the non-admin automation user (role="user", contactgroups=["all"]).
    # They own "user_pw" (owned_by="all") but not "admin_pw" (owned_by="admin").
    clients.Password.set_credentials(*with_automation_user_not_admin)

    # Normal user deletes their own password – this must not affect other passwords.
    clients.Password.delete("user_pw").assert_status_code(204)

    # Switch back to admin and verify the admin password still exists.
    # Before the fix, the admin's password was deleted as a side effect.
    clients.Password.set_credentials(*with_automation_user)
    resp = clients.Password.get_all()
    password_idents = [entry["id"] for entry in resp.json["value"]]
    assert "admin_pw" in password_idents, (
        "Admin password was unexpectedly deleted when the normal user deleted their own password."
    )


@pytest.mark.usefixtures("mock_password_file_regeneration")
def test_normal_user_cannot_delete_another_users_password(
    clients: ClientRegistry,
    with_automation_user_not_admin: tuple[str, str],
) -> None:
    """A normal monitoring user must not be able to delete a password they do not own.

    The admin's password is not visible to the normal user (not shared, not owned by their
    contact group), so the deletion must be rejected.
    """
    # Seed the password store directly to avoid managed-edition customer validation.
    PasswordStore().save(
        {
            "admin_pw": PasswordConfig(
                title="Admin Password",
                comment="",
                docu_url="",
                password="admin_secret",
                owned_by="admin",
                shared_with=[],
            ),
        },
        pprint_value=False,
    )

    # Switch to the non-admin automation user (role="user", contactgroups=["all"]).
    # "admin_pw" is owned_by="admin" which is not in the user's contact groups,
    # and is not shared with them, so it is not visible and the deletion must be rejected.
    # The password appears non-existent to this user (404), since visibility is filtered.
    clients.Password.set_credentials(*with_automation_user_not_admin)
    clients.Password.delete("admin_pw", expect_ok=False).assert_status_code(404)
