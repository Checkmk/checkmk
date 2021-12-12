#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersStorage,
)
from cmk.gui.valuespec import Dictionary, DropdownChoice, Percentage, TextInput, Tuple


def _item_spec_nimble_latency():
    return TextInput(title=_("Volume"), help=_("Specify the name of the Nimble volume."))


def _parameter_valuespec_nimble_latency():
    return Dictionary(
        help=_(
            "You can set limits for the latency of read or write I/O operations of Nimble "
            "storage volumes. Note that the operations are shown in terms of number of "
            "operations as a percentage of total read or write I/O operations within various "
            "latency ranges (e.g. 0-0.1 ms, 0.1-0.2 ms, etc.). In order to effectively "
            "set limits for these volumes, please select WARN/CRIT levels in terms of "
            "percentage of overall number of operations. To accommodate the large range of "
            "Nimble storage devices and their various functionalities (all-flash, hybrid, "
            "tape, etc.), it is possible to select the starting point at which values should "
            "be considered. "
            "For example, for some devices, you may only want to be notified with a WARN if "
            "10% of operations have a latency of 10-20 ms or above, and a CRIT if 20% of "
            'operations reach this threshold. You can achieve this by setting the "Range '
            'Reference" parameter to 10-20 ms, and warning and critical levels to 10% and 20% '
            "respectively."
        ),
        elements=[
            (
                "range_reference",
                DropdownChoice(
                    title="Range Reference",
                    help=_("The latency range at which values should start to be considered."),
                    choices=[
                        ("0.1", _("0.0 - 0.1 ms")),
                        ("0.2", _("0.1 - 0.2 ms")),
                        ("0.5", _("0.2 - 0.5 ms")),
                        ("1", _("0.5 - 1.0 ms")),
                        ("2", _("1.0 - 2.0 ms")),
                        ("5", _("2.0 - 5.0 ms")),
                        ("10", _("5.0 - 10.0 ms")),
                        ("20", _("10.0 - 20.0 ms")),
                        ("50", _("20.0 - 50.0 ms")),
                        ("100", _("50.0 - 100.0 ms")),
                        ("200", _("100.0 - 200.0 ms")),
                        ("500", _("200.0 - 500.0 ms")),
                        ("1000", _("500.0+ ms")),
                    ],
                    default_value="20",
                ),
            ),
            (
                "read",
                Tuple(
                    title=_("Read Latency"),
                    elements=[
                        Percentage(
                            title=_("Warning at"),
                            unit="%",
                            minvalue=0.0,
                            maxvalue=100.0,
                            default_value=10.0,
                        ),
                        Percentage(
                            title=_("Critical at"),
                            unit="%",
                            minvalue=0.0,
                            maxvalue=100.0,
                            default_value=20.0,
                        ),
                    ],
                    help=_(
                        "The default levels are suitable for hybrid storage systems. "
                        "Please consider lowering them if your storage system is all-flash."
                    ),
                ),
            ),
            (
                "write",
                Tuple(
                    title=_("Write Latency"),
                    elements=[
                        Percentage(
                            title=_("Warning at"),
                            unit="%",
                            minvalue=0.0,
                            maxvalue=100.0,
                            default_value=10.0,
                        ),
                        Percentage(
                            title=_("Critical at"),
                            unit="%",
                            minvalue=0.0,
                            maxvalue=100.0,
                            default_value=20.0,
                        ),
                    ],
                    help=_(
                        "The default levels are suitable for hybrid storage systems. "
                        "Please consider lowering them if your storage system is all-flash."
                    ),
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="nimble_latency",
        group=RulespecGroupCheckParametersStorage,
        item_spec=_item_spec_nimble_latency,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_nimble_latency,
        title=lambda: _("Nimble IO levels"),
    )
)
