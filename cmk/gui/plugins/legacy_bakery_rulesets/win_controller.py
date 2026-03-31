#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.agent_bakery import RulespecGroupMonitoringAgentsWindowsAgent
from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import HostRulespec, rulespec_registry
from cmk.gui.valuespec import CascadingDropdown, Checkbox, Dictionary, FixedValue, NetworkPort
from cmk.utils.rulesets.definition import RuleGroup


def _valuespec_agent_config_win_controller() -> Dictionary:
    return Dictionary(
        title=_("Windows Agent Controller troubleshooting"),
        elements=[
            (
                "check_controller_access",
                Checkbox(
                    title=_("Limit local agent data access to the Agent Controller"),
                    label=_("Protect agent data from unauthorized access"),
                    help=_(
                        "This is a security feature to prevent unauthorized local access to agent data. "
                        "You may disable this flag in case of an emergency. For example, if the "
                        "agent can't reliably determine the Agent Controller as a valid peer which "
                        "tries to access the data. "
                    ),
                    default_value=True,
                ),
            ),
            (
                "force_legacy",
                Checkbox(
                    title=_("Allow unencrypted legacy communication"),
                    label=_("Always allow to use unencrypted (legacy) communication as fallback"),
                    help=_(
                        "If the flag is set, then the Windows agent may use "
                        "unencrypted communication between the monitoring site and the host. "
                        "Enable this flag for compatibility reasons or if you experience "
                        "problems with the controller related to TLS or encryption. But please "
                        "pay attention, that this enables unencrypted communication if your "
                        "controller connection isn't properly configured."
                    ),
                    default_value=False,
                ),
            ),
            (
                "agent_channel",
                CascadingDropdown(
                    title=_("Internal agent communication channel"),
                    help=_(
                        "Configure the local communication channel between the Windows agent and "
                        "the Agent Controller. By default, a mailslot is used. If you encounter "
                        "problems with mailslot communication in your environment, you can switch "
                        "to a TCP socket on localhost instead.<br> "
                        "<b>Note:</b> We highly recomment to leave this option untouched unless you "
                        "encounter problems with the default configuration."
                    ),
                    choices=[
                        (
                            "mailslot",
                            _("Mailslot"),
                            FixedValue(value=None, totext=""),
                        ),
                        (
                            "tcp",
                            _("TCP socket on localhost"),
                            NetworkPort(
                                title=_("Port"),
                                default_value=28250,
                            ),
                        ),
                    ],
                    default_value=("mailslot", None),
                    sorted=False,
                ),
            ),
        ],
        optional_keys=["agent_channel"],
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupMonitoringAgentsWindowsAgent,
        name=RuleGroup.AgentConfig("win_controller"),
        valuespec=_valuespec_agent_config_win_controller,
    )
)
