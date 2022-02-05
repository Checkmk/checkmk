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
from cmk.gui.valuespec import Dictionary, Integer, Percentage, Tuple


def _parameter_valuespec_pulse_secure_users():
    return Dictionary(
        title=_("Number of signed-in web users"),
        elements=[
            (
                "upper_number_of_users",
                Tuple(
                    elements=[
                        Integer(title=_("warning at")),
                        Integer(title=_("critical at")),
                    ],
                ),
            )
        ],
        optional_keys=False,
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="pulse_secure_users",
        group=RulespecGroupCheckParametersApplications,
        parameter_valuespec=_parameter_valuespec_pulse_secure_users,
        title=lambda: _("Pulse Secure users"),
    )
)


def _parameter_valuespec_pulse_secure_disk_util():
    return Dictionary(
        title=_("Upper levels for disk utilization"),
        elements=[
            (
                "upper_levels",
                Tuple(
                    elements=[
                        Percentage(title=_("warning at"), allow_int=True, default_value=80),
                        Percentage(title=_("critical at"), allow_int=True, default_value=90),
                    ],
                ),
            )
        ],
        optional_keys=False,
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="pulse_secure_disk_util",
        group=RulespecGroupCheckParametersApplications,
        parameter_valuespec=_parameter_valuespec_pulse_secure_disk_util,
        title=lambda: _("Pulse Secure disk utilization"),
    )
)


def _parameter_valuespec_pulse_secure_mem_util():
    return Dictionary(
        elements=[
            (
                "mem_used_percent",
                Tuple(
                    title=_("Upper levels for IVE RAM utilization"),
                    elements=[
                        Percentage(title=_("warning at"), allow_int=True, default_value=80),
                        Percentage(title=_("critical at"), allow_int=True, default_value=90),
                    ],
                ),
            ),
            (
                "swap_used_percent",
                Tuple(
                    title=_("Upper levels for IVE swap utilization"),
                    elements=[
                        Percentage(title=_("warning at"), allow_int=True, default_value=80),
                        Percentage(title=_("critical at"), allow_int=True, default_value=90),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="pulse_secure_mem_util",
        group=RulespecGroupCheckParametersApplications,
        parameter_valuespec=_parameter_valuespec_pulse_secure_mem_util,
        title=lambda: _("Pulse Secure IVE memory utilization"),
    )
)
