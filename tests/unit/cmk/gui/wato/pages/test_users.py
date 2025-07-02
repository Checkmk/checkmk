#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from unittest.mock import ANY

from cmk.gui.breadcrumb import BreadcrumbItem
from cmk.gui.http import request
from cmk.gui.type_defs import UserSpec
from cmk.gui.wato.pages.users import ModeEditUser, ModeUsers

from cmk.crypto.password_hashing import PasswordHash


def test_users_breadcrumb_dont_list_users_topic(request_context: None) -> None:
    assert list(ModeUsers().breadcrumb()) == [
        BreadcrumbItem(title="Users", url="wato.py?mode=users"),
    ]


def test_edituser_breadcrumb_dont_list_users_topic(request_context: None) -> None:
    request.set_var("user", "testuser")
    assert list(ModeEditUser().breadcrumb()) == [
        BreadcrumbItem(title="Users", url="wato.py?mode=users"),
        BreadcrumbItem(title="Edit user testuser", url="wato.py?edit=testuser&mode=edit_user"),
    ]


def test_password_user_choose_secret_wo_secret(request_context: None) -> None:
    request.set_var("authmethod", "secret")
    mode = ModeEditUser()

    user_with_password_auth = UserSpec(
        is_automation_user=False,
        password=PasswordHash("$2y$12$foo"),
    )
    mode._handle_auth_attributes(user_with_password_auth)
    assert user_with_password_auth == {
        "is_automation_user": False,
        "store_automation_secret": False,
    }


def test_password_user_choose_secret_w_secret(request_context: None) -> None:
    request.set_var("authmethod", "secret")
    request.set_var("_auth_secret", "secret")
    mode = ModeEditUser()

    user_with_password_auth = UserSpec(
        is_automation_user=False,
        password=PasswordHash("$2y$12$foo"),
        serial=42,
    )
    mode._handle_auth_attributes(user_with_password_auth)
    assert user_with_password_auth == {
        "automation_secret": "secret",
        "is_automation_user": True,
        "last_pw_change": ANY,  # current time
        "password": ANY,  # hashed with random salt
        "serial": 43,
        "store_automation_secret": False,
    }


def test_automation_user_choose_secret_wo_secret(request_context: None) -> None:
    request.set_var("authmethod", "secret")
    mode = ModeEditUser()

    user_with_secret_auth = UserSpec(
        is_automation_user=True,
        last_pw_change=23,
        password=PasswordHash("$2y$12$foo"),
        serial=42,
        store_automation_secret=False,
    )
    mode._handle_auth_attributes(user_with_secret_auth)
    assert user_with_secret_auth == {
        "is_automation_user": True,
        "last_pw_change": 23,
        "password": "$2y$12$foo",
        "serial": 42,
        "store_automation_secret": False,
    }


def test_automation_user_choose_password_wo_pw(request_context: None) -> None:
    request.set_var("authmethod", "password")
    mode = ModeEditUser()

    user_with_secret_auth = UserSpec(
        is_automation_user=True,
        last_pw_change=23,
        password=PasswordHash("$2y$12$foo"),
        serial=42,
        store_automation_secret=False,
    )
    mode._handle_auth_attributes(user_with_secret_auth)
    assert user_with_secret_auth == {
        "is_automation_user": False,
        "last_pw_change": 23,
        "serial": 42,
        "enforce_pw_change": None,
    }


def test_automation_user_choose_password_w_pw(request_context: None) -> None:
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
    mode._handle_auth_attributes(user_with_secret_auth)
    assert user_with_secret_auth == {
        "is_automation_user": False,
        "last_pw_change": ANY,
        "serial": 43,
        "enforce_pw_change": None,
        "password": ANY,  # hashed with random salt
    }
