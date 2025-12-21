#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import typing
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from cmk.base.app import make_app
from cmk.base.config import load
from cmk.ccc.version import edition
from cmk.product_telemetry.exceptions import TelemetryConfigError
from cmk.utils import http_proxy_config, paths

type ProxySetting = (
    tuple[Literal["environment"], Literal["environment"]]
    | tuple[Literal["no_proxy"], None]
    | tuple[Literal["global"], str]
    | tuple[Literal["url"], http_proxy_config.ProxyConfigSpec]
)


@dataclass
class ProductTelemetrySettings:
    enable_telemetry: Literal["enabled", "disabled", "not_decided"]
    proxy_setting: ProxySetting


@dataclass(frozen=True)
class TelemetryConfig:
    enabled: bool
    state: Literal["not_decided", "enabled", "disabled"]
    proxy_config: http_proxy_config.HTTPProxyConfig


def load_telemetry_config(logger: logging.Logger) -> TelemetryConfig:
    base_config = load(
        discovery_rulesets=(),
        get_builtin_host_labels=make_app(edition(paths.omd_root)).get_builtin_host_labels,
    )

    try:
        config = read_config_file(paths.default_config_dir)
    except TelemetryConfigError:
        logger.exception("Failed to load config from file")

        config = ProductTelemetrySettings(
            enable_telemetry="not_decided",
            proxy_setting=("environment", "environment"),
        )

    proxy_config = get_proxy_config(
        proxy_setting=config.proxy_setting,
        global_proxies=base_config.loaded_config.http_proxies,
    )

    return TelemetryConfig(
        enabled=config.enable_telemetry == "enabled",
        state=config.enable_telemetry,
        proxy_config=proxy_config,
    )


def read_config_file(config_dir: Path) -> ProductTelemetrySettings:
    filename = config_dir / "telemetry.mk"

    if not filename.exists():
        raise TelemetryConfigError("Telemetry config file does not exist")

    try:
        with filename.open("rb") as f:
            settings: dict[str, Any] = {}
            # We exec this file because this is also how the ABCConfigDomain loads the config for other .mk files.
            # gui.watolib.config_domain_name.ABCConfigDomain.load_full_config
            exec(f.read(), {}, settings)  # nosec B102 # BNS:aee528

            return ProductTelemetrySettings(
                enable_telemetry=settings.get("product_telemetry", {}).get(
                    "enable_telemetry", "not_decided"
                ),
                proxy_setting=settings.get("product_telemetry", {}).get(
                    "proxy_setting", ("environment", "environment")
                ),
            )

    except Exception as e:
        raise TelemetryConfigError("Could not read telemetry config file") from e


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
