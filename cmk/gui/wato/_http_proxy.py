#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="type-arg"

import urllib.parse
from collections.abc import Iterable
from typing import get_args, Literal

from cmk.gui.i18n import _
from cmk.gui.valuespec import (
    CascadingDropdown,
    Dictionary,
    DropdownChoice,
    DropdownChoiceEntries,
    FixedValue,
    NetworkPort,
    TextInput,
    ValueSpec,
)
from cmk.gui.watolib.config_domains import ConfigDomainCore
from cmk.gui.watolib.password_store import MigrateToIndividualOrStoredPassword

_Schemes = Literal["http", "https", "socks4", "socks4a", "socks5", "socks5h"]
_allowed_schemes = frozenset(get_args(_Schemes))


def HTTPProxyReference(allowed_schemes: Iterable[_Schemes] = _allowed_schemes) -> ValueSpec:
    """Use this valuespec in case you want the user to configure a HTTP proxy
    The configured value is is used for preparing requests to work in a proxied environment."""

    def _global_proxy_choices() -> DropdownChoiceEntries:
        settings = ConfigDomainCore().load()
        return [
            (p["ident"], p["title"])
            for p in settings.get("http_proxies", {}).values()
            if urllib.parse.urlparse(p["proxy_url"]).scheme in allowed_schemes
        ]

    return CascadingDropdown(
        title=_("HTTP proxy"),
        default_value=("environment", "environment"),
        choices=[
            (
                "environment",
                _("Auto-detect proxy settings for this network"),
                FixedValue(
                    value="environment",
                    help=_(
                        "Use the proxy settings from the environment variables. The variables <tt>NO_PROXY</tt>, "
                        "<tt>HTTP_PROXY</tt> and <tt>HTTPS_PROXY</tt> are taken into account during execution. "
                        "Have a look at the python requests module documentation for further information. Note "
                        "that these variables must be defined as a site-user in ~/etc/environment and that "
                        "this might affect other notification methods which also use the requests module."
                    ),
                    totext=_(
                        "Use proxy settings from the process environment. This is the default."
                    ),
                ),
            ),
            (
                "no_proxy",
                _("No proxy"),
                FixedValue(
                    value=None,
                    totext=_("Connect directly to the destination instead of using a proxy."),
                ),
            ),
            (
                "global",
                _("Globally configured proxy"),
                DropdownChoice(
                    choices=_global_proxy_choices,
                    sorted=True,
                ),
            ),
            ("url", _("Manual proxy configuration"), HTTPProxyInput(allowed_schemes)),
        ],
        sorted=False,
    )


def HTTPProxyInput(allowed_schemes: Iterable[_Schemes] = _allowed_schemes) -> Dictionary:
    return Dictionary(
        required_keys=["scheme", "proxy_server_name", "port"],
        title=_("Proxy"),
        elements=[
            (
                "scheme",
                DropdownChoice(
                    title=_("Scheme"),
                    choices=[(scheme, scheme) for scheme in allowed_schemes],
                    default_value="http",
                ),
            ),
            (
                "proxy_server_name",
                TextInput(title=_("Proxy server name or IP address")),
            ),
            (
                "port",
                NetworkPort(title=_("Port")),
            ),
            (
                "auth",
                Dictionary(
                    required_keys=["user", "password"],
                    title=_("Authentication for proxy required"),
                    elements=[
                        (
                            "user",
                            TextInput(title=_("Username")),
                        ),
                        (
                            "password",
                            MigrateToIndividualOrStoredPassword(
                                title=_("Password"),
                                allow_empty=False,
                            ),
                        ),
                    ],
                ),
            ),
        ],
    )
