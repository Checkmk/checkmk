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


def _parameter_form() -> Dictionary:
    return Dictionary(
        elements={
            "levels_upper_total_threads": DictElement[SimpleLevelsConfigModel[int]](
                parameter_form=SimpleLevels(
                    title=Title("Upper thresholds on mail transfer threads"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Integer(),
                    prefill_levels_type=DefaultValue(LevelsType.FIXED),
                    prefill_fixed_levels=InputHint((500, 1000)),
                ),
            ),
            "levels_lower_total_threads": DictElement[SimpleLevelsConfigModel[int]](
                parameter_form=SimpleLevels(
                    title=Title("Lower thresholds on mail transfer threads"),
                    level_direction=LevelDirection.LOWER,
                    form_spec_template=Integer(),
                    prefill_levels_type=DefaultValue(LevelsType.NONE),
                    prefill_fixed_levels=InputHint((0, 0)),
                ),
            ),
        }
    )


rule_spec_cisco_sma_mail_transfer_threads = CheckParameters(
    name="cisco_sma_mail_transfer_threads",
    topic=Topic.GENERAL,
    parameter_form=_parameter_form,
    title=Title("Cisco SMA mail transfer threads"),
    condition=HostCondition(),
)
