#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any

from cmk.utils.rulesets.definition import RuleGroup

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.special_agents.common_tls_verification import tls_verify_flag_default_yes
from cmk.gui.plugins.wato.utils import HostRulespec, rulespec_registry
from cmk.gui.valuespec import (
    CascadingDropdown,
    Dictionary,
    DropdownChoice,
    HTTPUrl,
    NetworkPort,
    TextInput,
)
from cmk.gui.wato import (
    MigrateToIndividualOrStoredPassword,
    RulespecGroupDatasourceProgramsHardware,
)
from cmk.gui.watolib.rulespecs import Rulespec


def _factory_default_special_agents_innovaphone():
    # No default, do not use setting if no rule matches
    return Rulespec.FACTORY_DEFAULT_UNUSED


def _connection_set(options: list[str] | None = None, auth_option: str | None = None) -> list[Any]:
    """Standard connection elements set

    A set of frequently used connection configuration options.
    Using the listed elements here allows to use additional helper functions
    in base/check_legacy_includes/agent_helper & in cmk/special_agents/utils.py which serve
    to facilitate the API connection setup from the special_agent side

    Args:
        options:
            list of strings specifying which connection elements to include. If empty
            then all connection elements will be included
        auth_option:
            string which specify which connection authentication element to include

    Returns:
        list of Setup connection elements

    """
    connection_options: list[Any] = []
    if options is None:
        all_options = True
        options = []
    else:
        all_options = False

    if "connection_type" in options or all_options:
        connection_options.append(
            (
                "connection",
                CascadingDropdown(
                    choices=[
                        ("host_name", _("Host name")),
                        ("ip_address", _("IP Address")),
                        (
                            "url_custom",
                            _("Custom URL"),
                            Dictionary(
                                elements=[
                                    (
                                        "url_address",
                                        TextInput(
                                            title=_("Custom URL server address"),
                                            help=_(
                                                "Specify a custom URL to connect to "
                                                "your server. Do not include the "
                                                "protocol. This option overwrites "
                                                "all available options such as port and "
                                                "other URL prefixes."
                                            ),
                                            allow_empty=False,
                                        ),
                                    )
                                ],
                                optional_keys=[],
                            ),
                        ),
                    ],
                    title=_("Connection option"),
                ),
            )
        )

    if "port" in options or all_options:
        connection_options.append(
            (
                "port",
                NetworkPort(
                    title=_("TCP port number"),
                    help=_("Port number that server is listening on."),
                    default_value=4223,
                    minvalue=1,
                    maxvalue=65535,
                ),
            )
        )

    if "protocol" in options or all_options:
        connection_options.append(
            (
                "protocol",
                DropdownChoice(
                    title=_("Protocol"),
                    choices=[
                        ("http", "HTTP"),
                        ("https", "HTTPS"),
                    ],
                ),
            )
        )

    if "url_prefix" in options or all_options:
        connection_options.append(
            (
                "url-prefix",
                HTTPUrl(
                    title=_("Custom URL prefix"),
                    help=_(
                        "Specifies a URL prefix which is prepended to the path in calls to "
                        "the API. This is e.g. useful if you use the ip address or the hostname "
                        "as base address but require some additional prefix to make the correct "
                        "API call. Use the custom URL option if you need to specify a more "
                        "complex API url."
                    ),
                    allow_empty=False,
                ),
            )
        )

    if "path_prefix" in options or all_options:
        connection_options.append(
            (
                "path-prefix",
                TextInput(
                    title=_("Custom path prefix"),
                    help=_(
                        "Specifies an URL path suffix which is appended to the path in calls "
                        "to the API. This is e.g. useful if you use the ip address or the hostname "
                        "as base address and require to specify a path URL in order to make the "
                        'correct API calls. Do not prepend or append your custom path with "/". '
                        "Use the custom URL option if you need to specify a "
                        "more complex API URL"
                    ),
                    allow_empty=False,
                ),
            )
        )

    if "ssl_verify" in options or all_options:
        connection_options.append(tls_verify_flag_default_yes())

    if auth_option:
        connection_options.extend(_auth_option(auth_option))

    return connection_options


def _auth_option(option: str) -> list[Any]:
    auth: list[Any] = []
    if option == "basic":
        auth.append(
            (
                "auth_basic",
                Dictionary(
                    elements=[
                        (
                            "username",
                            TextInput(
                                title=_("Login username"),
                                allow_empty=False,
                            ),
                        ),
                        (
                            "password",
                            MigrateToIndividualOrStoredPassword(
                                title=_("Password"),
                                allow_empty=False,
                            ),
                        ),
                    ],
                    optional_keys=[],
                    title=_("Basic authentication"),
                ),
            )
        )

    elif option == "token":
        auth.append(
            (
                "token",
                TextInput(
                    title=_("API key/token"),
                    allow_empty=False,
                    size=70,
                ),
            )
        )
    return auth


def _valuespec_special_agents_innovaphone() -> Dictionary:
    return Dictionary(
        title=_("Innovaphone Gateways"),
        help=_("Please specify the user and password needed to access the xml interface"),
        elements=_connection_set(
            options=["protocol", "ssl_verify"],
            auth_option="basic",
        ),
        optional_keys=["protocol", "no-cert-check"],
    )


rulespec_registry.register(
    HostRulespec(
        factory_default=_factory_default_special_agents_innovaphone(),
        group=RulespecGroupDatasourceProgramsHardware,
        name=RuleGroup.SpecialAgents("innovaphone"),
        valuespec=_valuespec_special_agents_innovaphone,
    )
)
