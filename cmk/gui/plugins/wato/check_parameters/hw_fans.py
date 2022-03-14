#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersEnvironment,
)
from cmk.gui.valuespec import Checkbox, Dictionary, Integer, TextInput, Transform, Tuple


def _parameter_valuespec_hw_fans():
    hw_fans_dict = Dictionary(
        elements=[
            (
                "lower",
                Tuple(
                    help=_("Lower levels for the fan speed of a hardware device"),
                    title=_("Lower levels"),
                    elements=[
                        Integer(title=_("warning if below"), unit="rpm"),
                        Integer(title=_("critical if below"), unit="rpm"),
                    ],
                ),
            ),
            (
                "upper",
                Tuple(
                    help=_("Upper levels for the fan speed of a hardware device"),
                    title=_("Upper levels"),
                    elements=[
                        Integer(title=_("warning at"), unit="rpm"),
                        Integer(title=_("critical at"), unit="rpm"),
                    ],
                ),
            ),
            (
                "output_metrics",
                Checkbox(title=_("Performance data"), label=_("Enable performance data")),
            ),
        ],
        optional_keys=["upper", "output_metrics"],
    )
    return Transform(
        valuespec=hw_fans_dict,
        forth=lambda spec: spec if isinstance(spec, dict) else {"lower": spec},
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="hw_fans",
        group=RulespecGroupCheckParametersEnvironment,
        item_spec=lambda: TextInput(title=_("Fan Name"), help=_("The identificator of the fan.")),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_hw_fans,
        title=lambda: _("FAN speed of Hardware devices"),
    )
)
