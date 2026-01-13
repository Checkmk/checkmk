#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersNetworking,
)
from cmk.gui.valuespec import Dictionary, IPv4Address, ListOf, MonitoringState, TextInput, Tuple


def _parameter_valuespec_vpn_tunnel() -> Dictionary:
    return Dictionary(
        elements=[
            (
                "tunnels",
                ListOf(
                    valuespec=Tuple(
                        title=("VPN tunnel endpoints"),
                        elements=[
                            IPv4Address(
                                title=_("IP address or name of tunnel endpoint"),
                                help=_(
                                    "The configured value must match a tunnel reported by the monitored "
                                    "device."
                                ),
                            ),
                            TextInput(
                                title=_("Tunnel alias"),
                                help=_(
                                    "You can configure an individual alias here for the tunnel matching "
                                    "the IP address or name configured in the field above."
                                ),
                            ),
                            MonitoringState(
                                default_value=2,
                                title=_("State if tunnel is not found"),
                            ),
                        ],
                    ),
                    add_label=_("Add tunnel"),
                    movable=False,
                    title=_("VPN tunnel specific configuration"),
                ),
            ),
            (
                "state",
                MonitoringState(
                    title=_("Default state to report when tunnel cannot be found anymore"),
                    help=_(
                        "Default state if a tunnel, which is not listed above in this rule, "
                        "can no longer be found."
                    ),
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="vpn_tunnel",
        group=RulespecGroupCheckParametersNetworking,
        item_spec=lambda: TextInput(title=_("IP address of tunnel endpoint")),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_vpn_tunnel,
        title=lambda: _("VPN tunnel"),
    )
)
