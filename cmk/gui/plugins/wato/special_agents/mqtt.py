#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import cmk.gui.watolib as watolib
from cmk.gui.i18n import _
from cmk.gui.plugins.wato.special_agents.common import RulespecGroupDatasourceProgramsApps
from cmk.gui.plugins.wato.utils import HostRulespec, PasswordFromStore, rulespec_registry
from cmk.gui.valuespec import Dictionary, DropdownChoice, HostAddress, NetworkPort, TextInput


def _valuespec_special_agents_mqtt() -> Dictionary:
    return Dictionary(
        title=_("MQTT broker statistics"),
        help=_(
            "Connect to an MQTT broker to get statistics out of your instance. "
            "The information is fetched from the <tt>$SYS</tt> topic of the broker. The "
            "different brokers implement different topics as they are not standardized, "
            "means that not every service available with every broker. "
            "In multi-tentant, enterprise level cluster this agent may not be useful or "
            "probably only when directly connecting to single nodes, because the "
            "<tt>$SYS</tt> topic is node-specific."
        ),
        elements=[
            (
                "username",
                TextInput(
                    title=_("Username"),
                    help=_("The username used for broker authentication."),
                    size=32,
                    allow_empty=False,
                ),
            ),
            (
                "password",
                PasswordFromStore(
                    title=_("Password of the user"),
                    allow_empty=False,
                ),
            ),
            (
                "address",
                HostAddress(
                    title=_("Custom address"),
                    help=_(
                        "When set, this address is used for connecting to the MQTT "
                        "broker. If not set, the special agent will use the primary "
                        "address of the host to connect to the MQTT broker."
                    ),
                    size=32,
                    allow_empty=False,
                ),
            ),
            (
                "port",
                NetworkPort(
                    title=_("Port"),
                    default_value=1883,
                    help=_("The port that is used for the api call."),
                ),
            ),
            (
                "client-id",
                TextInput(
                    title=_("Client ID"),
                    help=_(
                        "Unique client ID used for the broker. Will be randomly "
                        "generated when not set."
                    ),
                    size=32,
                    allow_empty=False,
                ),
            ),
            (
                "protocol",
                DropdownChoice(
                    title=_("Protocol"),
                    choices=[
                        ("MQTTv31", "MQTTv31"),
                        ("MQTTv311", "MQTTv311"),
                        ("MQTTv5", "MQTTv5"),
                    ],
                    default_value="MQTTv311",
                ),
            ),
            (
                "instance-id",
                TextInput(
                    title=_("Instance ID"),
                    help=_("Unique ID used to identify the instance on the host within Checkmk."),
                    size=32,
                    allow_empty=False,
                    default_value="broker",
                ),
            ),
        ],
        required_keys=[],
    )


rulespec_registry.register(
    HostRulespec(
        factory_default=watolib.Rulespec.FACTORY_DEFAULT_UNUSED,
        group=RulespecGroupDatasourceProgramsApps,
        name="special_agents:mqtt",
        valuespec=_valuespec_special_agents_mqtt,
    )
)
