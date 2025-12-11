#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import typing
from dataclasses import dataclass
from typing import Literal

from cmk.base.config import load
from cmk.base.default_config.telemetry import ProxySetting
from cmk.utils import http_proxy_config


@dataclass(frozen=True)
class TelemetryConfig:
    enabled: bool
    state: Literal["not_decided", "enabled", "disabled"]
    proxy_config: http_proxy_config.HTTPProxyConfig


def load_telemetry_config() -> TelemetryConfig:
    config = load({})

    proxy_config = get_proxy_config(
        config.loaded_config.product_telemetry["proxy_setting"],
        global_proxies=config.loaded_config.http_proxies,
    )

    return TelemetryConfig(
        enabled=config.loaded_config.product_telemetry["enable_telemetry"][0] == "enabled",
        state=config.loaded_config.product_telemetry["enable_telemetry"][0],
        proxy_config=proxy_config,
    )


def get_proxy_config(
    proxy_setting: ProxySetting,
    *,
    global_proxies: typing.Mapping[str, http_proxy_config.HTTPProxySpec],
) -> http_proxy_config.HTTPProxyConfig:
    match proxy_setting:
        case ("no_proxy", None):
            return http_proxy_config.NoProxyConfig()
        case ("environment", "environment"):
            return http_proxy_config.EnvironmentProxyConfig()
        case ("url", proxy_spec):
            assert isinstance(proxy_spec, dict)
            return http_proxy_config.build_explicit_proxy_config(proxy_spec)
        case ("global", proxy_name):
            assert isinstance(proxy_name, str)

            try:
                proxy_spec = global_proxies[proxy_name]["proxy_config"]
            except KeyError:
                return http_proxy_config.EnvironmentProxyConfig()

            return http_proxy_config.build_explicit_proxy_config(proxy_spec)
        case _:
            return http_proxy_config.EnvironmentProxyConfig()
