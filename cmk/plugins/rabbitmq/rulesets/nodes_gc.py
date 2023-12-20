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
    FixedLevels,
    Float,
    Integer,
    Levels,
    Migrate,
    TextInput,
)
from cmk.rulesets.v1.rule_specs import CheckParameterWithItem, Topic


def _migrate_lower_upper(
    value: dict, lower_key: str, upper_key: str
) -> Mapping[str, tuple[str, tuple[int, int] | tuple[float, float] | None]]:
    migrated = {"levels_lower": ("no_levels", None), "levels_upper": ("no_levels", None)}
    if (lower_value := value.get(lower_key)) is not None:
        migrated["levels_lower"] = lower_value
    if (upper_Value := value.get(upper_key)) is not None:
        migrated["levels_upper"] = upper_Value
    return migrated


def _migrate_levels(
    value: object,
) -> Mapping[str, Mapping[str, tuple[str, tuple[int, int] | tuple[float, float] | None]]]:
    if not isinstance(value, dict):
        raise TypeError(value)
    migrated = value.copy()
    if "gc_num_upper" in value:
        migrated["gc_num"] = {
            "levels_lower": ("no_levels", None),
            "levels_upper": ("fixed", migrated.pop("gc_num_upper")),
        }
    if "gc_num_rate_lower" in value or "gc_num_rate_upper" in value:
        migrated["gc_num_rate"] = _migrate_lower_upper(
            value, "gc_num_rate_lower", "gc_num_rate_upper"
        )
    if "gc_bytes_reclaimed_upper" in value:
        migrated["gc_bytes_reclaimed"] = {
            "levels_lower": ("no_levels", None),
            "levels_upper": ("fixed", migrated.pop("gc_bytes_reclaimed_upper")),
        }
    if "gc_bytes_reclaimed_rate_lower" in value or "gc_bytes_reclaimed_rate_upper" in value:
        migrated["gc_bytes_reclaimed_rate"] = _migrate_lower_upper(
            value, "gc_bytes_reclaimed_rate_lower", "gc_bytes_reclaimed_rate_upper"
        )
    if "runqueue_lower" in value or "runqueue_upper" in value:
        migrated["runqueue"] = _migrate_lower_upper(value, "runqueue_lower", "runqueue_upper")

    return migrated


def _parameter_form_rabbitmq_nodes_gc() -> Dictionary:
    return Dictionary(
        elements={
            "gc_num": DictElement(
                parameter_form=Levels(
                    form_spec=Integer,
                    lower=None,
                    upper=(FixedLevels(), None),
                    title=Localizable("Levels for total number of GC runs"),
                    unit=Localizable("runs"),
                )
            ),
            "gc_num_rate": DictElement(
                parameter_form=Levels(
                    form_spec=Float,
                    lower=(FixedLevels(), None),
                    upper=(FixedLevels(), None),
                    title=Localizable("Levels for GC run rate"),
                    unit=Localizable("1/s"),
                )
            ),
            "gc_bytes_reclaimed": DictElement(
                parameter_form=Levels(
                    form_spec=DataSize,
                    lower=None,
                    upper=(FixedLevels(), None),
                    title=Localizable("Absolute levels for memory reclaimed by GC"),
                )
            ),
            "gc_bytes_reclaimed_rate": DictElement(
                parameter_form=Levels(
                    form_spec=DataSize,
                    lower=(FixedLevels(), None),
                    upper=(FixedLevels(), None),
                    title=Localizable("Levels for rate of memory per second reclaimed by GC"),
                )
            ),
            "runqueue": DictElement(
                parameter_form=Levels(
                    form_spec=Integer,
                    lower=(FixedLevels(), None),
                    upper=(FixedLevels(), None),
                    title=Localizable("Levels for runtime run queue"),
                )
            ),
        },
        transform=Migrate(raw_to_form=_migrate_levels),
    )


rule_spec_rabbitmq_nodes_gc = CheckParameterWithItem(
    name="rabbitmq_nodes_gc",
    topic=Topic.APPLICATIONS,
    item_form=TextInput(title=Localizable("Node name")),
    parameter_form=_parameter_form_rabbitmq_nodes_gc,
    title=Localizable("RabbitMQ nodes GC"),
)
