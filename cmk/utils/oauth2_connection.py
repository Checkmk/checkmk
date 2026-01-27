#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Literal, TypedDict

OAuth2ConnectorType = Literal["microsoft_entra_id"]


class OAuth2Connection(TypedDict):
    title: str
    client_secret: tuple[Literal["cmk_postprocessed"], Literal["stored_password"], tuple[str, str]]
    access_token: tuple[Literal["cmk_postprocessed"], Literal["stored_password"], tuple[str, str]]
    refresh_token: tuple[Literal["cmk_postprocessed"], Literal["stored_password"], tuple[str, str]]
    client_id: str
    tenant_id: str
    authority: str
    connector_type: OAuth2ConnectorType
