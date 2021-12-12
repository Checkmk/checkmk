#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)
from cmk.gui.valuespec import Dictionary, Float, TextInput, Tuple


def _item_spec_msx_database():
    return TextInput(
        title=_("Database Name"),
        help=_("Specify database names that the rule should apply to"),
    )


def _parameter_valuespec_msx_database():
    return Dictionary(
        title=_("Set Levels"),
        elements=[
            (
                "read_attached_latency",
                Tuple(
                    title=_("I/O Database Reads (Attached) Average Latency"),
                    elements=[
                        Float(title=_("Warning at"), unit=_("ms"), default_value=200.0),
                        Float(title=_("Critical at"), unit=_("ms"), default_value=250.0),
                    ],
                ),
            ),
            (
                "read_recovery_latency",
                Tuple(
                    title=_("I/O Database Reads (Recovery) Average Latency"),
                    elements=[
                        Float(title=_("Warning at"), unit=_("ms"), default_value=150.0),
                        Float(title=_("Critical at"), unit=_("ms"), default_value=200.0),
                    ],
                ),
            ),
            (
                "write_latency",
                Tuple(
                    title=_("I/O Database Writes (Attached) Average Latency"),
                    elements=[
                        Float(title=_("Warning at"), unit=_("ms"), default_value=40.0),
                        Float(title=_("Critical at"), unit=_("ms"), default_value=50.0),
                    ],
                ),
            ),
            (
                "log_latency",
                Tuple(
                    title=_("I/O Log Writes Average Latency"),
                    elements=[
                        Float(title=_("Warning at"), unit=_("ms"), default_value=5.0),
                        Float(title=_("Critical at"), unit=_("ms"), default_value=10.0),
                    ],
                ),
            ),
        ],
        optional_keys=[],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="msx_database",
        group=RulespecGroupCheckParametersApplications,
        item_spec=_item_spec_msx_database,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_msx_database,
        title=lambda: _("MS Exchange Database"),
    )
)
