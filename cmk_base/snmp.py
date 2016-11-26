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


OID_END              =  0  # Suffix-part of OID that was not specified
OID_STRING           = -1  # Complete OID as string ".1.3.6.1.4.1.343...."
OID_BIN              = -2  # Complete OID as binary string "\x01\x03\x06\x01..."
OID_END_BIN          = -3  # Same, but just the end part
OID_END_OCTET_STRING = -4  # yet same, but omit first byte (assuming that is the length byte)


def BINARY(oid):
    return "binary", oid


# Wrapper to mark OIDs as being cached for regular checks, but not for discovery
def CACHED_OID(oid):
    return "cached", oid


# Convert a string to an integer. This is done by consideren the string to by a
# little endian byte string.  Such strings are sometimes used by SNMP to encode
# 64 bit counters without needed COUNTER64 (which is not available in SNMP v1)
def binstring_to_int(binstring):
    value = 0
    mult = 1
    for byte in binstring[::-1]:
        value += mult * ord(byte)
        mult *= 256
    return value


