#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.background_job import BackgroundJobRegistry
from cmk.gui.i18n import _l
from cmk.gui.openapi.restful_objects.registry import EndpointRegistry
from cmk.gui.parentscan import rest_api as _rest_api
from cmk.gui.parentscan.background_job import ParentScanBackgroundJob
from cmk.gui.parentscan.page import ModeParentScan
from cmk.gui.permissions import Permission, PermissionRegistry
from cmk.gui.wato import PERMISSION_SECTION_WATO
from cmk.gui.watolib.mode import ModeRegistry


def register(
    mode_registry: ModeRegistry,
    job_registry: BackgroundJobRegistry,
    endpoint_registry: EndpointRegistry,
    permission_registry: PermissionRegistry,
    *,
    ignore_duplicate_endpoints: bool = False,
) -> None:
    mode_registry.register(ModeParentScan)
    job_registry.register(ParentScanBackgroundJob)
    _rest_api.register(endpoint_registry, ignore_duplicates=ignore_duplicate_endpoints)
    permission_registry.register(
        Permission(
            section=PERMISSION_SECTION_WATO,
            name="parentscan",
            title=_l("Perform network parent scan"),
            description=_l(
                "This permission is necessary for performing automatic "
                "scans for network parents of hosts (making use of traceroute). "
                "Please note, that for actually modifying the parents via the "
                "scan and for the creation of gateway hosts proper permissions "
                "for host and folders are also necessary."
            ),
            defaults=["admin", "user"],
        )
    )
