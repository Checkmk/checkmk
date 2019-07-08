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


@rulespec_registry.register
class RulespecCheckgroupParametersMemory(CheckParameterRulespecWithoutItem):
    @property
    def group(self):
        return RulespecGroupCheckParametersOperatingSystem

    @property
    def check_group_name(self):
        return "memory"

    @property
    def title(self):
        return _("Main memory usage (UNIX / Other Devices)")

    @property
    def parameter_valuespec(self):
        return Transform(
            Dictionary(
                elements=[
                    (
                        "levels",
                        Alternative(
                            title=_("Levels for memory"),
                            show_alternative_title=True,
                            default_value=(150.0, 200.0),
                            match=match_dual_level_type,
                            help=
                            _("The used and free levels for the memory on UNIX systems take into account the "
                              "currently used memory (RAM or SWAP) by all processes and sets this in relation "
                              "to the total RAM of the system. This means that the memory usage can exceed 100%. "
                              "A usage of 200% means that the total size of all processes is twice as large as "
                              "the main memory, so <b>at least</b> half of it is currently swapped out. For systems "
                              "without Swap space you should choose levels below 100%."),
                            elements=[
                                Alternative(
                                    title=_("Levels for used memory"),
                                    style="dropdown",
                                    elements=[
                                        Tuple(
                                            title=_("Specify levels in percentage of total RAM"),
                                            elements=[
                                                Percentage(title=_("Warning at a usage of"),
                                                           maxvalue=None),
                                                Percentage(title=_("Critical at a usage of"),
                                                           maxvalue=None)
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
                                                title=_(
                                                    "Specify levels in percentage of total RAM"),
                                                elements=[
                                                    Percentage(title=_("Warning if less than"),
                                                               maxvalue=None),
                                                    Percentage(title=_("Critical if less than"),
                                                               maxvalue=None)
                                                ],
                                            ),
                                            Tuple(
                                                title=_("Specify levels in absolute values"),
                                                elements=[
                                                    Integer(title=_("Warning if below"),
                                                            unit=_("MB")),
                                                    Integer(title=_("Critical if below"),
                                                            unit=_("MB"))
                                                ],
                                            ),
                                        ],
                                    ),
                                    title=_("Levels for free memory"),
                                    help=
                                    _("Keep in mind that if you have 1GB RAM and 1GB SWAP you need to "
                                      "specify 120% or 1200MB to get an alert if there is only 20% free RAM available. "
                                      "The free memory levels do not work with the fortigate check, because it does "
                                      "not provide total memory data."),
                                    allow_empty=False,
                                    forth=lambda val: tuple(-x for x in val),
                                    back=lambda val: tuple(-x for x in val))
                            ],
                        ),
                    ),
                    ("average",
                     Integer(
                         title=_("Averaging"),
                         help=_(
                             "If this parameter is set, all measured values will be averaged "
                             "over the specified time interval before levels are being applied. Per "
                             "default, averaging is turned off."),
                         unit=_("minutes"),
                         minvalue=1,
                         default_value=60,
                     )),
                ],
                optional_keys=["average"],
            ),
            forth=lambda t: isinstance(t, tuple) and {"levels": t} or t,
        )
