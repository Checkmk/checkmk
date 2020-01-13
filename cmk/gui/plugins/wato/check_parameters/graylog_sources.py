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


def _parameter_valuespec_graylog_sources():
    return Dictionary(elements=[
        ("msgs_upper",
         Tuple(
             title=_("Total message count upper levels"),
             elements=[
                 Integer(title=_("Warning at")),
                 Integer(title=_("Critical at")),
             ],
         )),
        ("msgs_lower",
         Tuple(
             title=_("Total message count lower levels"),
             elements=[
                 Integer(title=_("Warning below")),
                 Integer(title=_("Critical below")),
             ],
         )),
        ("msgs_avg",
         Integer(
             title=_("Message averaging"),
             help=_("By activating averaging, Check_MK will compute the average of "
                    "the message count over a given interval. If you define "
                    "alerting levels they will automatically be applied on the "
                    "averaged value. This helps to mask out short peaks."),
             unit=_("minutes"),
             minvalue=1,
             default_value=30,
         )),
        ("msgs_avg_upper",
         Tuple(
             title=_("Average message count upper levels"),
             elements=[
                 Integer(title=_("Warning at")),
                 Integer(title=_("Critical at")),
             ],
         )),
        ("msgs_avg_lower",
         Tuple(
             title=_("Average message count lower levels"),
             elements=[
                 Integer(title=_("Warning below")),
                 Integer(title=_("Critical below")),
             ],
         )),
    ],)


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="graylog_sources",
        group=RulespecGroupCheckParametersApplications,
        item_spec=lambda: TextAscii(title=_("Source name")),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_graylog_sources,
        title=lambda: _("Graylog sources"),
    ))
