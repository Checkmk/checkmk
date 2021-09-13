#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Helpers for the backends."""

from cmk.snmplib.type_defs import SNMPRawValue

__all__ = ["strip_snmp_value"]


def strip_snmp_value(value: str) -> SNMPRawValue:
    v = value.strip()
    if v.startswith('"'):
        v = v[1:-1]
        if len(v) > 2 and _is_hex_string(v):
            return _convert_from_hex(v)
        # Fix for non hex encoded string which have been somehow encoded by the
        # netsnmp command line tools. An example:
        # Checking windows systems via SNMP with hr_fs: disk names like c:\
        # are reported as c:\\, fix this to single \
        return v.strip().replace("\\\\", "\\").encode()
    return v.encode()


def _is_hex_string(value: str) -> bool:
    # as far as I remember, snmpwalk puts a trailing space within
    # the quotes in case of hex strings. So we require that space
    # to be present in order make sure, we really deal with a hex string.
    if value[-1] != " ":
        return False
    hexdigits = "0123456789abcdefABCDEF"
    n = 0
    for x in value:
        if n % 3 == 2:
            if x != " ":
                return False
        else:
            if x not in hexdigits:
                return False
        n += 1
    return True


def _convert_from_hex(value: str) -> bytes:
    """Convert string containing a Hex-String to bytes

    e.g. "B2 E0 7D 2C 4D 15" -> b'\xb2\xe0},M\x15'
    """
    return bytes(bytearray(int(hx, 16) for hx in value.split()))
