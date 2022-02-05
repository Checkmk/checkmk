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
from cmk.gui.valuespec import Dictionary, Float, Percentage, TextInput, Tuple


def _parameter_valuespec_docsis_channels_upstream():
    return Dictionary(
        elements=[
            (
                "signal_noise",
                Tuple(
                    title=_("Levels for signal/noise ratio"),
                    elements=[
                        Float(title=_("Warning at or below"), unit="dB", default_value=10.0),
                        Float(title=_("Critical at or below"), unit="dB", default_value=5.0),
                    ],
                ),
            ),
            (
                "correcteds",
                Tuple(
                    title=_("Levels for rate of corrected errors"),
                    elements=[
                        Percentage(title=_("Warning at"), default_value=5.0),
                        Percentage(title=_("Critical at"), default_value=8.0),
                    ],
                ),
            ),
            (
                "uncorrectables",
                Tuple(
                    title=_("Levels for rate of uncorrectable errors"),
                    elements=[
                        Percentage(title=_("Warning at"), default_value=1.0),
                        Percentage(title=_("Critical at"), default_value=2.0),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="docsis_channels_upstream",
        group=RulespecGroupCheckParametersNetworking,
        item_spec=lambda: TextInput(title=_("ID of the channel (usually ranging from 1)")),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_docsis_channels_upstream,
        title=lambda: _("Docsis Upstream Channels"),
    )
)
