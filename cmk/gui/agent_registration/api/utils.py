#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import cmk.gui.utils.permission_verification as permissions
from cmk.gui.exceptions import MKAuthException
from cmk.gui.logged_in import user
from cmk.gui.openapi.utils import ProblemException
from cmk.gui.watolib.hosts_and_folders import Host

PERMISSIONS_REGISTER_HOST = permissions.AnyPerm(
    [
        permissions.Perm("agent_registration.register_any_existing_host"),
        permissions.Perm("agent_registration.register_managed_existing_host"),
        permissions.AllPerm(
            [
                # read access
                permissions.Optional(permissions.Perm("wato.see_all_folders")),
                # write access
                permissions.AnyPerm(
                    [
                        permissions.Perm("wato.all_folders"),
                        permissions.Perm("wato.edit_hosts"),
                    ]
                ),
            ]
        ),
    ]
)


def verify_permissions(host: Host) -> None:
    if user.may("agent_registration.register_any_existing_host"):
        return
    if user.may("agent_registration.register_managed_existing_host") and host.is_contact(user):
        return

    unathorized_excpt = ProblemException(
        status=403,
        title="Insufficient permissions",
        detail="You have insufficient permissions to register this host. You either need the "
        "explicit permission to register any host, the explict permission to register this host or "
        "read and write access to this host.",
    )

    try:
        host.permissions.need_permission("read")
    except MKAuthException:
        raise unathorized_excpt
    try:
        host.permissions.need_permission("write")
    except MKAuthException:
        raise unathorized_excpt
