#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    LevelDirection,
    Percentage,
    SimpleLevels,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostCondition, Topic

# mypy: disable-error-code="no-untyped-def"


def _parameter_valuespec_proxmox_ve_node_cpu_allocation():
    return Dictionary(
        elements={
            "cpu_allocation_ratio": DictElement(
                required=True,
                parameter_form=SimpleLevels(
                    title=Title("CPU allocation ratio"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Percentage(),
                    prefill_fixed_levels=DefaultValue(value=(150, 200)),
                ),
            )
        }
    )


rule_spec_proxmox_ve_node_cpu_allocation = CheckParameters(
    name="proxmox_ve_node_cpu_allocation",
    topic=Topic.VIRTUALIZATION,
    parameter_form=_parameter_valuespec_proxmox_ve_node_cpu_allocation,
    title=Title("Proxmox VE Node CPU Allocation"),
    condition=HostCondition(),
)
