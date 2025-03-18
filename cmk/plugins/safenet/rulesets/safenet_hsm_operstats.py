#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    Float,
    Integer,
    LevelDirection,
    Levels,
    LevelsType,
    migrate_to_float_simple_levels,
    migrate_to_integer_simple_levels,
    migrate_to_upper_float_levels,
    PredictiveLevels,
    SimpleLevels,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostCondition, Topic


def _parameter_rulespec_safenet_hsm_operstats():
    return Dictionary(
        elements={
            "error_rate": DictElement(
                parameter_form=SimpleLevels(
                    title=Title("Error Rate"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Float(unit_symbol="1/s"),
                    prefill_levels_type=DefaultValue(LevelsType.FIXED),
                    prefill_fixed_levels=DefaultValue((0.0001, 0.0005)),
                    migrate=migrate_to_float_simple_levels,
                )
            ),
            "request_rate": DictElement(
                parameter_form=Levels(
                    title=Title("Request Rate"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Float(unit_symbol="1/s"),
                    prefill_levels_type=DefaultValue(LevelsType.FIXED),
                    prefill_fixed_levels=DefaultValue((0.0001, 0.0005)),
                    predictive=PredictiveLevels(
                        reference_metric="noncritical_events_rate",
                        prefill_abs_diff=DefaultValue((0.0001, 0.0005)),
                    ),
                    migrate=migrate_to_upper_float_levels,
                )
            ),
            "operation_errors": DictElement(
                parameter_form=SimpleLevels(
                    title=Title("Operation Errors"),
                    help_text=Help(
                        "Sets levels on total operation errors since last counter reset."
                    ),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Integer(),
                    prefill_levels_type=DefaultValue(LevelsType.FIXED),
                    prefill_fixed_levels=DefaultValue((0, 1)),
                    migrate=migrate_to_integer_simple_levels,
                )
            ),
        }
    )


rule_spec_safenet_hsm_operstats = CheckParameters(
    name="safenet_hsm_operstats",
    title=Title("Safenet HSM Operation Stats"),
    topic=Topic.APPLICATIONS,
    parameter_form=_parameter_rulespec_safenet_hsm_operstats,
    condition=HostCondition(),
)
