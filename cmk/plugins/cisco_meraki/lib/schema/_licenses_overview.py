#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

from typing import TypedDict


class RawLicensesOverview(TypedDict):
    """
    Organization Licenses Overview Resource
    <https://developer.cisco.com/meraki/api-v1/get-organization-licenses-overview/>
    """

    status: str
    expirationDate: str
    licensedDeviceCounts: dict[str, int]
    licenseCount: int
    states: _States
    licenseTypes: list[_LicenseType]
    systemsManager: _SystemsManager


class LicensesOverview(RawLicensesOverview):
    """Wrapped version of Licenses Overview Resource."""

    organisation_id: str
    organisation_name: str


class _States(TypedDict):
    active: _ExpiredOrRecentlyQueuedOrActive
    expired: _ExpiredOrRecentlyQueuedOrActive
    expiring: _Expiring
    recentlyQueued: _ExpiredOrRecentlyQueuedOrActive
    unused: _Unused
    unusedActive: _UnusedActive


class _Expiring(TypedDict):
    count: int
    critical: _CriticalOrWarning
    warning: _CriticalOrWarning


class _CriticalOrWarning(TypedDict):
    thresholdInDays: int
    expiringCount: int


class _ExpiredOrRecentlyQueuedOrActive(TypedDict):
    count: int


class _Unused(TypedDict):
    count: int
    soonestActivation: _SoonestActivation


class _SoonestActivation(TypedDict):
    activationDate: str
    toActivateCount: int


class _UnusedActive(TypedDict):
    count: int
    oldestActivation: _OldestActivation


class _OldestActivation(TypedDict):
    activationDate: str
    activeCount: int


class _LicenseType(TypedDict):
    licenseType: str
    counts: _LicenseTypeCounts


class _LicenseTypeCounts(TypedDict):
    unassigned: int


class _SystemsManager(TypedDict):
    counts: _SystemManagerCounts


class _SystemManagerCounts(TypedDict):
    totalSeats: int
    activeSeats: int
    unassignedSeats: int
    orgwideEnrolledDevices: int
