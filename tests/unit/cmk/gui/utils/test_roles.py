#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import ast
from dataclasses import asdict
from typing import get_args

import pytest

from cmk.ccc.user import UserId
from cmk.gui.config import Config
from cmk.gui.permissions import Permission, PermissionSection
from cmk.gui.role_types import BuiltInUserRole, BuiltInUserRoleID, CustomUserRole
from cmk.gui.type_defs import UserSpec
from cmk.gui.utils.roles import (
    builtin_role_id_from_str,
    UserPermissions,
    UserPermissionSerializableConfig,
)


def create_sample_roles() -> dict[str, BuiltInUserRole | CustomUserRole]:
    return {
        "admin": BuiltInUserRole(
            {
                "alias": "Administrator",
                "permissions": {"wato.edit": True, "general.use": True},
                "builtin": True,
            }
        ),
        "user": BuiltInUserRole(
            {
                "alias": "Normal monitoring user",
                "permissions": {"general.use": True},
                "builtin": True,
            }
        ),
        "guest": BuiltInUserRole(
            {
                "alias": "Guest user",
                "permissions": {},
                "builtin": True,
            }
        ),
        "custom_role": CustomUserRole(
            {
                "alias": "Custom role",
                "basedon": "user",
                "permissions": {"wato.use": True},
                "builtin": False,
            }
        ),
    }


def create_sample_permissions() -> dict[str, Permission]:
    general_section = PermissionSection(name="general", title="General", sort_index=10)
    wato_section = PermissionSection(name="wato", title="Setup", sort_index=20)

    return {
        "general.use": Permission(
            section=general_section,
            name="use",
            title="Use Multisite",
            description="Permission to use Multisite",
            defaults=["admin", "user"],
        ),
        "wato.use": Permission(
            section=wato_section,
            name="use",
            title="Enter Setup",
            description="Permission to enter Setup",
            defaults=["admin"],
        ),
        "wato.edit": Permission(
            section=wato_section,
            name="edit",
            title="Make changes in Setup",
            description="Permission to make changes in Setup",
            defaults=["admin"],
        ),
        "wato.users": Permission(
            section=wato_section,
            name="users",
            title="User management",
            description="Permission for user management",
            defaults=["admin"],
        ),
    }


def create_sample_users() -> dict[str, UserSpec]:
    return {
        "admin_user": UserSpec(roles=["admin"], contactgroups=[], force_authuser=False),
        "normal_user": UserSpec(roles=["user"], contactgroups=[], force_authuser=False),
        "guest_user": UserSpec(roles=["guest"], contactgroups=[], force_authuser=False),
        "multi_role_user": UserSpec(
            roles=["user", "custom_role"], contactgroups=[], force_authuser=False
        ),
    }


def create_config(
    roles: dict[str, BuiltInUserRole | CustomUserRole],
    users: dict[str, UserSpec],
) -> Config:
    config = Config()
    config.roles = roles
    config.multisite_users = users
    return config


def test_user_permissions_constructor() -> None:
    roles = create_sample_roles()
    permissions = create_sample_permissions()
    user_roles = {
        UserId("admin_user"): ["admin"],
        UserId("normal_user"): ["user"],
    }

    user_permissions = UserPermissions(
        roles=roles,
        permissions=permissions,
        user_roles=user_roles,
        default_user_profile_roles=["guest"],
    )

    assert user_permissions._roles is roles
    assert user_permissions._permissions is permissions
    assert user_permissions._user_roles is user_roles


def test_user_permissions_from_config() -> None:
    roles = create_sample_roles()
    permissions = create_sample_permissions()
    users = create_sample_users()
    config = create_config(roles=roles, users=users)

    user_permissions = UserPermissions.from_config(config, permissions)

    assert user_permissions._roles == config.roles
    assert user_permissions._permissions is permissions
    expected_user_roles = {
        UserId(user_id): user_spec["roles"] for user_id, user_spec in config.multisite_users.items()
    }
    assert user_permissions._user_roles == expected_user_roles


def test_user_permissions_from_serializable_config() -> None:
    roles = create_sample_roles()
    permissions = create_sample_permissions()
    users = create_sample_users()
    config = create_config(roles=roles, users=users)

    serializable = UserPermissionSerializableConfig.from_global_config(config)
    serialized = repr(asdict(serializable))

    user_permissions = UserPermissions.from_serialized_config(
        UserPermissionSerializableConfig(**ast.literal_eval(serialized)), permissions
    )

    assert user_permissions._roles == config.roles
    assert user_permissions._permissions is permissions
    expected_user_roles = {
        UserId(user_id): user_spec["roles"] for user_id, user_spec in config.multisite_users.items()
    }
    assert user_permissions._user_roles == expected_user_roles


def test_user_permissions_to_serializable_config() -> None:
    roles = create_sample_roles()
    permissions = create_sample_permissions()
    users = create_sample_users()
    config = create_config(roles=roles, users=users)

    user_permissions = UserPermissions.from_config(config, permissions)
    assert (
        user_permissions.to_serializable_config()
        == UserPermissionSerializableConfig.from_global_config(config)
    )


def test_may_with_roles_admin_default_permissions() -> None:
    roles = create_sample_roles()
    permissions = create_sample_permissions()
    user_permissions = UserPermissions(
        roles=roles,
        permissions=permissions,
        user_roles={},
        default_user_profile_roles=["guest"],
    )

    # Admin role has default permissions from _default_admin_permissions
    assert user_permissions.may_with_roles(["admin"], "general.use") is True
    assert user_permissions.may_with_roles(["admin"], "wato.use") is True
    assert user_permissions.may_with_roles(["admin"], "wato.edit") is True
    assert user_permissions.may_with_roles(["admin"], "wato.users") is True


def test_may_with_roles_explicit_permissions() -> None:
    roles = create_sample_roles()
    permissions = create_sample_permissions()
    user_permissions = UserPermissions(
        roles=roles,
        permissions=permissions,
        user_roles={},
        default_user_profile_roles=["guest"],
    )

    assert user_permissions.may_with_roles(["user"], "general.use") is True
    assert user_permissions.may_with_roles(["user"], "wato.edit") is False


def test_may_with_roles_permission_defaults() -> None:
    roles = create_sample_roles()
    permissions = create_sample_permissions()
    user_permissions = UserPermissions(
        roles=roles,
        permissions=permissions,
        user_roles={},
        default_user_profile_roles=["guest"],
    )

    assert user_permissions.may_with_roles(["guest"], "general.use") is False
    assert user_permissions.may_with_roles(["guest"], "wato.use") is False


def test_may_with_roles_custom_role() -> None:
    roles = create_sample_roles()
    permissions = create_sample_permissions()
    user_permissions = UserPermissions(
        roles=roles,
        permissions=permissions,
        user_roles={},
        default_user_profile_roles=["guest"],
    )

    assert user_permissions.may_with_roles(["custom_role"], "general.use") is True
    assert user_permissions.may_with_roles(["custom_role"], "wato.use") is True


def test_may_with_roles_multiple_roles() -> None:
    roles = create_sample_roles()
    permissions = create_sample_permissions()
    user_permissions = UserPermissions(
        roles=roles,
        permissions=permissions,
        user_roles={},
        default_user_profile_roles=["guest"],
    )

    assert user_permissions.may_with_roles(["guest", "admin"], "general.use") is True
    assert user_permissions.may_with_roles(["guest", "user"], "general.use") is True
    assert user_permissions.may_with_roles(["guest"], "general.use") is False


def test_may_with_roles_unknown_permission() -> None:
    roles = create_sample_roles()
    permissions = create_sample_permissions()
    user_permissions = UserPermissions(
        roles=roles,
        permissions=permissions,
        user_roles={},
        default_user_profile_roles=["guest"],
    )

    assert user_permissions.may_with_roles(["admin"], "unknown.permission") is False


def test_may_with_roles_compatibility_general_prefix() -> None:
    roles = create_sample_roles()
    permissions = create_sample_permissions()

    roles["test_role"] = BuiltInUserRole(
        {
            "alias": "Test role",
            "permissions": {"use": True},
            "builtin": True,
        }
    )

    user_permissions = UserPermissions(
        roles=roles,
        permissions=permissions,
        user_roles={},
        default_user_profile_roles=["guest"],
    )

    assert user_permissions.may_with_roles(["test_role"], "general.use") is True


def test_get_role_permissions() -> None:
    roles = create_sample_roles()
    permissions = create_sample_permissions()
    user_permissions = UserPermissions(
        roles=roles,
        permissions=permissions,
        user_roles={},
        default_user_profile_roles=["guest"],
    )

    role_permissions = user_permissions.get_role_permissions()

    assert "admin" in role_permissions
    assert "user" in role_permissions
    assert "guest" in role_permissions
    assert "custom_role" in role_permissions

    admin_perms = role_permissions["admin"]
    assert "general.use" in admin_perms
    assert "wato.use" in admin_perms
    assert "wato.edit" in admin_perms
    assert "wato.users" in admin_perms

    user_perms = role_permissions["user"]
    assert "general.use" in user_perms
    assert "wato.edit" not in user_perms


def test_builtin_role_id_from_str_valid_ids() -> None:
    valid_role_ids = get_args(BuiltInUserRoleID)
    for role_id in valid_role_ids:
        assert builtin_role_id_from_str(role_id) == role_id


def test_builtin_role_id_from_str_invalid_id() -> None:
    with pytest.raises(ValueError, match="Invalid built-in role ID"):
        builtin_role_id_from_str("invalid_role")


def test_builtin_role_id_from_str_custom_role() -> None:
    with pytest.raises(ValueError, match="Invalid built-in role ID"):
        builtin_role_id_from_str("custom_role")


def test_user_may_memoization() -> None:
    roles = create_sample_roles()
    permissions = create_sample_permissions()
    users = create_sample_users()
    config = create_config(roles=roles, users=users)

    user_permissions = UserPermissions.from_config(config, permissions)

    # Initially memo should be empty
    assert len(user_permissions._user_may_memo) == 0

    # First call should compute and cache the result
    result1 = user_permissions.user_may(UserId("admin_user"), "general.use")
    assert result1 is True
    assert len(user_permissions._user_may_memo) == 1
    assert (UserId("admin_user"), "general.use") in user_permissions._user_may_memo
    assert user_permissions._user_may_memo[(UserId("admin_user"), "general.use")] is True

    # Second call with same parameters should use cached result
    result2 = user_permissions.user_may(UserId("admin_user"), "general.use")
    assert result2 is True
    assert len(user_permissions._user_may_memo) == 1  # Still only one entry

    # Different user should create new cache entry
    result3 = user_permissions.user_may(UserId("normal_user"), "general.use")
    assert result3 is True
    assert len(user_permissions._user_may_memo) == 2
    assert (UserId("normal_user"), "general.use") in user_permissions._user_may_memo

    # Different permission should create new cache entry
    result4 = user_permissions.user_may(UserId("admin_user"), "wato.edit")
    assert result4 is True
    assert len(user_permissions._user_may_memo) == 3
    assert (UserId("admin_user"), "wato.edit") in user_permissions._user_may_memo


def test_user_may_memoization_preserves_behavior() -> None:
    """Test that memoization doesn't change the actual permission checking behavior"""
    roles = create_sample_roles()
    permissions = create_sample_permissions()
    users = create_sample_users()
    config = create_config(roles=roles, users=users)

    user_permissions = UserPermissions.from_config(config, permissions)

    # Test various permission scenarios to ensure memoization preserves correct results
    test_cases = [
        (UserId("admin_user"), "general.use", True),
        (UserId("admin_user"), "wato.edit", True),
        (UserId("normal_user"), "general.use", True),
        (UserId("normal_user"), "wato.edit", False),
        (UserId("guest_user"), "general.use", False),
        (UserId("guest_user"), "wato.use", False),
    ]

    # Call each test case multiple times to verify consistent memoized results
    for user_id, permission, expected in test_cases:
        # First call
        result1 = user_permissions.user_may(user_id, permission)
        assert result1 is expected, f"First call failed for {user_id}, {permission}"

        # Second call (should use cache)
        result2 = user_permissions.user_may(user_id, permission)
        assert result2 is expected, f"Second call failed for {user_id}, {permission}"
        assert result1 is result2, f"Memoized result differs for {user_id}, {permission}"

    # Verify all test cases were cached
    assert len(user_permissions._user_may_memo) == len(test_cases)
