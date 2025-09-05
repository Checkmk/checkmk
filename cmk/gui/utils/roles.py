#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import cast, Final, get_args, Literal

from cmk.ccc import store
from cmk.ccc.user import UserId
from cmk.gui.config import active_config, Config
from cmk.gui.permissions import Permission, permission_registry
from cmk.gui.role_types import BuiltInUserRole, BuiltInUserRoleID, CustomUserRole
from cmk.utils import paths


class UserPermissions:
    """Compute permissions of users and roles based on the given configuration.

    Implements some instance bound memoization to prevent expensive recomputations.
    """

    _default_admin_permissions: Final[frozenset[str]] = frozenset(
        {
            "general.use",  # use Multisite
            "wato.use",  # enter WATO
            "wato.edit",  # make changes in Setup...
            "wato.users",  # ... with access to user management
        }
    )

    @classmethod
    def from_config(
        cls, config: Config, permissions: Mapping[str, Permission]
    ) -> "UserPermissions":
        return cls(
            roles=config.roles,
            permissions=permissions,
            user_roles={
                UserId(user_id): user["roles"] for user_id, user in config.multisite_users.items()
            },
            default_user_profile_roles=config.default_user_profile["roles"],
        )

    def __init__(
        self,
        roles: Mapping[str, BuiltInUserRole | CustomUserRole],
        permissions: Mapping[str, Permission],
        user_roles: Mapping[UserId, Sequence[str]],
        default_user_profile_roles: Sequence[str],
    ) -> None:
        self._roles: Final = roles
        self._permissions: Final = permissions
        self._user_roles: Final = user_roles
        self._default_user_profile_roles: Final = default_user_profile_roles

        self._user_may_memo: dict[tuple[UserId | None, str], bool] = {}

    def roles_of_user(
        self,
        user_id: UserId | None,  # TODO: Can we get rid of the None user_id here?
    ) -> list[str]:
        def existing_role_ids(role_ids: Sequence[str]) -> list[str]:
            return [role_id for role_id in role_ids if role_id in self._roles]

        if user_id is not None and user_id in self._user_roles:
            return existing_role_ids(self._user_roles[user_id])

        # TODO: Can we get rid of these cases? Something basic like this would be nice:
        # return [role_id for role_id in self._user_roles.get(user_id, []) if role_id in self._roles]
        if user_id is not None and is_automation_user(user_id):
            return ["guest"]  # unknown user with automation account
        return existing_role_ids(self._default_user_profile_roles)

    def user_may(self, user_id: UserId | None, permission_name: str) -> bool:
        key = (user_id, permission_name)
        if key not in self._user_may_memo:
            self._user_may_memo[key] = self._user_may_no_memoize(user_id, permission_name)
        return self._user_may_memo[key]

    def _user_may_no_memoize(self, user_id: UserId | None, permission_name: str) -> bool:
        return self.may_with_roles(self.roles_of_user(user_id), permission_name)

    def may_with_roles(self, some_role_ids: list[str], permission_name: str) -> bool:
        # TODO: Can we get rid of the "admin" special case here? We should rather ensure
        # such permissions are not removed while editing the admin role.
        if "admin" in some_role_ids and permission_name in self._default_admin_permissions:
            return True

        # If at least one of the given roles has this permission, it's fine
        for role_id in some_role_ids:
            role = self._roles[role_id]

            they_may = role.get("permissions", {}).get(permission_name)
            # Handle compatibility with permissions without "general." that
            # users might have saved in their own custom roles.
            if they_may is None and permission_name.startswith("general."):
                they_may = role.get("permissions", {}).get(permission_name[8:])

            if they_may is None:  # not explicitely listed -> take defaults
                base_role_id = (
                    role["basedon"] if not role["builtin"] else builtin_role_id_from_str(role_id)
                )
                if permission_name not in self._permissions:
                    return False  # Permission unknown. Assume False. Functionality might be missing
                perm = self._permissions[permission_name]
                they_may = base_role_id in perm.defaults
            if they_may:
                return True
        return False

    def get_role_permissions(
        self,
    ) -> dict[str, list[str]]:
        """Returns the set of permissions for all roles"""
        role_permissions: dict[str, list[str]] = {}
        roleids = set(self._roles.keys())
        for perm in self._permissions.values():
            for role_id in roleids:
                if role_id not in role_permissions:
                    role_permissions[role_id] = []

                if self.may_with_roles([role_id], perm.name):
                    role_permissions[role_id].append(perm.name)
        return role_permissions


def builtin_role_id_from_str(role_id: str) -> BuiltInUserRoleID:
    if role_id not in get_args(BuiltInUserRoleID):
        raise ValueError("Invalid built-in role ID: {role_id}")
    return cast(BuiltInUserRoleID, role_id)


def is_two_factor_required(user_permissions: UserPermissions, user_id: UserId) -> bool:
    users_roles = user_permissions.roles_of_user(user_id)

    return any(
        active_config.roles[role_id].get("two_factor", False)
        for role_id in users_roles
        if role_id in active_config.roles
    )


def is_user_with_publish_permissions(
    for_type: Literal["visual", "pagetype"],
    user_id: UserId | None,
    type_name: str,
    user_permissions: UserPermissions,
) -> bool:
    """
    Visuals and PageTypes have different permission naming. We handle both
    types here to reduce duplicated code
    """
    publish_all_permission: str = "general.publish_" + type_name
    publish_groups_permission: str = (
        "general.publish_" + type_name + "_to_groups"
        if for_type == "visual"
        else "general.publish_to_groups_%s" % type_name
    )
    publish_foreign_groups_permission: str = (
        "general.publish_" + type_name + "_to_foreign_groups"
        if for_type == "visual"
        else "general.publish_to_foreign_groups_%s" % type_name
    )
    publish_sites_permission: str = (
        "general.publish_" + type_name + "_to_sites"
        if for_type == "visual"
        else "general.publish_to_sites_%s" % type_name
    )

    return (
        user_permissions.user_may(user_id, publish_all_permission)
        or user_permissions.user_may(user_id, publish_groups_permission)
        or user_permissions.user_may(user_id, publish_foreign_groups_permission)
        or user_permissions.user_may(user_id, publish_sites_permission)
    )


# TODO: Move to UserPermissions.user_may
def roles_of_user(user_id: UserId | None) -> list[str]:
    return UserPermissions.from_config(active_config, permission_registry).roles_of_user(user_id)


def is_automation_user(user_id: UserId) -> bool:
    return AutomationUserFile(user_id).load()


class AutomationUserFile:
    def __init__(self, user_id: UserId, profile_dir: Path | None = None) -> None:
        if profile_dir is None:
            profile_dir = paths.profile_dir
        self.path = profile_dir / user_id / "automation_user.mk"

    def load(self) -> bool:
        return store.load_object_from_file(self.path, default=False)

    def save(self, value: bool) -> None:
        self.path.parent.mkdir(mode=0o770, exist_ok=True)
        store.save_object_to_file(self.path, value)
