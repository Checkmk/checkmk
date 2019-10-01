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
    Age,
    Dictionary,
    FixedValue,
    Integer,
    ListChoice,
    TextAscii,
    Tuple,
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersNetworking,
)

hivemanger_states = [
    ("Critical", "Critical"),
    ("Maybe", "Maybe"),
    ("Major", "Major"),
    ("Minor", "Minor"),
]


def _parameter_valuespec_hivemanager_devices():
    return Dictionary(elements=[
        ('max_clients',
         Tuple(
             title=_("Number of clients"),
             help=_("Number of clients connected to a Device."),
             elements=[
                 Integer(title=_("Warning at"), unit=_("clients")),
                 Integer(title=_("Critical at"), unit=_("clients")),
             ],
         )),
        ('max_uptime',
         Tuple(
             title=_("Maximum uptime of Device"),
             elements=[
                 Age(title=_("Warning at")),
                 Age(title=_("Critical at")),
             ],
         )),
        ('alert_on_loss', FixedValue(
            False,
            totext="",
            title=_("Do not alert on connection loss"),
        )),
        ("warn_states",
         ListChoice(
             title=_("States treated as warning"),
             choices=hivemanger_states,
             default_value=['Maybe', 'Major', 'Minor'],
         )),
        ("crit_states",
         ListChoice(
             title=_("States treated as critical"),
             choices=hivemanger_states,
             default_value=['Critical'],
         )),
    ],)


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="hivemanager_devices",
        group=RulespecGroupCheckParametersNetworking,
        item_spec=lambda: TextAscii(title=_("Hostname of the Device")),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_hivemanager_devices,
        title=lambda: _("Hivemanager Devices"),
    ))
