#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.utils.rulesets.definition import RuleGroup

from cmk.gui.i18n import _
from cmk.gui.valuespec import Alternative, Dictionary, FixedValue, NetworkPort, TextInput
from cmk.gui.wato import MigrateToIndividualOrStoredPassword, RulespecGroupDatasourceProgramsApps
from cmk.gui.watolib.rulespecs import HostRulespec, rulespec_registry


def _valuespec_special_agents_ruckus_spot():
    return Dictionary(
        elements=[
            (
                "address",
                Alternative(
                    title=_("Server Address"),
                    help=_("Here you can set a manual address if the server differs from the host"),
                    elements=[
                        FixedValue(
                            value=True,
                            title=_("Use host address"),
                            totext="",
                        ),
                        TextInput(
                            title=_("Enter address"),
                        ),
                    ],
                    default_value=True,
                ),
            ),
            (
                "port",
                NetworkPort(
                    title=_("Port"),
                    default_value=8443,
                ),
            ),
            (
                "venueid",
                TextInput(
                    title=_("Venue ID"),
                    allow_empty=False,
                ),
            ),
            (
                "api_key",
                MigrateToIndividualOrStoredPassword(
                    title=_("API key"),
                    allow_empty=False,
                    size=70,
                ),
            ),
            (
                "cmk_agent",
                Dictionary(
                    title=_("Also contact Checkmk agent"),
                    help=_(
                        "With this setting, the special agent will also contact the "
                        "Checkmk agent on the same system at the specified port."
                    ),
                    elements=[
                        (
                            "port",
                            NetworkPort(
                                title=_("Port"),
                                default_value=6556,
                            ),
                        ),
                    ],
                    optional_keys=[],
                ),
            ),
        ],
        title=_("Ruckus Spot"),
        help=_(
            "This rule selects the Agent Ruckus Spot agent instead of the normal Checkmk Agent "
            "which collects the data through the Ruckus Spot web interface"
        ),
        optional_keys=["cmk_agent"],
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupDatasourceProgramsApps,
        name=RuleGroup.SpecialAgents("ruckus_spot"),
        valuespec=_valuespec_special_agents_ruckus_spot,
    )
)
