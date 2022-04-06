#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Dict, List, Literal, Optional

import cmk.utils.paths
from cmk.utils.type_defs import UserId

import cmk.gui.permissions as permissions
from cmk.gui.globals import active_config


def user_may(user_id: Optional[UserId], pname: str) -> bool:
    return may_with_roles(roles_of_user(user_id), pname)


def get_role_permissions() -> Dict[str, List[str]]:
    """Returns the set of permissions for all roles"""
    role_permissions: Dict[str, List[str]] = {}
    roleids = set(active_config.roles.keys())
    for perm in permissions.permission_registry.values():
        for role_id in roleids:
            if role_id not in role_permissions:
                role_permissions[role_id] = []

            if may_with_roles([role_id], perm.name):
                role_permissions[role_id].append(perm.name)
    return role_permissions


def may_with_roles(some_role_ids: List[str], pname: str) -> bool:
    # If at least one of the given roles has this permission, it's fine
    for role_id in some_role_ids:
        role = active_config.roles[role_id]

        they_may = role.get("permissions", {}).get(pname)
        # Handle compatibility with permissions without "general." that
        # users might have saved in their own custom roles.
        if they_may is None and pname.startswith("general."):
            they_may = role.get("permissions", {}).get(pname[8:])

        if they_may is None:  # not explicitely listed -> take defaults
            if "basedon" in role:
                base_role_id = role["basedon"]
            else:
                base_role_id = role_id
            if pname not in permissions.permission_registry:
                return False  # Permission unknown. Assume False. Functionality might be missing
            perm = permissions.permission_registry[pname]
            they_may = base_role_id in perm.defaults
        if they_may:
            return True
    return False


def is_user_with_publish_permissions(
    for_type: Literal["visual", "pagetype"],
    user_id: Optional[UserId],
    type_name: str,
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

    return (
        user_may(user_id, publish_all_permission)
        or user_may(user_id, publish_groups_permission)
        or user_may(user_id, publish_foreign_groups_permission)
    )


def roles_of_user(user_id: Optional[UserId]) -> List[str]:
    def existing_role_ids(role_ids):
        return [role_id for role_id in role_ids if role_id in active_config.roles]

    if user_id in active_config.multisite_users:
        return existing_role_ids(active_config.multisite_users[user_id]["roles"])
    if user_id in active_config.admin_users:
        return ["admin"]
    if user_id in active_config.guest_users:
        return ["guest"]
    if active_config.users is not None and user_id in active_config.users:
        return ["user"]
    if (
        user_id is not None
        and cmk.utils.paths.profile_dir.joinpath(user_id, "automation.secret").exists()
    ):
        return ["guest"]  # unknown user with automation account
    if "roles" in active_config.default_user_profile:
        return existing_role_ids(active_config.default_user_profile["roles"])
    if active_config.default_user_role:
        return existing_role_ids([active_config.default_user_role])
    return []
