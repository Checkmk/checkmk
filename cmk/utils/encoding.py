#!/usr/bin/env python
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
"""This module provides some bytes-unicode encoding functions"""

import six


def convert_to_unicode(value):
    if isinstance(value, six.text_type):
        return value
    try:
        return value.decode("utf-8")
    except UnicodeDecodeError:
        pass
    try:
        return value.decode("latin-1")
    except UnicodeDecodeError:
        return u"(Invalid byte sequence)"


def ensure_unicode(value):
    try:
        return value.decode("utf-8")
    except UnicodeEncodeError:
        return value


def ensure_bytestr(value):
    try:
        return value.encode("utf-8")
    except UnicodeDecodeError:
        return value


def decode_incoming_string(value, encoding="utf-8", fallback_encoding="latin-1"):
    try:
        return value.decode(encoding)
    except UnicodeDecodeError:
        return value.decode(fallback_encoding)


def snmp_decode_string(value, encoding):
    if encoding:
        return value.decode(encoding)

    # Try to determine the current string encoding. In case a UTF-8 decoding fails, we decode latin1.
    try:
        return value.decode('utf-8')
    except UnicodeDecodeError:
        return value.decode('latin1')


# Alas, we often have no clue about the actual encoding, so we have to guess:
# Initially we assume UTF-8, but fall back to latin-1 if it didn't work.
def decode_from_bytes(value):
    # This is just a safeguard if we are inadvertedly called with a Unicode
    # string. In theory this should never happen, but given the typing chaos in
    # this script, one never knows. In the Unicode case, Python tries to be
    # "helpful", but this fails miserably: Calling 'decode' on a Unicode string
    # implicitly converts it via 'encode("ascii")' to a byte string first, but
    # this can of course fail and doesn't make sense at all when we immediately
    # call 'decode' on this byte string again. In a nutshell: The implicit
    # conversions between str and unicode are a fundamentally broken idea, just
    # like all implicit things and "helpful" ideas in general. :-P For further
    # info see e.g. http://nedbatchelder.com/value/unipain.html
    if isinstance(value, six.text_type):
        return value

    try:
        return value.decode("utf-8")
    except Exception:
        return value.decode("latin-1")


def make_utf8(value):
    if isinstance(value, six.text_type):
        return value.encode('utf-8')
    return value
