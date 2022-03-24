#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.i18n import _
from cmk.gui.plugins.wato.special_agents.common import RulespecGroupDatasourceProgramsApps
from cmk.gui.plugins.wato.utils import HostRulespec, rulespec_registry
from cmk.gui.valuespec import Alternative, Dictionary, FixedValue, Integer, TextInput


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
                Integer(
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
                TextInput(
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
                        "Check_MK agent on the same system at the specified port."
                    ),
                    elements=[
                        (
                            "port",
                            Integer(
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
            "This rule selects the Agent Ruckus Spot agent instead of the normal Check_MK Agent "
            "which collects the data through the Ruckus Spot web interface"
        ),
        optional_keys=["cmk_agent"],
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupDatasourceProgramsApps,
        name="special_agents:ruckus_spot",
        valuespec=_valuespec_special_agents_ruckus_spot,
    )
)
