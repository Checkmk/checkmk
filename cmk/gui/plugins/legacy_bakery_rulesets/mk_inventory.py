#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.agent_bakery import RulespecGroupMonitoringAgentsAgentPlugins
from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import HostRulespec, rulespec_registry
from cmk.gui.valuespec import Age, Alternative, Dictionary, FixedValue, ListOfStrings
from cmk.utils.rulesets.definition import RuleGroup


def _valuespec_agent_config_mk_inventory() -> Alternative:
    return Alternative(
        title=_("HW/SW inventory (Linux, Windows, Solaris, AIX)"),
        help=_(
            "If you activate this option, the agent plug-in <tt>mk_inventory</tt> will be deployed on "
            "Linux and Windows hosts. It gathers information about installed hardware and software and makes the "
            "information available in graphical user interface (GUI) and for exporting to third-party software. <b>Note:</b> "
            "In order to actually use the inventory for a host you also need to enable it in "
            "the rule set <a href='wato.py?varname=active_checks%3Acmk_inv&folder=&mode=edit_ruleset'>"
            "Do HW/SW inventory</a>."
        ),
        elements=[
            Dictionary(
                title=_("Deploy the Checkmk HW/SW inventory plug-in"),
                elements=[
                    (
                        "interval",
                        Age(
                            title=_("Interval for collecting data"),
                        ),
                    ),
                    (
                        "exe_paths",
                        ListOfStrings(
                            title=_("Directories to search for <tt>EXE</tt> files (Windows)"),
                            size=64,
                        ),
                    ),
                    (
                        "reg_paths",
                        ListOfStrings(
                            title=_("Registry Keys to search for software (Windows)"),
                            size=64,
                        ),
                    ),
                ],
                optional_keys=["exe_paths", "reg_paths"],
            ),
            FixedValue(
                value=None,
                title=_("Do not deploy the Checkmk HW/SW inventory plug-in"),
                totext=_("(disabled)"),
            ),
        ],
        default_value={
            "interval": 14400,
            # "exe_paths" : [ r'', ],
            "reg_paths": [
                r"Software\Microsoft\Windows\CurrentVersion\Uninstall",
                r"Software\Wow6432Node\Microsoft\Windows\CurrentVersion\Uninstall",
            ],
        },
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupMonitoringAgentsAgentPlugins,
        name=RuleGroup.AgentConfig("mk_inventory"),
        valuespec=_valuespec_agent_config_mk_inventory,
    )
)
