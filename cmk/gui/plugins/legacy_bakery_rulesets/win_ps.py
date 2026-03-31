#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.agent_bakery import RulespecGroupMonitoringAgentsWindowsAgent
from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import HostRulespec, rulespec_registry
from cmk.gui.valuespec import Checkbox, Dictionary
from cmk.utils.rulesets.definition import RuleGroup


def _valuespec_agent_config_win_ps() -> Dictionary:
    return Dictionary(
        title=_("Fine-tune Windows process monitoring"),
        elements=[
            (
                "use_wmi",
                Checkbox(
                    title=_("Use WMI"),
                    label=_(
                        "Retrieve process information using WMI (Windows Management Instrumentation)"
                    ),
                    help=_(
                        "Rely on WMI (Windows Management Instrumentation) when retrieving process "
                        "information. Using WMI is mandatory for including the full path of a running "
                        "process in the list of processes."
                    ),
                    default_value=True,
                ),
            ),
            (
                "full_path",
                Checkbox(
                    title=_("Include full path"),
                    label=_(
                        "Include the full path of a process and its arguments in the process list. "
                        "Note: this requires using WMI for retrieving process information."
                    ),
                    help=_(
                        "Include the full path of a process and its arguments in the process list. "
                        "Note: this requires using WMI for retrieving process information."
                    ),
                    default_value=False,
                ),
            ),
        ],
        optional_keys=False,
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupMonitoringAgentsWindowsAgent,
        name=RuleGroup.AgentConfig("win_ps"),
        valuespec=_valuespec_agent_config_win_ps,
    )
)
