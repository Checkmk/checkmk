#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

from typing import (
    Literal,
    TypedDict,
)

from cmk.utils.http_proxy_config import ProxyConfigSpec

type ProxySetting = (
    tuple[Literal["environment"], Literal["environment"]]
    | tuple[Literal["no_proxy"], None]
    | tuple[Literal["global"], str]
    | tuple[Literal["url"], ProxyConfigSpec]
)


class ProductTelemetrySettings(TypedDict):
    enable_telemetry: tuple[Literal["enabled", "disabled", "not_decided"], None]
    proxy_setting: ProxySetting


product_telemetry: ProductTelemetrySettings = {
    "enable_telemetry": ("not_decided", None),
    "proxy_setting": ("environment", "environment"),
}
