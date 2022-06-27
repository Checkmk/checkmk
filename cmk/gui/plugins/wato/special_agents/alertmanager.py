#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


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


def _valuespec_generic_metrics_alertmanager():
    return Dictionary(
        elements=[
            (
                "hostname",
                TextInput(
                    title=_("Name of Piggyback Host"),
                    allow_empty=False,
                ),
            ),
            (
                "connection",
                CascadingDropdown(
                    choices=[
                        (
                            "ip_address",
                            _("IP Address"),
                            Dictionary(
                                elements=api_request_connection_elements(
                                    help_text=_(
                                        "Specifies a URL path prefix, which is prepended to API calls "
                                        "to the Alertmanager API. If this option is not relevant for "
                                        "your installation, please leave it unchecked."
                                    ),
                                    default_port=9093,
                                ),
                            ),
                        ),
                        (
                            "host_name",
                            _("Host name"),
                            Dictionary(
                                elements=api_request_connection_elements(
                                    help_text=_(
                                        "Specifies a URL path prefix, which is prepended to API calls "
                                        "to the Alertmanager API. If this option is not relevant for "
                                        "your installation, please leave it unchecked."
                                    ),
                                    default_port=9093,
                                ),
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
                    title=_("Alertmanager connection option"),
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
    (
        HostRulespec(
            group=RulespecGroupVMCloudContainer,
            name="special_agents:alertmanager",
            valuespec=_valuespec_generic_metrics_alertmanager,
        )
    )
)
