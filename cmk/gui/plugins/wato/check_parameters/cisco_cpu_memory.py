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
    Alternative,
    Dictionary,
    Integer,
    Percentage,
    Transform,
    Tuple,
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersOperatingSystem,
)
from cmk.gui.plugins.wato.check_parameters.utils import (
    match_dual_level_type,)


def _parameter_valuespec_memory():
    return Dictionary(elements=[
        (
            "levels",
            Alternative(
                title=_("Levels for Cisco CPU memory"),
                help=_("The performance graph will always display the occupied memory. "
                       "This is independent of the actual check levels which can be set "
                       "for both free and occupied memory levels."),
                default_value=(150.0, 200.0),
                match=match_dual_level_type,
                elements=[
                    Alternative(
                        title=_("Levels for occupied memory"),
                        help=_(
                            "Specify the threshold levels for the occupied memory. The occupied memory "
                            "consists of used and kernel reserved memory."),
                        style="dropdown",
                        elements=[
                            Tuple(
                                title=_("Specify levels in percentage of total RAM"),
                                elements=[
                                    Percentage(title=_("Warning at a usage of"), maxvalue=None),
                                    Percentage(title=_("Critical at a usage of"), maxvalue=None)
                                ],
                            ),
                            Tuple(
                                title=_("Specify levels in absolute values"),
                                elements=[
                                    Integer(title=_("Warning at"), unit=_("MB")),
                                    Integer(title=_("Critical at"), unit=_("MB"))
                                ],
                            ),
                        ],
                    ),
                    Transform(
                        Alternative(
                            style="dropdown",
                            elements=[
                                Tuple(
                                    title=_("Specify levels in percentage of total RAM"),
                                    elements=[
                                        Percentage(
                                            title=_("Warning if less than"),
                                            maxvalue=None,
                                        ),
                                        Percentage(
                                            title=_("Critical if less than"),
                                            maxvalue=None,
                                        )
                                    ],
                                ),
                                Tuple(
                                    title=_("Specify levels in absolute values"),
                                    elements=[
                                        Integer(title=_("Warning if below"), unit=_("MB")),
                                        Integer(title=_("Critical if below"), unit=_("MB"))
                                    ],
                                ),
                            ],
                        ),
                        title=_("Levels for free memory"),
                        help=_(
                            "Specify the threshold levels for the free memory space. The free memory "
                            "excludes the reserved kernel memory."),
                        forth=lambda val: tuple(-x for x in val),
                        back=lambda val: tuple(-x for x in val),
                    ),
                ],
            ),
        ),
    ],)


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="cisco_cpu_memory",
        group=RulespecGroupCheckParametersOperatingSystem,
        parameter_valuespec=_parameter_valuespec_memory,
        title=lambda: _("Cisco CPU Memory"),
    ))
