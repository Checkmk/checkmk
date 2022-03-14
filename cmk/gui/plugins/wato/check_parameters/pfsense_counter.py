#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)
from cmk.gui.valuespec import Dictionary, Float, Integer, Tuple


def _parameter_valuespec_pfsense_counter():
    return Dictionary(
        help=_("This rule set is for configuring levels for global packet counters."),
        elements=[
            (
                "average",
                Integer(
                    title=_("Averaging"),
                    help=_(
                        "When this option is activated then the packet rates are being "
                        "averaged <b>before</b> the levels are being applied. Setting this to zero will "
                        "deactivate averaging."
                    ),
                    unit=_("minutes"),
                    default_value=3,
                    minvalue=1,
                    label=_("Compute average over last "),
                ),
            ),
            (
                "fragment",
                Tuple(
                    title=_("Levels for rate of fragmented packets"),
                    elements=[
                        Float(title=_("Warning at"), unit=_("pkts/s"), default_value=100.0),
                        Float(title=_("Critical at"), unit=_("pkts/s"), default_value=10000.0),
                    ],
                ),
            ),
            (
                "normalized",
                Tuple(
                    title=_("Levels for rate of normalized packets"),
                    elements=[
                        Float(title=_("Warning at"), unit=_("pkts/s"), default_value=100.0),
                        Float(title=_("Critical at"), unit=_("pkts/s"), default_value=10000.0),
                    ],
                ),
            ),
            (
                "badoffset",
                Tuple(
                    title=_("Levels for rate of packets with bad offset"),
                    elements=[
                        Float(title=_("Warning at"), unit=_("pkts/s"), default_value=100.0),
                        Float(title=_("Critical at"), unit=_("pkts/s"), default_value=10000.0),
                    ],
                ),
            ),
            (
                "short",
                Tuple(
                    title=_("Levels for rate of short packets"),
                    elements=[
                        Float(title=_("Warning at"), unit=_("pkts/s"), default_value=100.0),
                        Float(title=_("Critical at"), unit=_("pkts/s"), default_value=10000.0),
                    ],
                ),
            ),
            (
                "memdrop",
                Tuple(
                    title=_("Levels for rate of packets dropped due to memory limitations"),
                    elements=[
                        Float(title=_("Warning at"), unit=_("pkts/s"), default_value=100.0),
                        Float(title=_("Critical at"), unit=_("pkts/s"), default_value=10000.0),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="pfsense_counter",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_pfsense_counter,
        title=lambda: _("pfSense Firewall Packet Rates"),
    )
)
