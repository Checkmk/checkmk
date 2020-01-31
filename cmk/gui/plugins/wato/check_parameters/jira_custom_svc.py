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
    Float,
    Integer,
    TextAscii,
    Tuple,
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)


def _parameter_valuespec_jira_custom_svc():
    return Dictionary(elements=[
        ("count_diff",
         Age(
             title=_("Timespan for difference calculation of total number of "
                     "issues"),
             display=["days", "hours", "minutes"],
             default_value=86400 * 7,
         )),
        ("custom_svc_count_lower",
         Tuple(
             title=_("Total number of issues lower level"),
             elements=[
                 Integer(title=_("Warning below"), unit="issues"),
                 Integer(title=_("Critical below"), unit="íssues"),
             ],
         )),
        ("custom_svc_count_upper",
         Tuple(
             title=_("Total number of issues upper level"),
             elements=[
                 Integer(title=_("Warning at"), unit="issues"),
                 Integer(title=_("Critical at"), unit="issues"),
             ],
         )),
        ("count_diff_lower",
         Tuple(
             title=_("Difference on total number of issues lower level"),
             elements=[
                 Integer(title=_("Warning below"), unit="issues"),
                 Integer(title=_("Critical below"), unit="íssues"),
             ],
         )),
        ("count_diff_upper",
         Tuple(
             title=_("Difference on total number of issues upper level"),
             elements=[
                 Integer(title=_("Warning at"), unit="issues"),
                 Integer(title=_("Critical at"), unit="issues"),
             ],
         )),
        ("sum_diff",
         Age(
             title=_("Timespan for difference calculation of summed up "
                     "values"),
             display=["days", "hours", "minutes"],
             default_value=86400 * 7,
         )),
        ("custom_svc_sum_lower",
         Tuple(
             title=_("Summed up values lower level"),
             elements=[
                 Integer(title=_("Warning below"), unit="issues"),
                 Integer(title=_("Critical below"), unit="íssues"),
             ],
         )),
        ("custom_svc_sum_upper",
         Tuple(
             title=_("Summed up values upper level"),
             elements=[
                 Integer(title=_("Warning at")),
                 Integer(title=_("Critical at")),
             ],
         )),
        ("sum_diff_lower",
         Tuple(
             title=_("Difference on summed up values lower level"),
             elements=[
                 Integer(title=_("Warning below"), unit="issues"),
                 Integer(title=_("Critical below"), unit="íssues"),
             ],
         )),
        ("sum_diff_upper",
         Tuple(
             title=_("Difference on summed up values upper level"),
             elements=[
                 Integer(title=_("Warning at"), unit="issues"),
                 Integer(title=_("Critical at"), unit="issues"),
             ],
         )),
        ("custom_svc_avg_lower",
         Tuple(
             title=_("Averaged values lower level"),
             elements=[Float(title=_("Warning below")),
                       Float(title=_("Critical below"))],
         )),
        ("custom_svc_avg_upper",
         Tuple(
             title=_("Averaged values upper level"),
             elements=[Float(title=_("Warning at")),
                       Float(title=_("Critical at"))],
         )),
    ],)


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="jira_custom_svc",
        group=RulespecGroupCheckParametersApplications,
        item_spec=lambda: TextAscii(title=_("Custom service name"),),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_jira_custom_svc,
        title=lambda: _("Jira custom service"),
    ))
