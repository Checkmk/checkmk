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
from cmk.gui.valuespec import Dictionary, DropdownChoice, Float, Tuple


def _item_spec_ddn_s2a_wait() -> DropdownChoice:
    return DropdownChoice(
        title=_("Host or Disk"),
        choices=[
            ("Disk", _("Disk")),
            ("Host", _("Host")),
        ],
    )


def _parameter_valuespec_ddn_s2a_wait() -> Dictionary:
    return Dictionary(
        elements=[
            (
                "read_avg",
                Tuple(
                    title=_("Read wait average"),
                    elements=[
                        Float(title=_("Warning at"), unit="s"),
                        Float(title=_("Critical at"), unit="s"),
                    ],
                ),
            ),
            (
                "read_min",
                Tuple(
                    title=_("Read wait minimum"),
                    elements=[
                        Float(title=_("Warning at"), unit="s"),
                        Float(title=_("Critical at"), unit="s"),
                    ],
                ),
            ),
            (
                "read_max",
                Tuple(
                    title=_("Read wait maximum"),
                    elements=[
                        Float(title=_("Warning at"), unit="s"),
                        Float(title=_("Critical at"), unit="s"),
                    ],
                ),
            ),
            (
                "write_avg",
                Tuple(
                    title=_("Write wait average"),
                    elements=[
                        Float(title=_("Warning at"), unit="s"),
                        Float(title=_("Critical at"), unit="s"),
                    ],
                ),
            ),
            (
                "write_min",
                Tuple(
                    title=_("Write wait minimum"),
                    elements=[
                        Float(title=_("Warning at"), unit="s"),
                        Float(title=_("Critical at"), unit="s"),
                    ],
                ),
            ),
            (
                "write_max",
                Tuple(
                    title=_("Write wait maximum"),
                    elements=[
                        Float(title=_("Warning at"), unit="s"),
                        Float(title=_("Critical at"), unit="s"),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="ddn_s2a_wait",
        group=RulespecGroupCheckParametersStorage,
        item_spec=_item_spec_ddn_s2a_wait,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_ddn_s2a_wait,
        title=lambda: _("DDN S2A read/write wait"),
    )
)
