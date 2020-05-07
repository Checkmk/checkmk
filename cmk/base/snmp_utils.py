#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import functools
from typing import (  # pylint: disable=unused-import
    Any, Text, Callable, List, Union, Tuple, Optional, Dict,
)
import string
import six

from cmk.utils.type_defs import (  # pylint: disable=unused-import
    DecodedString, ContextName, OID, RawValue, SNMPCommunity, SNMPCredentials, SNMPHostConfig,
    SNMPRowInfo, SNMPTiming,
)
from cmk.base.check_utils import SectionName, CheckPluginName  # pylint: disable=unused-import

SNMPValueEncoding = str
Column = Union[str, int, Tuple[SNMPValueEncoding, str]]
Columns = List[Column]
OIDWithColumns = Tuple[OID, Columns]
OIDWithSubOIDsAndColumns = Tuple[OID, List[OID], Columns]
SingleOIDInfo = Union[OIDWithColumns, OIDWithSubOIDsAndColumns]
MultiOIDInfo = List[SingleOIDInfo]
OIDInfo = Union[SingleOIDInfo, MultiOIDInfo]
OIDFunction = Callable[[OID, Optional[DecodedString], Optional[CheckPluginName]],
                       Optional[DecodedString]]
ScanFunction = Callable[[OIDFunction], bool]
SNMPRowInfoForStoredWalk = List[Tuple[OID, Text]]
ResultColumnsUnsanitized = List[Tuple[OID, SNMPRowInfo, SNMPValueEncoding]]
ResultColumnsSanitized = List[Tuple[List[RawValue], SNMPValueEncoding]]
DecodedBinary = List[int]
DecodedValues = Union[DecodedString, DecodedBinary]
ResultColumnsDecoded = List[List[DecodedValues]]
SNMPTable = List[List[DecodedValues]]
SNMPContext = Optional[str]

SNMPSectionContent = Union[SNMPTable, List[SNMPTable]]
SNMPSections = Dict[SectionName, SNMPSectionContent]
PersistedSNMPSection = Tuple[int, int, SNMPSectionContent]
PersistedSNMPSections = Dict[SectionName, PersistedSNMPSection]
RawSNMPData = SNMPSections

OID_END = 0  # Suffix-part of OID that was not specified
OID_STRING = -1  # Complete OID as string ".1.3.6.1.4.1.343...."
OID_BIN = -2  # Complete OID as binary string "\x01\x03\x06\x01..."
OID_END_BIN = -3  # Same, but just the end part
OID_END_OCTET_STRING = -4  # yet same, but omit first byte (assuming that is the length byte)


class OIDSpec:
    """Basic class for OID spec of the form ".1.2.3.4.5" or "2.3"
    """
    VALID_CHARACTERS = '.' + string.digits

    @classmethod
    def validate(cls, value):
        # type: (str) -> None
        if not isinstance(value, str):
            raise TypeError("expected a non-empty string: %r" % (value,))
        if not value:
            raise ValueError("expected a non-empty string: %r" % (value,))

        invalid = ''.join(c for c in value if c not in cls.VALID_CHARACTERS)
        if invalid:
            raise ValueError("invalid characters in OID descriptor: %r" % invalid)

        if value.endswith('.'):
            raise ValueError("%r should not end with '.'" % (value,))

    def __init__(self, value):
        # type: (str) -> None
        self.validate(value)
        self._value = value

    def __add__(self, right):
        # type: (Any) -> OIDSpec
        """Concatenate two OID specs

        We only allow adding (left to right) a "base" (starting with a '.')
        to an "column" (not starting with '.').
        We preserve the type of the column, which may signal caching or byte encoding.
        """
        if not isinstance(right, OIDSpec):
            raise TypeError("cannot add %r" % (right,))
        if not self._value.startswith('.') or right._value.startswith('.'):
            raise ValueError("can only add full OIDs to partial OIDs")
        return right.__class__("%s.%s" % (self, right))

    def __eq__(self, other):
        # type: (Any) -> bool
        if other.__class__ != self.__class__:
            return False
        return self._value == other._value

    def __str__(self):
        # type: () -> str
        return self._value

    def __repr__(self):
        # type: () -> str
        return "%s(%r)" % (self.__class__.__name__, self._value)


class OIDCached(OIDSpec):
    pass


class OIDBytes(OIDSpec):
    pass


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
