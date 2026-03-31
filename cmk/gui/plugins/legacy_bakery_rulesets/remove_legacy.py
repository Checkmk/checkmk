#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.agent_bakery import RulespecGroupMonitoringAgentsWindowsAgent
from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import HostRulespec, rulespec_registry
from cmk.gui.valuespec import Checkbox
from cmk.utils.rulesets.definition import RuleGroup


def _valuespec_agent_config_remove_legacy() -> Checkbox:
    return Checkbox(
        title=_("Legacy agent management"),
        label=_("Uninstall the legacy (pre 1.6) agent after installation of the new Windows agent"),
        help=_(
            "Enable this option if you want to uninstall the legacy agent "
            "after the new Windows agent have been installed."
        ),
        true_label="Uninstall legacy agent",
        false_label="Retain legacy agent",
        default_value=False,
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupMonitoringAgentsWindowsAgent,
        name=RuleGroup.AgentConfig("remove_legacy"),
        valuespec=_valuespec_agent_config_remove_legacy,
    )
)
