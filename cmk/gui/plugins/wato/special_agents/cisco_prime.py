#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.i18n import _
from cmk.gui.plugins.wato.special_agents.common import RulespecGroupDatasourceProgramsOS
from cmk.gui.plugins.wato.utils import HostRulespec, PasswordFromStore, rulespec_registry
from cmk.gui.valuespec import CascadingDropdown, Dictionary, FixedValue, Integer, TextInput, Tuple


def _valuespec_special_agents_cisco_prime():
    return Dictionary(
        elements=[
            (
                "host",
                CascadingDropdown(
                    choices=[
                        ("ip_address", _("IP Address")),
                        ("host_name", _("Host name")),
                        (
                            "custom",
                            _("Custom Host"),
                            Dictionary(
                                elements=[
                                    (
                                        "host",
                                        TextInput(
                                            title=_("Custom Host"),
                                            allow_empty=False,
                                        ),
                                    )
                                ],
                                optional_keys=[],
                            ),
                        ),
                    ],
                    default_value="ip_address",
                    title=_("Host to use for connecting to Cisco Prime"),
                ),
            ),
            (
                "basicauth",
                Tuple(
                    title=_("BasicAuth settings (optional)"),
                    help=_("The credentials for api calls with authentication."),
                    elements=[
                        TextInput(title=_("Username"), allow_empty=False),
                        PasswordFromStore(title=_("Password of the user"), allow_empty=False),
                    ],
                ),
            ),
            ("port", Integer(title=_("Port"), default_value=8080)),
            (
                "no-tls",
                FixedValue(
                    value=True,
                    title=_("Don't use TLS/SSL/Https (unsecure)"),
                    totext=_("TLS/SSL/Https disabled"),
                ),
            ),
            (
                "no-cert-check",
                FixedValue(
                    value=True,
                    title=_("Disable SSL certificate validation"),
                    totext=_("SSL certificate validation is disabled"),
                ),
            ),
            (
                "timeout",
                Integer(
                    title=_("Connect Timeout"),
                    help=_("The network timeout in seconds"),
                    default_value=60,
                    minvalue=1,
                    unit=_("seconds"),
                ),
            ),
        ],
        title=_("Cisco Prime"),
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupDatasourceProgramsOS,
        name="special_agents:cisco_prime",
        valuespec=_valuespec_special_agents_cisco_prime,
    )
)
