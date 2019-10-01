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
    DropdownChoice,
    Percentage,
    TextAscii,
    Tuple,
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersOperatingSystem,
)


def _parameter_valuespec_netscaler_vserver():
    return Dictionary(elements=[
        ("health_levels",
         Tuple(
             title=_("Lower health levels"),
             elements=[
                 Percentage(title=_("Warning below"), default_value=100.0),
                 Percentage(title=_("Critical below"), default_value=0.1),
             ],
         )),
        ("cluster_status",
         DropdownChoice(
             title=_("Cluster behaviour"),
             help=_("Here you can choose the cluster behaviour. The best state "
                    "of all nodes is the default. This means, if  you have at "
                    "least one node in status UP the check returns OK. Health levels "
                    "should be the same on each node. If you choose worst, the check "
                    "will return CRIT if at least one node is in a state other than OK. "
                    "Health levels should be the same on each node, so only the first "
                    "node the health-levels are checked."),
             choices=[
                 ("best", _("best state")),
                 ("worst", _("worst state")),
             ],
             default_value="best",
         )),
    ],)


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="netscaler_vserver",
        group=RulespecGroupCheckParametersOperatingSystem,
        item_spec=lambda: TextAscii(title=_("Name of VServer")),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_netscaler_vserver,
        title=lambda: _("Netscaler VServer States"),
    ))
