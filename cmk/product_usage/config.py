#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, TypeAlias

from cmk.utils import http_proxy_config, paths

from cmk.base import config as base_config

from cmk.product_usage.exceptions import ConfigError

ProxySetting: TypeAlias = (
    tuple[Literal["environment"], Literal["environment"]]
    | tuple[Literal["no_proxy"], None]
    | tuple[Literal["global"], str]
    | tuple[Literal["url"], str]
)


@dataclass
class ProductUsageAnalyticsSettings:
    enabled: Literal["enabled", "disabled", "not_decided"]
    proxy_setting: ProxySetting


@dataclass(frozen=True)
class ProductUsageConfig:
    enabled: bool
    state: Literal["not_decided", "enabled", "disabled"]
    proxy_config: http_proxy_config.HTTPProxyConfig


def load_config(logger: logging.Logger) -> ProductUsageConfig:
    base_config.load()

    try:
        config = read_config_file(Path(paths.default_config_dir))
    except ConfigError:
        logger.exception("Failed to load config from file")

        config = ProductUsageAnalyticsSettings(
            enabled="not_decided",
            proxy_setting=("environment", "environment"),
        )

    proxy_config = get_proxy_config(
        proxy_setting=config.proxy_setting,
        global_proxies=base_config.http_proxies,
    )

    return ProductUsageConfig(
        enabled=config.enabled == "enabled",
        state=config.enabled,
        proxy_config=proxy_config,
    )


def read_config_file(config_dir: Path) -> ProductUsageAnalyticsSettings:
    filename = config_dir / "product_usage_analytics.mk"

    if not filename.exists():
        raise ConfigError("Product usage analytics config file does not exist")

    try:
        with filename.open("rb") as f:
            settings: dict[str, Any] = {}
            # We exec this file because this is also how the ABCConfigDomain loads the config for other .mk files.
            # gui.watolib.config_domain_name.ABCConfigDomain.load_full_config
            exec(f.read(), {}, settings)  # nosec B102 # BNS:aee528

            return ProductUsageAnalyticsSettings(
                enabled=settings.get("product_usage_analytics", {}).get("enabled", "not_decided"),
                proxy_setting=settings.get("product_usage_analytics", {}).get(
                    "proxy_setting", ("environment", "environment")
                ),
            )

    except Exception as e:
        raise ConfigError("Could not read product usage analytics config file") from e


def get_proxy_config(
    proxy_setting: ProxySetting,
    *,
    global_proxies: dict[str, dict[str, str]],
) -> http_proxy_config.HTTPProxyConfig:
    match proxy_setting:
        case ("no_proxy", None):
            return http_proxy_config.NoProxyConfig()
        case ("environment", "environment"):
            return http_proxy_config.EnvironmentProxyConfig()
        case ("url", proxy_spec):
            assert isinstance(proxy_spec, str)
            return http_proxy_config.ExplicitProxyConfig(str(proxy_spec))
        case ("global", proxy_name):
            assert isinstance(proxy_name, str)
            try:
                proxy_url = global_proxies[proxy_name]["proxy_url"]
            except KeyError:
                return http_proxy_config.EnvironmentProxyConfig()

            return http_proxy_config.ExplicitProxyConfig(proxy_url)
        case _:
            return http_proxy_config.EnvironmentProxyConfig()
