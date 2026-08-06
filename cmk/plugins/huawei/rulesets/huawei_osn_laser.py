#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.rulesets.v1 import Help, Label, Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    Integer,
    LevelDirection,
    LevelsType,
    migrate_to_integer_simple_levels,
    SimpleLevels,
    SimpleLevelsConfigModel,
    String,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostAndItemCondition, Topic


def _dbm_lower_levels(title: Title) -> DictElement[SimpleLevelsConfigModel[int]]:
    return DictElement(
        required=False,
        parameter_form=SimpleLevels(
            title=title,
            help_text=Help("The signal must not get too weak, so only lower levels apply."),
            level_direction=LevelDirection.LOWER,
            form_spec_template=Integer(label=Label("dBm")),
            prefill_levels_type=DefaultValue(LevelsType.FIXED),
            prefill_fixed_levels=DefaultValue((-160, -180)),
            migrate=migrate_to_integer_simple_levels,
        ),
    )


def _parameter_form_huawei_osn_laser() -> Dictionary:
    return Dictionary(
        elements={
            "levels_low_in": _dbm_lower_levels(Title("Lower levels for laser input")),
            "levels_low_out": _dbm_lower_levels(Title("Lower levels for laser output")),
        },
    )


rule_spec_huawei_osn_laser = CheckParameters(
    name="huawei_osn_laser",
    title=Title("OSN laser attenuation"),
    topic=Topic.NETWORKING,
    parameter_form=_parameter_form_huawei_osn_laser,
    condition=HostAndItemCondition(
        item_title=Title("Laser ID"),
        item_form=String(),
    ),
)
