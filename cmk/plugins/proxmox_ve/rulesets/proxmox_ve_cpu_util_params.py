#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    Integer,
    LevelDirection,
    Percentage,
    SimpleLevels,
    validators,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostCondition, Topic


def _parameter_rulespec_proxmox_ve_cpu_util():
    return Dictionary(
        elements={
            "util": DictElement(
                required=True,
                parameter_form=SimpleLevels(
                    title=Title("CPU Utilization levels"),
                    prefill_fixed_levels=DefaultValue(value=(90.0, 95.0)),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Percentage(),
                ),
            ),
            "average": DictElement(
                required=False,
                parameter_form=Integer(
                    title=Title("Average CPU Value over"),
                    unit_symbol="minutes",
                    prefill=DefaultValue(1),
                    custom_validate=(validators.NumberInRange(min_value=1),),
                ),
            ),
        }
    )


rule_spec_proxmox_ve_cpu_util = CheckParameters(
    name="proxmox_ve_cpu_util",
    topic=Topic.CLOUD,
    parameter_form=_parameter_rulespec_proxmox_ve_cpu_util,
    title=Title("Proxmox VE CPU Utilization"),
    condition=HostCondition(),
)
