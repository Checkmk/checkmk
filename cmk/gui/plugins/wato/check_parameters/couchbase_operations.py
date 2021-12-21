#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)
from cmk.gui.valuespec import Dictionary, Float, TextInput, Tuple


def _parameter_valuespec_couchbase_operations():
    return Dictionary(
        title=_("Couchbase Operations"),
        elements=[
            (
                "ops",
                Tuple(
                    title="Operations per sec",
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
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="couchbase_ops",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        item_spec=lambda: TextInput(title=_("Node or bucket name")),
        parameter_valuespec=_parameter_valuespec_couchbase_operations,
        title=lambda: _("Couchbase Operations"),
    )
)

rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="couchbase_ops_nodes",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_couchbase_operations,
        title=lambda: _("Couchbase Total Node Operations"),
    )
)

rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="couchbase_ops_buckets",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_couchbase_operations,
        title=lambda: _("Couchbase Total Bucket Operations"),
    )
)
