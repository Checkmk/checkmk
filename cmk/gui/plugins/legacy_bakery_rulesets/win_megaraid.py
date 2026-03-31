#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.agent_bakery import RulespecGroupMonitoringAgentsAgentPlugins
from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import HostRulespec, rulespec_registry
from cmk.gui.valuespec import Alternative, Dictionary, FixedValue, TextInput
from cmk.utils.rulesets.definition import RuleGroup


def _valuespec_agent_config_win_megaraid() -> Alternative:
    return Alternative(
        title=_("MegaRAID monitoring (Windows)"),
        help=_(
            "This plug-in uses the command line tool <tt>MegaCli.exe</tt> in order to provide "
            "monitoring information of LSI RAID controllers and attached hard disks. You can "
            "download this tool from <a href='http://www.lsi.com/'>LSI</a>."
        ),
        elements=[
            Dictionary(
                title=_("Deploy MegaRAID plug-in"),
                elements=[
                    (
                        "megacli",
                        TextInput(
                            title=_("Path to <tt>MegaCLI.exe</tt>"),
                            size=64,
                            allow_empty=False,
                        ),
                    ),
                    (
                        "tempdir",
                        TextInput(
                            title=_("Path to temporary directory (will be created)"),
                            allow_empty=False,
                        ),
                    ),
                ],
                optional_keys=False,
            ),
            FixedValue(
                value=None, title=_("Do not deploy the MegaRAID plug-in"), totext=_("(disabled)")
            ),
        ],
        default_value={
            "megacli": r"C:\Program Files\LSI Corporation\MegaCLI\MegaCli.exe",
            "tempdir": r"C:\Temp",
        },
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupMonitoringAgentsAgentPlugins,
        name=RuleGroup.AgentConfig("win_megaraid"),
        valuespec=_valuespec_agent_config_win_megaraid,
    )
)
