#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersNetworking,
)
from cmk.gui.valuespec import Dictionary, Float, ListChoice, TextInput, Tuple


def _parameter_valuespec_docsis_cm_status():
    return Dictionary(
        elements=[
            (
                "error_states",
                ListChoice(
                    title=_("Modem States that lead to a critical state"),
                    help=_(
                        "If one of the selected states occurs the check will repsond with a critical state "
                    ),
                    choices=[
                        (1, "other"),
                        (2, "notReady"),
                        (3, "notSynchronized"),
                        (4, "phySynchronized"),
                        (5, "usParametersAcquired"),
                        (6, "rangingComplete"),
                        (7, "ipComplete"),
                        (8, "todEstablished"),
                        (9, "securityEstablished"),
                        (10, "paramTransferComplete"),
                        (11, "registrationComplete"),
                        (12, "operational"),
                        (13, "accessDenied"),
                    ],
                    default_value=[1, 2, 13],
                ),
            ),
            (
                "tx_power",
                Tuple(
                    title=_("Transmit Power"),
                    help=_("The operational transmit power"),
                    elements=[
                        Float(title=_("warning at"), unit="dBmV", default_value=20.0),
                        Float(title=_("critical at"), unit="dBmV", default_value=10.0),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="docsis_cm_status",
        group=RulespecGroupCheckParametersNetworking,
        item_spec=lambda: TextInput(title=_("ID of the Entry")),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_docsis_cm_status,
        title=lambda: _("Docsis Cable Modem Status"),
    )
)
