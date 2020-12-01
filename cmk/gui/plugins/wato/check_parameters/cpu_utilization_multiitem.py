#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.valuespec import (
    Transform,
    Dictionary,
    Integer,
    Percentage,
    TextAscii,
    Tuple,
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersOperatingSystem,
)


def _parameter_valuespec_cpu_utilization_multiitem():
    return Transform(
        Dictionary(
            help=_("The CPU utilization sums up the percentages of CPU time that is used "
                   "for user processes and kernel routines over all available cores within "
                   "the last check interval. The possible range is from 0% to 100%"),
            elements=[
                ("levels",
                 Tuple(
                     title=_("Alert on too high CPU utilization"),
                     elements=[
                         Percentage(title=_("Warning at a utilization of"), default_value=90.0),
                         Percentage(title=_("Critical at a utilization of"), default_value=95.0),
                     ],
                 )),
                ("average",
                 Integer(
                     title=_("Averaging"),
                     help=_("Average the CPU utilization over the specified time period "
                            "before levels are applied."),
                     unit=_("minutes"),
                     minvalue=1,
                     default_value=15,
                     label=_("Compute average over last "),
                 )),
            ],
        ),
        forth=transform_valuespec_cpu_utilization_multiitem,
    )


def transform_valuespec_cpu_utilization_multiitem(read_params):
    return read_params if isinstance(read_params, dict) else {"levels": read_params}


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="cpu_utilization_multiitem",
        group=RulespecGroupCheckParametersOperatingSystem,
        item_spec=lambda: TextAscii(title=_("Module name"), allow_empty=False),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_cpu_utilization_multiitem,
        title=lambda: _("CPU utilization of Devices with Modules"),
    ))
