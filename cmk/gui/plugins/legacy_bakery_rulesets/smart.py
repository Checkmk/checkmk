#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from typing import Literal

from cmk.gui.agent_bakery import RulespecGroupMonitoringAgentsAgentPlugins
from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import HostRulespec, rulespec_registry
from cmk.gui.valuespec import DropdownChoice, Migrate
from cmk.utils.rulesets.definition import RuleGroup


def _migrate(
    value: Literal["smart_posix", "smart", True] | None,
) -> Literal["smart_posix", "smart"] | None:
    if value is True:
        return "smart"
    return value


def _valuespec_agent_config_smart() -> Migrate[Literal["smart_posix", "smart"] | None]:
    return Migrate(
        migrate=_migrate,
        valuespec=DropdownChoice[Literal["smart_posix", "smart"] | None](
            title=_("SMART hard disk monitoring (Linux)"),
            help=_(
                "Hosts configured via this rule get the <tt>smart_posix</tt> plug-in "
                "deployed. Assuming you have installed <tt>smartmontools</tt>, "
                "your local hard disks will be monitored for temperature and errors. "
                "The legacy plug-in <tt>smart</tt> is deprecated and should not be used anymore. "
            ),
            choices=[
                ("smart_posix", _("Deploy SMART Posix plug-in")),
                ("smart", _("Deploy SMART legacy plug-in")),
                (None, _("Do not deploy SMART plug-in")),
            ],
        ),
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupMonitoringAgentsAgentPlugins,
        name=RuleGroup.AgentConfig("smart"),
        valuespec=_valuespec_agent_config_smart,
    )
)
