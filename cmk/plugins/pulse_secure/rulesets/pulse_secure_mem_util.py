#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.rulesets.v1 import Help, Title
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


def _percentage_levels(
    title: Title, default: tuple[float, float], help_text: Help | None = None
) -> DictElement[SimpleLevelsConfigModel[float]]:
    return DictElement(
        required=False,
        parameter_form=SimpleLevels(
            title=title,
            help_text=help_text,
            level_direction=LevelDirection.UPPER,
            form_spec_template=Percentage(),
            prefill_levels_type=DefaultValue(LevelsType.FIXED),
            prefill_fixed_levels=DefaultValue(default),
            migrate=migrate_to_float_simple_levels,
        ),
    )


def _parameter_form_pulse_secure_mem_util() -> Dictionary:
    return Dictionary(
        elements={
            "mem_used_percent": _percentage_levels(
                Title("Upper levels for IVE RAM utilization"), (90.0, 95.0)
            ),
            "swap_used_percent": _percentage_levels(
                Title("Upper levels for IVE swap utilization"),
                (5.0, 101.0),
                Help(
                    "The default critical level of 101 percent cannot be reached, so with "
                    "the defaults swap utilization only ever warns."
                ),
            ),
        },
    )


rule_spec_pulse_secure_mem_util = CheckParameters(
    name="pulse_secure_mem_util",
    # weblate-flags: read-only, vendor-name
    title=Title("Pulse Secure IVE memory utilization"),
    topic=Topic.APPLICATIONS,
    parameter_form=_parameter_form_pulse_secure_mem_util,
    condition=HostCondition(),
)
