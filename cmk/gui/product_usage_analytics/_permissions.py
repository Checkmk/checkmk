#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.default_permissions import PERMISSION_SECTION_GENERAL
from cmk.gui.i18n import _l
from cmk.gui.permissions import Permission, PermissionRegistry


def register(permission_registry: PermissionRegistry) -> None:
    permission_registry.register(PERMISSION_DOWNLOAD_PRODUCT_USAGE_ANALYTICS)


PERMISSION_DOWNLOAD_PRODUCT_USAGE_ANALYTICS = Permission(
    section=PERMISSION_SECTION_GENERAL,
    name="download_product_usage_analytics",
    title=_l("Download product usage data"),
    description=_l("Allows users to download the product usage data as a JSON file."),
    defaults=["admin"],
)
