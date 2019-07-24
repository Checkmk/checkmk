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
    Checkbox,
    Dictionary,
    MonitoringState,
    Percentage,
    TextAscii,
    Transform,
    Tuple,
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersPrinters,
)


def transform_printer_supply(params):
    if isinstance(params, tuple):
        if len(params) == 2:
            return {"levels": params}
        return {"levels": params[:2], "upturn_toner": params[2]}
    return params


@rulespec_registry.register
class RulespecCheckgroupParametersPrinterSupply(CheckParameterRulespecWithItem):
    @property
    def group(self):
        return RulespecGroupCheckParametersPrinters

    @property
    def check_group_name(self):
        return "printer_supply"

    @property
    def title(self):
        return _("Printer cartridge levels")

    @property
    def parameter_valuespec(self):
        return Transform(
            Dictionary(elements=[
                ("levels",
                 Tuple(
                     title=_("Levels for remaining supply"),
                     elements=[
                         Percentage(
                             title=_("Warning level for remaining"),
                             allow_int=True,
                             default_value=20.0,
                             help=_(
                                 "For consumable supplies, this is configured as the percentage of "
                                 "remaining capacity. For supplies that fill up, this is configured "
                                 "as remaining space."),
                         ),
                         Percentage(
                             title=_("Critical level for remaining"),
                             allow_int=True,
                             default_value=10.0,
                             help=_(
                                 "For consumable supplies, this is configured as the percentage of "
                                 "remaining capacity. For supplies that fill up, this is configured "
                                 "as remaining space."),
                         ),
                     ],
                 )),
                ("some_remaining",
                 MonitoringState(
                     title=_("State for <i>some remaining</i>"),
                     help=_("Some printers do not report a precise percentage but "
                            "just <i>some remaining</i> at a low fill state. Here you "
                            "can set the monitoring state for that situation"),
                     default_value=1,
                 )),
                ("upturn_toner",
                 Checkbox(
                     title=_("Upturn toner levels"),
                     label=_("Printer sends <i>used</i> material instead of <i>remaining</i>"),
                     help=_("Some Printers (eg. Konica for Drum Cartdiges) returning the available"
                            " fuel instead of what is left. In this case it's possible"
                            " to upturn the levels to handle this behavior"),
                 )),
            ],),
            forth=transform_printer_supply,
        )

    @property
    def item_spec(self):
        return TextAscii(title=_("cartridge specification"), allow_empty=True)
