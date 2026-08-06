#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    LevelDirection,
    LevelsType,
    migrate_to_float_simple_levels,
    Percentage,
    SimpleLevels,
    SimpleLevelsConfigModel,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostCondition, Topic


def _parameter_form_mobileiron_statistics() -> Dictionary:
    return Dictionary(
        elements={
            "non_compliant_summary_levels": DictElement[SimpleLevelsConfigModel[float]](
                required=True,
                parameter_form=SimpleLevels(
                    title=Title("Levels for non-compliant devices"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Percentage(),
                    prefill_levels_type=DefaultValue(LevelsType.FIXED),
                    prefill_fixed_levels=DefaultValue((10.0, 20.0)),
                    migrate=migrate_to_float_simple_levels,
                ),
            ),
        },
    )


rule_spec_mobileiron_statistics = CheckParameters(
    name="mobileiron_statistics",
    # weblate-flags: read-only, vendor-name
    title=Title("MobileIron statistics"),
    topic=Topic.APPLICATIONS,
    parameter_form=_parameter_form_mobileiron_statistics,
    condition=HostCondition(),
)
