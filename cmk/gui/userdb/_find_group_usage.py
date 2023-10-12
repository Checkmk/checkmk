#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.groups import GroupName
from cmk.gui.i18n import _
from cmk.gui.type_defs import GlobalSettings
from cmk.gui.watolib.hosts_and_folders import folder_preserving_link

from .store import load_users


def find_usages_of_contact_group_in_users(
    name: GroupName, _settings: GlobalSettings
) -> list[tuple[str, str]]:
    """Is the contactgroup assigned to a user?"""
    used_in = []
    users = load_users()
    for userid, user_spec in sorted(users.items(), key=lambda x: x[1].get("alias", x[0])):
        cgs = user_spec.get("contactgroups", [])
        if name in cgs:
            used_in.append(
                (
                    "{}: {}".format(_("User"), user_spec.get("alias", userid)),
                    folder_preserving_link([("mode", "edit_user"), ("edit", userid)]),
                )
            )
    return used_in
