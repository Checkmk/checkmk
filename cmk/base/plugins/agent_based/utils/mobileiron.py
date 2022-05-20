#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import NamedTuple, Optional


class Section(NamedTuple):
    policy_violation_count: Optional[int]
    compliance_state: Optional[bool]
    os_build_version: Optional[str]
    android_security_patch_level: Optional[str]
    platform_version: Optional[str]
    client_version: Optional[str]
    uptime: Optional[int]
    ip_address: Optional[str]
    device_model: Optional[str]
    platform_type: Optional[str]
    registration_state: Optional[str]
    manufacturer: Optional[str]
    serial_number: Optional[str]
    dm_partition_name: Optional[str]


class SourceHostSection(NamedTuple):
    query_time: Optional[int]
    total_count: Optional[int]
