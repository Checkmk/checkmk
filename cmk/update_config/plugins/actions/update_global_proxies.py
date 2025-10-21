#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re
from logging import Logger
from typing import override, TypedDict
from uuid import uuid4

from cmk.gui.watolib.config_domains import ConfigDomainCore
from cmk.update_config.lib import ExpiryVersion
from cmk.update_config.registry import (
    update_action_registry,
    UpdateAction,
)
from cmk.utils.http_proxy_config import HTTPProxySpec, ProxyAuthSpec, ProxyConfigSpec


class PreviousProxySpec(TypedDict):
    ident: str
    title: str
    proxy_url: str


def _migrate_proxy_url(url: str) -> ProxyConfigSpec:
    """Converts a proxy URL to a GlobalProxy.
    Args:
        url: The proxy URL to convert.
    Returns:
        GlobalProxy: The converted GlobalProxy.

    Example:
    url = http://username:proxy_password@proxy.server:8080
    to
    {
        "scheme": "http",
        "proxy_server_name": "proxy.server",
        "port": "8080",
        "auth": {
            "user": "username",
            "password": ("password", "proxy_password")
        }
    }
    """
    match = re.compile(
        r"^(?:(?P<scheme>https?|socks4|socks4a|socks5|socks5h)://)?"
        r"(?:(?P<user>[^:@]+)(?::(?P<password>[^@]+))?@)?"
        r"(?P<server>[^:/]+)"
        r"(?:\:(?P<port>\d+))?"
    ).match(url)

    global_proxy = ProxyConfigSpec(
        scheme=match.group("scheme") if match and match.group("scheme") else "http",
        proxy_server_name=match.group("server") if match and match.group("server") else "",
        port=int(match.group("port")) if match and match.group("port") else 0,
    )

    if match and match.group("user") and match.group("password"):
        global_proxy["auth"] = ProxyAuthSpec(
            user=match.group("user"),
            password=(
                "cmk_postprocessed",
                "explicit_password",
                (f"uuid{uuid4()}", match.group("password")),
            ),
        )

    return global_proxy


class UpdateGlobalProxies(UpdateAction):
    @override
    def __call__(self, logger: Logger) -> None:
        settings = ConfigDomainCore().load()
        global_proxies: dict[str, HTTPProxySpec | PreviousProxySpec] = settings.get(
            "http_proxies", {}
        )
        for proxy_id, proxy_config in global_proxies.items():
            if "proxy_url" in proxy_config:
                global_proxies[proxy_id] = HTTPProxySpec(
                    ident=proxy_config["ident"],
                    title=proxy_config["title"],
                    proxy_config=_migrate_proxy_url(
                        proxy_config["proxy_url"]  # type: ignore[typeddict-item]
                    ),
                )
                logger.info(f'Migrated global proxy "{proxy_id}".')

        ConfigDomainCore().save(settings)


update_action_registry.register(
    UpdateGlobalProxies(
        name="global_proxies_migration",
        title="Migrate global proxies configuration",
        sort_index=19,  # Has to run before global_settings
        expiry_version=ExpiryVersion.NEVER,
    )
)
