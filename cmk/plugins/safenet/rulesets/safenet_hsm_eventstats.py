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
    LevelsType,
    migrate_to_float_simple_levels,
    migrate_to_integer_simple_levels,
    SimpleLevels,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostCondition, Topic


def _parameter_rulespec_safenet_hsm_eventstats() -> Dictionary:
    return Dictionary(
        elements={
            "critical_events": DictElement(
                parameter_form=SimpleLevels(
                    title=Title("Critical Events"),
                    help_text=Help(
                        "Sets levels on total critical events since last counter reset."
                    ),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Integer(),
                    prefill_levels_type=DefaultValue(LevelsType.FIXED),
                    prefill_fixed_levels=DefaultValue((0, 1)),
                    migrate=migrate_to_integer_simple_levels,
                )
            ),
            "noncritical_events": DictElement(
                parameter_form=SimpleLevels(
                    title=Title("Non-Critical Events"),
                    help_text=Help(
                        "Sets levels on total noncritical events since last counter reset."
                    ),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Integer(),
                    prefill_levels_type=DefaultValue(LevelsType.FIXED),
                    prefill_fixed_levels=DefaultValue((0, 1)),
                    migrate=migrate_to_integer_simple_levels,
                )
            ),
            "critical_event_rate": DictElement(
                parameter_form=SimpleLevels(
                    title=Title("Critical Event Rate"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Float(unit_symbol="1/s"),
                    prefill_levels_type=DefaultValue(LevelsType.FIXED),
                    prefill_fixed_levels=DefaultValue((0.0001, 0.0005)),
                    migrate=migrate_to_float_simple_levels,
                )
            ),
            "noncritical_event_rate": DictElement(
                parameter_form=SimpleLevels(
                    title=Title("Non-Critical Event Rate"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Float(unit_symbol="1/s"),
                    prefill_levels_type=DefaultValue(LevelsType.FIXED),
                    prefill_fixed_levels=DefaultValue((0.0001, 0.0005)),
                    migrate=migrate_to_float_simple_levels,
                )
            ),
        }
    )


rule_spec_safenet_hsm_eventstats = CheckParameters(
    name="safenet_hsm_eventstats",
    title=Title("Safenet HSM Event Stats"),
    topic=Topic.APPLICATIONS,
    parameter_form=_parameter_rulespec_safenet_hsm_eventstats,
    condition=HostCondition(),
)
