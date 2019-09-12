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
    Transform,
    Tuple,
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersOperatingSystem,
)
from cmk.gui.plugins.wato.check_parameters.utils import (
    size_trend_elements,)


def _parameter_valuespec_cisco_mem():
    return Transform(
        Dictionary(elements=[
            ("levels",
             Alternative(
                 title=_("Levels for memory usage"),
                 elements=[
                     Tuple(
                         title=_("Specify levels in percentage of total RAM"),
                         elements=[
                             Percentage(title=_("Warning at a usage of"),
                                        unit=_("% of RAM"),
                                        maxvalue=None),
                             Percentage(title=_("Critical at a usage of"),
                                        unit=_("% of RAM"),
                                        maxvalue=None)
                         ],
                     ),
                     Tuple(
                         title=_("Specify levels in absolute usage values"),
                         elements=[
                             Integer(title=_("Warning at"), unit=_("MB")),
                             Integer(title=_("Critical at"), unit=_("MB"))
                         ],
                     ),
                 ],
             )),
        ] + size_trend_elements),
        forth=lambda spec: spec if isinstance(spec, dict) else {"levels": spec},
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="cisco_mem",
        group=RulespecGroupCheckParametersOperatingSystem,
        item_spec=lambda: TextAscii(title=_("Memory Pool Name"), allow_empty=False),
        parameter_valuespec=_parameter_valuespec_cisco_mem,
        title=lambda: _("Cisco Memory Usage"),
    ))
