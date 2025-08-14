#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.plugins.wato.check_parameters.fileinfo_utils import (
    get_fileinfo_negative_age_tolerance_element,
)
from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import (
    DataSize,
    DefaultValue,
    DictElement,
    Dictionary,
    InputHint,
    LevelDirection,
    LevelsType,
    migrate_to_float_simple_levels,
    migrate_to_integer_simple_levels,
    ServiceState,
    SIMagnitude,
    SimpleLevels,
    TimeMagnitude,
    TimeSpan,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostAndItemCondition, Topic


def _parameter_valuespec_fileinfo() -> Dictionary:
    return Dictionary(
        elements={
            "minage": DictElement(
                required=False,
                parameter_form=SimpleLevels(
                    title=Title("Minimal age"),
                    level_direction=LevelDirection.LOWER,
                    prefill_levels_type=DefaultValue(LevelsType.FIXED),
                    prefill_fixed_levels=InputHint((0, 0)),
                    migrate=migrate_to_float_simple_levels,
                    form_spec_template=TimeSpan(
                        displayed_magnitudes=[
                            TimeMagnitude.DAY,
                            TimeMagnitude.HOUR,
                            TimeMagnitude.MINUTE,
                            TimeMagnitude.SECOND,
                        ]
                    ),
                ),
            ),
            "maxage": DictElement(
                required=False,
                parameter_form=SimpleLevels(
                    title=Title("Maximal age"),
                    level_direction=LevelDirection.UPPER,
                    prefill_levels_type=DefaultValue(LevelsType.FIXED),
                    prefill_fixed_levels=InputHint((0, 0)),
                    migrate=migrate_to_float_simple_levels,
                    form_spec_template=TimeSpan(
                        displayed_magnitudes=[
                            TimeMagnitude.DAY,
                            TimeMagnitude.HOUR,
                            TimeMagnitude.MINUTE,
                            TimeMagnitude.SECOND,
                        ]
                    ),
                ),
            ),
            "minsize": DictElement(
                required=False,
                parameter_form=SimpleLevels(
                    title=Title("Minimal size"),
                    level_direction=LevelDirection.LOWER,
                    prefill_levels_type=DefaultValue(LevelsType.FIXED),
                    prefill_fixed_levels=InputHint((0, 0)),
                    migrate=migrate_to_integer_simple_levels,
                    form_spec_template=DataSize(
                        displayed_magnitudes=[
                            SIMagnitude.BYTE,
                            SIMagnitude.KILO,
                            SIMagnitude.MEGA,
                            SIMagnitude.GIGA,
                            SIMagnitude.TERA,
                        ]
                    ),
                ),
            ),
            "maxsize": DictElement(
                required=False,
                parameter_form=SimpleLevels(
                    title=Title("Maximal size"),
                    level_direction=LevelDirection.UPPER,
                    prefill_levels_type=DefaultValue(LevelsType.FIXED),
                    prefill_fixed_levels=InputHint((0, 0)),
                    migrate=migrate_to_integer_simple_levels,
                    form_spec_template=DataSize(
                        displayed_magnitudes=[
                            SIMagnitude.BYTE,
                            SIMagnitude.KILO,
                            SIMagnitude.MEGA,
                            SIMagnitude.GIGA,
                            SIMagnitude.TERA,
                        ]
                    ),
                ),
            ),
            "state_missing": DictElement(
                required=False,
                parameter_form=ServiceState(
                    prefill=DefaultValue(ServiceState.UNKNOWN),
                    title=Title("State when file is missing"),
                ),
            ),
            "negative_age_tolerance": get_fileinfo_negative_age_tolerance_element(),
        },
    )


rule_spec_fileinfo = CheckParameters(
    name="fileinfo",
    title=Title("Size and age of single files"),
    topic=Topic.STORAGE,
    parameter_form=_parameter_valuespec_fileinfo,
    condition=HostAndItemCondition(
        item_title=Title("File name"),
    ),
)
