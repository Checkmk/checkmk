#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import typing

from cmk.gui.exceptions import MKUserError
from cmk.gui.i18n import _
from cmk.gui.plugins.wato.special_agents.common import (
    api_request_authentication,
    api_request_connection_elements,
    RulespecGroupVMCloudContainer,
    ssl_verification,
)
from cmk.gui.plugins.wato.utils import HostRulespec, rulespec_registry
from cmk.gui.valuespec import (
    CascadingDropdown,
    Dictionary,
    DropdownChoice,
    FixedValue,
    ListOfStrings,
    TextInput,
)


def _deprecate_dynamic_host_adress(*value: object, **kwargs: object) -> typing.NoReturn:
    raise MKUserError(None, _("The options IP Address and Host name are deprecated - Werk 14573."))


def _valuespec_generic_metrics_alertmanager():
    return Dictionary(
        elements=[
            (
                "hostname",
                TextInput(
                    title=_("Optionally forward output to host"),
                    help=_(
                        "If given forward output to a different host using piggyback mechanics."
                    ),
                ),
            ),
            (
                "connection",
                CascadingDropdown(
                    choices=[
                        (
                            "ip_address",
                            _("(deprecated) IP Address"),
                            Dictionary(
                                elements=api_request_connection_elements(
                                    help_text=_(
                                        "Specifies a URL path prefix, which is prepended to API calls "
                                        "to the Prometheus API. If this option is not relevant for "
                                        "your installation, please leave it unchecked."
                                    ),
                                    default_port=9091,
                                ),
                                help=_("Use IP address of assigned host"),
                                validate=_deprecate_dynamic_host_adress,
                            ),
                        ),
                        (
                            "host_name",
                            _("(deprecated) Host name"),
                            Dictionary(
                                elements=api_request_connection_elements(
                                    help_text=_(
                                        "Specifies a URL path prefix, which is prepended to API calls "
                                        "to the Prometheus API. If this option is not relevant for "
                                        "your installation, please leave it unchecked."
                                    ),
                                    default_port=9091,
                                ),
                                help=_("Use host name of assigned host"),
                                validate=_deprecate_dynamic_host_adress,
                            ),
                        ),
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
                    title=_("Prometheus connection option"),
                ),
            ),
            ssl_verification(),
            api_request_authentication(),
            (
                "protocol",
                DropdownChoice(
                    title=_("Protocol"),
                    choices=[
                        ("http", "HTTP"),
                        ("https", "HTTPS"),
                    ],
                ),
            ),
            (
                "ignore_alerts",
                Dictionary(
                    title=_("Ignore alert rules"),
                    help=_(
                        "The ignore option can target alert rules on different levels including "
                        "specific rules as well as entire rule groups. Matching rules will be filtered "
                        "out on the alertmanager agent side."
                    ),
                    elements=[
                        (
                            "ignore_na",
                            FixedValue(
                                value=True,
                                title=_("Ignore alert rules with no status"),
                                totext="",
                                help=_(
                                    "Alert rules that don't export a status are ignored with this option."
                                ),
                            ),
                        ),
                        (
                            "ignore_alert_rules",
                            ListOfStrings(
                                title=_("Ignore specific alert rules"),
                                help=_("Name of specific alert rules you want to ignore."),
                            ),
                        ),
                        (
                            "ignore_alert_groups",
                            ListOfStrings(
                                title=_("Ignore all alert rules within certain alert rule groups"),
                            ),
                        ),
                    ],
                    optional_keys=["ignore_na"],
                    default_keys=["ignore_na"],
                ),
            ),
        ],
        title=_("Alertmanager"),
        optional_keys=["auth_basic"],
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupVMCloudContainer,
        name="special_agents:alertmanager",
        valuespec=_valuespec_generic_metrics_alertmanager,
    )
)
