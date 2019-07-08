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
    CascadingDropdown,
    Dictionary,
    Filesize,
    Percentage,
    Tuple,
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersOperatingSystem,
)

# Beware: This is not yet implemented in the check.
# def PredictiveMemoryChoice(what):
#     return ( "predictive", _("Predictive levels for %s") % what,
#         PredictiveLevels(
#            unit = _("GB"),
#            default_difference = (0.5, 1.0)
#     ))


def UsedSize(**args):
    GB = 1024 * 1024 * 1024
    return Tuple(elements=[
        Filesize(title=_("Warning at"), default_value=1 * GB),
        Filesize(title=_("Critical at"), default_value=2 * GB),
    ],
                 **args)


def FreeSize(**args):
    GB = 1024 * 1024 * 1024
    return Tuple(elements=[
        Filesize(title=_("Warning below"), default_value=2 * GB),
        Filesize(title=_("Critical below"), default_value=1 * GB),
    ],
                 **args)


def UsedPercentage(default_percents=None, of_what=None):
    if of_what:
        unit = _("%% of %s") % of_what
        maxvalue = None
    else:
        unit = "%"
        maxvalue = 101.0
    return Tuple(elements=[
        Percentage(
            title=_("Warning at"),
            default_value=default_percents and default_percents[0] or 80.0,
            unit=unit,
            maxvalue=maxvalue,
        ),
        Percentage(title=_("Critical at"),
                   default_value=default_percents and default_percents[1] or 90.0,
                   unit=unit,
                   maxvalue=maxvalue),
    ])


def FreePercentage(default_percents=None, of_what=None):
    if of_what:
        unit = _("%% of %s") % of_what
    else:
        unit = "%"
    return Tuple(elements=[
        Percentage(title=_("Warning below"),
                   default_value=default_percents and default_percents[0] or 20.0,
                   unit=unit),
        Percentage(title=_("Critical below"),
                   default_value=default_percents and default_percents[1] or 10.0,
                   unit=unit),
    ])


def DualMemoryLevels(what, default_percents=None):
    return CascadingDropdown(
        title=_("Levels for %s") % what,
        choices=[
            ("perc_used", _("Percentual levels for used %s") % what,
             UsedPercentage(default_percents)),
            ("perc_free", _("Percentual levels for free %s") % what, FreePercentage()),
            ("abs_used", _("Absolute levels for used %s") % what, UsedSize()),
            ("abs_free", _("Absolute levels for free %s") % what, FreeSize()),
            # PredictiveMemoryChoice(_("used %s") % what), # not yet implemented
            ("ignore", _("Do not impose levels")),
        ])


@rulespec_registry.register
class RulespecCheckgroupParametersMemoryArbor(CheckParameterRulespecWithoutItem):
    @property
    def group(self):
        return RulespecGroupCheckParametersOperatingSystem

    @property
    def check_group_name(self):
        return "memory_arbor"

    @property
    def title(self):
        return _("Memory and Swap usage on Arbor devices")

    @property
    def match_type(self):
        return "dict"

    @property
    def parameter_valuespec(self):
        return Dictionary(elements=[
            ("levels_ram", DualMemoryLevels(_("RAM"))),
            ("levels_swap", DualMemoryLevels(_("Swap"))),
        ],)
