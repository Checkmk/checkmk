#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    Integer,
    LevelDirection,
    SimpleLevels,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostAndItemCondition, Topic


def _make_form() -> Dictionary:
    return Dictionary(
        help_text=Help("This ruleset allows you to configure levels for the daily usage costs."),
        elements={
            "age": DictElement(
                required=False,
                parameter_form=SimpleLevels(
                    title=Title("Time since last AD Connect sync"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Integer(),
                    prefill_fixed_levels=DefaultValue((1800, 3600)),
                ),
            )
        },
    )


rule_spec_azure_usagedetails = CheckParameters(
    name="azure_v2_ad",
    title=Title("Azure AD Connect"),
    topic=Topic.NETWORKING,
    parameter_form=_make_form,
    condition=HostAndItemCondition(item_title=Title("Accounts display name")),
)
