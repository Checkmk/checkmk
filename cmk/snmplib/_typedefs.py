#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import abc
import copy
import dataclasses
import enum
import logging
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Literal, NamedTuple, Protocol, Self

from cmk.ccc.exceptions import MKSNMPError
from cmk.ccc.hostaddress import HostAddress, HostName

from cmk.utils.sectionname import SectionName

SNMPContext = str
SNMPValueEncoding = Literal["string", "binary"]
OID = str
OIDRange = tuple[int, int]
RangeLimit = tuple[Literal["first", "last"], int] | tuple[Literal["mid"], OIDRange]
SNMPRawValue = bytes
SNMPRowInfo = list[tuple[OID, SNMPRawValue]]


class SNMPContextTimeout(MKSNMPError):
    pass


# TODO: Be more specific about the possible tuples
# if the credentials are a string, we use that as community,
# if it is a four-tuple, we use it as V3 auth parameters:
# (1) security level (-l)
# (2) auth protocol (-a, e.g. 'md5')
# (3) security name (-u)
# (4) auth password (-A)
# And if it is a six-tuple, it has the following additional arguments:
# (5) privacy protocol (DES|AES|AES-192|AES-256) (-x)
# (6) privacy protocol pass phrase (-X)
SNMPCommunity = str
SNMPv3NoAuthNoPriv = tuple[str, str]
SNMPv3AuthNoPriv = tuple[str, str, str, str]
SNMPv3AuthPriv = tuple[str, str, str, str, str, str]
type SNMPCredentials = SNMPCommunity | SNMPv3NoAuthNoPriv | SNMPv3AuthNoPriv | SNMPv3AuthPriv
# TODO: Cleanup to named tuple
SNMPTiming = dict


class SNMPBackendEnum(enum.Enum):
    INLINE = "Inline"
    CLASSIC = "Classic"
    STORED_WALK = "StoredWalk"

    def serialize(self) -> str:
        return self.name

    @classmethod
    def deserialize(cls, name: str) -> Self:
        return cls[name]


class SNMPVersion(enum.Enum):
    V1 = enum.auto()
    V2C = enum.auto()
    V3 = enum.auto()

    def serialize(self) -> str:
        return self.name

    @classmethod
    def deserialize(cls, name: str) -> Self:
        return cls[name]


def ensure_str(value: str | bytes, *, encoding: str | None) -> str:
    if isinstance(value, str):
        return value
    if encoding:
        return value.decode(encoding)
    try:
        return value.decode()
    except UnicodeDecodeError:
        return value.decode("latin1")


@dataclass(frozen=True, kw_only=True)
class SNMPContextConfig:
    section: SectionName | None
    contexts: Sequence[SNMPContext]
    timeout_policy: Literal["stop", "continue"]

    @classmethod
    def default(cls) -> Self:
        return cls(section=None, contexts=[""], timeout_policy="stop")

    def serialize(self) -> tuple[str | None, Sequence[SNMPContext], Literal["stop", "continue"]]:
        return (
            str(self.section) if self.section is not None else None,
            self.contexts,
            self.timeout_policy,
        )

    @classmethod
    def deserialize(
        cls, serialized: tuple[str | None, Sequence[SNMPContext], Literal["stop", "continue"]]
    ) -> Self:
        section, contexts, timeout = serialized
        return cls(
            section=SectionName(section) if section is not None else None,
            contexts=contexts,
            timeout_policy=timeout,
        )


# Wraps the configuration of a host into a single object for the SNMP code
@dataclass(frozen=True, kw_only=True)
class SNMPHostConfig:
    is_ipv6_primary: bool
    hostname: HostName
    ipaddress: HostAddress
    credentials: SNMPCredentials
    port: int
    snmp_version: SNMPVersion
    bulkwalk_enabled: bool
    bulk_walk_size_of: int
    timing: SNMPTiming
    oid_range_limits: Mapping[SectionName, Sequence[RangeLimit]]
    snmpv3_contexts: Sequence[SNMPContextConfig]
    character_encoding: str | None
    snmp_backend: SNMPBackendEnum

    @property
    def use_bulkwalk(self) -> bool:
        return self.bulkwalk_enabled and self.snmp_version is not SNMPVersion.V1

    def snmpv3_contexts_of(
        self,
        section_name: SectionName | None,
    ) -> SNMPContextConfig:
        if not section_name or self.snmp_version is not SNMPVersion.V3:
            return SNMPContextConfig.default()
        for ctx in self.snmpv3_contexts:
            if ctx.section is None or ctx.section == section_name:
                return ctx
        return SNMPContextConfig.default()

    def serialize(self) -> Mapping[str, object]:
        serialized = dataclasses.asdict(self)
        serialized["snmp_backend"] = serialized["snmp_backend"].serialize()
        serialized["snmp_version"] = serialized["snmp_version"].serialize()
        serialized["oid_range_limits"] = {
            str(sn): rl for sn, rl in serialized["oid_range_limits"].items()
        }
        serialized["snmpv3_contexts"] = [c.serialize() for c in self.snmpv3_contexts]
        return serialized

    @classmethod
    def deserialize(cls, serialized: Mapping[str, Any]) -> Self:
        serialized_ = copy.deepcopy(dict(serialized))
        serialized_["snmp_backend"] = SNMPBackendEnum.deserialize(serialized_["snmp_backend"])
        serialized_["snmp_version"] = SNMPVersion.deserialize(serialized_["snmp_version"])
        serialized_["oid_range_limits"] = {
            SectionName(sn): rl for sn, rl in serialized_["oid_range_limits"].items()
        }
        serialized_["snmpv3_contexts"] = [
            SNMPContextConfig.deserialize(c) for c in serialized_["snmpv3_contexts"]
        ]
        return cls(**serialized_)


class SNMPBackend(abc.ABC):
    def __init__(self, snmp_config: SNMPHostConfig, logger: logging.Logger) -> None:
        super().__init__()
        self._logger = logger
        self.config = snmp_config

    @property
    def logger(self) -> logging.Logger:
        return self._logger

    @property
    def hostname(self) -> HostName:
        return self.config.hostname

    @property
    def address(self) -> HostAddress | None:
        return self.config.ipaddress

    @property
    def port(self) -> int:
        return self.config.port

    @port.setter
    def port(self, new_port: int) -> None:
        self.config = dataclasses.replace(self.config, port=new_port)

    @abc.abstractmethod
    def get(self, /, oid: OID, *, context: SNMPContext) -> SNMPRawValue | None:
        """Fetch a single OID from the given host in the given SNMP context
        The OID may end with .* to perform a GETNEXT request. Otherwise a GET
        request is sent to the given host.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def walk(
        self,
        /,
        oid: OID,
        *,
        context: SNMPContext,
        section_name: SectionName | None = None,
        table_base_oid: OID | None = None,
    ) -> SNMPRowInfo:
        return []


class SpecialColumn(enum.IntEnum):
    # Until we remove all but the first, its worth having an enum
    END = 0  # Suffix-part of OID that was not specified
    STRING = -1  # Complete OID as string ".1.3.6.1.4.1.343...."
    BIN = -2  # Complete OID as binary string "\x01\x03\x06\x01..."
    END_BIN = -3  # Same, but just the end part
    END_OCTET_STRING = -4  # yet same, but omit first byte (assuming that is the length byte)


class OIDSpecLike(Protocol):
    @property
    def column(self) -> int | str: ...

    @property
    def encoding(self) -> Literal["string", "binary"]: ...

    @property
    def save_to_cache(self) -> bool: ...


class BackendOIDSpec(NamedTuple):
    column: str | SpecialColumn
    encoding: SNMPValueEncoding
    save_to_cache: bool

    def _serialize(self) -> tuple[str, str, bool] | tuple[int, str, bool]:
        if isinstance(self.column, SpecialColumn):
            return (int(self.column), self.encoding, self.save_to_cache)
        return (self.column, self.encoding, self.save_to_cache)

    @classmethod
    def deserialize(
        cls,
        column: str | int,
        encoding: SNMPValueEncoding,
        save_to_cache: bool,
    ) -> Self:
        return cls(
            SpecialColumn(column) if isinstance(column, int) else column, encoding, save_to_cache
        )


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
        oids: Iterable[OIDSpecLike],
    ) -> Self:
        return cls(
            base=base,
            oids=[
                BackendOIDSpec.deserialize(oid.column, oid.encoding, oid.save_to_cache)
                for oid in oids
            ],
        )

    def to_json(self) -> Mapping[str, Any]:
        return {
            "base": self.base,
            "oids": [oid._serialize() for oid in self.oids],
        }

    @classmethod
    def from_json(cls, serialized: Mapping[str, Any]) -> Self:
        return cls(
            base=serialized["base"],
            oids=[BackendOIDSpec.deserialize(*oid) for oid in serialized["oids"]],
        )
