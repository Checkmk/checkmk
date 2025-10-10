#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    LevelDirection,
    migrate_to_float_simple_levels,
    Percentage,
    SimpleLevels,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostCondition, Topic

# mypy: disable-error-code="no-untyped-def"


def _parameter_rulespec_proxmox_ve_mem_usage():
    return Dictionary(
        elements={
            "levels": DictElement(
                required=True,
                parameter_form=SimpleLevels(
                    title=Title("Levels"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Percentage(),
                    prefill_fixed_levels=DefaultValue(value=(80.0, 90.0)),
                    migrate=migrate_to_float_simple_levels,
                ),
            )
        }
    )


rule_spec_proxmox_ve_mem_usage = CheckParameters(
    name="proxmox_ve_mem_usage",
    topic=Topic.VIRTUALIZATION,
    parameter_form=_parameter_rulespec_proxmox_ve_mem_usage,
    title=Title("Proxmox VE memory percentage used"),
    condition=HostCondition(),
)
