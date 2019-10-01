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
    ListOf,
    TextAscii,
    Tuple,
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersStorage,
)


def _parameter_valuespec_snapvault():
    return Dictionary(elements=[
        (
            "lag_time",
            Tuple(
                title=_("Default levels"),
                elements=[
                    Age(title=_("Warning at")),
                    Age(title=_("Critical at")),
                ],
            ),
        ),
        ("policy_lag_time",
         ListOf(
             Tuple(
                 orientation="horizontal",
                 elements=[
                     TextAscii(title=_("Policy name")),
                     Tuple(
                         title=_("Maximum age"),
                         elements=[
                             Age(title=_("Warning at")),
                             Age(title=_("Critical at")),
                         ],
                     ),
                 ],
             ),
             title=_('Policy specific levels (Clustermode only)'),
             help=_(
                 "Here you can specify levels for different policies which overrule the levels "
                 "from the <i>Default levels</i> parameter. This setting only works in NetApp Clustermode setups."
             ),
             allow_empty=False,
         ))
    ],)


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="snapvault",
        group=RulespecGroupCheckParametersStorage,
        item_spec=lambda: TextAscii(title=_("Source Path"), allow_empty=False),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_snapvault,
        title=lambda: _("NetApp Snapvaults / Snapmirror Lag Time"),
    ))
