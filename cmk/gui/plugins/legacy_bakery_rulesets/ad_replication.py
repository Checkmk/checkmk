#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.agent_bakery import RulespecGroupMonitoringAgentsAgentPlugins
from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import HostRulespec, rulespec_registry
from cmk.gui.valuespec import DropdownChoice
from cmk.utils.rulesets.definition import RuleGroup


def _valuespec_agent_config_ad_replication() -> DropdownChoice[bool]:
    return DropdownChoice(
        title=_("Active Directory Replication (Windows)"),
        help=_(
            "This plug-in checks the replication of Active Directory. "
            "To be able to run this check you need appropriate credentials "
            "in the target domain. Normally the Checkmk agent runs as service "
            "with local system credentials which are not sufficient for this check. "
            "To solve this problem you can, e.g., change the account the service "
            "is being started with to a domain user account with enough "
            "permissions on the DC."
        ),
        choices=[
            (True, _("Deploy AD-Replication plug-in")),
            (None, _("Do not deploy AD-Replication plug-in")),
        ],
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupMonitoringAgentsAgentPlugins,
        name=RuleGroup.AgentConfig("ad_replication"),
        valuespec=_valuespec_agent_config_ad_replication,
    )
)
