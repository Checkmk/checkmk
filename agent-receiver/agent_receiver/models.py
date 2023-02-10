#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import re
from collections.abc import Callable, Iterator, Mapping
from dataclasses import dataclass
from enum import Enum
from typing import NamedTuple, Self
from uuid import UUID

from cryptography.x509 import CertificateSigningRequest, load_pem_x509_csr
from fastapi import HTTPException
from pydantic import BaseModel, validator

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
            UUID(cn, version=4)
        except ValueError:
            raise ValueError(f"CN {cn} is not a valid version-4 UUID")
        return cls(csr)


class CertificateRenewalBody(BaseModel):
    csr: CsrField


class PairingBody(BaseModel):
    csr: str


class PairingResponse(BaseModel):
    root_cert: str
    client_cert: str


class RenewCertResponse(BaseModel):
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


class RegistrationWithHNBody(BaseModel):
    uuid: UUID
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


class RegistrationWithLabelsBody(BaseModel):
    uuid: UUID
    agent_labels: Mapping[str, str]


class RegistrationStatusEnum(Enum):
    NEW = "new"
    PENDING = "pending"
    DECLINED = "declined"
    READY = "ready"
    DISCOVERABLE = "discoverable"


class RegistrationData(NamedTuple):
    status: RegistrationStatusEnum
    message: str | None


class ConnectionMode(Enum):
    PULL = "pull-agent"
    PUSH = "push-agent"


class RegistrationStatus(BaseModel):
    hostname: str | None = None
    status: RegistrationStatusEnum | None = None
    type: ConnectionMode | None = None
    message: str | None = None
