#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from pathlib import Path
from unittest.mock import ANY

import pytest

from cmk.crypto.password import PasswordPolicy
from cmk.crypto.password_hashing import PasswordHash
from cmk.gui.breadcrumb import BreadcrumbItem
from cmk.gui.http import request
from cmk.gui.type_defs import UserSpec
from cmk.gui.wato.pages.users import (
    _get_user_role_links,
    _RoleAlias,
    _RoleLinkSpec,
    ModeEditUser,
    ModeUsers,
)


@pytest.mark.usefixtures("request_context")
def test_get_user_role_links() -> None:
    """If a user role doesn't exist in the roles mapping, do not crash when building urls."""
    roles: Mapping[str, _RoleAlias] = {"admin": {"alias": "Administrator"}}
    user_roles = ["admin", "nonexistent_role"]

    value = _get_user_role_links(user_roles, roles)
    expected = [
        _RoleLinkSpec(
            alias="Administrator",
            url="wato.py?edit=admin&folder=&mode=edit_role",
        ),
        _RoleLinkSpec(
            alias="nonexistent_role",  # falls back to the user role
            url="wato.py?edit=nonexistent_role&folder=&mode=edit_role",
        ),
    ]

    assert value == expected


@pytest.mark.usefixtures("request_context")
def test_users_breadcrumb_dont_list_users_topic() -> None:
    assert list(ModeUsers().breadcrumb()) == [
        BreadcrumbItem(title="Users", url="wato.py?mode=users"),
    ]


@pytest.mark.usefixtures("request_context")
def test_edituser_breadcrumb_dont_list_users_topic() -> None:
    request.set_var("user", "testuser")
    assert list(ModeEditUser().breadcrumb()) == [
        BreadcrumbItem(title="Users", url="wato.py?mode=users"),
        BreadcrumbItem(title="Edit user testuser", url="wato.py?edit=testuser&mode=edit_user"),
    ]


@pytest.mark.usefixtures("request_context")
def test_password_user_choose_secret_wo_secret() -> None:
    request.set_var("authmethod", "secret")
    mode = ModeEditUser()

    user_with_password_auth = UserSpec(
        is_automation_user=False,
        password=PasswordHash("$2y$12$foo"),
    )
    mode._handle_auth_attributes(user_with_password_auth, PasswordPolicy(12, None, False, Path("")))
    assert user_with_password_auth == {
        "is_automation_user": False,
        "store_automation_secret": False,
    }


@pytest.mark.usefixtures("request_context")
def test_password_user_choose_secret_w_secret() -> None:
    request.set_var("authmethod", "secret")
    request.set_var("_auth_secret", "secret")
    mode = ModeEditUser()

    user_with_password_auth = UserSpec(
        is_automation_user=False,
        password=PasswordHash("$2y$12$foo"),
        serial=42,
    )
    mode._handle_auth_attributes(user_with_password_auth, PasswordPolicy(12, None, False, Path("")))
    assert user_with_password_auth == {
        "automation_secret": "secret",
        "is_automation_user": True,
        "last_pw_change": ANY,  # current time
        "password": ANY,  # hashed with random salt
        "serial": 43,
        "store_automation_secret": False,
    }


@pytest.mark.usefixtures("request_context")
def test_automation_user_choose_secret_wo_secret() -> None:
    request.set_var("authmethod", "secret")
    mode = ModeEditUser()

    user_with_secret_auth = UserSpec(
        is_automation_user=True,
        last_pw_change=23,
        password=PasswordHash("$2y$12$foo"),
        serial=42,
        store_automation_secret=False,
    )
    mode._handle_auth_attributes(user_with_secret_auth, PasswordPolicy(12, None, False, Path("")))
    assert user_with_secret_auth == {
        "is_automation_user": True,
        "last_pw_change": 23,
        "password": "$2y$12$foo",
        "serial": 42,
        "store_automation_secret": False,
    }


@pytest.mark.usefixtures("request_context")
def test_automation_user_choose_password_wo_pw() -> None:
    request.set_var("authmethod", "password")
    mode = ModeEditUser()

    user_with_secret_auth = UserSpec(
        is_automation_user=True,
        last_pw_change=23,
        password=PasswordHash("$2y$12$foo"),
        serial=42,
        store_automation_secret=False,
    )
    mode._handle_auth_attributes(user_with_secret_auth, PasswordPolicy(12, None, False, Path("")))
    assert user_with_secret_auth == {
        "is_automation_user": False,
        "last_pw_change": 23,
        "serial": 42,
        "enforce_pw_change": None,
    }


@pytest.mark.usefixtures("request_context")
def test_automation_user_choose_password_w_pw() -> None:
    mode = ModeEditUser()
    request.set_var("authmethod", "password")
    request.set_var("_password_" + mode._pw_suffix(), "longer_than_12")

    user_with_secret_auth = UserSpec(
        is_automation_user=True,
        last_pw_change=23,
        password=PasswordHash("$2y$12$foo"),
        serial=42,
        store_automation_secret=False,
    )
    mode._handle_auth_attributes(user_with_secret_auth, PasswordPolicy(12, None, False, Path("")))
    assert user_with_secret_auth == {
        "is_automation_user": False,
        "last_pw_change": ANY,
        "serial": 43,
        "enforce_pw_change": None,
        "password": ANY,  # hashed with random salt
    }
