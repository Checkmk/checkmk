#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.checkengine.snmplib import SNMPBackendEnum
from cmk.fetchers.snmp_backend import discover_backends


def test_available_snmp_backends() -> None:
    assert set(discover_backends()) == {
        SNMPBackendEnum.CLASSIC,
        SNMPBackendEnum.STORED_WALK,
    }
