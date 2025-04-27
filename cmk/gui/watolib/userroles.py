#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re
from collections.abc import Iterator, Mapping
from datetime import datetime
from typing import NewType

from marshmallow import ValidationError

from cmk.gui.exceptions import MKUserError
from cmk.gui.i18n import _
from cmk.gui.permissions import permission_registry
from cmk.gui.type_defs import Users
from cmk.gui.userdb import (
    is_two_factor_login_enabled,
    load_roles,
    load_users,
    save_users,
    UserRole,
    UserRolesConfigFile,
)

RoleID = NewType("RoleID", str)


def clone_role(
    role_id: RoleID,
    pprint_value: bool,
    new_role_id: str | None = None,
    new_alias: str | None = None,
    two_factor: bool | None = None,
) -> UserRole:
    all_roles: dict[RoleID, UserRole] = get_all_roles()
    role_to_clone: UserRole = get_role(role_id)

    if new_role_id is None:
        new_role_id = str(role_id)

    while new_role_id in all_roles.keys():
        new_role_id += "x"

    if new_alias is None:
        new_alias = role_to_clone.alias

    while new_alias in {role.alias for role in all_roles.values()}:
        new_alias += _(" (copy)")

    cloned_user_role = UserRole(
        name=new_role_id,
        basedon=role_to_clone.basedon or role_to_clone.name,
        two_factor=role_to_clone.two_factor if two_factor is None else two_factor,
        alias=new_alias,
        permissions=role_to_clone.permissions,
    )
    all_roles[RoleID(new_role_id)] = cloned_user_role
    UserRolesConfigFile().save(
        {role.name: role.to_dict() for role in all_roles.values()}, pprint_value
    )

    return cloned_user_role


def get_all_roles() -> dict[RoleID, UserRole]:
    stored_roles: dict[str, dict] = load_roles()
    return {
        RoleID(roleid): UserRole(name=roleid, **params) for roleid, params in stored_roles.items()
    }


def get_role(role_id: RoleID) -> UserRole:
    all_roles: Mapping[RoleID, UserRole] = get_all_roles()
    if role := all_roles.get(role_id):
        return role
    raise MKUserError(None, _("This role does not exist."))


def role_exists(role_id: RoleID) -> bool:
    if get_all_roles().get(role_id) is not None:
        return True
    return False


def delete_role(role_id: RoleID, pprint_value: bool) -> None:
    all_roles: dict[RoleID, UserRole] = get_all_roles()
    role_to_delete: UserRole = get_role(role_id)

    if role_to_delete.builtin:
        raise MKUserError(None, _("You cannot delete the built-in roles!"))

    # Check if currently being used by a user
    users: Users = load_users()
    for user in users.values():
        if role_id in user["roles"]:
            raise MKUserError(
                None,
                _("You cannot delete roles, that are still in use (%s)!") % role_id,
            )

    # TODO: Not sure this call is required. Error is already raised above if an existing user has this role.
    rename_user_role(role_id, None)  # Remove from existing users

    del all_roles[role_id]
    UserRolesConfigFile().save(
        {role.name: role.to_dict() for role in all_roles.values()}, pprint_value
    )


def rename_user_role(role_id: RoleID, new_role_id: RoleID | None) -> None:
    users = load_users(lock=True)
    for user in users.values():
        if role_id in user["roles"]:
            user["roles"].remove(role_id)
            if new_role_id:
                user["roles"].append(new_role_id)
    save_users(users, datetime.now())


def validate_new_alias(old_alias: str, new_alias: str) -> None:
    if old_alias != new_alias:
        existing_aliases = {role.alias: role_id for role_id, role in get_all_roles().items()}
        if role_id := existing_aliases.get(new_alias):
            raise ValidationError(_("This alias is already used in the role %s.") % role_id)


def validate_new_roleid(old_roleid: str, new_roleid: str) -> None:
    existing_role: UserRole = get_role(RoleID(old_roleid))
    if not new_roleid:
        raise ValidationError(_("You have to provide a role ID."))

    if old_roleid != new_roleid:
        if existing_role.builtin:
            raise ValidationError(_("The ID of a built-in user role cannot be changed"))

        if new_roleid in get_all_roles():
            raise ValidationError(_("The ID is already used by another role"))

        if not re.match("^[-a-z0-9A-Z_]*$", new_roleid):
            raise ValidationError(
                _("Invalid role ID. Only the characters a-z, A-Z, 0-9, _ and - are allowed.")
            )


def update_permissions(role: UserRole, new_permissions: Iterator[tuple[str, str]] | None) -> None:
    if new_permissions is None:
        return

    for var_name, value in new_permissions:
        var_name = var_name.replace("perm_", "")
        try:
            perm = permission_registry[var_name]
        except KeyError:
            continue

        if value == "yes":
            role.permissions[perm.name] = True
        elif value == "no":
            role.permissions[perm.name] = False
        elif value == "default":
            try:
                del role.permissions[perm.name]
            except KeyError:
                pass  # Already at defaults


def update_role(role: UserRole, old_roleid: RoleID, new_roleid: RoleID, pprint_value: bool) -> None:
    all_roles: dict[RoleID, UserRole] = get_all_roles()
    del all_roles[old_roleid]
    all_roles[new_roleid] = role
    UserRolesConfigFile().save(
        {role.name: role.to_dict() for role in all_roles.values()}, pprint_value
    )


def logout_users_with_role(role_id: RoleID) -> None:
    users = load_users(lock=True)
    for user_id, user in users.items():
        if role_id in user["roles"] and not is_two_factor_login_enabled(user_id):
            user["serial"] = user.get("serial", 0) + 1
    save_users(users, datetime.now())
