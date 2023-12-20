#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import enum
from dataclasses import dataclass

from ._localize import Localizable


class ProxySchema(enum.StrEnum):
    HTTP = "http"
    HTTPS = "https"
    SOCKS4 = "socks4"
    SOCKS4A = "socks4a"
    SOCKS5 = "socks5"
    SOCKS5H = "socks5h"


@dataclass(frozen=True)
class Proxy:
    """Specifies a form for configuring a proxy

    Args:
        allowed_schemas: Set of available proxy schemas that can be used in a proxy url
        title: Human readable title
        help_text: Description to help the user with the configuration
    """

    allowed_schemas: frozenset[ProxySchema] = frozenset(
        {
            ProxySchema.HTTP,
            ProxySchema.HTTPS,
            ProxySchema.SOCKS4,
            ProxySchema.SOCKS4A,
            ProxySchema.SOCKS5,
            ProxySchema.SOCKS5H,
        }
    )
    title: Localizable | None = None
    help_text: Localizable | None = None


@dataclass(frozen=True)
class Metric:
    """Specifies a form selecting from a list of metrics registered in Checkmk

    Args:
        title: Human readable title
        help_text: Description to help the user with the configuration
    """

    title: Localizable | None = None
    help_text: Localizable | None = None
