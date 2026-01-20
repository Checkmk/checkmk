#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)
from cmk.gui.valuespec import Dictionary, Integer, TextInput, Tuple


def _parameter_valuespec_oracle_crs_res() -> Dictionary:
    return Dictionary(
        elements=[
            (
                "number_of_nodes_not_in_target_state",
                Tuple(
                    title=_("Number of nodes not in target state"),
                    elements=[
                        Integer(
                            title=_("Warning at"),
                            default_value=1,
                            unit="nodes",
                        ),
                        Integer(
                            title=_("Critical at"),
                            default_value=2,
                            unit="nodes",
                        ),
                    ],
                ),
            ),
        ]
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="oracle_crs_res",
        group=RulespecGroupCheckParametersApplications,
        item_spec=lambda: TextInput(title=_("GI resource"), allow_empty=False),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_oracle_crs_res,
        title=lambda: _("Oracle CRS Res"),
    )
)
