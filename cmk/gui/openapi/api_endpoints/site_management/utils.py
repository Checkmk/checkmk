#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.utils import permission_verification as permissions

PERMISSIONS = permissions.Perm("wato.sites")

PERMISSIONS_WITH_SAML_CONNECTION_READ = permissions.AllPerm(
    [
        PERMISSIONS,
        # Only bodies that reference a SAML connection reach the check in
        # SAMLConnectionIDConverter, hence optional.
        permissions.Optional(permissions.Perm("wato.global")),
    ]
)

LOGIN_PERMISSIONS = permissions.AllPerm(
    [
        permissions.Perm("wato.users"),
        PERMISSIONS,
    ]
)
