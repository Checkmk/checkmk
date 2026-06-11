#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.openapi.framework.model import api_field, api_model


@api_model
class UpdateMasterControlModel:
    notifications: bool | None = api_field(
        default=None,
        description="Enable or disable notifications on the site.",
        example=True,
    )
    service_checks: bool | None = api_field(
        default=None,
        description="Enable or disable active service checks on the site.",
        example=True,
    )

    def to_changes(self) -> dict[str, bool]:
        """Return only the settings that were explicitly provided, keyed by API field name."""
        changes: dict[str, bool] = {}
        if self.notifications is not None:
            changes["notifications"] = self.notifications
        if self.service_checks is not None:
            changes["service_checks"] = self.service_checks
        return changes
