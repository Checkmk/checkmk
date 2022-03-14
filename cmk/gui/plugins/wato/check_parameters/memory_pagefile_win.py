#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithoutItem,
    PredictiveLevels,
    rulespec_registry,
    RulespecGroupCheckParametersOperatingSystem,
)
from cmk.gui.valuespec import (
    Alternative,
    Dictionary,
    Filesize,
    Integer,
    Percentage,
    Transform,
    Tuple,
)


def _parameter_valuespec_memory_pagefile_win():
    return Dictionary(
        elements=[
            (
                "memory",
                Alternative(
                    title=_("Memory Levels"),
                    elements=[
                        Tuple(
                            title=_("Memory usage in percent"),
                            elements=[
                                Percentage(title=_("Warning at")),
                                Percentage(title=_("Critical at")),
                            ],
                        ),
                        Transform(
                            valuespec=Tuple(
                                title=_("Absolute free memory"),
                                elements=[
                                    Filesize(title=_("Warning if less than")),
                                    Filesize(title=_("Critical if less than")),
                                ],
                            ),
                            # Note: Filesize values lesser 1MB will not work
                            # -> need hide option in filesize valuespec
                            back=lambda x: (x[0] // 1024 // 1024, x[1] // 1024 // 1024),
                            forth=lambda x: (x[0] * 1024 * 1024, x[1] * 1024 * 1024),
                        ),
                        PredictiveLevels(unit=_("GB"), default_difference=(0.5, 1.0)),
                    ],
                    default_value=(80.0, 90.0),
                ),
            ),
            (
                "pagefile",
                Alternative(
                    title=_("Commit charge Levels"),
                    elements=[
                        Tuple(
                            title=_("Commit charge in percent (relative to commit limit)"),
                            elements=[
                                Percentage(title=_("Warning at")),
                                Percentage(title=_("Critical at")),
                            ],
                        ),
                        Transform(
                            valuespec=Tuple(
                                title=_("Absolute commitable memory"),
                                elements=[
                                    Filesize(title=_("Warning if less than")),
                                    Filesize(title=_("Critical if less than")),
                                ],
                            ),
                            # Note: Filesize values lesser 1MB will not work
                            # -> need hide option in filesize valuespec
                            back=lambda x: (x[0] // 1024 // 1024, x[1] // 1024 // 1024),
                            forth=lambda x: (x[0] * 1024 * 1024, x[1] * 1024 * 1024),
                        ),
                        PredictiveLevels(unit=_("GB"), default_difference=(0.5, 1.0)),
                    ],
                    default_value=(80.0, 90.0),
                ),
            ),
            (
                "average",
                Integer(
                    title=_("Averaging"),
                    help=_(
                        "If this parameter is set, all measured values will be averaged "
                        "over the specified time interval before levels are being applied. Per "
                        "default, averaging is turned off. "
                    ),
                    unit=_("minutes"),
                    minvalue=1,
                    default_value=60,
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="memory_pagefile_win",
        group=RulespecGroupCheckParametersOperatingSystem,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_memory_pagefile_win,
        title=lambda: _("Memory levels for Windows"),
    )
)
