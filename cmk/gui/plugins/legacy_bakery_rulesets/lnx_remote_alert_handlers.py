#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.agent_bakery import RulespecGroupMonitoringAgentsLinuxUnixAgent
from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import HostRulespec, rulespec_registry
from cmk.gui.valuespec import Dictionary, ID, ListChoice, SSHKeyPair
from cmk.gui.watolib.user_scripts import user_script_choices
from cmk.utils.rulesets.definition import RuleGroup


def RemoteAlertHandlerChoice(opsys: str) -> ListChoice:
    return ListChoice(
        title=_("Alert handlers to deploy"),
        choices=lambda: user_script_choices("agents/%s/alert_handlers" % opsys),
        allow_empty=False,
    )


def _valuespec_agent_config_lnx_remote_alert_handlers() -> Dictionary:
    return Dictionary(
        title=_("Remote alert handlers (Linux)"),
        help=_(
            "This rule set allows you to install executable scripts on your target machines "
            "that can be called by the Checkmk server via an alert handler. That way "
            "you can for example automatically restart a crashed process or similar things "
            "upon a critical check. The alert handlers are prepared to be called via SSH "
            "with command restriction. The SSH key pair for this is directly created within "
            "each rule. The alert handlers are scripts that need to be put in the directory "
            "<tt>local/share/check_mk/agents/linux/alert_handlers</tt> and made executable."
        ),
        elements=[
            ("handlers", RemoteAlertHandlerChoice("linux")),
            (
                "runas",
                ID(
                    title=_("Linux user to run handlers"),
                    default_value="root",
                    allow_empty=False,
                ),
            ),
            (
                "sshkey",
                SSHKeyPair(
                    title=_("SSH key pair for remote login"),
                ),
            ),
        ],
        optional_keys=False,
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupMonitoringAgentsLinuxUnixAgent,
        match_type="all",
        name=RuleGroup.AgentConfig("lnx_remote_alert_handlers"),
        valuespec=_valuespec_agent_config_lnx_remote_alert_handlers,
    )
)
