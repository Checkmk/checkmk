#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.agent_bakery import RulespecGroupMonitoringAgentsWindowsAgent
from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import HostRulespec, rulespec_registry
from cmk.gui.valuespec import DropdownChoice
from cmk.utils.rulesets.definition import RuleGroup


def _valuespec_agent_config_win_clean_uninstall() -> DropdownChoice[str]:
    return DropdownChoice(
        title=_("Clean up Checkmk agent program data directory on uninstall"),
        label=_("On Checkmk agent uninstallation"),
        help=_(
            "Choose what to do with the files under <tt>%PROGRAMDATA%\\checkmk</tt>:"
            "<ul>"
            "<li><i>Do not remove anything</i>: Leave all files in place after uninstallation.<br>"
            "<li><i>Remove data managed by the Checkmk agent</i>: Remove only files that got"
            " created on Checkmk agent installation. This includes files that came from bakery"
            " plugins, even if they have been edited by a user. Keep runtime files that have been"
            " created after installation, like state files, registration files, and logs."
            "<li><i>Remove all files and subdirectories</i>: Remove all files regardless of their origin."
            "</ul>"
            "<b>Caution</b>: Uninstallation also happens on every agent update!"
            " As a consequence, this rule will break automatic agent updates and TLS encrypted"
            " agent communication on setting <i>Remove all files and subdirectories</i>, since the"
            " removed files also include your agent updater and agent controller registrations."
        ),
        choices=[
            ("none", _("Do not remove anything")),
            ("smart", _("Remove data managed by the Checkmk agent")),
            ("all", _("Remove all files and subdirectories")),
        ],
        default_value="none",
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupMonitoringAgentsWindowsAgent,
        name=RuleGroup.AgentConfig("win_clean_uninstall"),
        valuespec=_valuespec_agent_config_win_clean_uninstall,
    )
)
