#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Optional

from cmk.utils.type_defs import CheckPluginNameStr

import cmk.snmplib.utils as snmp_utils
from cmk.snmplib.type_defs import OID, SNMPDecodedString


def oid_kea(_arg: OID,
            _decoded: Optional[SNMPDecodedString] = None,
            _name: Optional[CheckPluginNameStr] = None) -> Optional[SNMPDecodedString]:
    """OID function of a Kea"""
    return "Kea"


def scan_kea(oid):
    """Scan function scanning for Keas"""
    return oid(".O.I.D") == "Kea"


def test_mutex_scan_registry_register():
    scan_registry = snmp_utils.MutexScanRegistry()

    assert not scan_registry._is_specific(oid_kea)
    assert scan_kea is scan_registry.register(scan_kea)
    assert scan_registry._is_specific(oid_kea)


def test_mutex_scan_registry_as_fallback():
    scan_registry = snmp_utils.MutexScanRegistry()

    @scan_registry.as_fallback
    def scan_parrot(oid):
        return bool(oid(".O.I.D"))

    assert scan_parrot(oid_kea)

    scan_registry.register(scan_kea)
    assert not scan_parrot(oid_kea)
