#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
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
from cmk.rulesets.v1 import Label, rule_specs, Title
from cmk.rulesets.v1.form_specs import (
    BooleanChoice,
    DefaultValue,
    DictElement,
    Dictionary,
    Float,
    LevelDirection,
    SimpleLevels,
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
    condition=rule_specs.HostAndItemCondition(item_title=Title("Residual current phase name")),
)
