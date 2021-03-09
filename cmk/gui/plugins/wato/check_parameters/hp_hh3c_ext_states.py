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


def _parameter_valuespec_hp_hh3c_ext_states():
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


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="hp_hh3c_ext_states",
        group=RulespecGroupCheckParametersNetworking,
        item_spec=lambda: TextAscii(title=_("Port"), help=_("The Port Description")),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_hp_hh3c_ext_states,
        title=lambda: _("States of HP Switch modules"),
    ))
