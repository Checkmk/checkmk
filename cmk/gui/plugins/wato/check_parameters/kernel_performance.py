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
    Dictionary,
    Tuple,
    Float,
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    Levels,
    RulespecGroupCheckParametersOperatingSystem,
)


@rulespec_registry.register
class RulespecCheckgroupParametersKernelPerformance(CheckParameterRulespecWithoutItem):
    @property
    def group(self):
        return RulespecGroupCheckParametersOperatingSystem

    @property
    def check_group_name(self):
        return "kernel_performance"

    @property
    def title(self):
        return _("Number of kernel events per second")

    @property
    def parameter_valuespec(self):
        return Dictionary(elements=[
            ("ctxt",
             Levels(
                 unit=_("events per second"),
                 title=_("Context Switches"),
                 default_levels=(1000, 5000),
                 default_difference=(500.0, 1000.0),
                 default_value=None,
             )),
            ("processes",
             Levels(
                 unit=_("events per second"),
                 title=_("Process Creations"),
                 default_levels=(1000, 5000),
                 default_difference=(500.0, 1000.0),
                 default_value=None,
             )),
            ("pgmajfault",
             Levels(
                 unit=_("events per second"),
                 title=_("Major Page Faults"),
                 default_levels=(1000, 5000),
                 default_difference=(500.0, 1000.0),
                 default_value=None,
             )),
            (
                "page_swap_in_levels_lower",
                Tuple(title=_("Swap In Lower"),
                      elements=[
                          Float(title=_("Swap In warning below"), unit=_("events per second")),
                          Float(title=_("Swap In critical below"), unit=_("events per second"))
                      ]),
            ),
            (
                "page_swap_in_levels",
                Tuple(title=_("Swap In Upper"),
                      elements=[
                          Float(title=_("Swap In warning at"), unit=_("events per second")),
                          Float(title=_("Swap In critical at"), unit=_("events per second"))
                      ]),
            ),
            (
                "page_swap_out_levels_lower",
                Tuple(title=_("Swap Out Lower"),
                      elements=[
                          Float(title=_("Swap Out warning below"), unit=_("events per second")),
                          Float(title=_("Swap Out critical below"), unit=_("events per second"))
                      ]),
            ),
            (
                "page_swap_out_levels",
                Tuple(title=_("Swap Out Upper"),
                      elements=[
                          Float(title=_("Swap Out warning at"), unit=_("events per second")),
                          Float(title=_("Swap Out critical at"), unit=_("events per second"))
                      ]),
            ),
        ],)
