#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from datetime import datetime
from pathlib import Path
from typing import cast
from unittest.mock import ANY

import pytest

from cmk.ccc.user import UserId
from cmk.ccc.version import Edition
from cmk.crypto.password import PasswordPolicy
from cmk.crypto.password_hashing import PasswordHash
from cmk.gui import userdb
from cmk.gui.breadcrumb import BreadcrumbItem
from cmk.gui.config import Config
from cmk.gui.http import request
from cmk.gui.pages import PageContext
from cmk.gui.permissions import all_permissions
from cmk.gui.type_defs import UserSpec
from cmk.gui.user_connection_config_types import LDAPUserConnectionConfig
from cmk.gui.userdb import get_user_attributes
from cmk.gui.utils.roles import UserPermissions
from cmk.gui.utils.session import session
from cmk.gui.utils.transaction_manager import transactions
from cmk.gui.wato.pages.users import (
    _get_user_role_links,
    _RoleAlias,
    _RoleLinkSpec,
    ModeEditUser,
    ModeUsers,
)
from tests.testlib.unit.gui.web_test_app import SetConfig


@pytest.mark.usefixtures("request_context")
def test_edit_user_keeps_the_stored_connector(test_edition: Edition) -> None:
    """Saving a user in Setup preserves whoever owns them.

    ``_get_identity_userattrs`` copies the connector from the *stored* user, so
    an LDAP- or SAML-owned account stays owned by that connection across an
    edit. Nothing in the Setup form can reassign it -- a crafted ``connector``
    request variable is ignored -- which is what stops an ordinary edit from
    silently migrating the user to local authentication and detaching them from
    their directory.
    """
    request.set_var("alias", "Directory User")
    request.set_var("pager", "")
    # First alternative of each valuespec on this form ("Use the global
    # configuration" / "All sites"), so it parses without further input.
    request.set_var("idle_timeout_use", "0")
    request.set_var("authorized_sites_use", "0")
    # A hand-crafted form field must not be able to reassign ownership.
    request.set_var("connector", "htpasswd")

    mode = ModeEditUser(
        test_edition,
        PageContext(
            config=Config(),
            request=request,
            transactions=transactions,
            session=session,
            user_permissions=UserPermissions.from_config(Config(), all_permissions()),
        ),
    )
    mode._user = UserSpec(connector="ldap_corp", alias="Directory User")  # noqa: SLF001

    user_attrs = UserSpec()
    mode._get_identity_userattrs(user_attrs)  # noqa: SLF001

    assert user_attrs["connector"] == "ldap_corp", (
        "an edit must not reassign the owning connector -- doing so would "
        "migrate the user to local authentication and orphan them from LDAP/SAML"
    )


@pytest.mark.usefixtures("request_context")
def test_edit_user_can_disable_the_login_of_a_connector_managed_user(
    test_edition: Edition, set_config: SetConfig
) -> None:
    """An administrator may disable the login of an LDAP or SAML user in Setup;
    the lock is not owned by the connector (CMK-40515)."""
    user_id = UserId("directory_user")
    ldap_connection = cast(
        LDAPUserConnectionConfig,
        {"type": "ldap", "id": "ldap_corp", "disabled": False, "active_plugins": {}},
    )
    with set_config(user_connections=[ldap_connection]):
        users = userdb.load_users(lock=True)
        users[user_id] = UserSpec(alias="Directory User", connector="ldap_corp", locked=False)
        userdb.save_users(
            users,
            get_user_attributes([]),
            [],
            now=datetime.now(),
            pprint_value=False,
            call_users_saved_hook=False,
            changed_users=[user_id],
        )
        request.set_var("edit", str(user_id))
        request.set_var("locked", "1")
        request.set_var("authmethod", "secret")
        mode = ModeEditUser(
            test_edition,
            PageContext(
                config=Config(),
                request=request,
                transactions=transactions,
                session=session,
                user_permissions=UserPermissions.from_config(Config(), all_permissions()),
            ),
        )

        user_attrs = UserSpec()
        mode._get_security_userattrs(user_attrs, PasswordPolicy(12, None, False, Path("")))  # noqa: SLF001

    assert user_attrs["locked"] is True


@pytest.mark.usefixtures("request_context")
def test_get_user_role_links() -> None:
    """If a user role doesn't exist in the roles mapping, do not crash when building urls."""
    roles: Mapping[str, _RoleAlias] = {"admin": {"alias": "Administrator"}}
    user_roles = ["admin", "nonexistent_role"]

    value = _get_user_role_links(user_roles, roles)
    expected = [
        _RoleLinkSpec(
            alias="Administrator",
            url="wato.py?edit=admin&mode=edit_role",
        ),
        _RoleLinkSpec(
            alias="nonexistent_role",  # falls back to the user role
            url="wato.py?edit=nonexistent_role&mode=edit_role",
        ),
    ]

    assert value == expected


@pytest.mark.usefixtures("request_context")
def test_users_breadcrumb_dont_list_users_topic(test_edition: Edition) -> None:
    assert list(
        ModeUsers(
            test_edition,
            PageContext(
                config=Config(),
                request=request,
                transactions=transactions,
                session=session,
                user_permissions=UserPermissions.from_config(Config(), all_permissions()),
            ),
        ).breadcrumb()
    ) == [
        BreadcrumbItem(title="Users", url="wato.py?mode=users", id="users"),
    ]


@pytest.mark.usefixtures("request_context")
def test_edituser_breadcrumb_dont_list_users_topic(test_edition: Edition) -> None:
    request.set_var("user", "testuser")
    assert list(
        ModeEditUser(
            test_edition,
            PageContext(
                config=Config(),
                request=request,
                transactions=transactions,
                session=session,
                user_permissions=UserPermissions.from_config(Config(), all_permissions()),
            ),
        ).breadcrumb()
    ) == [
        BreadcrumbItem(title="Users", url="wato.py?mode=users", id="users"),
        BreadcrumbItem(
            title="Edit user testuser",
            url="wato.py?edit=testuser&mode=edit_user",
            id="edit_user",
        ),
    ]


@pytest.mark.usefixtures("request_context")
def test_password_user_choose_secret_wo_secret(test_edition: Edition) -> None:
    request.set_var("authmethod", "secret")
    mode = ModeEditUser(
        test_edition,
        PageContext(
            config=Config(),
            request=request,
            transactions=transactions,
            session=session,
            user_permissions=UserPermissions.from_config(Config(), all_permissions()),
        ),
    )

    user_with_password_auth = UserSpec(
        is_automation_user=False,
        password=PasswordHash("$2y$12$foo"),
    )
    mode._handle_auth_attributes(user_with_password_auth, PasswordPolicy(12, None, False, Path("")))  # noqa: SLF001
    assert user_with_password_auth == {
        "is_automation_user": False,
        "store_automation_secret": False,
    }


@pytest.mark.usefixtures("request_context")
def test_password_user_choose_secret_w_secret(test_edition: Edition) -> None:
    request.set_var("authmethod", "secret")
    request.set_var("_auth_secret", "secret")
    mode = ModeEditUser(
        test_edition,
        PageContext(
            config=Config(),
            request=request,
            transactions=transactions,
            session=session,
            user_permissions=UserPermissions.from_config(Config(), all_permissions()),
        ),
    )

    user_with_password_auth = UserSpec(
        is_automation_user=False,
        password=PasswordHash("$2y$12$foo"),
        serial=42,
    )
    mode._handle_auth_attributes(user_with_password_auth, PasswordPolicy(12, None, False, Path("")))  # noqa: SLF001
    assert user_with_password_auth == {
        "automation_secret": "secret",
        "is_automation_user": True,
        "last_pw_change": ANY,  # current time
        "password": ANY,  # hashed with random salt
        "serial": 43,
        "store_automation_secret": False,
    }


@pytest.mark.usefixtures("request_context")
def test_automation_user_choose_secret_wo_secret(test_edition: Edition) -> None:
    request.set_var("authmethod", "secret")
    mode = ModeEditUser(
        test_edition,
        PageContext(
            config=Config(),
            request=request,
            transactions=transactions,
            session=session,
            user_permissions=UserPermissions.from_config(Config(), all_permissions()),
        ),
    )

    user_with_secret_auth = UserSpec(
        is_automation_user=True,
        last_pw_change=23,
        password=PasswordHash("$2y$12$foo"),
        serial=42,
        store_automation_secret=False,
    )
    mode._handle_auth_attributes(user_with_secret_auth, PasswordPolicy(12, None, False, Path("")))  # noqa: SLF001
    assert user_with_secret_auth == {
        "is_automation_user": True,
        "last_pw_change": 23,
        "password": "$2y$12$foo",
        "serial": 42,
        "store_automation_secret": False,
    }


@pytest.mark.usefixtures("request_context")
def test_automation_user_choose_password_wo_pw(test_edition: Edition) -> None:
    request.set_var("authmethod", "password")
    mode = ModeEditUser(
        test_edition,
        PageContext(
            config=Config(),
            request=request,
            transactions=transactions,
            session=session,
            user_permissions=UserPermissions.from_config(Config(), all_permissions()),
        ),
    )

    user_with_secret_auth = UserSpec(
        is_automation_user=True,
        last_pw_change=23,
        password=PasswordHash("$2y$12$foo"),
        serial=42,
        store_automation_secret=False,
    )
    mode._handle_auth_attributes(user_with_secret_auth, PasswordPolicy(12, None, False, Path("")))  # noqa: SLF001
    assert user_with_secret_auth == {
        "is_automation_user": False,
        "last_pw_change": 23,
        "serial": 42,
        "enforce_pw_change": None,
    }


@pytest.mark.usefixtures("request_context")
def test_automation_user_choose_password_w_pw(test_edition: Edition) -> None:
    mode = ModeEditUser(
        test_edition,
        PageContext(
            config=Config(),
            request=request,
            transactions=transactions,
            session=session,
            user_permissions=UserPermissions.from_config(Config(), all_permissions()),
        ),
    )
    request.set_var("authmethod", "password")
    request.set_var("_password_" + mode._pw_suffix(), "longer_than_12")  # noqa: SLF001

    user_with_secret_auth = UserSpec(
        is_automation_user=True,
        last_pw_change=23,
        password=PasswordHash("$2y$12$foo"),
        serial=42,
        store_automation_secret=False,
    )
    mode._handle_auth_attributes(user_with_secret_auth, PasswordPolicy(12, None, False, Path("")))  # noqa: SLF001
    assert user_with_secret_auth == {
        "is_automation_user": False,
        "last_pw_change": ANY,
        "serial": 43,
        "enforce_pw_change": None,
        "password": ANY,  # hashed with random salt
    }
