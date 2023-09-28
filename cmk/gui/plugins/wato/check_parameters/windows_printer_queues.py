#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersPrinters,
)
from cmk.gui.valuespec import Dictionary, Integer, ListChoice, TextInput, Tuple


def _parameter_valuespec_windows_printer_queues() -> Dictionary:
    return Dictionary(
        title=_("Windows Printer Configuration"),
        elements=[
            (
                "levels",
                Tuple(
                    title=_("Levels for the number of print jobs"),
                    help=_(
                        "This rule is applied to the number of print jobs "
                        "currently waiting in windows printer queue."
                    ),
                    elements=[
                        Integer(title=_("Warning at"), unit=_("jobs"), default_value=40),
                        Integer(title=_("Critical at"), unit=_("jobs"), default_value=60),
                    ],
                ),
            ),
            (
                "crit_states",
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
                ),
            ),
            (
                "warn_states",
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
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="windows_printer_queues",
        group=RulespecGroupCheckParametersPrinters,
        item_spec=lambda: TextInput(title=_("Printer Name"), allow_empty=True),
        parameter_valuespec=_parameter_valuespec_windows_printer_queues,
        title=lambda: _("Windows printers: number of open jobs"),
    )
)
