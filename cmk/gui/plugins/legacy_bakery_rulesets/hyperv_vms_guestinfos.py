#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.agent_bakery import RulespecGroupMonitoringAgentsAgentPlugins
from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import HostRulespec, rulespec_registry
from cmk.gui.valuespec import DropdownChoice
from cmk.utils.rulesets.definition import RuleGroup


def _valuespec_agent_config_hyperv_vms_guestinfos() -> DropdownChoice[bool | None]:
    return DropdownChoice(
        title=_("Hyper-V VM Guest Information (Windows)"),
        help=_(
            "This plug-in provides information about integration services "
            "and checkpoints (snapshots) for each Hyper-V VM guest."
        ),
        choices=[
            (True, _("Deploy plug-in for Hyper-V VM Guest Information")),
            (None, _("Do not deploy plug-in for Hyper-V VM Guest Information")),
        ],
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupMonitoringAgentsAgentPlugins,
        name=RuleGroup.AgentConfig("hyperv_vms_guestinfos"),
        valuespec=_valuespec_agent_config_hyperv_vms_guestinfos,
        is_deprecated=True,
    )
)
