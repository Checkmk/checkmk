#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.pages import PageRegistry
from cmk.gui.permissions import PermissionRegistry

from . import _permissions
from . import download as telemetry_download_page


def register(
    page_registry: PageRegistry,
    permission_registry: PermissionRegistry,
) -> None:
    telemetry_download_page.register(page_registry)
    _permissions.register(permission_registry)
