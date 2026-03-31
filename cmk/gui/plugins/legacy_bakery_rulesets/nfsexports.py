#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.agent_bakery import RulespecGroupMonitoringAgentsAgentPlugins
from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import HostRulespec, rulespec_registry
from cmk.gui.valuespec import DropdownChoice
from cmk.utils.rulesets.definition import RuleGroup


def _valuespec_agent_config_nfsexports() -> DropdownChoice[bool | None]:
    return DropdownChoice(
        title=_("NFS4 exports (Linux, Solaris)"),
        help=_("This plug-in monitors the NFS version 4 exports of a Linux host."),
        choices=[
            (True, _("Deploy NFS4 exports plug-in")),
            (None, _("Do not deploy NFS4 exports plug-in")),
        ],
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupMonitoringAgentsAgentPlugins,
        name=RuleGroup.AgentConfig("nfsexports"),
        valuespec=_valuespec_agent_config_nfsexports,
    )
)
