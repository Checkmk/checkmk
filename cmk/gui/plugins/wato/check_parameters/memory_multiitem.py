#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersOperatingSystem,
)
from cmk.gui.valuespec import Alternative, Dictionary, Filesize, Percentage, TextInput, Tuple


def _parameter_valuespec_memory_multiitem():
    return Dictionary(
        help=_(
            "The memory levels for one specific module of this host. This is relevant for hosts that have "
            "several distinct memory areas, e.g. pluggable cards"
        ),
        elements=[
            (
                "levels",
                Alternative(
                    title=_("Memory levels"),
                    elements=[
                        Tuple(
                            title=_("Specify levels in percentage of total RAM"),
                            elements=[
                                Percentage(
                                    title=_("Warning at a memory usage of"),
                                    default_value=80.0,
                                    maxvalue=None,
                                ),
                                Percentage(
                                    title=_("Critical at a memory usage of"),
                                    default_value=90.0,
                                    maxvalue=None,
                                ),
                            ],
                        ),
                        Tuple(
                            title=_("Specify levels in absolute usage values"),
                            elements=[
                                Filesize(title=_("Warning at")),
                                Filesize(title=_("Critical at")),
                            ],
                        ),
                    ],
                ),
            ),
        ],
        optional_keys=[],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="memory_multiitem",
        group=RulespecGroupCheckParametersOperatingSystem,
        item_spec=lambda: TextInput(title=_("Module name"), allow_empty=False),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_memory_multiitem,
        title=lambda: _("Main memory usage of devices with modules"),
    )
)
