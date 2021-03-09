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
    Alternative,
    Dictionary,
    Integer,
    Percentage,
    TextAscii,
    Tuple,
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)


def _item_spec_jvm_memory():
    return TextAscii(
        title=_("Name of the virtual machine"),
        help=_("The name of the application server"),
        allow_empty=False,
    )


def _parameter_valuespec_jvm_memory():
    return Dictionary(
        help=_("This rule allows to set the warn and crit levels of the heap / "
               "non-heap and total memory area usage on web application servers. "
               "Other keywords for this rule: Tomcat, Jolokia, JMX. "),
        elements=[
            ("totalheap",
             Alternative(
                 title=_("Total Memory Levels"),
                 elements=[
                     Tuple(
                         title=_("Percentage levels of used space"),
                         elements=[
                             Percentage(title=_("Warning at"), label=_("% usage")),
                             Percentage(title=_("Critical at"), label=_("% usage")),
                         ],
                     ),
                     Tuple(
                         title=_("Absolute free space in MB"),
                         elements=[
                             Integer(title=_("Warning if below"), unit=_("MB")),
                             Integer(title=_("Critical if below"), unit=_("MB")),
                         ],
                     )
                 ],
             )),
            ("heap",
             Alternative(
                 title=_("Heap Memory Levels"),
                 elements=[
                     Tuple(
                         title=_("Percentage levels of used space"),
                         elements=[
                             Percentage(title=_("Warning at"), label=_("% usage")),
                             Percentage(title=_("Critical at"), label=_("% usage")),
                         ],
                     ),
                     Tuple(
                         title=_("Absolute free space in MB"),
                         elements=[
                             Integer(title=_("Warning if below"), unit=_("MB")),
                             Integer(title=_("Critical if below"), unit=_("MB")),
                         ],
                     )
                 ],
             )),
            ("nonheap",
             Alternative(
                 title=_("Nonheap Memory Levels"),
                 elements=[
                     Tuple(
                         title=_("Percentage levels of used space"),
                         elements=[
                             Percentage(title=_("Warning at"), label=_("% usage")),
                             Percentage(title=_("Critical at"), label=_("% usage")),
                         ],
                     ),
                     Tuple(
                         title=_("Absolute free space in MB"),
                         elements=[
                             Integer(title=_("Warning if below"), unit=_("MB")),
                             Integer(title=_("Critical if below"), unit=_("MB")),
                         ],
                     )
                 ],
             )),
            ("perm",
             Tuple(
                 title=_("Perm Memory usage"),
                 elements=[
                     Percentage(title=_("Warning at"), label=_("% usage")),
                     Percentage(title=_("Critical at"), label=_("% usage")),
                 ],
             )),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="jvm_memory",
        group=RulespecGroupCheckParametersApplications,
        item_spec=_item_spec_jvm_memory,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_jvm_memory,
        title=lambda: _("JVM memory levels"),
    ))
