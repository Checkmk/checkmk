#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.i18n import _
from cmk.gui.plugins.wato.special_agents.common import RulespecGroupDatasourceProgramsApps
from cmk.gui.plugins.wato.utils import HostRulespec, rulespec_registry
from cmk.gui.valuespec import (
    Checkbox,
    Dictionary,
    DropdownChoice,
    Integer,
    Password,
    TextInput,
    Transform,
    Tuple,
)
from cmk.gui.watolib.rulespecs import Rulespec


def _special_agents_activemq_transform_activemq(value):
    if not isinstance(value, tuple):
        if "protocol" not in value:
            value["protocol"] = "http"
        return value
    new_value = {}
    new_value["servername"] = value[0]
    new_value["port"] = value[1]
    new_value["use_piggyback"] = "piggybag" in value[2]  # piggybag...
    return new_value


def _factory_default_special_agents_activemq():
    # No default, do not use setting if no rule matches
    return Rulespec.FACTORY_DEFAULT_UNUSED


def _valuespec_special_agents_activemq():
    return Transform(
        valuespec=Dictionary(
            elements=[
                (
                    "servername",
                    TextInput(
                        title=_("Server Name"),
                        allow_empty=False,
                    ),
                ),
                ("port", Integer(title=_("Port Number"), default_value=8161)),
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
                        elements=[TextInput(title=_("Username")), Password(title=_("Password"))],
                    ),
                ),
            ],
            optional_keys=["basicauth"],
        ),
        title=_("Apache ActiveMQ queues"),
        forth=_special_agents_activemq_transform_activemq,
    )


rulespec_registry.register(
    HostRulespec(
        factory_default=_factory_default_special_agents_activemq(),
        group=RulespecGroupDatasourceProgramsApps,
        name="special_agents:activemq",
        valuespec=_valuespec_special_agents_activemq,
    )
)
