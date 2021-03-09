#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Check_MK.
# The official homepage is at http://mathias-kettner.de/check_mk.
#
# check_mk is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# tails. You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

from cmk.gui.i18n import _
from cmk.gui.valuespec import (
    Alternative,
    Dictionary,
    Filesize,
    Integer,
    Percentage,
    Transform,
    Tuple,
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    PredictiveLevels,
    RulespecGroupCheckParametersOperatingSystem,
)


def _parameter_valuespec_memory_pagefile_win():
    return Dictionary(
        elements=[
            (
                "memory",
                Alternative(
                    title=_("Memory Levels"),
                    style="dropdown",
                    elements=[
                        Tuple(
                            title=_("Memory usage in percent"),
                            elements=[
                                Percentage(title=_("Warning at")),
                                Percentage(title=_("Critical at")),
                            ],
                        ),
                        Transform(
                            Tuple(
                                title=_("Absolute free memory"),
                                elements=[
                                    Filesize(title=_("Warning if less than")),
                                    Filesize(title=_("Critical if less than")),
                                ],
                            ),
                            # Note: Filesize values lesser 1MB will not work
                            # -> need hide option in filesize valuespec
                            back=lambda x: (x[0] / 1024 / 1024, x[1] / 1024 / 1024),
                            forth=lambda x: (x[0] * 1024 * 1024, x[1] * 1024 * 1024)),
                        PredictiveLevels(unit=_("GB"), default_difference=(0.5, 1.0))
                    ],
                    default_value=(80.0, 90.0))),
            (
                "pagefile",
                Alternative(
                    title=_("Commit charge Levels"),
                    style="dropdown",
                    elements=[
                        Tuple(
                            title=_("Commit charge in percent (relative to commit limit)"),
                            elements=[
                                Percentage(title=_("Warning at")),
                                Percentage(title=_("Critical at")),
                            ],
                        ),
                        Transform(
                            Tuple(
                                title=_("Absolute commitable memory"),
                                elements=[
                                    Filesize(title=_("Warning if less than")),
                                    Filesize(title=_("Critical if less than")),
                                ],
                            ),
                            # Note: Filesize values lesser 1MB will not work
                            # -> need hide option in filesize valuespec
                            back=lambda x: (x[0] / 1024 / 1024, x[1] / 1024 / 1024),
                            forth=lambda x: (x[0] * 1024 * 1024, x[1] * 1024 * 1024)),
                        PredictiveLevels(unit=_("GB"), default_difference=(0.5, 1.0))
                    ],
                    default_value=(80.0, 90.0))),
            ("average",
             Integer(
                 title=_("Averaging"),
                 help=_("If this parameter is set, all measured values will be averaged "
                        "over the specified time interval before levels are being applied. Per "
                        "default, averaging is turned off. "),
                 unit=_("minutes"),
                 minvalue=1,
                 default_value=60,
             )),
        ],)


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="memory_pagefile_win",
        group=RulespecGroupCheckParametersOperatingSystem,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_memory_pagefile_win,
        title=lambda: _("Memory levels for Windows"),
    ))
