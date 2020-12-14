#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest  # type: ignore[import]

import cmk.helpers.snmp_backend._utils as utils
from cmk.helpers.snmp_backend import StoredWalkSNMPBackend


@pytest.mark.parametrize("value,expected", [
    ("", b""),
    ("\"\"", b""),
    ("\"B2 E0 7D 2C 4D 15 \"", b"\xb2\xe0},M\x15"),
    ("\"B2 E0 7D 2C 4D 15\"", b"B2 E0 7D 2C 4D 15"),
])
def test_strip_snmp_value(value, expected):
    assert utils.strip_snmp_value(value) == expected


class TestStoredWalkSNMPBackend:
    @pytest.mark.parametrize("a, b, result", [
        ("1.2.3", "1.2.3", 0),
        ("1.2.3", ".1.2.3", 0),
        (".1.2.3", "1.2.3", 0),
        (".1.2.3", ".1.2.3", 0),
        ("1.2.3", "1.2.3.4", 0),
        ("1.2.3.4", "1.2.3", 1),
        ("1.2.3", "4.5.6", -1),
    ])
    def test_compare_oids(self, a, b, result):
        assert StoredWalkSNMPBackend._compare_oids(a, b) == result
