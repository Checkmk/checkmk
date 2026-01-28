#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.utils import permission_verification as permissions

IGNORE_PERMISSIONS = permissions.Undocumented(
    permissions.AnyPerm(
        [
            permissions.Perm("mkeventd.seeall"),
            permissions.Perm("general.see_all"),
            permissions.OkayToIgnorePerm("bi.see_all"),
        ]
    )
)

UPDATE_AND_ACKNOWLEDGE_PERMISSIONS = permissions.AllPerm(
    [
        permissions.Perm("mkeventd.update"),
        permissions.Perm("mkeventd.update_comment"),
        permissions.Perm("mkeventd.update_contact"),
        IGNORE_PERMISSIONS,
    ]
)

CHANGE_STATE_PERMISSIONS = permissions.AllPerm(
    [
        permissions.Perm("mkeventd.changestate"),
        IGNORE_PERMISSIONS,
    ]
)

DEL_PERMISSION = permissions.AllPerm(
    [
        permissions.Perm("mkeventd.delete"),
        IGNORE_PERMISSIONS,
    ]
)
