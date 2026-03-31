#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from typing import Literal

from cmk.gui.agent_bakery import RulespecGroupMonitoringAgentsWindowsAgent
from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import HostRulespec, rulespec_registry
from cmk.gui.valuespec import DropdownChoice
from cmk.utils.rulesets.definition import RuleGroup


def _valuespec_agent_config_win_script_async() -> DropdownChoice[Literal["sequential", "parallel"]]:
    return DropdownChoice(
        title=_("Asynchronous execution of plug-ins (deprecated)"),
        help=_("This rulespec is deprecated and will be removed in future versions."),
        choices=[
            ("sequential", _("Run asynchronous plug-ins sequential")),
            ("parallel", _("Run asynchronous plug-ins in parallel")),
        ],
        default_value="sequential",
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupMonitoringAgentsWindowsAgent,
        name=RuleGroup.AgentConfig("win_script_async"),
        valuespec=_valuespec_agent_config_win_script_async,
        is_deprecated=True,
    )
)
