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
from cmk.gui.valuespec import Dictionary, Integer, TextInput


def _item_spec_firewall_if():
    return TextInput(
        title=_("Interface"),
        help=_("The description of the interface as provided by the device"),
    )


def _parameter_valuespec_firewall_if():
    return Dictionary(
        elements=[
            (
                "ipv4_in_blocked",
                Levels(
                    title=_("Levels for rate of incoming IPv4 packets blocked"),
                    unit=_("pkts/s"),
                    default_levels=(100.0, 10000.0),
                    default_difference=(5, 8),
                    default_value=None,
                ),
            ),
            (
                "average",
                Integer(
                    title=_("Averaging"),
                    help=_(
                        "When this option is activated then the block rate is being "
                        "averaged <b>before</b> the levels are being applied."
                    ),
                    unit=_("minutes"),
                    default_value=3,
                    minvalue=1,
                    label=_("Compute average over last "),
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="firewall_if",
        group=RulespecGroupCheckParametersApplications,
        item_spec=_item_spec_firewall_if,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_firewall_if,
        title=lambda: _("Firewall Interfaces"),
    )
)
