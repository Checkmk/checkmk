#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.i18n import _
from cmk.gui.plugins.wato.special_agents.common import RulespecGroupDatasourceProgramsApps
from cmk.gui.plugins.wato.utils import HostRulespec, IndividualOrStoredPassword, rulespec_registry
from cmk.gui.valuespec import Dictionary, FixedValue, Integer, ListOfStrings, NetworkPort, TextInput


def _valuespec_special_agents_mobileiron():
    return Dictionary(
        elements=[
            ("username", TextInput(title=_("Username"), allow_empty=False)),
            ("password", IndividualOrStoredPassword(title=_("Password"), allow_empty=False)),
            (
                "port",
                NetworkPort(
                    title=_("Port"),
                    default_value=443,
                    help=_("The port that is used for the API call."),
                ),
            ),
            (
                "no-cert-check",
                FixedValue(
                    True,
                    title=_("Disable SSL certificate validation"),
                    totext=_("SSL certificate validation is disabled"),
                ),
            ),
            (
                "partition",
                ListOfStrings(
                    allow_empty=False,
                    title=_("Retrieve information about the following partitions"),
                ),
            ),
            (
                "proxy_details",
                Dictionary(
                    title=_("Use proxy for MobileIron API connection"),
                    elements=[
                        ("proxy_host", TextInput(title=_("Proxy host"), allow_empty=True)),
                        ("proxy_port", Integer(title=_("Port"))),
                        (
                            "proxy_user",
                            TextInput(
                                title=_("Username"),
                                size=32,
                            ),
                        ),
                        ("proxy_password", IndividualOrStoredPassword(title=_("Password"))),
                    ],
                    optional_keys=["proxy_port", "proxy_user", "proxy_password"],
                ),
            ),
        ],
        optional_keys=["no-cert-check"],
        title=_("MobileIron API"),
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupDatasourceProgramsApps,
        name="special_agents:mobileiron",
        valuespec=_valuespec_special_agents_mobileiron,
    )
)
