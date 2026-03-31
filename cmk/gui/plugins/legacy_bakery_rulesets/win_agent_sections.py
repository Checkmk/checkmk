#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.agent_bakery import RulespecGroupMonitoringAgentsWindowsAgent
from cmk.gui.i18n import _
from cmk.gui.plugins.legacy_bakery_rulesets.utils import windows_sections
from cmk.gui.plugins.wato.utils import HostRulespec, rulespec_registry
from cmk.gui.valuespec import ListChoice
from cmk.utils.rulesets.definition import RuleGroup


def _valuespec_agent_config_win_agent_sections() -> ListChoice:
    return ListChoice(
        title=_("Enabled sections (Windows agent)"),
        help=_(
            "This option allows to select specific sections of the Checkmk agent. "
            "All of the sections checked below will be executed. "
            "Sections that are not selected here will be skipped. "
            "Skipping sections reduces CPU load on the monitored host and the amount "
            "of transferred data. However, it may result in the absence of the associated "
            "Checkmk service or services. "
            "The most CPU performance is needed by the Eventlog monitoring and the "
            "performance counters. "
        ),
        choices=[(k, v) for k, v, _, _ in windows_sections()],
        default_value=[k if e else "" for k, _, e, _ in windows_sections()],
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupMonitoringAgentsWindowsAgent,
        name=RuleGroup.AgentConfig("win_agent_sections"),
        valuespec=_valuespec_agent_config_win_agent_sections,
    )
)
