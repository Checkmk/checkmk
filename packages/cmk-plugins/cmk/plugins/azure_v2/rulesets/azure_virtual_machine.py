#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import (
    DataSize,
    DefaultValue,
    DictElement,
    Dictionary,
    Float,
    IECMagnitude,
    LevelDirection,
    SimpleLevels,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostCondition, Topic


def _make_form() -> Dictionary:
    return Dictionary(
        elements={
            "disk_read": DictElement(
                parameter_form=SimpleLevels(
                    title=Title("Disk read throughput"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=DataSize(displayed_magnitudes=[IECMagnitude.BYTE]),
                    prefill_fixed_levels=DefaultValue((1024 * 1024 * 100, 1024 * 1024 * 200)),
                )
            ),
            "disk_write": DictElement(
                parameter_form=SimpleLevels(
                    title=Title("Disk write throughput"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=DataSize(displayed_magnitudes=[IECMagnitude.BYTE]),
                    prefill_fixed_levels=DefaultValue((1024 * 1024 * 100, 1024 * 1024 * 200)),
                )
            ),
            "disk_read_ios": DictElement(
                parameter_form=SimpleLevels(
                    title=Title("Disk read operations"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Float(),
                    prefill_fixed_levels=DefaultValue((100.0, 200.0)),
                )
            ),
            "disk_write_ios": DictElement(
                parameter_form=SimpleLevels(
                    title=Title("Disk write operations"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Float(),
                    prefill_fixed_levels=DefaultValue((100.0, 200.0)),
                )
            ),
        }
    )


rule_spec_azure_v2_vm_disk = CheckParameters(
    name="azure_v2_vm_disk",
    topic=Topic.APPLICATIONS,
    parameter_form=_make_form,
    title=Title("Azure VM Disk"),
    condition=HostCondition(),
)
