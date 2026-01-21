#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    LevelDirection,
    SimpleLevels,
    SimpleLevelsConfigModel,
    TimeMagnitude,
    TimeSpan,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostAndItemCondition, Topic


def _netapp_system_time_offset() -> Dictionary:
    return Dictionary(
        elements={
            "upper_levels": DictElement[SimpleLevelsConfigModel[float]](
                required=True,
                parameter_form=SimpleLevels(
                    title=Title("Levels on absolute time offset"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=TimeSpan(
                        displayed_magnitudes=[
                            TimeMagnitude.HOUR,
                            TimeMagnitude.MINUTE,
                            TimeMagnitude.SECOND,
                        ],
                    ),
                    prefill_fixed_levels=DefaultValue((30, 60)),
                ),
            )
        }
    )


rule_spec_netapp_system_time_offset = CheckParameters(
    name="netapp_system_time_offset",
    title=Title("Netapp system time offset"),
    topic=Topic.STORAGE,
    parameter_form=_netapp_system_time_offset,
    condition=HostAndItemCondition(item_title=Title("Node")),
)
