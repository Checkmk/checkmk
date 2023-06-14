#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.i18n import _
from cmk.gui.plugins.wato.special_agents.common import RulespecGroupDatasourceProgramsApps
from cmk.gui.plugins.wato.utils import (
    HostRulespec,
    MigrateToIndividualOrStoredPassword,
    rulespec_registry,
)
from cmk.gui.valuespec import Checkbox, Dictionary, DropdownChoice, NetworkPort, TextInput, Tuple
from cmk.gui.watolib.rulespecs import Rulespec


def _factory_default_special_agents_activemq():
    # No default, do not use setting if no rule matches
    return Rulespec.FACTORY_DEFAULT_UNUSED


def _valuespec_special_agents_activemq() -> Dictionary:
    return Dictionary(
        title=_("Apache ActiveMQ queues"),
        elements=[
            (
                "servername",
                TextInput(
                    title=_("Server Name"),
                    allow_empty=False,
                ),
            ),
            ("port", NetworkPort(title=_("Port Number"), default_value=8161)),
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
            ("use_piggyback", Checkbox(title=_("Use Piggyback"), label=_("Enable"))),
            (
                "basicauth",
                Tuple(
                    title=_("BasicAuth settings (optional)"),
                    elements=[
                        TextInput(title=_("Username")),
                        MigrateToIndividualOrStoredPassword(title=_("Password")),
                    ],
                ),
            ),
        ],
        optional_keys=["basicauth"],
    )


rulespec_registry.register(
    HostRulespec(
        factory_default=_factory_default_special_agents_activemq(),
        group=RulespecGroupDatasourceProgramsApps,
        name="special_agents:activemq",
        valuespec=_valuespec_special_agents_activemq,
    )
)
