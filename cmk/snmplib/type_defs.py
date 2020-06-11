#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import abc
import string
from typing import Any, AnyStr, Callable, Dict, List, NamedTuple, Optional, Tuple, Union

from six import ensure_str

from cmk.utils.type_defs import CheckPluginName as _CheckPluginName
from cmk.utils.type_defs import HostAddress as _HostAddress
from cmk.utils.type_defs import HostName as _HostName
from cmk.utils.type_defs import SectionName as _SectionName

ContextName = str
DecodedString = str
DecodedBinary = List[int]
DecodedValues = Union[DecodedString, DecodedBinary]
SNMPValueEncoding = str
SNMPTable = List[List[DecodedValues]]
SNMPContext = Optional[str]
SNMPSectionContent = Union[SNMPTable, List[SNMPTable]]
SNMPSections = Dict[_SectionName, SNMPSectionContent]
PersistedSNMPSection = Tuple[int, int, SNMPSectionContent]
PersistedSNMPSections = Dict[_SectionName, PersistedSNMPSection]
RawSNMPData = SNMPSections
Column = Union[str, int, Tuple[SNMPValueEncoding, str]]
Columns = List[Column]
OID = str
OIDWithColumns = Tuple[OID, Columns]
OIDWithSubOIDsAndColumns = Tuple[OID, List[OID], Columns]
OIDFunction = Callable[[OID, Optional[DecodedString], Optional[_CheckPluginName]],
                       Optional[DecodedString]]
ScanFunction = Callable[[OIDFunction], bool]
# TODO (CMK-4490): Typing here is just wrong as there is no practical
# difference between an OIDWithColumns and OIDWithSubOIDsAndColumns with
# an empty List[OID].
SingleOIDInfo = Union[OIDWithColumns, OIDWithSubOIDsAndColumns]
MultiOIDInfo = List[SingleOIDInfo]
OIDInfo = Union[SingleOIDInfo, MultiOIDInfo]
RawValue = bytes
SNMPRowInfo = List[Tuple[OID, RawValue]]

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
class SNMPHostConfig(
        NamedTuple("SNMPHostConfig", [
            ("is_ipv6_primary", bool),
            ("hostname", _HostName),
            ("ipaddress", _HostAddress),
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
            ("record_stats", bool),
        ])):
    @property
    def is_snmpv3_host(self):
        # type: () -> bool
        return isinstance(self.credentials, tuple)

    def snmpv3_contexts_of(self, check_plugin_name):
        # type: (Optional[_CheckPluginName]) -> List[SNMPContext]
        if not check_plugin_name or not self.is_snmpv3_host:
            return [None]
        for ty, rules in self.snmpv3_contexts:
            if ty is None or ty == check_plugin_name:
                return rules
        return [None]

    def update(self, **kwargs):
        # type: (Dict[str, Any]) -> SNMPHostConfig
        """Return a new SNMPHostConfig with updated attributes."""
        cfg = self._asdict()
        cfg.update(**kwargs)
        return SNMPHostConfig(**cfg)

    def ensure_str(self, value):
        # type: (AnyStr) -> str
        if self.character_encoding:
            return ensure_str(value, self.character_encoding)
        try:
            return ensure_str(value, "utf-8")
        except UnicodeDecodeError:
            return ensure_str(value, "latin1")


class ABCSNMPBackend(metaclass=abc.ABCMeta):
    def __init__(self, snmp_config):
        # type: (SNMPHostConfig) -> None
        super(ABCSNMPBackend, self).__init__()
        self.config = snmp_config

    @property
    def hostname(self):
        # type: () -> _HostName
        return self.config.hostname

    @property
    def address(self):
        # type: () -> _HostAddress
        return self.config.ipaddress

    @abc.abstractmethod
    def get(self, oid, context_name=None):
        # type: (OID, Optional[ContextName]) -> Optional[RawValue]
        """Fetch a single OID from the given host in the given SNMP context
        The OID may end with .* to perform a GETNEXT request. Otherwise a GET
        request is sent to the given host.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def walk(self, oid, check_plugin_name=None, table_base_oid=None, context_name=None):
        # type: (OID, Optional[_CheckPluginName], Optional[OID], Optional[ContextName]) -> SNMPRowInfo
        return []


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


# The old API defines OID_END = 0.  Once we can drop the old API,
# replace every occurence of this with OIDEnd.
CompatibleOIDEnd = int


# We inherit from CompatibleOIDEnd = int because we must be compatible with the
# old APIs OID_END, OID_STRING and so on (in particular OID_END = 0).
class OIDEnd(CompatibleOIDEnd):
    """OID specification to get the end of the OID string
    When specifying an OID in an SNMPTree object, the parse function
    will be handed the corresponding value of that OID. If you use OIDEnd()
    instead, the parse function will be given the tailing portion of the
    OID (the part that you not already know).
    """

    # NOTE: The default constructor already does the right thing for our "glorified 0".
    def __repr__(self):
        return "OIDEnd()"


class ABCSNMPTree(metaclass=abc.ABCMeta):
    # pylint: disable=no-init
    @property
    @abc.abstractmethod
    def base(self):
        # type: () -> OIDSpec
        raise NotImplementedError()

    @property
    @abc.abstractmethod
    def oids(self):
        # type: () -> List[Union[OIDSpec, CompatibleOIDEnd]]
        raise NotImplementedError()
