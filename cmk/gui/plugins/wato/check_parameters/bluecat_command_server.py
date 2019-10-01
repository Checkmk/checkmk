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
    ListChoice,
)
from cmk.gui.plugins.wato.check_parameters.bluecat_ntp import bluecat_operstates
from cmk.gui.plugins.wato import (
    RulespecGroupCheckParametersNetworking,
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
)


def _parameter_valuespec_bluecat_command_server():
    return Dictionary(
        elements=[
            ("oper_states",
             Dictionary(
                 title=_("Operations States"),
                 elements=[
                     ("warning",
                      ListChoice(
                          title=_("States treated as warning"),
                          choices=bluecat_operstates,
                          default_value=[2, 3, 4],
                      )),
                     ("critical",
                      ListChoice(
                          title=_("States treated as critical"),
                          choices=bluecat_operstates,
                          default_value=[5],
                      )),
                 ],
                 required_keys=['warning', 'critical'],
             )),
        ],
        required_keys=['oper_states'],  # There is only one value, so its required
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="bluecat_command_server",
        group=RulespecGroupCheckParametersNetworking,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_bluecat_command_server,
        title=lambda: _("Bluecat Command Server Settings"),
    ))
