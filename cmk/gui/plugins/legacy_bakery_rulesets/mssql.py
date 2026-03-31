#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Sequence

from cmk.gui.agent_bakery import RulespecGroupMonitoringAgentsAgentPlugins
from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import HostRulespec, rulespec_registry
from cmk.gui.valuespec import (
    Alternative,
    CascadingDropdown,
    Dictionary,
    FixedValue,
    Integer,
    ListOf,
    ListOfStrings,
    Password,
    TextInput,
    Tuple,
)
from cmk.gui.valuespec.definitions import CascadingDropdownChoice
from cmk.utils.rulesets.definition import RuleGroup


def _mssql_authentication_choices() -> Sequence[CascadingDropdownChoice]:
    return [
        ("system", _("System authentication")),
        (
            "db",
            _("Database user credentials"),
            Tuple(
                elements=[
                    TextInput(
                        title=_("User ID"),
                        default_value="monitoring",
                    ),
                    Password(title=_("Password")),
                ]
            ),
        ),
    ]


def _valuespec_agent_config_mssql() -> Alternative:
    return Alternative(
        title=_("Microsoft SQL Server"),
        help=_(
            "This plug-in is deprecated and will be removed in Checkmk 2.4.0 (see werk "
            '15844 for details). Please switch to the new ruleset "Microsoft SQL server '
            '(Linux, Windows)".'
            "This plug-in can be used to collect information of all running MSSQL servers "
            "on the local system. "
            'The current implementation of the check uses the "trusted authentication" '
            "where no user/password needs to be created in the MSSQL server instance by "
            "default. Using this method, you needed to grant the user running the Checkmk "
            "windows agent service access to the MSSQL database. Otherwise you "
            "can configure the credentials of a database user which has the permission to "
            "read the needed information from the server instance."
        ),
        elements=[
            Dictionary(
                title=_("Deploy MSSQL Server plug-in"),
                elements=[
                    (
                        "auth_default",
                        CascadingDropdown(
                            title=_("Authentication (defaults)"),
                            choices=_mssql_authentication_choices,
                        ),
                    ),
                    (
                        "auth_instances",
                        ListOf(
                            valuespec=Tuple(
                                elements=[
                                    TextInput(
                                        title=_("Instance ID"),
                                    ),
                                    CascadingDropdown(
                                        title=_("Authentication (defaults)"),
                                        choices=_mssql_authentication_choices,
                                    ),
                                ],
                            ),
                            allow_empty=False,
                            title=_("Authentication (instance-specific)"),
                        ),
                    ),
                    (
                        "inst_excludes",
                        ListOfStrings(
                            title=_("Exclude instances"),
                        ),
                    ),
                    (
                        "timeout_connection",
                        Integer(
                            title=_("Set connection timeout"),
                            help=_(
                                "Time to wait for a connection to an instance to open "
                                "before continuing with the next instance. If unset, the "
                                "default value from ADO is used."
                            ),
                            default_value=15,
                            minvalue=0,
                            unit=_("seconds"),
                        ),
                    ),
                    (
                        "timeout_command",
                        Integer(
                            title=_("Set command timeout"),
                            help=_(
                                "Time to wait for a command to finish before continuing "
                                "with the next command. If unset, the default value from "
                                "ADO is used."
                            ),
                            default_value=30,
                            minvalue=0,
                            unit=_("seconds"),
                        ),
                    ),
                ],
                required_keys=["auth_default"],
            ),
            FixedValue(
                value=None,
                title=_("Do not deploy plug-in for Microsoft SQL Server"),
                totext=_("(disabled)"),
            ),
        ],
        default_value={
            "auth_default": "system",
        },
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupMonitoringAgentsAgentPlugins,
        name=RuleGroup.AgentConfig("mssql"),
        valuespec=_valuespec_agent_config_mssql,
        is_deprecated=True,
    )
)
