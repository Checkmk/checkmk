#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import cmk.gui.utils.permission_verification as permissions

PERMISSIONS_AGENT_REGISTRATION = permissions.AllPerm(
    [
        permissions.Perm("wato.manage_hosts"),
        permissions.Perm("wato.edit_hosts"),
        permissions.Perm("wato.download_agents"),
        permissions.Perm("wato.download_all_agents"),
    ]
)
