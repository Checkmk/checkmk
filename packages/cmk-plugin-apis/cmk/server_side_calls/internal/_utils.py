#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from dataclasses import dataclass

from cmk.server_side_calls.v1 import Secret


@dataclass(frozen=True)
class URLProxyAuth:
    user: str
    password: Secret


@dataclass(frozen=False)
class URLProxy:
    scheme: str
    proxy_server_name: str
    port: int
    auth: URLProxyAuth | None = None


@dataclass(frozen=False)
class OAuth2Connection:
    client_secret: Secret
    access_token: Secret
    refresh_token: Secret
    client_id: str
    tenant_id: str
    authority: str
    connector_type: str
