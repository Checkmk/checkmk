#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import NamedTuple, Optional


class Section(NamedTuple):
    policyViolationCount: Optional[int]
    complianceState: Optional[bool]
    osBuildVersion: Optional[str]
    androidSecurityPatchLevel: Optional[str]
    platformVersion: Optional[str]
    clientVersion: Optional[str]
    uptime: Optional[int]
    ipAddress: Optional[str]
    deviceModel: Optional[str]
    platformType: Optional[str]
    registrationState: Optional[str]
    manufacturer: Optional[str]
    serialNumber: Optional[str]
    dmPartitionName: Optional[str]


class SourceHostSection(NamedTuple):
    queryTime: Optional[int]
    total_count: Optional[int]
