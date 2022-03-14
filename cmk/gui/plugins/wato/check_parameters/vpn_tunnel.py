#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersNetworking,
)
from cmk.gui.valuespec import Dictionary, IPv4Address, ListOf, MonitoringState, TextInput, Tuple


def _parameter_valuespec_vpn_tunnel():
    return Dictionary(
        elements=[
            (
                "tunnels",
                ListOf(
                    valuespec=Tuple(
                        title=("VPN Tunnel Endpoints"),
                        elements=[
                            IPv4Address(
                                title=_("IP-Address or Name of Tunnel Endpoint"),
                                help=_(
                                    "The configured value must match a tunnel reported by the monitored "
                                    "device."
                                ),
                            ),
                            TextInput(
                                title=_("Tunnel Alias"),
                                help=_(
                                    "You can configure an individual alias here for the tunnel matching "
                                    "the IP-Address or Name configured in the field above."
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
                    title=_("Default state to report when tunnel can not be found anymore"),
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
        item_spec=lambda: TextInput(title=_("IP-Address of Tunnel Endpoint")),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_vpn_tunnel,
        title=lambda: _("VPN Tunnel"),
    )
)
