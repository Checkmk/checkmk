#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import functools
from typing import Callable, List, Optional, Tuple

import six

from cmk.utils.type_defs import OID, CheckPluginName, DecodedString

OIDFunction = Callable[[OID, Optional[DecodedString], Optional[CheckPluginName]],
                       Optional[DecodedString]]
ScanFunction = Callable[[OIDFunction], bool]
SNMPRowInfoForStoredWalk = List[Tuple[OID, str]]


def binstring_to_int(binstring):
    # type: (bytes) -> int
    """Convert a string to an integer.

    This is done by consideren the string to be a little endian byte string.
    Such strings are sometimes used by SNMP to encode 64 bit counters without
    needed COUNTER64 (which is not available in SNMP v1)."""
    value = 0
    mult = 1
    for byte in six.iterbytes(binstring[::-1]):
        value += mult * byte
        mult *= 256
    return value


class MutexScanRegistry(object):  # pylint: disable=useless-object-inheritance
    """Register scan functions that are checked before a fallback is used

    Add any number of scan functions to a registry instance by decorating
    them like this:

        @mutex_scan_registry_instance.register
        def my_snmp_scan_function(oid):
            ...

    You can then declare a scan function to be a fallback to those functions
    by decorating it with "@mutex_scan_registry_instance.as_fallback",
    meaning that the fallback function will only be evaluated if all of the
    scan functions registered earlier return something falsey.
    """
    def __init__(self):
        # type: () -> None
        super(MutexScanRegistry, self).__init__()
        self._specific_scans = []  # type: List[ScanFunction]

    def _is_specific(self, oid):
        # type: (OIDFunction) -> bool
        return any(scan(oid) for scan in self._specific_scans)

    def register(self, scan_function):
        # type: (ScanFunction) -> ScanFunction
        self._specific_scans.append(scan_function)
        return scan_function

    def as_fallback(self, scan_function):
        # type: (ScanFunction) -> ScanFunction
        @functools.wraps(scan_function)
        def wrapper(oid):
            # type: (OIDFunction) -> bool
            if self._is_specific(oid):
                return False
            return scan_function(oid)

        return wrapper
