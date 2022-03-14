#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersOperatingSystem,
)
from cmk.gui.valuespec import CascadingDropdown, Dictionary, Filesize, Percentage, Tuple

# Beware: This is not yet implemented in the check.
# def PredictiveMemoryChoice(what):
#     return ( "predictive", _("Predictive levels for %s") % what,
#         PredictiveLevels(
#            unit = _("GB"),
#            default_difference = (0.5, 1.0)
#     ))


def UsedSize() -> Tuple:
    GB = 1024 * 1024 * 1024
    return Tuple(
        elements=[
            Filesize(title=_("Warning at"), default_value=1 * GB),
            Filesize(title=_("Critical at"), default_value=2 * GB),
        ]
    )


def FreeSize() -> Tuple:
    GB = 1024 * 1024 * 1024
    return Tuple(
        elements=[
            Filesize(title=_("Warning below"), default_value=2 * GB),
            Filesize(title=_("Critical below"), default_value=1 * GB),
        ]
    )


def UsedPercentage(default_percents=None, of_what=None):
    if of_what:
        unit = _("%% of %s") % of_what
        maxvalue = None
    else:
        unit = "%"
        maxvalue = 101.0
    return Tuple(
        elements=[
            Percentage(
                title=_("Warning at"),
                default_value=default_percents and default_percents[0] or 80.0,
                unit=unit,
                maxvalue=maxvalue,
            ),
            Percentage(
                title=_("Critical at"),
                default_value=default_percents and default_percents[1] or 90.0,
                unit=unit,
                maxvalue=maxvalue,
            ),
        ]
    )


def FreePercentage(default_percents=None, of_what=None):
    if of_what:
        unit = _("%% of %s") % of_what
    else:
        unit = "%"
    return Tuple(
        elements=[
            Percentage(
                title=_("Warning below"),
                default_value=default_percents and default_percents[0] or 20.0,
                unit=unit,
            ),
            Percentage(
                title=_("Critical below"),
                default_value=default_percents and default_percents[1] or 10.0,
                unit=unit,
            ),
        ]
    )


def DualMemoryLevels(what, default_percents=None):
    return CascadingDropdown(
        title=_("Levels for %s") % what,
        choices=[
            (
                "perc_used",
                _("Percentual levels for used %s") % what,
                UsedPercentage(default_percents),
            ),
            ("perc_free", _("Percentual levels for free %s") % what, FreePercentage()),
            ("abs_used", _("Absolute levels for used %s") % what, UsedSize()),
            ("abs_free", _("Absolute levels for free %s") % what, FreeSize()),
            # PredictiveMemoryChoice(_("used %s") % what), # not yet implemented
            ("ignore", _("Do not impose levels")),
        ],
    )


def _parameter_valuespec_memory_arbor():
    return Dictionary(
        elements=[
            ("levels_ram", DualMemoryLevels(_("RAM"))),
            ("levels_swap", DualMemoryLevels(_("Swap"))),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="memory_arbor",
        group=RulespecGroupCheckParametersOperatingSystem,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_memory_arbor,
        title=lambda: _("Memory and Swap usage on Arbor devices"),
    )
)
