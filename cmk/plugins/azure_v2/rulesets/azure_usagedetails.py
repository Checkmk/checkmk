#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    Float,
    LevelDirection,
    SimpleLevels,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostAndItemCondition, Topic


def _make_form() -> Dictionary:
    return Dictionary(
        help_text=Help("This ruleset allows you to configure levels for the daily usage costs."),
        elements={
            "costs": DictElement(
                required=False,
                parameter_form=SimpleLevels(
                    title=Title("Upper levels on daily costs"),
                    help_text=Help(
                        "The levels on costs will be considered to be in the currency"
                        " corresponding to the reported data."
                    ),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Float(),
                    prefill_fixed_levels=DefaultValue((0.0, 0.0)),
                ),
            )
        },
    )


rule_spec_azure_usagedetails = CheckParameters(
    name="azure_v2_usagedetails",
    title=Title("Azure Usage Details (Costs)"),
    topic=Topic.APPLICATIONS,
    parameter_form=_make_form,
    condition=HostAndItemCondition(item_title=Title("Service Type")),
)
