#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import cmk.gui.watolib as watolib
from cmk.gui.i18n import _
from cmk.gui.plugins.wato.special_agents.common import RulespecGroupDatasourceProgramsApps
from cmk.gui.plugins.wato.utils import HostRulespec, PasswordFromStore, rulespec_registry
from cmk.gui.valuespec import Dictionary, DropdownChoice, Integer, ListChoice, TextInput


def _factory_default_special_agents_splunk():
    # No default, do not use setting if no rule matches
    return watolib.Rulespec.FACTORY_DEFAULT_UNUSED


def _valuespec_special_agents_splunk():
    return Dictionary(
        title=_("Splunk"),
        help=_("Requests data from a Splunk instance."),
        optional_keys=["instance", "port"],
        elements=[
            (
                "instance",
                TextInput(
                    title=_("Splunk instance to query."),
                    help=_(
                        "Use this option to set which host should be checked "
                        "by the special agent."
                    ),
                    size=32,
                    allow_empty=False,
                ),
            ),
            ("user", TextInput(title=_("Username"), size=32, allow_empty=False)),
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
                    help=_(
                        "Use this option to query a port which is different from standard port 8089."
                    ),
                    default_value=8089,
                ),
            ),
            (
                "infos",
                ListChoice(
                    title=_("Informations to query"),
                    help=_(
                        "Defines what information to query. You can "
                        "choose to query license state and usage, Splunk "
                        "system messages, Splunk jobs, shown in the job "
                        "menu within Splunk. You can also query for "
                        "component health and fired alerts."
                    ),
                    choices=[
                        ("license_state", _("Licence state")),
                        ("license_usage", _("Licence usage")),
                        ("system_msg", _("System messages")),
                        ("jobs", _("Jobs")),
                        ("health", _("Health")),
                        ("alerts", _("Alerts")),
                    ],
                    default_value=[
                        "license_state",
                        "license_usage",
                        "system_msg",
                        "jobs",
                        "health",
                        "alerts",
                    ],
                    allow_empty=False,
                ),
            ),
        ],
    )


rulespec_registry.register(
    HostRulespec(
        factory_default=_factory_default_special_agents_splunk(),
        group=RulespecGroupDatasourceProgramsApps,
        name="special_agents:splunk",
        valuespec=_valuespec_special_agents_splunk,
    )
)
