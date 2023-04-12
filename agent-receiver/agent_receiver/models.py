#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import re
from collections.abc import Callable, Iterator, Mapping
from dataclasses import dataclass
from enum import Enum
from typing import Literal, Self

from cryptography.x509 import CertificateSigningRequest, load_pem_x509_csr
from fastapi import HTTPException
from pydantic import BaseModel, UUID4, validator

from .certs import extract_cn_from_csr


@dataclass(frozen=True)
class CsrField:
    csr: CertificateSigningRequest

    @classmethod
    def __get_validators__(cls) -> Iterator[Callable[[object], Self]]:
        yield cls.validate

    @classmethod
    def validate(cls, v: object) -> Self:
        if isinstance(v, CertificateSigningRequest):
            csr = v
        else:
            if not isinstance(v, str):
                raise TypeError("CertificateSigningRequest or string required")
            csr = load_pem_x509_csr(v.encode())
        if not csr.is_signature_valid:
            raise ValueError("Invalid CSR (signature and public key do not match)")
        try:
            cn = extract_cn_from_csr(csr)
        except IndexError:
            raise ValueError("CSR contains no CN")
        try:
            UUID4(cn)
        except ValueError:
            raise ValueError(f"CN {cn} is not a valid version-4 UUID")
        return cls(csr)


class CertificateRenewalBody(BaseModel, frozen=True):
    csr: CsrField


class PairingBody(BaseModel, frozen=True):
    csr: str


class PairingResponse(BaseModel, frozen=True):
    root_cert: str
    client_cert: str


class RenewCertResponse(BaseModel, frozen=True):
    agent_cert: str


# duplicated from cmk.gui.valuespec
def _is_valid_host_name(hostname: str) -> bool:
    # http://stackoverflow.com/questions/2532053/validate-a-hostname-string/2532344#2532344
    if len(hostname) > 255:
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


class RegistrationWithHNBody(BaseModel, frozen=True):
    uuid: UUID4
    host_name: str

    @validator("host_name")
    @classmethod
    def valid_hostname(cls, v):
        if not _is_valid_host_name(v):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid hostname: '{v}'",
            )
        return v


class RegisterExistingBody(RegistrationWithHNBody):
    uuid: UUID4
    csr: CsrField
    host_name: str

    @validator("host_name")
    @classmethod
    def valid_hostname(cls, v):
        if not _is_valid_host_name(v):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid hostname: '{v}'",
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
