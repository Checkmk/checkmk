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
    Percentage,
    TextAscii,
    Tuple,
)
from cmk.gui.plugins.wato import (
    RulespecGroupCheckParametersApplications,
    CheckParameterRulespecWithItem,
    rulespec_registry,
)


def _parameter_valuespec_elasticsearch_indices():
    return Dictionary(
        elements=[
            ("elasticsearch_count_rate",
             Tuple(title=_("Document count delta"),
                   help=_("If this parameter is set, the document count delta of the "
                          "last minute will be compared to the delta of the average X "
                          "minutes. You can set WARN or CRIT levels to check if the last "
                          "minute's delta is X percent higher than the average delta."),
                   elements=[
                       Percentage(title=_("Warning at"), unit=_("percent higher than average")),
                       Percentage(title=_("Critical at"), unit=_("percent higher than average")),
                       Integer(title=_("Averaging"),
                               unit=_("minutes"),
                               minvalue=1,
                               default_value=30),
                   ])),
            ("elasticsearch_size_rate",
             Tuple(title=_("Size delta"),
                   help=_("If this parameter is set, the size delta of the last minute "
                          "will be compared to the delta of the average X minutes. "
                          "You can set WARN or CRIT levels to check if the last minute's "
                          "delta is X percent higher than the average delta."),
                   elements=[
                       Percentage(title=_("Warning at"), unit=_("percent higher than average")),
                       Percentage(title=_("Critical at"), unit=_("percent higher than average")),
                       Integer(title=_("Averaging"),
                               unit=_("minutes"),
                               minvalue=1,
                               default_value=30),
                   ])),
        ],
        optional_keys=["count_rate", "size_rate"],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="elasticsearch_indices",
        group=RulespecGroupCheckParametersApplications,
        item_spec=lambda: TextAscii(title=_("Name of indice")),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_elasticsearch_indices,
        title=lambda: _("Elasticsearch Indices"),
    ))
