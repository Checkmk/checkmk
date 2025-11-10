#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from typing import Protocol

from meraki.exceptions import APIError  # type: ignore[import-not-found]

from cmk.plugins.cisco_meraki.lib.log import LOGGER
from cmk.plugins.cisco_meraki.lib.schema import Organisation, RawOrganisation


class OrganizationsSDK(Protocol):
    def getOrganizations(self) -> Sequence[RawOrganisation]: ...
    def getOrganization(self, organizationId: str) -> RawOrganisation: ...


class OrganizationsClient:
    def __init__(self, sdk: OrganizationsSDK) -> None:
        self._sdk = sdk

    def get_all(self) -> Sequence[Organisation]:
        try:
            return [
                Organisation(id_=organisation["id"], name=organisation["name"])
                for organisation in self._sdk.getOrganizations()
            ]
        except APIError as e:
            LOGGER.debug("Get organisations: %r", e)
            return []

    def get_by_id(self, org_id: str) -> Organisation:
        try:
            org = self._sdk.getOrganization(org_id)
        except APIError as e:
            LOGGER.debug("Get organisation by ID %r: %r", org_id, e)
            return Organisation(id_=org_id, name="")
        return Organisation(id_=org["id"], name=org["name"])
