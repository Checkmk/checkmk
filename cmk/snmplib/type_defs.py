#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc
import enum
import json
import logging
import string
from typing import (
    Any,
    AnyStr,
    Callable,
    cast,
    Dict,
    Iterable,
    List,
    NamedTuple,
    Optional,
    Sequence,
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
from cmk.utils.type_defs import SNMPDetectBaseType as _SNMPDetectBaseType

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

SNMPDeviceTypes = [
    "appliance",
    "firewall",
    "printer",
    "router",
    "sensor",
    "switch",
    "ups",
    "wlc",
]


class SNMPEnumEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, SNMPBackend):
            return {"__snmpenum__": str(o)}
        return json.JSONEncoder.default(self, o)


def read_as_enum(data):
    if "__snmpenum__" in data:
        _type_enum, name = data["__snmpenum__"].split(".")
        return getattr(SNMPBackend, name)
    return data


class SNMPBackend(enum.Enum):
    inline = "Inline"
    pysnmp = "PySNMP"
    classic = "Classic"


class SNMPDetectSpec(_SNMPDetectBaseType):
    """A specification for SNMP device detection"""
    @classmethod
    def from_json(cls, serialized: Dict[str, Any]) -> "SNMPDetectSpec":
        try:
            # The cast is necessary as mypy does not infer types in a list comprehension.
            # See https://github.com/python/mypy/issues/5068
            return cls([[cast(SNMPDetectAtom, tuple(inner))
                         for inner in outer]
                        for outer in serialized["snmp_detect_spec"]])
        except (LookupError, TypeError, ValueError) as exc:
            raise ValueError(serialized) from exc

    def to_json(self) -> Dict[str, Any]:
        return {"snmp_detect_spec": self}


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
            ("snmp_backend", SNMPBackend),
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


class SpecialColumn(enum.IntEnum):
    # Until we remove all but the first, its worth having an enum
    END = 0  # Suffix-part of OID that was not specified
    STRING = -1  # Complete OID as string ".1.3.6.1.4.1.343...."
    BIN = -2  # Complete OID as binary string "\x01\x03\x06\x01..."
    END_BIN = -3  # Same, but just the end part
    END_OCTET_STRING = -4  # yet same, but omit first byte (assuming that is the length byte)


class OIDSpec:
    """Basic class for OID spec of the form ".1.2.3.4.5" or "2.3"
    """
    VALID_CHARACTERS = set(('.', *string.digits))

    @classmethod
    def validate(cls, value: str) -> None:
        if not isinstance(value, str):
            raise TypeError(f"expected a non-empty string: {value!r}")
        if not value:
            raise ValueError(f"expected a non-empty string: {value!r}")
        if not cls.VALID_CHARACTERS.issuperset(value):
            invalid_chars = ''.join(sorted(set(value).difference(cls.VALID_CHARACTERS)))
            raise ValueError(f"invalid characters in OID descriptor: {invalid_chars!r}")
        if value.endswith('.'):
            raise ValueError(f"{value} should not end with '.'")

    def __init__(self, value: Union["OIDSpec", str]) -> None:
        if isinstance(value, OIDSpec):
            value = str(value)
        else:
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


class BackendSNMPTree(NamedTuple):
    """The 'working class' pentant to the check APIs 'SNMPTree'

    It mainly features (de)serialization. Validation is done during
    section registration, so we can assume sane values here.
    """
    base: str
    oids: Sequence[Union[OIDSpec, SpecialColumn]]

    @classmethod
    def from_frontend(cls, *, base: str, oids: Iterable[Union[str, OIDSpec,
                                                              int]]) -> 'BackendSNMPTree':
        return cls(
            base=base,
            oids=[
                oid if isinstance(oid, OIDSpec) else
                (SpecialColumn(oid) if isinstance(oid, int) else OIDSpec(oid)) for oid in oids
            ],
        )

    def to_json(self) -> Dict[str, Any]:
        return {
            "base": self.base,
            "oids": [BackendSNMPTree._serialize_oid(oid) for oid in self.oids],
        }

    @classmethod
    def from_json(cls, serialized: Dict[str, Any]) -> "BackendSNMPTree":
        return cls(
            base=serialized["base"],
            oids=[BackendSNMPTree._deserialize_oid(*oid) for oid in serialized["oids"]],
        )

    @staticmethod
    def _serialize_oid(oid: Union[OIDSpec, SpecialColumn]) -> Tuple[str, Union[str, int]]:
        if isinstance(oid, OIDSpec):
            return type(oid).__name__, str(oid)
        if isinstance(oid, SpecialColumn):
            return "SpecialColumn", oid.value
        raise TypeError(oid)

    @staticmethod
    def _deserialize_oid(type_: str, value: Union[str, int]) -> Union[OIDSpec, SpecialColumn]:
        try:
            return {
                "OIDSpec": OIDSpec,
                "OIDBytes": OIDBytes,
                "OIDCached": OIDCached,
                "SpecialColumn": SpecialColumn,
            }[type_](value)
        except LookupError as exc:
            raise TypeError(type_) from exc
