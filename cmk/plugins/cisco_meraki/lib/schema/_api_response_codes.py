#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

from typing import TypedDict


class RawApiResponseCodes(TypedDict):
    """
    Api Requests Overview Response Codes by Interval
    <https://developer.cisco.com/meraki/api-v1/get-organization-api-requests-overview-response-codes-by-interval/>
    """

    startTs: str
    endTs: str
    counts: list[_Count]


class ApiResponseCodes(RawApiResponseCodes):
    organization_id: str
    organization_name: str
    api_enabled: bool


class _Count(TypedDict):
    code: int
    count: int
