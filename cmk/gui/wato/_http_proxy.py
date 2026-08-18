#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="type-arg"

from collections.abc import Iterable
from typing import get_args, Literal

from cmk.gui.form_specs.unstable import CascadingSingleChoiceExtended
from cmk.gui.form_specs.unstable.cascading_single_choice_extended import (
    CascadingSingleChoiceElementExtended,
)
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
from cmk.gui.watolib.password_store import postprocessable_ios_password
from cmk.rulesets.internal.form_specs import SingleChoiceElementExtended, SingleChoiceExtended
from cmk.rulesets.v1 import form_specs as fs
from cmk.rulesets.v1 import Help, Label, Title

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
            if p.get("proxy_config", {}).get("scheme") in allowed_schemes
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


def http_proxy_reference_form_spec() -> CascadingSingleChoiceExtended:
    def _global_proxy_elements() -> list[SingleChoiceElementExtended[str]]:
        settings = ConfigDomainCore().load()
        return [
            SingleChoiceElementExtended[str](
                name=str(proxy["ident"]),
                title=Title(str(proxy["title"])),  # astrein: disable=localization-checker
            )
            for proxy in sorted(
                settings.get("http_proxies", {}).values(), key=lambda proxy: str(proxy["title"])
            )
        ]

    return CascadingSingleChoiceExtended(
        title=Title("HTTP proxy"),
        prefill=fs.DefaultValue("environment"),
        elements=[
            fs.CascadingSingleChoiceElement(
                name="environment",
                title=Title("Auto-detect proxy settings for this network"),
                parameter_form=fs.FixedValue(
                    value="environment",
                    label=Label(
                        "Use proxy settings from the process environment. This is the default."
                    ),
                    help_text=Help(
                        "Use the proxy settings from the environment variables. The variables <tt>NO_PROXY</tt>, "
                        "<tt>HTTP_PROXY</tt> and <tt>HTTPS_PROXY</tt> are taken into account during execution. "
                        "Have a look at the python requests module documentation for further information. Note "
                        "that these variables must be defined as a site-user in ~/etc/environment and that "
                        "this might affect other notification methods which also use the requests module."
                    ),
                ),
            ),
            fs.CascadingSingleChoiceElement(
                name="no_proxy",
                title=Title("No proxy"),
                parameter_form=fs.FixedValue(
                    value=None,
                    label=Label("Connect directly to the destination instead of using a proxy."),
                ),
            ),
            CascadingSingleChoiceElementExtended(
                name="global",
                title=Title("Globally configured proxy"),
                parameter_form=SingleChoiceExtended[str](
                    elements=_global_proxy_elements,
                    invalid_element_validation=fs.InvalidElementValidator(
                        mode=fs.InvalidElementMode.KEEP
                    ),
                ),
            ),
            fs.CascadingSingleChoiceElement(
                name="url",
                title=Title("Manual proxy configuration"),
                parameter_form=http_proxy_input_form_spec(),
            ),
        ],
    )


def http_proxy_input_form_spec() -> fs.Dictionary:
    return fs.Dictionary(
        title=Title("Proxy"),
        elements={
            "scheme": fs.DictElement(
                required=True,
                parameter_form=fs.SingleChoice(
                    title=Title("Scheme"),
                    elements=[
                        fs.SingleChoiceElement(name="http", title=Title("http")),
                        fs.SingleChoiceElement(name="https", title=Title("https")),
                        fs.SingleChoiceElement(name="socks4", title=Title("socks4")),
                        fs.SingleChoiceElement(name="socks4a", title=Title("socks4a")),
                        fs.SingleChoiceElement(name="socks5", title=Title("socks5")),
                        fs.SingleChoiceElement(name="socks5h", title=Title("socks5h")),
                    ],
                    prefill=fs.DefaultValue("http"),
                ),
            ),
            "proxy_server_name": fs.DictElement(
                required=True,
                parameter_form=fs.String(title=Title("Proxy server name or IP address")),
            ),
            "port": fs.DictElement(
                required=True,
                parameter_form=fs.Integer(
                    title=Title("Port"),
                    custom_validate=[fs.validators.NetworkPort()],
                ),
            ),
            "auth": fs.DictElement(
                parameter_form=fs.Dictionary(
                    title=Title("Authentication for proxy required"),
                    elements={
                        "user": fs.DictElement(
                            required=True,
                            parameter_form=fs.String(title=Title("Username")),
                        ),
                        "password": fs.DictElement(
                            required=True,
                            parameter_form=fs.Password(
                                title=Title("Password"),
                                custom_validate=[fs.validators.LengthInRange(min_value=1)],
                            ),
                        ),
                    },
                ),
            ),
        },
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
                        ("user", TextInput(title=_("Username"))),
                        ("password", postprocessable_ios_password(title=_("Password"))),
                    ],
                ),
            ),
        ],
    )
