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
    TextAscii,
    Tuple,
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersEnvironment,
)


@rulespec_registry.register
class RulespecCheckgroupParametersPduGude(CheckParameterRulespecWithItem):
    @property
    def group(self):
        return RulespecGroupCheckParametersEnvironment

    @property
    def check_group_name(self):
        return "pdu_gude"

    @property
    def title(self):
        return _("Levels for Gude PDU Devices")

    @property
    def match_type(self):
        return "dict"

    @property
    def parameter_valuespec(self):
        return Dictionary(elements=[
            ("kWh",
             Tuple(
                 title=_("Total accumulated Active Energy of Power Channel"),
                 elements=[
                     Integer(title=_("warning at"), unit=_("kW")),
                     Integer(title=_("critical at"), unit=_("kW")),
                 ],
             )),
            ("W",
             Tuple(
                 title=_("Active Power"),
                 elements=[
                     Integer(title=_("warning at"), unit=_("W")),
                     Integer(title=_("critical at"), unit=_("W")),
                 ],
             )),
            ("A",
             Tuple(
                 title=_("Current on Power Channel"),
                 elements=[
                     Integer(title=_("warning at"), unit=_("A")),
                     Integer(title=_("critical at"), unit=_("A")),
                 ],
             )),
            ("V",
             Tuple(
                 title=_("Voltage on Power Channel"),
                 elements=[
                     Integer(title=_("warning if below"), unit=_("V")),
                     Integer(title=_("critical if below"), unit=_("V")),
                 ],
             )),
            ("VA",
             Tuple(
                 title=_("Line Mean Apparent Power"),
                 elements=[
                     Integer(title=_("warning at"), unit=_("VA")),
                     Integer(title=_("critical at"), unit=_("VA")),
                 ],
             )),
        ],)

    @property
    def item_spec(self):
        return TextAscii(title=_("Phase Number"), help=_("The Number of the power Phase."))
