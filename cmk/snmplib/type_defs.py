#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc
import enum
import logging
from typing import (
    Any,
    AnyStr,
    Callable,
    cast,
    Dict,
    Iterable,
    List,
    Literal,
    Mapping,
    NamedTuple,
    NewType,
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
SNMPValueEncoding = Literal["string", "binary"]
SNMPTable = List[List[SNMPDecodedValues]]
SNMPContext = Optional[str]
SNMPSectionContent = Union[SNMPTable, List[SNMPTable]]
SNMPRawData = NewType("SNMPRawData", Mapping[_SectionName, SNMPSectionContent])
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


class SNMPBackend(enum.Enum):
    inline = "Inline"
    pysnmp = "PySNMP"
    classic = "Classic"

    def serialize(self) -> str:
        return self.name

    @classmethod
    def deserialize(cls, name: str) -> "SNMPBackend":
        return cls[name]


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
            ("ipaddress", Optional[_HostAddress]),
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

    # TODO: Why not directly use SNMPHostConfig._replace(...)?
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

    def serialize(self):
        serialized = self._asdict()
        serialized["snmp_backend"] = serialized["snmp_backend"].serialize()
        return serialized

    @classmethod
    def deserialize(cls, serialized: Dict[str, Any]) -> "SNMPHostConfig":
        serialized["snmp_backend"] = SNMPBackend.deserialize(serialized["snmp_backend"])
        return cls(**serialized)


class ABCSNMPBackend(metaclass=abc.ABCMeta):
    def __init__(self, snmp_config: SNMPHostConfig, logger: logging.Logger) -> None:
        super(ABCSNMPBackend, self).__init__()
        self._logger = logger
        self.config = snmp_config

    @property
    def hostname(self) -> _HostName:
        return self.config.hostname

    @property
    def address(self) -> Optional[_HostAddress]:
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


class BackendOIDSpec(NamedTuple):
    column: Union[str, SpecialColumn]
    encoding: SNMPValueEncoding
    save_to_cache: bool

    def _serialize(self) -> Union[Tuple[str, str, bool], Tuple[int, str, bool]]:
        if isinstance(self.column, SpecialColumn):
            return (int(self.column), self.encoding, self.save_to_cache)
        return (self.column, self.encoding, self.save_to_cache)

    @classmethod
    def deserialize(
        cls,
        column: Union[str, int],
        encoding: SNMPValueEncoding,
        save_to_cache: bool,
    ) -> 'BackendOIDSpec':
        return cls(
            SpecialColumn(column) if isinstance(column, int) else column, encoding, save_to_cache)


class BackendSNMPTree(NamedTuple):
    """The 'working class' pendant to the check APIs 'SNMPTree'

    It mainly features (de)serialization. Validation is done during
    section registration, so we can assume sane values here.
    """
    base: str
    oids: Sequence[BackendOIDSpec]

    @classmethod
    def from_frontend(
        cls,
        *,
        base: str,
        oids: Iterable[Tuple[Union[str, int], SNMPValueEncoding, bool]],
    ) -> 'BackendSNMPTree':
        return cls(
            base=base,
            oids=[BackendOIDSpec.deserialize(*oid) for oid in oids],
        )

    def to_json(self) -> Dict[str, Any]:
        return {
            "base": self.base,
            "oids": [oid._serialize() for oid in self.oids],
        }

    @classmethod
    def from_json(cls, serialized: Dict[str, Any]) -> "BackendSNMPTree":
        return cls(
            base=serialized["base"],
            oids=[BackendOIDSpec.deserialize(*oid) for oid in serialized["oids"]],
        )
