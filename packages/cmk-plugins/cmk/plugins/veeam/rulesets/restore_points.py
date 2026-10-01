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
    SimpleLevels,
    TimeMagnitude,
    TimeSpan,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostAndItemCondition, Topic

_HOUR = 60.0 * 60.0


def _parameter_form_veeam_restore_points() -> Dictionary:
    return Dictionary(
        elements={
            "age": DictElement(
                parameter_form=SimpleLevels[float](
                    title=Title("Last restore point age"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=TimeSpan(
                        displayed_magnitudes=[TimeMagnitude.HOUR],
                    ),
                    prefill_levels_type=DefaultValue(LevelsType.FIXED),
                    prefill_fixed_levels=DefaultValue((30 * _HOUR, 48 * _HOUR)),
                    migrate=migrate_to_float_simple_levels,
                ),
            ),
        },
    )


rule_spec_veeam_restore_points = CheckParameters(
    name="veeam_restore_points",
    title=Title("Veeam: Restore points"),
    topic=Topic.APPLICATIONS,
    parameter_form=_parameter_form_veeam_restore_points,
    condition=HostAndItemCondition(item_title=Title("Backup object name")),
)
