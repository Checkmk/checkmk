#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Warn about global proxies whose credentials look percent-encoded.

Proxy user names and passwords are now stored as typed and encoded only when a proxy URL
is built. Credentials that were entered percent-encoded, or converted from a proxy URL by
the update to Checkmk 2.4, are therefore encoded twice and no longer authenticate. They
cannot be fixed automatically, since a password may contain such a sequence on purpose,
so the admin is asked to check them. Only the proxy is named, never the credentials.
"""

import re
from collections.abc import Mapping
from logging import Logger
from typing import Final, override

from cmk.gui.watolib.config_domains import ConfigDomainCore
from cmk.gui.watolib.password_store import PasswordStore
from cmk.update_config.lib import ExpiryVersion
from cmk.update_config.registry import update_action_registry, UpdateAction

_PERCENT_ENCODED: Final = re.compile(r"%[0-9A-Fa-f]{2}")


def _secret(password: object, stored_secrets: Mapping[str, str]) -> str:
    match password:
        case ("cmk_postprocessed", "explicit_password", (str(), str(secret))):
            return secret
        case ("cmk_postprocessed", "stored_password", (str(password_id), str())):
            return stored_secrets.get(password_id, "")
        case _:
            return ""


def proxies_with_encoded_credentials(
    http_proxies: Mapping[str, object], stored_secrets: Mapping[str, str]
) -> list[str]:
    """The titles of the global proxies whose user or password contain "%XX" sequences"""
    found = []
    for ident, proxy in http_proxies.items():
        match proxy:
            case {
                "title": title,
                "proxy_config": {"auth": {"user": str(user), "password": password}},
            }:
                if _PERCENT_ENCODED.search(user) or _PERCENT_ENCODED.search(
                    _secret(password, stored_secrets)
                ):
                    found.append(str(title))
            case _:
                continue
    return found


class WarnEncodedProxyCredentials(UpdateAction):
    @override
    def __call__(self, logger: Logger) -> None:
        http_proxies = ConfigDomainCore().load().get("http_proxies", {})
        if not isinstance(http_proxies, Mapping) or not http_proxies:
            return
        stored_secrets = {
            password_id: spec["password"]
            for password_id, spec in PasswordStore().load_for_reading().items()
        }
        for title in proxies_with_encoded_credentials(http_proxies, stored_secrets):
            logger.warning(
                "The credentials of the global proxy '%(title)s' contain percent-encoded "
                "characters. Proxy credentials are now used as typed, so please check them "
                "in the global settings and enter them as typed, for example '@' instead "
                "of '%%40'.",
                {"title": title},
            )


update_action_registry.register(
    WarnEncodedProxyCredentials(
        name="warn_encoded_proxy_credentials",
        title="Checking the credentials of global proxies",
        sort_index=100,
        expiry_version=ExpiryVersion.CMK_310,
    )
)
