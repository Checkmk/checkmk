#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import json
from typing import NamedTuple, Optional

from ..agent_based_api.v1.type_defs import StringTable


class Section(NamedTuple):
    policyViolationCount: Optional[int]
    complianceState: Optional[bool]
    osBuildVersion: Optional[str]
    androidSecurityPatchLevel: Optional[str]
    platformVersion: Optional[str]
    clientVersion: Optional[str]
    availableCapacity: Optional[float]
    uptime: Optional[int]
    ipAddress: Optional[str]


def parse_mobileiron(string_table: StringTable) -> Section:
    json_raw = json.loads(string_table[0][0])
    return Section(
        policyViolationCount=json_raw.get("policyViolationCount"),
        complianceState=json_raw.get("complianceState"),
        osBuildVersion=json_raw.get("osBuildVersion"),
        androidSecurityPatchLevel=json_raw.get("androidSecurityPatchLevel"),
        platformVersion=json_raw.get("platformVersion"),
        clientVersion=json_raw.get("clientVersion"),
        availableCapacity=json_raw.get("availableCapacity"),
        uptime=json_raw.get("uptime"),
        ipAddress=json_raw.get("ipAddress"),
    )
