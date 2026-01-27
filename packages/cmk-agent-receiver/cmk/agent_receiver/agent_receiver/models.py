#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import re
import socket
from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
from typing import Literal, override, Self

from cryptography.x509 import CertificateSigningRequest
from fastapi import HTTPException
from pydantic import BaseModel, field_validator, GetCoreSchemaHandler, UUID4
from pydantic_core import core_schema

from cmk.agent_receiver.lib.certs import validate_csr


@dataclass(frozen=True)
class CsrField:
    csr: CertificateSigningRequest

    @classmethod
    def __get_pydantic_core_schema__(
        cls,
        source_type: object,
        _handler: GetCoreSchemaHandler,
    ) -> core_schema.CoreSchema:
        return core_schema.no_info_after_validator_function(
            cls.validate, core_schema.str_schema(), serialization=core_schema.to_string_ser_schema()
        )

    @classmethod
    def validate(cls, v: object) -> Self:
        if not isinstance(v, CertificateSigningRequest | str):
            raise TypeError("CertificateSigningRequest or string required")
        return cls(validate_csr(v))


class CertificateRenewalBody(BaseModel, frozen=True):
    csr: CsrField


class PairingBody(BaseModel, frozen=True):
    csr: str


class PairingResponse(BaseModel, frozen=True):
    root_cert: str
    client_cert: str


class RenewCertResponse(BaseModel, frozen=True):
    agent_cert: str


def _is_valid_host_name(hostname: str) -> bool:
    # duplicated from cmk.gui.valuespec
    # http://stackoverflow.com/questions/2532053/validate-a-hostname-string/2532344#2532344
    if not hostname or len(hostname) > 255:
        return False

    if hostname[-1] == ".":
        hostname = hostname[:-1]  # strip exactly one dot from the right, if present

    # must be not all-numeric, so that it can't be confused with an IPv4 address.
    # Host names may start with numbers (RFC 1123 section 2.1) but never the final part,
    # since TLDs are alphabetic.
    if re.match(r"[\d.]+$", hostname):
        return False

    allowed = re.compile(r"(?!-)[A-Z_\d-]{1,63}(?<!-)$", re.IGNORECASE)
    return all(allowed.match(x) for x in hostname.split("."))


def _is_valid_ipv4_address(address: str) -> bool:
    # duplicated from cmk.gui.valuespec
    # http://stackoverflow.com/questions/319279/how-to-validate-ip-address-in-python/4017219#4017219
    try:
        socket.inet_pton(socket.AF_INET, address)
    except AttributeError:  # no inet_pton here, sorry
        try:
            socket.inet_aton(address)
        except OSError:
            return False

        return address.count(".") == 3

    except OSError:  # not a valid address
        return False

    return True


def _is_valid_ipv6_address(address: str) -> bool:
    # duplicated from cmk.gui.valuespec
    # http://stackoverflow.com/questions/319279/how-to-validate-ip-address-in-python/4017219#4017219
    try:
        address = address.split("%")[0]
        socket.inet_pton(socket.AF_INET6, address)
    except OSError:  # not a valid address
        return False
    return True


def _is_valid_hostname_or_ip(uri: str) -> bool:
    """Check if the given URI is a valid hostname or IP address

    Some examples (see unit tests for more):
    >>> _is_valid_hostname_or_ip("test.checkmk.com")
    True
    >>> _is_valid_hostname_or_ip("127.0.0.1")
    True
    >>> _is_valid_hostname_or_ip("2606:2800:220:1:248:1893:25c8:1946")
    True
    >>> _is_valid_hostname_or_ip("::1")
    True
    >>> _is_valid_hostname_or_ip("my/../host")
    False
    """
    return _is_valid_host_name(uri) or _is_valid_ipv4_address(uri) or _is_valid_ipv6_address(uri)


class RegistrationWithHNBody(BaseModel, frozen=True):
    uuid: UUID4
    host_name: str

    @field_validator("host_name")
    @classmethod
    def valid_hostname(cls, v: str) -> str:
        if not _is_valid_hostname_or_ip(v):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid host name: '{v}'",
            )
        return v


class RegisterExistingBody(RegistrationWithHNBody, frozen=True):
    uuid: UUID4
    csr: CsrField
    host_name: str

    @field_validator("host_name")
    @staticmethod
    @override
    def valid_hostname(v: str) -> str:
        if not _is_valid_hostname_or_ip(v):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid host name: '{v}'",
            )
        return v


class ConnectionMode(Enum):
    PULL = "pull-agent"
    PUSH = "push-agent"


class RegisterExistingResponse(BaseModel, frozen=True):
    root_cert: str
    agent_cert: str
    connection_mode: ConnectionMode


class RegisterNewBody(BaseModel, frozen=True):
    uuid: UUID4
    csr: CsrField
    agent_labels: Mapping[str, str]


class RegisterNewResponse(BaseModel, frozen=True):
    root_cert: str


class RegisterNewOngoingResponseInProgress(BaseModel, frozen=True):
    # the agent controller uses the status field for distinguishing the different variants when
    # deserializing the response from the receiver
    status: Literal["InProgress"] = "InProgress"


class RegisterNewOngoingResponseDeclined(BaseModel, frozen=True):
    status: Literal["Declined"] = "Declined"
    reason: str


class RegisterNewOngoingResponseSuccess(BaseModel, frozen=True):
    status: Literal["Success"] = "Success"
    agent_cert: str
    connection_mode: ConnectionMode


class RequestForRegistration(BaseModel, frozen=True):
    uuid: UUID4
    username: str
    agent_labels: Mapping[str, str]
    agent_cert: str
    state: Mapping[str, str] | None = None

    def rejection_notice(self) -> str | None:
        return (self.state or {}).get("readable")


class R4RStatus(Enum):
    NEW = "new"
    PENDING = "pending"
    DECLINED = "declined"
    DISCOVERABLE = "discoverable"


class RegistrationStatus(BaseModel, frozen=True):
    hostname: str | None = None
    status: R4RStatus | None = None
    connection_mode: ConnectionMode | None = None
    message: str | None = None
    # Kept for backwards compatibility
    type: ConnectionMode | None = None


class RegistrationStatusV2ResponseNotRegistered(BaseModel, frozen=True):
    status: Literal["NotRegistered"] = "NotRegistered"


class RegistrationStatusV2ResponseRegistered(BaseModel, frozen=True):
    status: Literal["Registered"] = "Registered"
    hostname: str
    connection_mode: ConnectionMode
