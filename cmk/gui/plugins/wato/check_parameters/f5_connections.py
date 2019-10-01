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
    Tuple,
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    Levels,
    RulespecGroupCheckParametersApplications,
)


def _parameter_valuespec_f5_connections():
    return Dictionary(elements=[
        ("conns",
         Levels(title=_("Max. number of connections"),
                default_value=None,
                default_levels=(25000, 30000))),
        ("ssl_conns",
         Levels(title=_("Max. number of SSL connections"),
                default_value=None,
                default_levels=(25000, 30000))),
        ("connections_rate",
         Levels(title=_("Maximum connections per second"),
                default_value=None,
                default_levels=(500, 1000))),
        ("connections_rate_lower",
         Tuple(
             title=_("Minimum connections per second"),
             elements=[
                 Integer(title=_("Warning at")),
                 Integer(title=_("Critical at")),
             ],
         )),
        ("http_req_rate",
         Levels(title=_("HTTP requests per second"), default_value=None,
                default_levels=(500, 1000))),
    ],)


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="f5_connections",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_f5_connections,
        title=lambda: _("F5 Loadbalancer Connections"),
    ))
