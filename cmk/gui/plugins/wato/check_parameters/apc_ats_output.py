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
    Integer,
    Percentage,
    TextAscii,
    Tuple,
)
from cmk.gui.plugins.wato import (
    RulespecGroupCheckParametersEnvironment,
    CheckParameterRulespecWithItem,
    rulespec_registry,
)


@rulespec_registry.register
class RulespecCheckgroupParametersApcAtsOutput(CheckParameterRulespecWithItem):
    @property
    def group(self):
        return RulespecGroupCheckParametersEnvironment

    @property
    def check_group_name(self):
        return "apc_ats_output"

    @property
    def title(self):
        return _("APC Automatic Transfer Switch Output")

    @property
    def match_type(self):
        return "dict"

    @property
    def parameter_valuespec(self):
        return Dictionary(
            title=_("Levels for ATS Output parameters"),
            optional_keys=True,
            elements=[
                ("output_voltage_max",
                 Tuple(title=_("Maximum Levels for Voltage"),
                       elements=[
                           Integer(title=_("Warning at"), unit="Volt"),
                           Integer(title=_("Critical at"), unit="Volt"),
                       ])),
                ("output_voltage_min",
                 Tuple(title=_("Minimum Levels for Voltage"),
                       elements=[
                           Integer(title=_("Warning if below"), unit="Volt"),
                           Integer(title=_("Critical if below"), unit="Volt"),
                       ])),
                ("load_perc_max",
                 Tuple(title=_("Maximum Levels for load in percent"),
                       elements=[
                           Percentage(title=_("Warning at")),
                           Percentage(title=_("Critical at")),
                       ])),
                ("load_perc_min",
                 Tuple(title=_("Minimum Levels for load in percent"),
                       elements=[
                           Percentage(title=_("Warning if below")),
                           Percentage(title=_("Critical if below")),
                       ])),
            ],
        )

    @property
    def item_spec(self):
        return TextAscii(title=_("ID of phase"),)
