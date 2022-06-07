#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.i18n import _
from cmk.gui.plugins.wato.special_agents.common import RulespecGroupDatasourceProgramsApps
from cmk.gui.plugins.wato.utils import HostRulespec, PasswordFromStore, rulespec_registry
from cmk.gui.valuespec import Dictionary, DropdownChoice, Integer, ListChoice, TextInput
from cmk.gui.watolib.rulespecs import Rulespec


def _factory_default_special_agents_rabbitmq():
    # No default, do not use setting if no rule matches
    return Rulespec.FACTORY_DEFAULT_UNUSED


def _valuespec_special_agents_rabbitmq():
    return Dictionary(
        title=_("RabbitMQ"),
        help=_("Requests data from a RabbitMQ instance."),
        elements=[
            (
                "instance",
                TextInput(
                    title=_("RabbitMQ instance to query"),
                    help=_(
                        "Use this option to set which instance should be "
                        "checked by the special agent. Please add the "
                        "hostname here, eg. my_rabbitmq.com. If not set, the "
                        "assigned host is used as instance."
                    ),
                    size=32,
                    allow_empty=False,
                ),
            ),
            (
                "user",
                TextInput(
                    title=_("Username"),
                    help=_("The username that should be used for accessing the RabbitMQ API."),
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
                "protocol",
                DropdownChoice(
                    title=_("Protocol"),
                    choices=[
                        ("http", "HTTP"),
                        ("https", "HTTPS"),
                    ],
                    default_value="https",
                ),
            ),
            (
                "port",
                Integer(
                    title=_("Port"),
                    default_value=15672,
                    help=_("The port that is used for the api call."),
                ),
            ),
            (
                "sections",
                ListChoice(
                    title=_("Informations to query"),
                    help=_(
                        "Defines what information to query. You can choose "
                        "between the cluster, nodes, vhosts and queues."
                    ),
                    choices=[
                        ("cluster", _("Clusterwide")),
                        ("nodes", _("Nodes")),
                        ("vhosts", _("Vhosts")),
                        ("queues", _("Queues")),
                    ],
                    default_value=["cluster", "nodes", "vhosts", "queues"],
                    allow_empty=False,
                ),
            ),
        ],
        optional_keys=[
            "instance",
            "port",
        ],
    )


rulespec_registry.register(
    HostRulespec(
        factory_default=_factory_default_special_agents_rabbitmq(),
        group=RulespecGroupDatasourceProgramsApps,
        name="special_agents:rabbitmq",
        valuespec=_valuespec_special_agents_rabbitmq,
    )
)
