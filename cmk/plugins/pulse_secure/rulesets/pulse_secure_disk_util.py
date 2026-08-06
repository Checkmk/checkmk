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


def _parameter_form_pulse_secure_disk_util() -> Dictionary:
    return Dictionary(
        elements={
            "upper_levels": DictElement[SimpleLevelsConfigModel[float]](
                required=True,
                parameter_form=SimpleLevels(
                    title=Title("Upper levels for disk utilization"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Percentage(),
                    prefill_levels_type=DefaultValue(LevelsType.FIXED),
                    prefill_fixed_levels=DefaultValue((80.0, 90.0)),
                    migrate=migrate_to_float_simple_levels,
                ),
            ),
        },
    )


rule_spec_pulse_secure_disk_util = CheckParameters(
    name="pulse_secure_disk_util",
    # weblate-flags: read-only, vendor-name
    title=Title("Pulse Secure disk utilization"),
    topic=Topic.APPLICATIONS,
    parameter_form=_parameter_form_pulse_secure_disk_util,
    condition=HostCondition(),
)
