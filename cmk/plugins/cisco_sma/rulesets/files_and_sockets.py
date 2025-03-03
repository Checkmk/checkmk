#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    InputHint,
    Integer,
    LevelDirection,
    LevelsType,
    SimpleLevels,
    SimpleLevelsConfigModel,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostCondition, Topic


def _parameter_form_cisco_sma_files_and_sockets() -> Dictionary:
    return Dictionary(
        elements={
            "levels_upper_open_files_and_sockets": DictElement[SimpleLevelsConfigModel[int]](
                required=False,
                parameter_form=SimpleLevels(
                    title=Title("Upper threshold on open files and sockets"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Integer(),
                    prefill_levels_type=DefaultValue(LevelsType.FIXED),
                    prefill_fixed_levels=InputHint((5500, 6000)),
                ),
            ),
            "levels_lower_open_files_and_sockets": DictElement[SimpleLevelsConfigModel[int]](
                required=False,
                parameter_form=SimpleLevels(
                    title=Title("Lower threshold on open files and sockets"),
                    level_direction=LevelDirection.LOWER,
                    form_spec_template=Integer(),
                    prefill_levels_type=DefaultValue(LevelsType.NONE),
                    prefill_fixed_levels=InputHint((0, 0)),
                ),
            ),
        }
    )


rule_spec_cisco_sma_files_and_sockets = CheckParameters(
    name="cisco_sma_files_and_sockets",
    topic=Topic.GENERAL,
    parameter_form=_parameter_form_cisco_sma_files_and_sockets,
    title=Title("Cisco SMA files and sockets"),
    condition=HostCondition(),
)
