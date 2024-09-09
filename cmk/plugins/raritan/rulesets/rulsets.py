#!/usr/bin/env python3
# -*- encoding: utf-8; py-indent-offset: 4 -*-
#   _____  __          __  _____
#  / ____| \ \        / / |  __ \
# | (___    \ \  /\  / /  | |__) |
#  \___ \    \ \/  \/ /   |  _  /
#  ____) |    \  /\  /    | | \ \
# |_____/      \/  \/     |_|  \_\
#
# (c) 2024 SWR
# @author Frank Baier <frank.baier@swr.de>
#
from cmk.rulesets.v1 import rule_specs, Title, Label
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    BooleanChoice,
    LevelDirection,
    SimpleLevels,
    validators,
    Float,
)


def _parameters_residual_current() -> Dictionary:
    return Dictionary(
        elements={
            "warn_missing_data": DictElement(
                parameter_form=BooleanChoice(
                    title=Title("Missing Residual current on the PDUs"),
                    label=Label("Warn on missing Residual current"),
                    prefill=DefaultValue(True),
                ),
                required=True,
            ),
            "warn_missing_levels": DictElement(
                parameter_form=BooleanChoice(
                    title=Title("Missing levels from the PDU or rule"),
                    label=Label("Warn on missing levels"),
                    prefill=DefaultValue(True),
                ),
                required=True,
            ),
            "residual_levels": DictElement(
                parameter_form=SimpleLevels(
                    title=Title("Residual current levels"),
                    form_spec_template=Float(),
                    level_direction=LevelDirection.UPPER,
                    prefill_fixed_levels=DefaultValue((0, 0.030)),
                    custom_validate=(validators.NumberInRange(0.03, 0.3),),
                ),
                required=False,
            ),
        },
    )


rule_spec_mem_win = rule_specs.CheckParameters(
    title=Title("Residual current parameters for PDUs"),
    name="residual_current",
    topic=rule_specs.Topic.POWER,
    parameter_form=_parameters_residual_current,
    condition=rule_specs.HostCondition(),
)
