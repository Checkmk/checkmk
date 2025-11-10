#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

from typing import Protocol

from meraki.exceptions import APIError  # type: ignore[import-not-found]

from cmk.plugins.cisco_meraki.lib.log import LOGGER
from cmk.plugins.cisco_meraki.lib.schema import LicensesOverview, Organisation, RawLicensesOverview


class LicensesSDK(Protocol):
    def getOrganizationLicensesOverview(self, organizationId: str) -> RawLicensesOverview: ...


class LicensesClient:
    def __init__(self, sdk: LicensesSDK) -> None:
        self._sdk = sdk

    def get_overview(self, org: Organisation) -> LicensesOverview | None:
        if not (raw_overview := self._get_raw_overview(org)):
            return None

        return LicensesOverview(
            organisation_id=org["id_"],
            organisation_name=org["name"],
            **raw_overview,
        )

    def _get_raw_overview(self, org: Organisation) -> RawLicensesOverview | None:
        org_id = org["id_"]
        try:
            return self._sdk.getOrganizationLicensesOverview(org_id)
        except APIError as e:
            LOGGER.debug("Organisation ID: %r: Get license overview: %r", org_id, e)
            return None
