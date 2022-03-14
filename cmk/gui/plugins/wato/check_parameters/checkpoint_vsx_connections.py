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
from cmk.gui.valuespec import Dictionary, Integer, Percentage, TextInput, Tuple


def _parameter_valuespec_checkpoint_vsx_connections():
    return Dictionary(
        help=_(
            "This rule allows you to configure the number of maximum "
            "connections for a given VSID."
        ),
        elements=[
            (
                "levels_perc",
                Tuple(
                    title=_("Percentage of maximum available connections"),
                    elements=[
                        Percentage(
                            title=_("Warning at"),
                            # xgettext: no-python-format
                            unit=_("% of maximum connections"),
                        ),
                        Percentage(
                            title=_("Critical at"),
                            # xgettext: no-python-format
                            unit=_("% of maximum connections"),
                        ),
                    ],
                ),
            ),
            (
                "levels_abs",
                Tuple(
                    title=_("Absolute number of connections"),
                    elements=[
                        Integer(title=_("Warning at"), minvalue=0, unit=_("connections")),
                        Integer(title=_("Critical at"), minvalue=0, unit=_("connections")),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="checkpoint_vsx_connections",
        group=RulespecGroupCheckParametersNetworking,
        item_spec=lambda: TextInput(title=_("VSID")),
        parameter_valuespec=_parameter_valuespec_checkpoint_vsx_connections,
        title=lambda: _("Checkpoint VSID connections"),
    )
)
