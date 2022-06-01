#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Dict, Mapping, NewType, Optional

import cmk.utils.store as store

import cmk.gui.hooks as hooks
import cmk.gui.plugins.userdb.utils as userdb_utils
import cmk.gui.userdb as userdb
from cmk.gui.exceptions import MKUserError
from cmk.gui.globals import config, transactions
from cmk.gui.i18n import _
from cmk.gui.type_defs import UserRole
from cmk.gui.watolib.utils import multisite_dir

RoleID = NewType("RoleID", str)


def clone_role(role_id: RoleID) -> UserRole:
    all_roles: Dict[RoleID, UserRole] = get_all_roles()
    role_to_clone: UserRole = get_role(role_id)

    new_role_id = str(role_id)
    while new_role_id in all_roles.keys():
        new_role_id += "x"

    newalias = role_to_clone.alias
    while newalias in {role.alias for role in all_roles.values()}:
        newalias += _(" (copy)")

    cloned_user_role = UserRole(name=new_role_id, basedon=role_to_clone.name, alias=newalias)
    all_roles[RoleID(new_role_id)] = cloned_user_role
    save_all_roles(all_roles)

    return cloned_user_role


def get_all_roles() -> Dict[RoleID, UserRole]:
    stored_roles: dict[str, dict] = userdb_utils.load_roles()
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


def delete_role(role_id: RoleID) -> None:
    all_roles: Dict[RoleID, UserRole] = get_all_roles()
    role_to_delete: UserRole = get_role(role_id)

    if transactions.transaction_valid() and role_to_delete.builtin:
        raise MKUserError(None, _("You cannot delete the builtin roles!"))

    # Check if currently being used by a user
    users = userdb.load_users()
    for user in users.values():
        if role_id in user["roles"]:
            raise MKUserError(
                None,
                _("You cannot delete roles, that are still in use (%s)!") % role_id,
            )

    # TODO: Not sure this call is required. Error is already raised above if an existing user has this role.
    rename_user_role(role_id, None)  # Remove from existing users

    del all_roles[role_id]
    save_all_roles(all_roles)


def save_all_roles(all_roles: Dict[RoleID, UserRole]) -> None:
    roles_as_dicts: Dict[str, dict] = {role.name: role.to_dict() for role in all_roles.values()}
    config.roles.update(roles_as_dicts)
    store.mkdir(multisite_dir())
    store.save_to_mk_file(
        multisite_dir() + "roles.mk",
        "roles",
        roles_as_dicts,
        pprint_value=config.wato_pprint_config,
    )

    hooks.call("roles-saved", roles_as_dicts)


def rename_user_role(role_id: RoleID, new_role_id: Optional[RoleID]) -> None:
    users = userdb.load_users(lock=True)
    for user in users.values():
        if role_id in user["roles"]:
            user["roles"].remove(role_id)
            if new_role_id:
                user["roles"].append(new_role_id)
    userdb.save_users(users)
