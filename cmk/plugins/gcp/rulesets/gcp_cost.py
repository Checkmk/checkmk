#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import (
    DictElement,
    Dictionary,
    Float,
    InputHint,
    SimpleLevels,
)
from cmk.rulesets.v1.form_specs._levels import LevelDirection
from cmk.rulesets.v1.form_specs._migrations import (
    migrate_to_float_simple_levels,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostAndItemCondition, Topic


def _parameter_valuespec_gcp_cost():
    return Dictionary(
        title=Title("Levels monthly GCP costs"),
        elements={
            "levels": DictElement(
                parameter_form=SimpleLevels(
                    level_direction=LevelDirection.UPPER,
                    title=Title("Amount in billed currency"),
                    form_spec_template=Float(),
                    prefill_fixed_levels=InputHint(value=(0, 0)),
                    migrate=migrate_to_float_simple_levels,
                )
            ),
        },
    )


rule_spec_gcp_cost = CheckParameters(
    name="gcp_cost",
    title=Title("GCP Cost"),
    topic=Topic.CLOUD,
    parameter_form=_parameter_valuespec_gcp_cost,
    condition=HostAndItemCondition(item_title=Title("Project")),
)
