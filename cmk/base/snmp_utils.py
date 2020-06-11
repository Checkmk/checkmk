#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import functools
from typing import List, Tuple

from six import iterbytes

from cmk.utils.exceptions import MKGeneralException

from cmk.snmplib.type_defs import OID, OIDFunction, ScanFunction, SNMPHostConfig

import cmk.base.config as config
import cmk.base.ip_lookup as ip_lookup

SNMPRowInfoForStoredWalk = List[Tuple[OID, str]]


# TODO: This belongs in `cmk.base.config.HostConfig` but we cannot
# have it there now since `ip_lookup` imports `config` and that
# results in circular imports.
def create_snmp_host_config(hostname):
    # type: (str) -> SNMPHostConfig
    host_config = config.get_config_cache().get_host_config(hostname)

    # ip_lookup.lookup_ipv4_address() returns Optional[str] in general, but for
    # all cases that reach the code here we seem to have "str".
    address = ip_lookup.lookup_ip_address(hostname)
    if address is None:
        raise MKGeneralException("Failed to gather IP address of %s" % hostname)

    return host_config.snmp_config(address)


def binstring_to_int(binstring):
    # type: (bytes) -> int
    """Convert a string to an integer.

    This is done by consideren the string to be a little endian byte string.
    Such strings are sometimes used by SNMP to encode 64 bit counters without
    needed COUNTER64 (which is not available in SNMP v1)."""
    value = 0
    mult = 1
    for byte in iterbytes(binstring[::-1]):
        value += mult * byte
        mult *= 256
    return value


class MutexScanRegistry:
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
