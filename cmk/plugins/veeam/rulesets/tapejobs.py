#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
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


def _parameter_form_veeam_tapejobs() -> Dictionary:
    return Dictionary(
        elements={
            "levels_upper": DictElement(
                parameter_form=SimpleLevels[float](
                    title=Title("Levels for the duration of the backup job"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=TimeSpan(
                        displayed_magnitudes=[
                            TimeMagnitude.DAY,
                            TimeMagnitude.HOUR,
                            TimeMagnitude.MINUTE,
                            TimeMagnitude.SECOND,
                        ],
                    ),
                    prefill_levels_type=DefaultValue(LevelsType.FIXED),
                    prefill_fixed_levels=DefaultValue((86400.0, 172800.0)),
                    migrate=migrate_to_float_simple_levels,
                ),
                required=True,
            ),
        },
    )


rule_spec_veeam_tapejobs = CheckParameters(
    name="veeam_tapejobs",
    title=Title("Veeam tape backup jobs"),
    topic=Topic.STORAGE,
    parameter_form=_parameter_form_veeam_tapejobs,
    condition=HostAndItemCondition(item_title=Title("Name of the tape job")),
)
