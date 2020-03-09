#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=protected-access
import pytest  # type: ignore[import]

from cmk.base import snmp_utils


@pytest.mark.parametrize("value", [3, ("foo", "bar")])
def test_oidspec_invalid_type(value):
    with pytest.raises(TypeError):
        _ = snmp_utils.OIDSpec(value)


@pytest.mark.parametrize("value", ["", "foo", "1."])
def test_oidspec_invalid_value(value):
    with pytest.raises(ValueError):
        _ = snmp_utils.OIDSpec(value)


@pytest.mark.parametrize("value", ["foo", 1])
def test_oidspec_invalid_adding_type(value):
    oid = snmp_utils.OIDSpec(".1.2.3")
    with pytest.raises(TypeError):
        _ = oid + value


@pytest.mark.parametrize("left, right", [
    (snmp_utils.OIDBytes("4.5"), snmp_utils.OIDBytes("4.5")),
    (snmp_utils.OIDSpec(".1.2.3"), snmp_utils.OIDSpec(".1.2.3")),
])
def test_oidspec_invalid_adding_value(left, right):
    with pytest.raises(ValueError):
        _ = left + right


def test_oidspec():

    oid_base = snmp_utils.OIDSpec(".1.2.3")
    oid_column = snmp_utils.OIDBytes("4.5")

    assert str(oid_base) == ".1.2.3"
    assert str(oid_column) == "4.5"

    assert repr(oid_base) == "OIDSpec('.1.2.3')"
    assert repr(oid_column) == "OIDBytes('4.5')"

    oid_sum = oid_base + oid_column
    assert isinstance(oid_sum, snmp_utils.OIDBytes)
    assert str(oid_sum) == ".1.2.3.4.5"


def oid_kea(_arg):
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
