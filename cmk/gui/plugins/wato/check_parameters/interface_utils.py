#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Module to hold shared code for interface check parameter module internals"""

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import PredictiveLevels
from cmk.gui.valuespec import CascadingDropdown, Integer, Percentage, Tuple


def vs_interface_traffic():
    def vs_abs_perc():
        return CascadingDropdown(
            orientation="horizontal",
            choices=[
                (
                    "perc",
                    _("Percentual levels (in relation to port speed)"),
                    Tuple(
                        orientation="float",
                        show_titles=False,
                        elements=[
                            Percentage(label=_("Warning at")),
                            Percentage(label=_("Critical at")),
                        ],
                    ),
                ),
                (
                    "abs",
                    _("Absolute levels in bits or bytes per second"),
                    Tuple(
                        orientation="float",
                        show_titles=False,
                        elements=[
                            Integer(label=_("Warning at")),
                            Integer(label=_("Critical at")),
                        ],
                    ),
                ),
                ("predictive", _("Predictive Levels (only on CMC)"), PredictiveLevels()),
            ],
        )

    return CascadingDropdown(
        orientation="horizontal",
        choices=[
            ("upper", _("Upper"), vs_abs_perc()),
            ("lower", _("Lower"), vs_abs_perc()),
        ],
    )
