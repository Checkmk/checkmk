#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.check_parameters.utils import match_dual_level_type
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersOperatingSystem,
)
from cmk.gui.valuespec import Alternative, Dictionary, Integer, Percentage, Transform, Tuple


# if you refactor this: grep for "DualMemoryLevels"
def _parameter_valuespec_memory():
    return Transform(
        valuespec=Dictionary(
            elements=[
                (
                    "levels",
                    Alternative(
                        title=_("Levels for memory"),
                        show_alternative_title=True,
                        default_value=(150.0, 200.0),
                        match=match_dual_level_type,
                        help=_(
                            "The used and free levels for the memory on UNIX systems take into account the "
                            "currently used memory (RAM or Swap) by all processes and sets this in relation "
                            "to the total RAM of the system. This means that the memory usage can exceed 100%. "
                            "A usage of 200% means that the total size of all processes is twice as large as "
                            "the main memory, so <b>at least</b> half of it is currently swapped out. For systems "
                            "without Swap space you should choose levels below 100%."
                        ),
                        elements=[
                            Alternative(
                                title=_("Levels for used memory"),
                                elements=[
                                    Tuple(
                                        title=_("Specify levels in percentage of total RAM"),
                                        elements=[
                                            Percentage(
                                                title=_("Warning at a usage of"), maxvalue=None
                                            ),
                                            Percentage(
                                                title=_("Critical at a usage of"), maxvalue=None
                                            ),
                                        ],
                                    ),
                                    Tuple(
                                        title=_("Specify levels in absolute values"),
                                        elements=[
                                            Integer(title=_("Warning at"), unit=_("MiB")),
                                            Integer(title=_("Critical at"), unit=_("MiB")),
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
                                                Integer(title=_("Warning if below"), unit=_("MiB")),
                                                Integer(
                                                    title=_("Critical if below"), unit=_("MiB")
                                                ),
                                            ],
                                        ),
                                    ],
                                ),
                                title=_("Levels for free memory"),
                                help=
                                # xgettext: no-python-format
                                _(
                                    "Keep in mind that if you have 1GB RAM and 1GB Swap you need to "
                                    "specify 120% or 1200MB to get an alert if there is only 20% free RAM available. "
                                    "The free memory levels do not work with the fortigate check, because it does "
                                    "not provide total memory data."
                                ),
                                forth=lambda val: tuple(-x for x in val),
                                back=lambda val: tuple(-x for x in val),
                            ),
                        ],
                    ),
                ),
                (
                    "average",
                    Integer(
                        title=_("Averaging"),
                        help=_(
                            "If this parameter is set, all measured values will be averaged "
                            "over the specified time interval before levels are being applied. Per "
                            "default, averaging is turned off."
                        ),
                        unit=_("minutes"),
                        minvalue=1,
                        default_value=60,
                    ),
                ),
            ],
            optional_keys=["average"],
        ),
        forth=lambda t: isinstance(t, tuple) and {"levels": t} or t,
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="memory",
        group=RulespecGroupCheckParametersOperatingSystem,
        parameter_valuespec=_parameter_valuespec_memory,
        title=lambda: _("Main memory usage (UNIX / Other Devices)"),
    )
)
