#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Annotated

from cryptography import x509
from pydantic import BaseModel, Field, field_validator


class RelayRegistrationRequest(BaseModel, frozen=True):
    relay_id: Annotated[str, Field(min_length=1)]
    alias: Annotated[str, Field(min_length=1)]
    csr: str

    @field_validator("csr")
    @classmethod
    def validate_and_parse_csr(cls, v: str) -> str:
        _validate_csr(v)
        return v


class RelayRegistrationResponse(BaseModel, frozen=True):
    relay_id: str
    root_cert: str
    client_cert: str


class RelayRefreshCertRequest(BaseModel, frozen=True):
    csr: str

    @field_validator("csr")
    @classmethod
    def validate_and_parse_csr(cls, v: str) -> str:
        _validate_csr(v)
        return v


class RelayRefreshCertResponse(BaseModel, frozen=True):
    root_cert: str
    client_cert: str


def _validate_csr(csr: str) -> None:
    try:
        _ = x509.load_pem_x509_csr(csr.encode())
    except Exception:
        raise ValueError("Invalid CSR: Could not parse PEM data")
