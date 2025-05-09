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
    SimpleLevels,
    TimeMagnitude,
    TimeSpan,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostCondition, Topic


def _parameter_valuespec_proxmox_ve_snapshot_age_requirements():
    return Dictionary(
        elements={
            "oldest_levels": DictElement(
                required=True,
                parameter_form=SimpleLevels(
                    title=Title("Max age of the oldest snapshot"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=TimeSpan(
                        displayed_magnitudes=[
                            TimeMagnitude.DAY,
                            TimeMagnitude.HOUR,
                        ]
                    ),
                    prefill_fixed_levels=DefaultValue(
                        value=(60.0 * 60.0 * 24.0, 60.0 * 60.0 * 24.0 * 2.0)
                    ),
                    migrate=migrate_to_float_simple_levels,
                ),
            )
        }
    )


rule_spec_proxmox_ve_vm_snapshot_age = CheckParameters(
    name="proxmox_ve_vm_snapshot_age",
    topic=Topic.VIRTUALIZATION,
    parameter_form=_parameter_valuespec_proxmox_ve_snapshot_age_requirements,
    title=Title("Proxmox VE VM Snapshot Age"),
    condition=HostCondition(),
)
