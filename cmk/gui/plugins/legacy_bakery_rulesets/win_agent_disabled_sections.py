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


def _valuespec_agent_config_win_agent_disabled_sections() -> ListChoice:
    return ListChoice(
        title=_("Disabled sections (Windows agent)"),
        help=" ".join(
            (
                _("This option allows to skip specific sections of the Checkmk agent."),
                _("Selected sections will not be executed by the agent."),
                _(
                    "Skipping sections reduces CPU load on the monitored host and the amount "
                    "of transferred data. However, it may result in the absence of the associated "
                    "Checkmk service or services."
                ),
                _(
                    "Most of the CPU performance is needed by the event log monitoring and the "
                    "performance counters."
                ),
            )
        ),
        choices=[(k, v) for k, v, _, _ in windows_sections()],
        default_value=[k if d else "" for k, _, _, d in windows_sections()],
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupMonitoringAgentsWindowsAgent,
        name=RuleGroup.AgentConfig("win_agent_disabled_sections"),
        valuespec=_valuespec_agent_config_win_agent_disabled_sections,
    )
)
