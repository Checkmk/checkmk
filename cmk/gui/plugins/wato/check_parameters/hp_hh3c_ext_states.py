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
    MonitoringState,
    TextAscii,
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersNetworking,
)


@rulespec_registry.register
class RulespecCheckgroupParametersHpHh3CExtStates(CheckParameterRulespecWithItem):
    @property
    def group(self):
        return RulespecGroupCheckParametersNetworking

    @property
    def check_group_name(self):
        return "hp_hh3c_ext_states"

    @property
    def title(self):
        return _("States of HP Switch modules")

    @property
    def match_type(self):
        return "dict"

    @property
    def parameter_valuespec(self):
        return Dictionary(elements=[
            ("oper",
             Dictionary(
                 title=_("Operational states"),
                 elements=[
                     ("not_supported", MonitoringState(title=_("Not supported"), default_value=1)),
                     ("disabled", MonitoringState(title=_("Disabled"), default_value=2)),
                     ("enabled", MonitoringState(title=_("Enabled"), default_value=0)),
                     ("dangerous", MonitoringState(title=_("Dangerous"), default_value=2)),
                 ],
             )),
            ("admin",
             Dictionary(
                 title=_("Administrative states"),
                 elements=[
                     ("not_supported", MonitoringState(title=_("Not supported"), default_value=1)),
                     ("locked", MonitoringState(title=_("Locked"), default_value=0)),
                     ("shutting_down", MonitoringState(title=_("Shutting down"), default_value=2)),
                     ("unlocked", MonitoringState(title=_("Unlocked"), default_value=2)),
                 ],
             )),
        ],)

    @property
    def item_spec(self):
        return TextAscii(title=_("Port"), help=_("The Port Description"))
