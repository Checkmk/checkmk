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
from cmk.gui.valuespec import Dictionary, Filesize, TextInput, Tuple


def _parameter_valuespec_storage_throughput() -> Dictionary:
    return Dictionary(
        elements=[
            (
                "read",
                Tuple(
                    title=_("Read throughput per second"),
                    elements=[
                        Filesize(title=_("Warning at")),
                        Filesize(title=_("Critical at")),
                    ],
                ),
            ),
            (
                "write",
                Tuple(
                    title=_("Write throughput per second"),
                    elements=[
                        Filesize(title=_("Warning at")),
                        Filesize(title=_("Critical at")),
                    ],
                ),
            ),
            (
                "total",
                Tuple(
                    title=_("Total throughput per second"),
                    elements=[
                        Filesize(title=_("Warning at")),
                        Filesize(title=_("Critical at")),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="storage_throughput",
        group=RulespecGroupCheckParametersStorage,
        item_spec=lambda: TextInput(title=_("Port index or 'Total'")),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_storage_throughput,
        title=lambda: _("DDN S2A throughput"),
    )
)
