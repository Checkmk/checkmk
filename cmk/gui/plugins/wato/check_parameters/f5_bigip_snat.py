#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    Levels,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)
from cmk.gui.valuespec import Dictionary, TextInput


def _parameter_valuespec_f5_bigip_snat():
    return Dictionary(
        elements=[
            (
                "if_in_octets",
                Levels(
                    title=_("Incoming Traffic Maximum"),
                    unit=_("bytes/s"),
                    default_difference=(5, 8),
                    default_value=None,
                ),
            ),
            (
                "if_in_octets_lower",
                Levels(
                    title=_("Incoming Traffic Minimum"),
                    unit=_("bytes/s"),
                    default_difference=(5, 8),
                    default_value=None,
                ),
            ),
            (
                "if_out_octets",
                Levels(
                    title=_("Outgoing Traffic Maximum"),
                    unit=_("bytes/s"),
                    default_difference=(5, 8),
                    default_value=None,
                ),
            ),
            (
                "if_out_octets_lower",
                Levels(
                    title=_("Outgoing Traffic Minimum"),
                    unit=_("bytes/s"),
                    default_difference=(5, 8),
                    default_value=None,
                ),
            ),
            (
                "if_total_octets",
                Levels(
                    title=_("Total Traffic Maximum"),
                    unit=_("bytes/s"),
                    default_difference=(5, 8),
                    default_value=None,
                ),
            ),
            (
                "if_total_octets_lower",
                Levels(
                    title=_("Total Traffic Minimum"),
                    unit=_("bytes/s"),
                    default_difference=(5, 8),
                    default_value=None,
                ),
            ),
            (
                "if_in_pkts",
                Levels(
                    title=_("Incoming Packets Maximum"),
                    unit=_("packets/s"),
                    default_difference=(5, 8),
                    default_value=None,
                ),
            ),
            (
                "if_in_pkts_lower",
                Levels(
                    title=_("Incoming Packets Minimum"),
                    unit=_("packets/s"),
                    default_difference=(5, 8),
                    default_value=None,
                ),
            ),
            (
                "if_out_pkts",
                Levels(
                    title=_("Outgoing Packets Maximum"),
                    unit=_("packets/s"),
                    default_difference=(5, 8),
                    default_value=None,
                ),
            ),
            (
                "if_out_pkts_lower",
                Levels(
                    title=_("Outgoing Packets Minimum"),
                    unit=_("packets/s"),
                    default_difference=(5, 8),
                    default_value=None,
                ),
            ),
            (
                "if_total_pkts",
                Levels(
                    title=_("Total Packets Maximum"),
                    unit=_("packets/s"),
                    default_difference=(5, 8),
                    default_value=None,
                ),
            ),
            (
                "if_total_pkts_lower",
                Levels(
                    title=_("Total Packets Minimum"),
                    unit=_("packets/s"),
                    default_difference=(5, 8),
                    default_value=None,
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="f5_bigip_snat",
        group=RulespecGroupCheckParametersApplications,
        item_spec=lambda: TextInput(title=_("Source NAT Name"), allow_empty=False),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_f5_bigip_snat,
        title=lambda: _("F5 Loadbalancer Source NAT"),
    )
)
