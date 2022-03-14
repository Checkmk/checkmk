#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Literal, Mapping

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithoutItem,
    Levels,
    rulespec_registry,
    RulespecGroupCheckParametersOperatingSystem,
)
from cmk.gui.valuespec import Dictionary, Transform


def _forth(p: object) -> Mapping[Literal["levels"], object]:
    return p if isinstance(p, dict) and list(p) == ["levels"] else {"levels": p}


def _parameter_valuespec_cpu_load():
    return Transform(
        valuespec=Dictionary(
            elements=[
                (
                    "levels",
                    Levels(
                        title=_("Levels on CPU load"),
                        help=_(
                            "The CPU load of a system is the number of processes currently being "
                            "in the state <u>running</u>, i.e. either they occupy a CPU or wait "
                            "for one. The <u>load average</u> is the averaged CPU load over the last 1, "
                            "5 or 15 minutes. The following levels will be applied on the average "
                            "load. On Linux system the 15-minute average load is used when applying "
                            "those levels. The configured levels are multiplied with the number of "
                            "CPUs, so you should configure the levels based on the value you want to "
                            'be warned "per CPU".'
                        ),
                        unit="per core",
                        default_difference=(2.0, 4.0),
                        default_levels=(5.0, 10.0),
                    ),
                )
            ],
            optional_keys=False,
        ),
        forth=_forth,
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="cpu_load",
        group=RulespecGroupCheckParametersOperatingSystem,
        parameter_valuespec=_parameter_valuespec_cpu_load,
        title=lambda: _("CPU load (not utilization!)"),
    )
)
