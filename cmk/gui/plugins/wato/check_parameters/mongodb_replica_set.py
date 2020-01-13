#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2019             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Check_MK.
# The official homepage is at https://checkmk.com/.
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
from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithItem,
    RulespecGroupCheckParametersStorage,
    rulespec_registry,
)
from cmk.gui.valuespec import Dictionary, Integer, TextAscii, Tuple, Age


def _parameter_valuespec_mongodb_replication_lag():
    return Dictionary(
        elements=[("levels_mongdb_replication_lag",
                   _sec_tuple("Levels over an extended time period on replication lag"))])


def _sec_tuple(title):
    return Tuple(
        title=_(title),
        elements=[
            Integer(title=_(
                "Time between the last operation on primary's oplog and on secondary above"),
                    unit=_("seconds"),
                    default_value=10,
                    minvalue=0),
            Age(title=_("Warning equal or after "), default_value=5 * 60),
            Age(title=_("Critical equal or after "), default_value=15 * 60)
        ],
        help=_("Replication lag is a delay between an operation on the primary and the application "
               "of that operation from the oplog to the secondary."
               "With this configuration, check_mk will alert if replication lag is "
               "exceeding a threshold over an extended period of time."))


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="mongodb_replica_set",
        group=RulespecGroupCheckParametersStorage,
        item_spec=lambda: TextAscii(title=_("MongoDB Replica Set"),),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_mongodb_replication_lag,
        title=lambda: _("MongoDB Replica Set"),
    ))
