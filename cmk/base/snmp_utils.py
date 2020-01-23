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

import abc
import functools
from typing import (  # pylint: disable=unused-import
    Text, Callable, List, NamedTuple, Union, Tuple, Optional, Dict, TypeVar,
)
import six
from cmk.base.utils import HostAddress, HostName  # pylint: disable=unused-import
from cmk.base.check_utils import SectionName, CheckPluginName  # pylint: disable=unused-import

ContextName = str
OID = str
SNMPValueEncoding = str
Column = Union[str, Tuple[SNMPValueEncoding, str]]
Columns = List[Column]
OIDWithColumns = Tuple[OID, Columns]
OIDWithSubOIDsAndColumns = Tuple[OID, List[OID], Columns]
SingleOIDInfo = Union[OIDWithColumns, OIDWithSubOIDsAndColumns]
MultiOIDInfo = List[SingleOIDInfo]
OIDInfo = Union[SingleOIDInfo, MultiOIDInfo]
RawValue = str
OIDFunction = Callable[[OID, Optional[RawValue], Optional[CheckPluginName]], Optional[RawValue]]
ScanFunction = Callable[[OIDFunction], bool]
SNMPRowInfo = List[Tuple[OID, RawValue]]
ResultColumnsUnsanitized = List[Tuple[OID, SNMPRowInfo, SNMPValueEncoding]]
ResultColumnsSanitized = List[Tuple[List[RawValue], SNMPValueEncoding]]
DecodedString = Text
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


def BINARY(oid):
    # type: (OID) -> Tuple[str, str]
    """Tell Check_MK to process this OID as binary data to the check."""
    return "binary", oid


def CACHED_OID(oid):
    # type: (OID) -> Tuple[str, str]
    """Use this to mark OIDs as being cached for regular checks,
    but not for discovery"""
    return "cached", oid


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


def is_snmpv3_host(snmp_config):
    # type: (SNMPHostConfig) -> bool
    return isinstance(snmp_config.credentials, tuple)


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
SNMPCommunity = str
# TODO: This does not work as intended
#SNMPv3NoAuthNoPriv = Tuple[str, str]
#SNMPv3AuthNoPriv = Tuple[str, str, str, str]
#SNMPv3AuthPriv = Tuple[str, str, str, str, str, str]
#SNMPCredentials = Union[SNMPCommunity, SNMPv3NoAuthNoPriv, SNMPv3AuthNoPriv, SNMPv3AuthPriv]
SNMPCredentials = Union[SNMPCommunity, Tuple[str, ...]]

# TODO: Cleanup to named tuple
SNMPTiming = Dict

# Wraps the configuration of a host into a single object for the SNMP code
SNMPHostConfig = NamedTuple("SNMPHostConfig", [
    ("is_ipv6_primary", bool),
    ("hostname", HostName),
    ("ipaddress", HostAddress),
    ("credentials", SNMPCredentials),
    ("port", int),
    ("is_bulkwalk_host", bool),
    ("is_snmpv2or3_without_bulkwalk_host", bool),
    ("bulk_walk_size_of", int),
    ("timing", SNMPTiming),
    ("oid_range_limits", list),
    ("snmpv3_contexts", list),
    ("character_encoding", Optional[str]),
    ("is_usewalk_host", bool),
    ("is_inline_snmp_host", bool),
])


class ABCSNMPBackend(six.with_metaclass(abc.ABCMeta, object)):
    @abc.abstractmethod
    def get(self, snmp_config, oid, context_name=None):
        # type: (SNMPHostConfig, OID, Optional[ContextName]) -> Optional[RawValue]
        """Fetch a single OID from the given host in the given SNMP context

        The OID may end with .* to perform a GETNEXT request. Otherwise a GET
        request is sent to the given host.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def walk(self,
             snmp_config,
             oid,
             check_plugin_name=None,
             table_base_oid=None,
             context_name=None):
        # type: (SNMPHostConfig, OID, Optional[CheckPluginName], Optional[OID], Optional[ContextName]) -> SNMPRowInfo
        return []


class MutexScanRegistry(object):
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
