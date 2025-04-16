#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import cast

from cmk.rulesets.v1 import Help, Label, Title
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
    Percentage,
    SIMagnitude,
    SimpleLevels,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostAndItemCondition, Topic

DEFAULT_LEVEL_PERCENT = (80.0, 85.0)


def _set_default_levels(model: object) -> dict[str, object]:
    model = cast(dict[str, object], model)
    if "levels" not in model:
        model["levels"] = ("no_levels", None)

    if "levels_perc" not in model:
        model["levels_perc"] = ("fixed", DEFAULT_LEVEL_PERCENT)

    return model


def _make_form() -> Dictionary:
    return Dictionary(
        migrate=_set_default_levels,
        elements={
            "levels": DictElement(
                required=True,
                parameter_form=SimpleLevels(
                    title=Title("Upper levels for the DB space size"),
                    help_text=Help(
                        "Automatic space management in Informix allows storage space to "
                        "grow. Use this rule to monitor the growth."
                    ),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=DataSize(
                        label=Label("B"),
                        displayed_magnitudes=(
                            SIMagnitude.MEGA,
                            SIMagnitude.GIGA,
                            SIMagnitude.TERA,
                        ),
                    ),
                    migrate=migrate_to_integer_simple_levels,
                    prefill_levels_type=DefaultValue(LevelsType.NONE),
                    prefill_fixed_levels=InputHint((1000**3, 5 * 1000**3)),
                ),
            ),
            "levels_perc": DictElement(
                required=True,
                parameter_form=SimpleLevels(
                    title=Title("Upper percentual levels for the DB space size"),
                    help_text=Help("Monitor the usage of DB space"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Percentage(),
                    migrate=migrate_to_float_simple_levels,
                    prefill_levels_type=DefaultValue(LevelsType.FIXED),
                    prefill_fixed_levels=DefaultValue(DEFAULT_LEVEL_PERCENT),
                ),
            ),
        },
    )


rule_spec_informix_dbspaces = CheckParameters(
    name="informix_dbspaces",
    topic=Topic.APPLICATIONS,
    parameter_form=_make_form,
    title=Title("Informix DB spaces"),
    condition=HostAndItemCondition(item_title=Title("Instance name")),
)
