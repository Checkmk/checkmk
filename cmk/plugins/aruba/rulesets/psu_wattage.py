#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.rulesets.v1 import Label, Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    Float,
    InputHint,
    LevelDirection,
    LevelsType,
    migrate_to_float_simple_levels,
    Percentage,
    Prefill,
    SimpleLevels,
    SimpleLevelsConfigModel,
    String,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostAndItemCondition, Topic


def _watt_levels(
    title: Title, direction: LevelDirection
) -> DictElement[SimpleLevelsConfigModel[float]]:
    return DictElement(
        required=False,
        parameter_form=SimpleLevels(
            title=title,
            level_direction=direction,
            form_spec_template=Float(label=Label("W")),
            prefill_levels_type=DefaultValue(LevelsType.FIXED),
            prefill_fixed_levels=InputHint((0.0, 0.0)),
            migrate=migrate_to_float_simple_levels,
        ),
    )


def _percentage_levels(
    title: Title, direction: LevelDirection, prefill: Prefill[tuple[float, float]]
) -> DictElement[SimpleLevelsConfigModel[float]]:
    return DictElement(
        required=False,
        parameter_form=SimpleLevels(
            title=title,
            level_direction=direction,
            form_spec_template=Percentage(),
            prefill_levels_type=DefaultValue(LevelsType.FIXED),
            prefill_fixed_levels=prefill,
            migrate=migrate_to_float_simple_levels,
        ),
    )


def _parameter_form_psu_wattage() -> Dictionary:
    return Dictionary(
        title=Title("Levels for power supply wattage"),
        elements={
            "levels_abs_upper": _watt_levels(
                Title("Upper levels (absolute)"), LevelDirection.UPPER
            ),
            "levels_abs_lower": _watt_levels(
                Title("Lower levels (absolute)"), LevelDirection.LOWER
            ),
            "levels_perc_upper": _percentage_levels(
                Title("Upper levels (in percent)"),
                LevelDirection.UPPER,
                DefaultValue((80.0, 90.0)),
            ),
            "levels_perc_lower": _percentage_levels(
                Title("Lower levels (in percent)"),
                LevelDirection.LOWER,
                DefaultValue((1.0, 0.1)),
            ),
        },
    )


rule_spec_psu_wattage = CheckParameters(
    name="psu_wattage",
    title=Title("Power supply wattage"),
    topic=Topic.NETWORKING,
    parameter_form=_parameter_form_psu_wattage,
    condition=HostAndItemCondition(item_title=Title("PSU"), item_form=String()),
)
