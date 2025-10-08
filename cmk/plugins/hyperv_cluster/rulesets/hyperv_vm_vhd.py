#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import (
    CascadingSingleChoice,
    CascadingSingleChoiceElement,
    DataSize,
    DictElement,
    Dictionary,
    IECMagnitude,
    InputHint,
    LevelDirection,
    Percentage,
    SimpleLevels,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostAndItemCondition, Topic

rule_spec_hyperv_vm_vhd = CheckParameters(
    name="hyperv_vm_vhd",
    title=Title("Hyper-V VM VHD"),
    topic=Topic.STORAGE,
    condition=HostAndItemCondition(item_title=Title("Disk")),
    parameter_form=lambda: Dictionary(
        elements={
            "size_limit": DictElement(
                required=False,
                parameter_form=CascadingSingleChoice(
                    title=Title("Max size for image file"),
                    elements=[
                        CascadingSingleChoiceElement(
                            name="relative",
                            title=Title("Max size for image file (relative to max disk size)"),
                            parameter_form=SimpleLevels(
                                level_direction=LevelDirection.UPPER,
                                form_spec_template=Percentage(),
                                prefill_fixed_levels=InputHint(value=(80, 90)),
                            ),
                        ),
                        CascadingSingleChoiceElement(
                            name="absolute",
                            title=Title("Max size for image file (absolute value)"),
                            parameter_form=SimpleLevels(
                                level_direction=LevelDirection.UPPER,
                                form_spec_template=DataSize(
                                    displayed_magnitudes=[
                                        IECMagnitude.MEBI,
                                        IECMagnitude.GIBI,
                                        IECMagnitude.TEBI,
                                    ]
                                ),
                                prefill_fixed_levels=InputHint(value=(16 * 1024**3, 32 * 1024**3)),
                            ),
                        ),
                    ],
                ),
            )
        }
    ),
)
