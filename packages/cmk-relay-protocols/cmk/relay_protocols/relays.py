#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pydantic import BaseModel


class RelayRegistrationRequest(BaseModel, frozen=True):
    relay_name: str
    csr: str


class RelayRegistrationResponse(BaseModel, frozen=True):
    relay_id: str
