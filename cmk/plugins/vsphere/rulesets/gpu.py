#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    Float,
    LevelDirection,
    SimpleLevels,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostAndItemCondition, Topic

rule_spec_esx_vsphere_counters_gpu_utilization = CheckParameters(
    name="esx_vsphere_counters_gpu_utilization",
    title=Title("ESX GPU Utilization"),
    topic=Topic.OPERATING_SYSTEM,
    parameter_form=lambda: Dictionary(
        elements={
            "levels_upper": DictElement(
                parameter_form=SimpleLevels[float](
                    title=Title("Upper percentage threshold for GPU utilization"),
                    form_spec_template=Float(),
                    level_direction=LevelDirection.UPPER,
                    prefill_fixed_levels=DefaultValue(value=(80.0, 90.0)),
                ),
                required=True,
            ),
        },
    ),
    condition=HostAndItemCondition(item_title=Title("GPU")),
)
