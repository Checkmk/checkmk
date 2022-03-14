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
from cmk.gui.valuespec import Dictionary, Percentage, TextInput, Tuple


def _parameter_valuespec_couchbase_fragmentation():
    return Dictionary(
        title=_("Couchbase Fragmentation"),
        elements=[
            (
                "docs",
                Tuple(
                    title="Documents fragmentation",
                    elements=[
                        Percentage(title="warn"),
                        Percentage(title="crit"),
                    ],
                ),
            ),
            (
                "views",
                Tuple(
                    title="Views fragmentation",
                    elements=[
                        Percentage(title="warn"),
                        Percentage(title="crit"),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="couchbase_fragmentation",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        item_spec=lambda: TextInput(title=_("Bucket name")),
        parameter_valuespec=_parameter_valuespec_couchbase_fragmentation,
        title=lambda: _("Couchbase Fragmentation"),
    )
)
