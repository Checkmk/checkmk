#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.rulesets.v1 import Help, Label, Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    LevelDirection,
    SimpleLevels,
    String,
    TimeMagnitude,
    TimeSpan,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostCondition, Topic

# mypy: disable-error-code="no-untyped-def"


def _parameter_valuespec_proxmox_ve_vm_info():
    return Dictionary(
        title=Title("Check Parameter"),
        elements={
            "required_vm_status": DictElement(
                required=False,
                parameter_form=String(
                    title=Title("Modify: Check VM Status (off: ignore VM status)"),
                    label=Label("Warn if VM status value is not"),
                    prefill=DefaultValue("running"),
                    migrate=lambda v: "" if v is None else str(v),
                ),
            ),
            "lock_duration": DictElement(
                required=True,
                parameter_form=SimpleLevels[float](
                    title=Title("Lock Duration levels"),
                    help_text=Help(
                        "If the VM is locked longer than the defined levels, "
                        "a warning/critical state is triggered."
                        "If this is set to 'No Levels', the lock duration is not checked."
                    ),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=TimeSpan(
                        displayed_magnitudes=[
                            TimeMagnitude.HOUR,
                            TimeMagnitude.MINUTE,
                        ]
                    ),
                    prefill_fixed_levels=DefaultValue(value=(15 * 60, 30 * 60)),
                ),
            ),
        },
    )


rule_spec_proxmox_ve_vm_info = CheckParameters(
    name="proxmox_ve_vm_info",
    topic=Topic.CLOUD,
    parameter_form=_parameter_valuespec_proxmox_ve_vm_info,
    title=Title("Proxmox VE VM Info"),
    condition=HostCondition(),
)
