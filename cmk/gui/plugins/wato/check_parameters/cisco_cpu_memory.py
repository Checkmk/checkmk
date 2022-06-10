#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.check_parameters.filesystem_utils import match_dual_level_type
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersOperatingSystem,
)
from cmk.gui.valuespec import Alternative, Dictionary, Integer, Percentage, Transform, Tuple


def _parameter_valuespec_memory():
    return Dictionary(
        elements=[
            (
                "levels",
                Alternative(
                    title=_("Levels for Cisco CPU memory"),
                    help=_(
                        "The performance graph will always display the occupied memory. "
                        "This is independent of the actual check levels which can be set "
                        "for both free and occupied memory levels."
                    ),
                    default_value=(150.0, 200.0),
                    match=match_dual_level_type,
                    elements=[
                        Alternative(
                            title=_("Levels for occupied memory"),
                            help=_(
                                "Specify the threshold levels for the occupied memory. The occupied memory "
                                "consists of used and kernel reserved memory."
                            ),
                            elements=[
                                Tuple(
                                    title=_("Specify levels in percentage of total RAM"),
                                    elements=[
                                        Percentage(title=_("Warning at a usage of"), maxvalue=None),
                                        Percentage(
                                            title=_("Critical at a usage of"), maxvalue=None
                                        ),
                                    ],
                                ),
                                Tuple(
                                    title=_("Specify levels in absolute values"),
                                    elements=[
                                        Integer(title=_("Warning at"), unit=_("MB")),
                                        Integer(title=_("Critical at"), unit=_("MB")),
                                    ],
                                ),
                            ],
                        ),
                        Transform(
                            valuespec=Alternative(
                                elements=[
                                    Tuple(
                                        title=_("Specify levels in percentage of total RAM"),
                                        elements=[
                                            Percentage(
                                                title=_("Warning if less than"),
                                                maxvalue=None,
                                            ),
                                            Percentage(
                                                title=_("Critical if less than"),
                                                maxvalue=None,
                                            ),
                                        ],
                                    ),
                                    Tuple(
                                        title=_("Specify levels in absolute values"),
                                        elements=[
                                            Integer(title=_("Warning if below"), unit=_("MB")),
                                            Integer(title=_("Critical if below"), unit=_("MB")),
                                        ],
                                    ),
                                ],
                            ),
                            title=_("Levels for free memory"),
                            help=_(
                                "Specify the threshold levels for the free memory space. The free memory "
                                "excludes the reserved kernel memory."
                            ),
                            forth=lambda val: tuple(-x for x in val),
                            back=lambda val: tuple(-x for x in val),
                        ),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="cisco_cpu_memory",
        group=RulespecGroupCheckParametersOperatingSystem,
        parameter_valuespec=_parameter_valuespec_memory,
        title=lambda: _("Cisco CPU Memory"),
    )
)
