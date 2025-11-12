#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

from typing import Protocol

from meraki.exceptions import APIError  # type: ignore[import-not-found]

from cmk.plugins.cisco_meraki.lib.log import LOGGER
from cmk.plugins.cisco_meraki.lib.schema import LicensesOverview, RawLicensesOverview


class LicensesSDK(Protocol):
    def getOrganizationLicensesOverview(self, organizationId: str) -> RawLicensesOverview: ...


class LicensesClient:
    def __init__(self, sdk: LicensesSDK) -> None:
        self._sdk = sdk

    def __call__(self, id_: str, name: str) -> LicensesOverview | None:
        if not (raw_overview := self._get_raw_overview(id_)):
            return None

        return LicensesOverview(
            organisation_id=id_,
            organisation_name=name,
            **raw_overview,
        )

    def _get_raw_overview(self, org_id: str) -> RawLicensesOverview | None:
        try:
            return self._sdk.getOrganizationLicensesOverview(org_id)
        except APIError as e:
            LOGGER.debug("Organisation ID: %r: Get license overview: %r", org_id, e)
            return None
