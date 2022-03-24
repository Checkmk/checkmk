#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import cmk.gui.watolib as watolib
from cmk.gui.i18n import _
from cmk.gui.plugins.wato.special_agents.common import RulespecGroupDatasourceProgramsApps
from cmk.gui.plugins.wato.utils import HostRulespec, rulespec_registry
from cmk.gui.valuespec import Dictionary, DropdownChoice, Integer, Password, TextInput, Tuple


def _special_agents_jolokia_mk_jolokia_elements():
    return [
        (
            "port",
            Integer(
                title=_("TCP port for connection"),
                default_value=8080,
                minvalue=1,
                maxvalue=65535,
            ),
        ),
        (
            "login",
            Tuple(
                title=_("Optional login (if required)"),
                elements=[
                    TextInput(
                        title=_("User ID for web login (if login required)"),
                        default_value="monitoring",
                    ),
                    Password(title=_("Password for this user")),
                    DropdownChoice(
                        title=_("Login mode"),
                        choices=[
                            ("basic", _("HTTP Basic Authentication")),
                            ("digest", _("HTTP Digest")),
                        ],
                    ),
                ],
            ),
        ),
        (
            "suburi",
            TextInput(
                title=_("relative URI under which Jolokia is visible"),
                default_value="jolokia",
                size=30,
            ),
        ),
        (
            "instance",
            TextInput(
                title=_("Name of the instance in the monitoring"),
                help=_(
                    "If you do not specify a name here, then the TCP port number "
                    "will be used as an instance name."
                ),
            ),
        ),
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
    ]


def _factory_default_special_agents_jolokia():
    # No default, do not use setting if no rule matches
    return watolib.Rulespec.FACTORY_DEFAULT_UNUSED


def _valuespec_special_agents_jolokia():
    return Dictionary(
        title=_("Jolokia"),
        help=_("This rule allows querying the Jolokia web API."),
        elements=_special_agents_jolokia_mk_jolokia_elements(),
    )


rulespec_registry.register(
    HostRulespec(
        factory_default=_factory_default_special_agents_jolokia(),
        group=RulespecGroupDatasourceProgramsApps,
        name="special_agents:jolokia",
        valuespec=_valuespec_special_agents_jolokia,
    )
)
