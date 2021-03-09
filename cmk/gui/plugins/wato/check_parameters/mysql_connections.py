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
    Percentage,
    TextAscii,
    Tuple,
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)


def _item_spec_mysql_connections():
    return TextAscii(
        title=_("Instance"),
        help=_("Only needed if you have multiple MySQL Instances on one server"),
    )


def _parameter_valuespec_mysql_connections():
    return Dictionary(elements=[
        ("perc_used",
         Tuple(
             title=_("Max. parallel connections"),
             help=_("Compares the maximum number of connections that have been "
                    "in use simultaneously since the server started with the maximum simultaneous "
                    "connections allowed by the configuration of the server. This threshold "
                    "makes the check raise warning/critical states if the percentage is equal to "
                    "or above the configured levels."),
             elements=[
                 Percentage(title=_("Warning at")),
                 Percentage(title=_("Critical at")),
             ],
         )),
    ],)


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="mysql_connections",
        group=RulespecGroupCheckParametersApplications,
        item_spec=_item_spec_mysql_connections,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_mysql_connections,
        title=lambda: _("MySQL Connections"),
    ))
