#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.agent_bakery import RulespecGroupMonitoringAgentsWindowsAgent
from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import HostRulespec, rulespec_registry
from cmk.gui.valuespec import Integer
from cmk.utils.rulesets.definition import RuleGroup


def _valuespec_agent_config_win_set_wmi_timeout() -> Integer:
    return Integer(
        title=_("Windows WMI Timeout"),
        unit=_("seconds"),
        default_value=3,
        minvalue=2,
        maxvalue=12,
        help=_(
            "Increase this value if WMI-based services are switching "
            "constantly into stale state. Default value is 3."
        ),
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupMonitoringAgentsWindowsAgent,
        name=RuleGroup.AgentConfig("win_set_wmi_timeout"),
        valuespec=_valuespec_agent_config_win_set_wmi_timeout,
    )
)
