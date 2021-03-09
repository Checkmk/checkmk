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
    ListChoice,
    TextAscii,
    Transform,
    Tuple,
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersPrinters,
)


def windows_printer_queues_forth(old):
    default = {
        "warn_states": [8, 11],
        "crit_states": [9, 10],
    }
    if isinstance(old, tuple):
        default['levels'] = old
    if isinstance(old, dict):
        return old
    return default


def _parameter_valuespec_windows_printer_queues():
    return Transform(
        Dictionary(
            title=_("Windows Printer Configuration"),
            elements=[
                (
                    "levels",
                    Tuple(
                        title=_("Levels for the number of print jobs"),
                        help=_("This rule is applied to the number of print jobs "
                               "currently waiting in windows printer queue."),
                        elements=[
                            Integer(title=_("Warning at"), unit=_("jobs"), default_value=40),
                            Integer(title=_("Critical at"), unit=_("jobs"), default_value=60),
                        ],
                    ),
                ),
                ("crit_states",
                 ListChoice(
                     title=_("States who should lead to critical"),
                     choices=[
                         (0, "Unkown"),
                         (1, "Other"),
                         (2, "No Error"),
                         (3, "Low Paper"),
                         (4, "No Paper"),
                         (5, "Low Toner"),
                         (6, "No Toner"),
                         (7, "Door Open"),
                         (8, "Jammed"),
                         (9, "Offline"),
                         (10, "Service Requested"),
                         (11, "Output Bin Full"),
                     ],
                     default_value=[9, 10],
                 )),
                ("warn_states",
                 ListChoice(
                     title=_("States who should lead to warning"),
                     choices=[
                         (0, "Unkown"),
                         (1, "Other"),
                         (2, "No Error"),
                         (3, "Low Paper"),
                         (4, "No Paper"),
                         (5, "Low Toner"),
                         (6, "No Toner"),
                         (7, "Door Open"),
                         (8, "Jammed"),
                         (9, "Offline"),
                         (10, "Service Requested"),
                         (11, "Output Bin Full"),
                     ],
                     default_value=[8, 11],
                 )),
            ],
        ),
        forth=windows_printer_queues_forth,
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="windows_printer_queues",
        group=RulespecGroupCheckParametersPrinters,
        item_spec=lambda: TextAscii(title=_("Printer Name"), allow_empty=True),
        parameter_valuespec=_parameter_valuespec_windows_printer_queues,
        title=lambda: _("Number of open jobs of a printer on windows"),
    ))
