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
from cmk.gui.valuespec import Dictionary, Float, Percentage, TextInput, Tuple


def _parameter_valuespec_couchbase_cache():
    return Dictionary(
        title=_("Couchbase: Cache"),
        elements=[
            (
                "cache_misses",
                Tuple(
                    title="Levels on cache misses per second",
                    elements=[
                        Float(
                            title="warn",
                        ),
                        Float(
                            title="crit",
                        ),
                    ],
                ),
            ),
            (
                "cache_hits",
                Tuple(
                    title="Nodes only: Lower levels for hits in %",
                    elements=[
                        Percentage(
                            title="warn",
                        ),
                        Percentage(
                            title="crit",
                        ),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="couchbase_cache",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        item_spec=lambda: TextInput(title=_("Node or bucket name")),
        parameter_valuespec=_parameter_valuespec_couchbase_cache,
        title=lambda: _("Couchbase Cache"),
    )
)
