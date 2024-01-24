#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Mapping

from cmk.rulesets.v1 import Localizable
from cmk.rulesets.v1.form_specs import (
    DataSize,
    DictElement,
    Dictionary,
    Float,
    Integer,
    LevelDirection,
    Levels,
    Migrate,
    Text,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostAndItemCondition, Topic


def _migrate_levels(
    value: object,
) -> Mapping[str, tuple[str, tuple[int, int] | tuple[float, float] | None]]:
    if not isinstance(value, dict):
        raise TypeError(value)

    migrated = {}

    for key, levels in value.items():
        if not isinstance(levels, tuple):
            raise TypeError(value)

        if levels[0] not in ("no_levels", "fixed"):
            migrated[key] = ("fixed", levels)
        else:
            migrated[key] = levels

    return migrated


def _parameter_form_rabbitmq_nodes_gc() -> Dictionary:
    return Dictionary(
        elements={
            "gc_num_upper": DictElement(
                parameter_form=Levels(
                    form_spec=Integer,
                    level_direction=LevelDirection.UPPER,
                    predictive=None,
                    title=Localizable("Upper level for total number of GC runs"),
                    unit=Localizable("runs"),
                )
            ),
            "gc_num_rate_upper": DictElement(
                parameter_form=Levels(
                    form_spec=Float,
                    level_direction=LevelDirection.UPPER,
                    predictive=None,
                    title=Localizable("Upper level for GC run rate"),
                    unit=Localizable("1/s"),
                )
            ),
            "gc_num_rate_lower": DictElement(
                parameter_form=Levels(
                    form_spec=Float,
                    level_direction=LevelDirection.LOWER,
                    predictive=None,
                    title=Localizable("Lower level for GC run rate"),
                    unit=Localizable("1/s"),
                )
            ),
            "gc_bytes_reclaimed_upper": DictElement(
                parameter_form=Levels(
                    form_spec=DataSize,
                    level_direction=LevelDirection.UPPER,
                    predictive=None,
                    title=Localizable("Absolute levels for memory reclaimed by GC"),
                )
            ),
            "gc_bytes_reclaimed_rate_upper": DictElement(
                parameter_form=Levels(
                    form_spec=DataSize,
                    level_direction=LevelDirection.UPPER,
                    predictive=None,
                    title=Localizable("Upper level for rate of memory reclaimed by GC"),
                )
            ),
            "gc_bytes_reclaimed_rate_lower": DictElement(
                parameter_form=Levels(
                    form_spec=DataSize,
                    level_direction=LevelDirection.LOWER,
                    predictive=None,
                    title=Localizable("Lower level for rate of memory reclaimed by GC"),
                )
            ),
            "runqueue_upper": DictElement(
                parameter_form=Levels(
                    form_spec=Integer,
                    level_direction=LevelDirection.UPPER,
                    predictive=None,
                    title=Localizable("Upper level for runtime run queue"),
                )
            ),
            "runqueue_lower": DictElement(
                parameter_form=Levels(
                    form_spec=Integer,
                    level_direction=LevelDirection.LOWER,
                    predictive=None,
                    title=Localizable("Lower level for runtime run queue"),
                )
            ),
        },
        transform=Migrate(model_to_form=_migrate_levels),
    )


rule_spec_rabbitmq_nodes_gc = CheckParameters(
    name="rabbitmq_nodes_gc",
    topic=Topic.APPLICATIONS,
    parameter_form=_parameter_form_rabbitmq_nodes_gc,
    title=Localizable("RabbitMQ nodes GC"),
    condition=HostAndItemCondition(item_form=Text(title=Localizable("Node name"))),
)
