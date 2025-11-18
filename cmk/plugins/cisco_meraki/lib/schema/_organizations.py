#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

from typing import TypedDict


class RawOrganisation(TypedDict):
    """
    Organization Resource
    <https://developer.cisco.com/meraki/api-v1/get-organization/>
    """

    id: str
    name: str
    url: str
    api: _Api
    licensing: _Licensing
    cloud: _Cloud
    management: _Management


class _Api(TypedDict):
    enabled: bool


class _Licensing(TypedDict):
    model: str


class _Cloud(TypedDict):
    region: _Region


class _Region(TypedDict):
    name: str
    host: _Host


class _Host(TypedDict):
    name: str


class _Management(TypedDict):
    details: list[_Detail]


class _Detail(TypedDict):
    name: str
    value: str
