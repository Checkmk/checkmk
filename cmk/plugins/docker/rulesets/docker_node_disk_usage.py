#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    DataSize,
    DictElement,
    Dictionary,
    IECMagnitude,
    InputHint,
    Integer,
    LevelDirection,
    migrate_to_integer_simple_levels,
    SimpleLevels,
    SingleChoice,
    SingleChoiceElement,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostAndItemCondition, Topic

_MAGNITUDES = tuple(IECMagnitude)[:4]


def _parameter_form_docker_node_disk_usage() -> Dictionary:
    return Dictionary(
        help_text=Help(
            "Allows to define levels for the counts and size of Docker containers, images, "
            "local volumes, and the build cache."
        ),
        elements={
            "size": DictElement(
                parameter_form=SimpleLevels(
                    title=Title("Size"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=DataSize(displayed_magnitudes=_MAGNITUDES),
                    prefill_fixed_levels=InputHint((0, 0)),
                    migrate=migrate_to_integer_simple_levels,
                ),
            ),
            "reclaimable": DictElement(
                parameter_form=SimpleLevels(
                    title=Title("Reclaimable"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=DataSize(displayed_magnitudes=_MAGNITUDES),
                    prefill_fixed_levels=InputHint((0, 0)),
                    migrate=migrate_to_integer_simple_levels,
                ),
            ),
            "count": DictElement(
                parameter_form=SimpleLevels(
                    title=Title("Total count"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Integer(),
                    prefill_fixed_levels=InputHint((0, 0)),
                    migrate=migrate_to_integer_simple_levels,
                ),
            ),
            "active": DictElement(
                parameter_form=SimpleLevels(
                    title=Title("Active"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Integer(),
                    prefill_fixed_levels=InputHint((0, 0)),
                    migrate=migrate_to_integer_simple_levels,
                ),
            ),
        },
    )


rule_spec_docker_node_disk_usage = CheckParameters(
    name="docker_node_disk_usage",
    title=Title("Docker node disk usage"),
    topic=Topic.APPLICATIONS,
    parameter_form=_parameter_form_docker_node_disk_usage,
    condition=HostAndItemCondition(
        item_title=Title("Type"),
        item_form=SingleChoice(
            elements=[
                SingleChoiceElement(name="buildcache", title=Title("Build cache")),
                SingleChoiceElement(name="containers", title=Title("Containers")),
                SingleChoiceElement(name="images", title=Title("Images")),
                SingleChoiceElement(name="volumes", title=Title("Local Volumes")),
            ],
        ),
    ),
)
