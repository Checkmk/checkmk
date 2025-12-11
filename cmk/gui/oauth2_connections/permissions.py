#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.default_permissions import PERMISSION_SECTION_GENERAL
from cmk.gui.i18n import _l
from cmk.gui.permissions import Permission

PermissionUseOAuthConnections = Permission(
    section=PERMISSION_SECTION_GENERAL,
    name="oauth2_connections",
    title=_l("Manage OAuth2 connections"),
    description=_l(
        "With this permission set, users can manage OAuth2 connections for authentication."
    ),
    defaults=["admin"],
)
