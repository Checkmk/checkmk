#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""FormSpecs that allow a selection form preconfigured resources in a setup"""

import enum
from dataclasses import dataclass
from typing import Literal

from ._base import FormSpec


class ProxySchema(enum.StrEnum):
    HTTP = "http"
    HTTPS = "https"
    SOCKS4 = "socks4"
    SOCKS4A = "socks4a"
    SOCKS5 = "socks5"
    SOCKS5H = "socks5h"


@dataclass(frozen=True, kw_only=True)
class Proxy(
    FormSpec[
        tuple[
            Literal["cmk_postprocessed"],
            Literal["environment_proxy", "no_proxy", "stored_proxy", "explicit_proxy"],
            str,
        ]
    ]
):
    """Specifies a form for configuring a proxy

    Args:
        allowed_schemas: Set of available proxy schemas that can be used in a proxy url
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


@dataclass(frozen=True, kw_only=True)
class Metric(FormSpec[str]):
    """Specifies a form selecting from a list of metrics registered in Checkmk"""


@dataclass(frozen=True, kw_only=True)
class MonitoredHost(FormSpec[str]):
    """Specifies a form selecting from a list of hosts configured in Checkmk"""


@dataclass(frozen=True, kw_only=True)
class MonitoredService(FormSpec[str]):
    """Specifies a form selecting from a list of currently monitored services in Checkmk"""


@dataclass(frozen=True, kw_only=True)
class Password(
    FormSpec[
        tuple[
            Literal["cmk_postprocessed"],
            Literal["explicit_password", "stored_password"],
            tuple[str, str],
        ]
    ]
):
    """Specifies a form for configuring passwords (explicit or from password store)"""


@dataclass(frozen=True, kw_only=True)
class TimePeriod(FormSpec[tuple[Literal["cmk_postprocessed"], Literal["stored_time_period"], str]]):
    """Specifies a form selecting from a list of time periods configured in Checkmk"""
