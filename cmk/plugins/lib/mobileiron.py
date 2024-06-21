#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import NamedTuple


class Section(NamedTuple):
    policy_violation_count: int | None
    compliance_state: bool | None
    os_build_version: str | None
    android_security_patch_level: str | None
    platform_version: str | None
    client_version: str | None
    uptime: int | None
    ip_address: str | None
    device_model: str | None
    platform_type: str | None
    registration_state: str | None
    manufacturer: str | None
    serial_number: str | None
    dm_partition_name: str | None


class SourceHostSection(NamedTuple):
    non_compliant: int
    total_count: int
