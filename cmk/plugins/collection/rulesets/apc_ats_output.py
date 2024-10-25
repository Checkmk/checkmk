#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import (
    DictElement,
    Dictionary,
    Float,
    InputHint,
    Integer,
    SimpleLevels,
)
from cmk.rulesets.v1.form_specs._levels import LevelDirection
from cmk.rulesets.v1.form_specs._migrations import (
    migrate_to_float_simple_levels,
    migrate_to_integer_simple_levels,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostAndItemCondition, Topic


def _parameter_valuespec_apc_ats_output():
    return Dictionary(
        title=Title("Levels for ATS output parameters"),
        elements={
            "output_voltage_max": DictElement(
                parameter_form=SimpleLevels(
                    level_direction=LevelDirection.UPPER,
                    title=Title("Maximum levels for voltage"),
                    form_spec_template=Integer(unit_symbol="Volt"),
                    prefill_fixed_levels=InputHint(value=(0, 0)),
                    migrate=migrate_to_integer_simple_levels,
                )
            ),
            "output_voltage_min": DictElement(
                parameter_form=SimpleLevels(
                    level_direction=LevelDirection.LOWER,
                    title=Title("Minimum levels for voltage"),
                    form_spec_template=Integer(unit_symbol="Volt"),
                    prefill_fixed_levels=InputHint(value=(0, 0)),
                    migrate=migrate_to_integer_simple_levels,
                )
            ),
            "output_current_max": DictElement(
                parameter_form=SimpleLevels(
                    level_direction=LevelDirection.UPPER,
                    title=Title("Maximum levels for current"),
                    form_spec_template=Integer(unit_symbol="A"),
                    prefill_fixed_levels=InputHint(value=(0, 0)),
                )
            ),
            "output_current_min": DictElement(
                parameter_form=SimpleLevels(
                    level_direction=LevelDirection.LOWER,
                    title=Title("Minimum levels for current"),
                    form_spec_template=Integer(unit_symbol="A"),
                    prefill_fixed_levels=InputHint(value=(0, 0)),
                )
            ),
            "output_power_max": DictElement(
                parameter_form=SimpleLevels(
                    level_direction=LevelDirection.UPPER,
                    title=Title("Maximum levels for power"),
                    form_spec_template=Integer(unit_symbol="W"),
                    prefill_fixed_levels=InputHint(value=(0, 0)),
                )
            ),
            "output_power_min": DictElement(
                parameter_form=SimpleLevels(
                    level_direction=LevelDirection.LOWER,
                    title=Title("Minimum levels for power"),
                    form_spec_template=Integer(unit_symbol="W"),
                    prefill_fixed_levels=InputHint(value=(0, 0)),
                )
            ),
            "load_perc_max": DictElement(
                parameter_form=SimpleLevels(
                    level_direction=LevelDirection.UPPER,
                    title=Title("Maximum levels for load in percent"),
                    form_spec_template=Float(unit_symbol="%"),
                    prefill_fixed_levels=InputHint(value=(0, 0)),
                    migrate=migrate_to_float_simple_levels,
                )
            ),
            "load_perc_min": DictElement(
                parameter_form=SimpleLevels(
                    level_direction=LevelDirection.LOWER,
                    title=Title("Minimum levels for load in percent"),
                    form_spec_template=Float(unit_symbol="%"),
                    prefill_fixed_levels=InputHint(value=(0, 0)),
                    migrate=migrate_to_float_simple_levels,
                )
            ),
        },
    )


rule_spec_ovs_bonding = CheckParameters(
    name="apc_ats_output",
    title=Title("APC Automatic Transfer Switch Output"),
    topic=Topic.ENVIRONMENTAL,
    parameter_form=_parameter_valuespec_apc_ats_output,
    condition=HostAndItemCondition(item_title=Title("ID of phase")),
)
