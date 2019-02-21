#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Check_MK.
# The official homepage is at http://mathias-kettner.de/check_mk.
#
# check_mk is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# tails. You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

from typing import NamedTuple, Union, Tuple

OID_END = 0  # Suffix-part of OID that was not specified
OID_STRING = -1  # Complete OID as string ".1.3.6.1.4.1.343...."
OID_BIN = -2  # Complete OID as binary string "\x01\x03\x06\x01..."
OID_END_BIN = -3  # Same, but just the end part
OID_END_OCTET_STRING = -4  # yet same, but omit first byte (assuming that is the length byte)


def BINARY(oid):
    """Tell Check_MK to process this OID as binary data to the check."""
    return "binary", oid


def CACHED_OID(oid):
    """Use this to mark OIDs as being cached for regular checks,
    but not for discovery"""
    return "cached", oid


def binstring_to_int(binstring):
    """Convert a string to an integer.

    This is done by consideren the string to by a little endian byte string.
    Such strings are sometimes used by SNMP to encode 64 bit counters without
    needed COUNTER64 (which is not available in SNMP v1)."""
    value = 0
    mult = 1
    for byte in binstring[::-1]:
        value += mult * ord(byte)
        mult *= 256
    return value


# TODO: Be more specific about the possible tuples
# if the credentials are a string, we use that as community,
# if it is a four-tuple, we use it as V3 auth parameters:
# (1) security level (-l)
# (2) auth protocol (-a, e.g. 'md5')
# (3) security name (-u)
# (4) auth password (-A)
# And if it is a six-tuple, it has the following additional arguments:
# (5) privacy protocol (DES|AES) (-x)
# (6) privacy protocol pass phrase (-X)
SNMPCredentials = Union[str, Tuple[str, str, str, str], Tuple[str, str, str, str], Tuple[str, str]]

# Wraps the configuration of a host into a single object for the SNMP code
SNMPHostConfig = NamedTuple("SNMPHostConfig", [
    ("hostname", str),
    ("ipaddress", str),
    ("credentials", SNMPCredentials),
    ("port", int),
    ("is_bulkwalk_host", bool),
    ("is_snmpv2c_host", bool),
    ("bulk_walk_size_of", int),
])
