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
from cmk.gui.valuespec import Dictionary, Integer, TextInput, Tuple


def _item_spec_cisco_vpn_sessions():
    return TextInput(
        title=_("Session type"),
        help=_(
            "Type of the VPN connection, either 'IPsec RA', 'IPsec L2L', 'AnyConnect SVC', "
            "'WebVPN' or 'Summary'. The last item refers to the overall number of sessions "
            "(summed over all session types)."
        ),
        allow_empty=False,
    )


def _parameter_valuespec_asa_svc_sessions():
    return Dictionary(
        title=_("Number of active sessions"),
        elements=[
            (
                "active_sessions",
                Tuple(
                    title="Active sessions",
                    elements=[
                        Integer(
                            title=_("Warning at"),
                            unit=_("sessions"),
                        ),
                        Integer(
                            title=_("Critical at"),
                            unit=_("sessions"),
                        ),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="cisco_vpn_sessions",
        group=RulespecGroupCheckParametersNetworking,
        item_spec=_item_spec_cisco_vpn_sessions,
        parameter_valuespec=_parameter_valuespec_asa_svc_sessions,
        title=lambda: _("Cisco VPN Sessions"),
    )
)
