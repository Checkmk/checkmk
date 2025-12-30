#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Annotated

from pydantic import BaseModel, Field


class RelayRegistrationRequest(BaseModel, frozen=True):
    relay_id: Annotated[str, Field(min_length=1)]
    alias: Annotated[str, Field(min_length=1)]
    csr: Annotated[str, Field(min_length=1)]


class RelayRegistrationResponse(BaseModel, frozen=True):
    relay_id: str
    root_cert: str
    client_cert: str


class RelayRefreshCertRequest(BaseModel, frozen=True):
    csr: Annotated[str, Field(min_length=1)]


class RelayRefreshCertResponse(BaseModel, frozen=True):
    root_cert: str
    client_cert: str
