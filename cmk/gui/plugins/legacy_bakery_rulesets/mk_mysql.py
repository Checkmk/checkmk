#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.agent_bakery import RulespecGroupMonitoringAgentsAgentPlugins
from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import HostRulespec, rulespec_registry
from cmk.gui.valuespec import (
    Age,
    Alternative,
    Dictionary,
    FixedValue,
    ListOf,
    NetworkPort,
    TextInput,
    Tuple,
)
from cmk.gui.wato import MigrateToIndividualOrStoredPassword
from cmk.utils.rulesets.definition import RuleGroup


def _valuespec_agent_config_mk_mysql() -> Alternative:
    return Alternative(
        title=_("MySQL databases"),
        help=_(
            "This will deploy the agent plug-in <tt>mk_mysql</tt> on Linux systems and "
            "<tt>mk_mysql.ps1</tt> on Windows systems for monitoring several aspects "
            "of MySQL databases. On Windows, the plug-in will look for service names containing the "
            "strings <tt>MySQL</tt> or <tt>MariaDB</tt>."
        ),
        elements=[
            Dictionary(
                title=_("Deploy the MySQL plug-in"),
                elements=[
                    (
                        "credentials",
                        Tuple(
                            title=_("Credentials to access the database"),
                            elements=[
                                TextInput(
                                    title=_("User ID"),
                                    default_value="monitoring",
                                ),
                                MigrateToIndividualOrStoredPassword(title=_("Password")),
                            ],
                        ),
                    ),
                    (
                        "sockets",
                        ListOf(
                            Dictionary(
                                elements=[
                                    (
                                        "socket",
                                        TextInput(title=_("Socket"), allow_empty=False),
                                    ),
                                    (
                                        "alias",
                                        TextInput(
                                            title=_("Alias"),
                                            help=_("An optional alias name for your MySQL socket"),
                                        ),
                                    ),
                                ],
                                optional_keys=["alias"],
                            ),
                            title=_("Sockets"),
                            default_value=[
                                {"socket": "/var/run/mysqld/mysqld.sock"},
                            ],
                        ),
                    ),
                    ("host", TextInput(title=_("Host"), default_value="127.0.0.1")),
                    ("custom_port", NetworkPort(title=_("Custom port"), default_value=3306)),
                    (
                        "interval",
                        Age(
                            title=_("Run asynchronously"),
                            label=_("Interval for collecting data"),
                            default_value=300,
                        ),
                    ),
                ],
            ),
            FixedValue(
                value=None,
                title=_("Do not deploy the MySQL plug-in"),
                totext=_("(disabled)"),
            ),
        ],
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupMonitoringAgentsAgentPlugins,
        name=RuleGroup.AgentConfig("mk_mysql"),
        valuespec=_valuespec_agent_config_mk_mysql,
    )
)
