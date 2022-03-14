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
from cmk.gui.valuespec import Dictionary, Float, TextInput, Tuple


def _parameter_valuespec_docsis_channels_downstream():
    return Dictionary(
        elements=[
            (
                "power",
                Tuple(
                    title=_("Transmit Power"),
                    help=_("The operational transmit power"),
                    elements=[
                        Float(title=_("warning at or below"), unit="dBmV", default_value=5.0),
                        Float(title=_("critical at or below"), unit="dBmV", default_value=1.0),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="docsis_channels_downstream",
        group=RulespecGroupCheckParametersNetworking,
        item_spec=lambda: TextInput(title=_("ID of the channel (usually ranging from 1)")),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_docsis_channels_downstream,
        title=lambda: _("Docsis Downstream Channels"),
    )
)
