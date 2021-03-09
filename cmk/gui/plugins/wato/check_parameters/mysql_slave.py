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
    TextAscii,
    Tuple,
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)


def _item_spec_mysql_slave():
    return TextAscii(
        title=_("Instance"),
        help=_("Only needed if you have multiple MySQL Instances on one server"),
    )


def _parameter_valuespec_mysql_slave():
    return Dictionary(elements=[
        ("seconds_behind_master",
         Tuple(
             title=_("Max. time behind the master"),
             help=_(
                 "Compares the time which the slave can be behind the master. "
                 "This rule makes the check raise warning/critical states if the time is equal to "
                 "or above the configured levels."),
             elements=[
                 Age(title=_("Warning at")),
                 Age(title=_("Critical at")),
             ],
         )),
    ],
                      optional_keys=None)


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="mysql_slave",
        group=RulespecGroupCheckParametersApplications,
        item_spec=_item_spec_mysql_slave,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_mysql_slave,
        title=lambda: _("MySQL Slave"),
    ))
