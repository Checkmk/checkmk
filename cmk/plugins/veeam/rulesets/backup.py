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


def _parameter_form_veeam_backup() -> Dictionary:
    return Dictionary(
        elements={
            "age": DictElement(
                parameter_form=SimpleLevels[float](
                    title=Title("Time since end of last backup"),
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
                    prefill_fixed_levels=DefaultValue((108000.0, 172800.0)),
                    migrate=migrate_to_float_simple_levels,
                ),
                # The legacy valuespec kept "age" optional; the check falls back to
                # its default levels when a rule does not set it.
                required=False,
            ),
        },
    )


rule_spec_veeam_backup = CheckParameters(
    name="veeam_backup",
    title=Title("Veeam: Time since last backup"),
    topic=Topic.APPLICATIONS,
    parameter_form=_parameter_form_veeam_backup,
    condition=HostAndItemCondition(item_title=Title("Job name")),
)
