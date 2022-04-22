#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersStorage,
)
from cmk.gui.valuespec import Dictionary, Integer, Percentage, Transform, Tuple


def _parameter_valuespec_netapp_disks():
    return Transform(
        valuespec=Dictionary(
            elements=[
                (
                    "failed_spare_ratio",
                    Tuple(
                        title=_("Failed to spare ratio"),
                        help=_(
                            "You can set a limit to the failed to spare disk ratio. "
                            "The ratio is calculated with <i>failed / (failed + spare)</i>."
                        ),
                        elements=[
                            Percentage(title=_("Warning at or above"), default_value=1.0),
                            Percentage(title=_("Critical at or above"), default_value=50.0),
                        ],
                    ),
                ),
                (
                    "offline_spare_ratio",
                    Tuple(
                        title=_("Offline to spare ratio"),
                        help=_(
                            "You can set a limit to the offline to spare disk ratio. "
                            "The ratio is calculated with <i>offline / (offline + spare)</i>."
                        ),
                        elements=[
                            Percentage(title=_("Warning at or above"), default_value=1.0),
                            Percentage(title=_("Critical at or above"), default_value=50.0),
                        ],
                    ),
                ),
                (
                    "number_of_spare_disks",
                    Tuple(
                        title=_("Number of spare disks"),
                        help=_("You can set a lower limit to the absolute number of spare disks."),
                        elements=[
                            Integer(title=_("Warning below"), default_value=2, minvalue=0),
                            Integer(title=_("Critical below"), default_value=1, minvalue=0),
                        ],
                    ),
                ),
            ],
        ),
        forth=lambda a: "broken_spare_ratio" in a
        and {"failed_spare_ratio": a["broken_spare_ratio"]}
        or a,
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="netapp_disks",
        group=RulespecGroupCheckParametersStorage,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_netapp_disks,
        title=lambda: _("Filer Disk Levels (NetApp, IBM SVC)"),
    )
)
