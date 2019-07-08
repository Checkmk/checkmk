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
    RulespecGroupCheckParametersApplications,
)


@rulespec_registry.register
class RulespecCheckgroupParametersMysqlSessions(CheckParameterRulespecWithItem):
    @property
    def group(self):
        return RulespecGroupCheckParametersApplications

    @property
    def check_group_name(self):
        return "mysql_sessions"

    @property
    def title(self):
        return _("MySQL Sessions & Connections")

    @property
    def match_type(self):
        return "dict"

    @property
    def parameter_valuespec(self):
        return Dictionary(
            help=_("This check monitors the current number of active sessions to the MySQL "
                   "database server as well as the connection rate."),
            elements=[
                (
                    "total",
                    Tuple(
                        title=_("Number of current sessions"),
                        elements=[
                            Integer(title=_("Warning at"), unit=_("sessions"), default_value=100),
                            Integer(title=_("Critical at"), unit=_("sessions"), default_value=200),
                        ],
                    ),
                ),
                (
                    "running",
                    Tuple(
                        title=_("Number of currently running sessions"),
                        help=_("Levels for the number of sessions that are currently active"),
                        elements=[
                            Integer(title=_("Warning at"), unit=_("sessions"), default_value=10),
                            Integer(title=_("Critical at"), unit=_("sessions"), default_value=20),
                        ],
                    ),
                ),
                (
                    "connections",
                    Tuple(
                        title=_("Number of new connections per second"),
                        elements=[
                            Integer(title=_("Warning at"),
                                    unit=_("connection/sec"),
                                    default_value=20),
                            Integer(title=_("Critical at"),
                                    unit=_("connection/sec"),
                                    default_value=40),
                        ],
                    ),
                ),
            ],
        )

    @property
    def item_spec(self):
        return TextAscii(
            title=_("Instance"),
            help=_("Only needed if you have multiple MySQL Instances on one server"),
        )
