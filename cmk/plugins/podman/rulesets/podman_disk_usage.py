#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="type-arg"


from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    DataSize,
    DictElement,
    Dictionary,
    IECMagnitude,
    InputHint,
    Integer,
    LevelDirection,
    SimpleLevels,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostAndItemCondition, Topic

MAGNITUDES = tuple(IECMagnitude)[:4]


def _valuespec_disk_usage(property: str, reclaimable: bool) -> DictElement:
    elements = {
        "size_upper": DictElement(
            required=False,
            parameter_form=SimpleLevels(
                title=Title("Total size upper levels"),
                form_spec_template=DataSize(displayed_magnitudes=MAGNITUDES),
                level_direction=LevelDirection.UPPER,
                prefill_fixed_levels=InputHint((0, 0)),
            ),
        ),
        "total": DictElement(
            required=False,
            parameter_form=SimpleLevels(
                title=Title(  # astrein: disable=localization-checker
                    f"Total number of {property} upper levels"
                ),
                form_spec_template=Integer(),
                level_direction=LevelDirection.UPPER,
                prefill_fixed_levels=InputHint((0, 0)),
            ),
        ),
        "active": DictElement(
            required=False,
            parameter_form=SimpleLevels(
                title=Title(  # astrein: disable=localization-checker
                    f"Total number of active {property} upper levels"
                ),
                form_spec_template=Integer(),
                level_direction=LevelDirection.UPPER,
                prefill_fixed_levels=InputHint((0, 0)),
            ),
        ),
    }

    if reclaimable:
        elements["reclaimable_upper"] = DictElement(
            required=False,
            parameter_form=SimpleLevels(
                title=Title("Total reclaimable size upper levels"),
                form_spec_template=DataSize(displayed_magnitudes=MAGNITUDES),
                level_direction=LevelDirection.UPPER,
                prefill_fixed_levels=InputHint((0, 0)),
            ),
        )

    return DictElement(
        required=False,
        parameter_form=Dictionary(
            title=Title(f"{property.capitalize()} "),  # astrein: disable=localization-checker
            elements=elements,
        ),
    )


def podman_disk_usage() -> Dictionary:
    return Dictionary(
        help_text=Help("Thresholds for the podman disk usage services."),
        elements={
            "containers": _valuespec_disk_usage("containers", reclaimable=True),
            "images": _valuespec_disk_usage("images", reclaimable=False),
            "volumes": _valuespec_disk_usage("volumes", reclaimable=True),
        },
    )


rule_spec_podman_disk_usage = CheckParameters(
    name="podman_disk_usage",
    title=Title("Podman disk usage"),
    topic=Topic.APPLICATIONS,
    parameter_form=podman_disk_usage,
    condition=HostAndItemCondition(item_title=Title("Item name")),
)
