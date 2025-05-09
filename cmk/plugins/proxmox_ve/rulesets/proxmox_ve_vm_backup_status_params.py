#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.rulesets.v1 import Label, Title
from cmk.rulesets.v1.form_specs import (
    DataSize,
    DefaultValue,
    DictElement,
    Dictionary,
    LevelDirection,
    migrate_to_float_simple_levels,
    migrate_to_integer_simple_levels,
    SIMagnitude,
    SimpleLevels,
    TimeMagnitude,
    TimeSpan,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostCondition, Topic


def _parameter_valuespec_proxmox_ve_vm_backup_requirements() -> Dictionary:
    return Dictionary(
        elements={
            "age_levels_upper": DictElement(
                required=False,
                parameter_form=SimpleLevels(
                    title=Title("Age levels"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=TimeSpan(
                        displayed_magnitudes=[
                            TimeMagnitude.DAY,
                            TimeMagnitude.HOUR,
                            TimeMagnitude.MINUTE,
                        ]
                    ),
                    prefill_fixed_levels=DefaultValue(
                        value=(
                            60.0 * 60.0 * 26.0,  # a bit more than a day
                            60.0 * 60.0 * 50.0,  # a bit more than two days
                        )
                    ),
                    migrate=migrate_to_float_simple_levels,
                ),
            ),
            "duration_levels_upper": DictElement(
                required=False,
                parameter_form=SimpleLevels(
                    title=Title("Duration levels"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=TimeSpan(
                        displayed_magnitudes=[
                            TimeMagnitude.HOUR,
                            TimeMagnitude.MINUTE,
                        ]
                    ),
                    prefill_fixed_levels=DefaultValue(value=(60.0, 60.0 * 3.0)),
                    migrate=migrate_to_float_simple_levels,
                ),
            ),
            "bandwidth_levels_lower": DictElement(
                required=False,
                parameter_form=SimpleLevels(
                    title=Title("Bandwidth levels (per second)"),
                    level_direction=LevelDirection.LOWER,
                    form_spec_template=DataSize(
                        label=Label("/s"),
                        displayed_magnitudes=[SIMagnitude.MEGA],
                    ),
                    prefill_fixed_levels=DefaultValue(value=(10_000_000, 5_000_000)),
                    migrate=lambda v: migrate_to_integer_simple_levels(v, scale=1000 * 1000),
                ),
            ),
        }
    )


rule_spec_proxmox_ve_vm_backup_status = CheckParameters(
    name="proxmox_ve_vm_backup_status",
    topic=Topic.VIRTUALIZATION,
    parameter_form=_parameter_valuespec_proxmox_ve_vm_backup_requirements,
    title=Title("Proxmox VE VM Backup"),
    condition=HostCondition(),
)
