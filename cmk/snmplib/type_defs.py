#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc
import collections
import logging
import string
from typing import (
    Any,
    AnyStr,
    Callable,
    Dict,
    Iterable,
    List,
    NamedTuple,
    Optional,
    Tuple,
    TypeVar,
    Union,
)

from six import ensure_str

from cmk.utils.type_defs import AgentRawData as _AgentRawData
from cmk.utils.type_defs import CheckPluginNameStr as _CheckPluginName
from cmk.utils.type_defs import HostAddress as _HostAddress
from cmk.utils.type_defs import HostName as _HostName
from cmk.utils.type_defs import SectionName as _SectionName

SNMPContextName = str
SNMPDecodedString = str
SNMPDecodedBinary = List[int]
SNMPDecodedValues = Union[SNMPDecodedString, SNMPDecodedBinary]
SNMPValueEncoding = str
SNMPTable = List[List[SNMPDecodedValues]]
SNMPContext = Optional[str]
SNMPSectionContent = Union[SNMPTable, List[SNMPTable]]
SNMPSections = Dict[_SectionName, SNMPSectionContent]
SNMPPersistedSection = Tuple[int, int, SNMPSectionContent]
SNMPPersistedSections = Dict[_SectionName, SNMPPersistedSection]
SNMPRawData = SNMPSections
OID = str
OIDFunction = Callable[[OID, Optional[SNMPDecodedString], Optional[_CheckPluginName]],
                       Optional[SNMPDecodedString]]
SNMPScanFunction = Callable[[OIDFunction], bool]
SNMPRawValue = bytes
SNMPRowInfo = List[Tuple[OID, SNMPRawValue]]

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

SNMPDetectAtom = Tuple[str, str, bool]  # (oid, regex_pattern, expected_match)

# TODO(ml): This type does not really belong here but there currently
#           is not better place.
AbstractRawData = Union[_AgentRawData, SNMPRawData]
TRawData = TypeVar("TRawData", bound=AbstractRawData)


# make this a class in order to hide the List implementation from the sphinx doc!
class SNMPDetectSpec(List[List[SNMPDetectAtom]]):
    """A specification for SNMP device detection

    Note that the structure of this object is not part of the API,
    and may change at any time.
    """


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
    def is_snmpv3_host(self) -> bool:
        return isinstance(self.credentials, tuple)

    def snmpv3_contexts_of(self, section_name: Optional[_SectionName]) -> List[SNMPContext]:
        if not section_name or not self.is_snmpv3_host:
            return [None]
        section_name_str = str(section_name)
        for ty, rules in self.snmpv3_contexts:
            if ty is None or ty == section_name_str:
                return rules
        return [None]

    def update(self, **kwargs: Dict[str, Any]) -> "SNMPHostConfig":
        """Return a new SNMPHostConfig with updated attributes."""
        cfg = self._asdict()
        cfg.update(**kwargs)
        return SNMPHostConfig(**cfg)

    def ensure_str(self, value: AnyStr) -> str:
        if self.character_encoding:
            return ensure_str(value, self.character_encoding)
        try:
            return ensure_str(value, "utf-8")
        except UnicodeDecodeError:
            return ensure_str(value, "latin1")


class ABCSNMPBackend(metaclass=abc.ABCMeta):
    def __init__(self, snmp_config: SNMPHostConfig, logger: logging.Logger) -> None:
        super(ABCSNMPBackend, self).__init__()
        self._logger = logger
        self.config = snmp_config

    @property
    def hostname(self) -> _HostName:
        return self.config.hostname

    @property
    def address(self) -> _HostAddress:
        return self.config.ipaddress

    @abc.abstractmethod
    def get(self,
            oid: OID,
            context_name: Optional[SNMPContextName] = None) -> Optional[SNMPRawValue]:
        """Fetch a single OID from the given host in the given SNMP context
        The OID may end with .* to perform a GETNEXT request. Otherwise a GET
        request is sent to the given host.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def walk(self,
             oid: OID,
             check_plugin_name: Optional[_CheckPluginName] = None,
             table_base_oid: Optional[OID] = None,
             context_name: Optional[SNMPContextName] = None) -> SNMPRowInfo:
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
    def validate(cls, value: str) -> None:
        if not isinstance(value, str):
            raise TypeError("expected a non-empty string: %r" % (value,))
        if not value:
            raise ValueError("expected a non-empty string: %r" % (value,))
        invalid = ''.join(c for c in value if c not in cls.VALID_CHARACTERS)
        if invalid:
            raise ValueError("invalid characters in OID descriptor: %r" % invalid)
        if value.endswith('.'):
            raise ValueError("%r should not end with '.'" % (value,))

    def __init__(self, value: Union["OIDSpec", str]) -> None:
        if isinstance(value, OIDSpec):
            value = str(value)

        self.validate(value)
        self._value = value

    def __add__(self, right: Any) -> "OIDSpec":
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

    def __eq__(self, other: Any) -> bool:
        if other.__class__ != self.__class__:
            return False
        return self._value == other._value

    def __str__(self) -> str:
        return self._value

    def __repr__(self) -> str:
        return "%s(%r)" % (self.__class__.__name__, self._value)


class OIDCached(OIDSpec):
    pass


class OIDBytes(OIDSpec):
    pass


# The old API defines OID_END = 0.  Once we can drop the old API,
# replace every occurence of this with OIDEnd.
OIDEndCompat = int


# We inherit from OIDEndCompat = int because we must be compatible with the
# old APIs OID_END, OID_STRING and so on (in particular OID_END = 0).
class OIDEnd(OIDEndCompat):
    """OID specification to get the end of the OID string
    When specifying an OID in an SNMPTree object, the parse function
    will be handed the corresponding value of that OID. If you use OIDEnd()
    instead, the parse function will be given the tailing portion of the
    OID (the part that you not already know).
    """

    # NOTE: The default constructor already does the right thing for our "glorified 0".
    def __repr__(self):
        return "OIDEnd()"


SNMPTreeInputOIDs = Iterable[Union[str, OIDSpec, OIDEnd]]


class SNMPTree:
    """Specify an OID table to fetch

    For every SNMPTree that is specified, the parse function will
    be handed a list of lists with the values of the corresponding
    OIDs.
    """
    def __init__(
        self,
        *,
        base: Union[OIDSpec, str],
        oids: SNMPTreeInputOIDs,
    ) -> None:
        super(SNMPTree, self).__init__()
        self._base = self._sanitize_base(base)
        self._oids = self._sanitize_oids(oids)

    def to_json(self) -> Dict[str, Any]:
        return {
            "base": SNMPTree._serialize_oid(self.base),
            "oids": [SNMPTree._serialize_oid(oid) for oid in self.oids],
        }

    @classmethod
    def from_json(cls, serialized: Dict[str, Any]) -> "SNMPTree":
        return cls(
            base=SNMPTree._deserialize_base(*serialized["base"]),
            oids=[SNMPTree._deserialize_oids(*oid) for oid in serialized["oids"]],
        )

    @staticmethod
    def _sanitize_base(base: Union[OIDSpec, str]) -> OIDSpec:
        oid_base = OIDSpec(base)
        if not str(oid_base).startswith('.'):
            raise ValueError("%r must start with '.'" % (oid_base,))
        return oid_base

    @staticmethod
    def _sanitize_oids(oids: SNMPTreeInputOIDs) -> List[Union[OIDSpec, OIDEndCompat]]:

        # This check is stricter than the typization of oids. We do not want oids to be a str,
        # however, unfortunately, str == Iterable[str], so it is currently not possible to exclude
        # str by typization. Therefore, for now, we simply keep the check if oids is a list.
        if not isinstance(oids, list):
            raise TypeError("oids must be a list")

        # Remove the "int" once OIDEndCompat is not needed anymore.
        # We must handle int, for legacy code. Typing should prevent us from
        # adding new cases.
        typed_oids = [
            oid if isinstance(oid, (OIDSpec, OIDEnd, int)) else OIDSpec(oid) for oid in oids
        ]

        # remaining validations only regard true OIDSpec objects
        oid_specs = [o for o in typed_oids if isinstance(o, OIDSpec)]
        if len(oid_specs) < 2:
            return typed_oids  # type: ignore[return-value] # allow for legacy code

        for oid in oid_specs:
            if str(oid).startswith('.'):
                raise ValueError("column %r must not start with '.'" % (oid,))

        # make sure the base is as long as possible
        heads_counter = collections.Counter(str(oid).split('.', 1)[0] for oid in oid_specs)
        head, count = max(heads_counter.items(), key=lambda x: x[1])
        if count == len(oid_specs) and all(str(o) != head for o in oid_specs):
            raise ValueError("base can be extended by '.%s'" % head)

        return typed_oids  # type: ignore[return-value] # allow for legacy code

    @property
    def base(self) -> OIDSpec:
        return self._base

    @property
    def oids(self) -> List[Union[OIDSpec, OIDEndCompat]]:
        return self._oids

    @staticmethod
    def _serialize_oid(oid: Union[OIDSpec, OIDEndCompat]) -> Tuple[str, Union[str, int]]:
        if isinstance(oid, OIDSpec):
            return type(oid).__name__, str(oid)
        if isinstance(oid, OIDEndCompat):
            return "OIDEnd", 0
        raise TypeError(oid)

    @staticmethod
    def _deserialize_base(type_: str, value: str) -> OIDSpec:
        # Note: base *cannot* be OIDEnd.
        try:
            return {
                "OIDSpec": OIDSpec,
                "OIDBytes": OIDBytes,
                "OIDCached": OIDCached,
            }[type_](value)
        except LookupError as exc:
            raise TypeError(type_) from exc

    @staticmethod
    def _deserialize_oids(type_: str, value: Union[str, int]) -> Union[str, OIDSpec, OIDEnd]:
        try:
            return {
                "OIDSpec": OIDSpec,
                "OIDBytes": OIDBytes,
                "OIDCached": OIDCached,
                "OIDEnd": OIDEndCompat,
            }[type_](value)
        except LookupError as exc:
            raise TypeError(type_) from exc

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, self.__class__):
            return False
        return self.__dict__ == other.__dict__

    def __repr__(self) -> str:
        return "%s(base=%r, oids=%r)" % (self.__class__.__name__, self.base, self.oids)
