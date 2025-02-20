#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.rulesets.v1 import Help, Label, Title
from cmk.rulesets.v1.form_specs import (
    DataSize,
    DefaultValue,
    DictElement,
    Dictionary,
    Float,
    LevelDirection,
    Levels,
    migrate_to_upper_float_levels,
    migrate_to_upper_integer_levels,
    PredictiveLevels,
    SIMagnitude,
    String,
    TimeMagnitude,
    TimeSpan,
    validators,
)
from cmk.rulesets.v1.rule_specs import (
    CheckParameters,
    HostAndItemCondition,
    Topic,
)


def _parameter_form() -> Dictionary:
    return Dictionary(
        migrate=_migrate,
        elements={
            "read_throughput": DictElement(
                parameter_form=Levels(
                    title=Title("Read throughput"),
                    form_spec_template=DataSize(
                        label=Label("/s"),
                        displayed_magnitudes=[SIMagnitude.MEGA],
                    ),
                    level_direction=LevelDirection.UPPER,
                    prefill_fixed_levels=DefaultValue((50_000_000, 100_000_000)),
                    predictive=PredictiveLevels(
                        reference_metric="read_throughput",
                        prefill_abs_diff=DefaultValue((0.0, 0.0)),
                    ),
                    migrate=migrate_to_upper_integer_levels,
                ),
            ),
            "write_throughput": DictElement(
                parameter_form=Levels(
                    title=Title("Write throughput"),
                    form_spec_template=DataSize(
                        label=Label("/s"),
                        displayed_magnitudes=[SIMagnitude.MEGA],
                    ),
                    level_direction=LevelDirection.UPPER,
                    prefill_fixed_levels=DefaultValue((50_000_000, 100_000_000)),
                    predictive=PredictiveLevels(
                        reference_metric="read_throughput",
                        prefill_abs_diff=DefaultValue((0.0, 0.0)),
                    ),
                    migrate=migrate_to_upper_integer_levels,
                ),
            ),
            "average": DictElement(
                parameter_form=TimeSpan(
                    title=Title("Average"),
                    help_text=Help(
                        "When averaging is set, a floating average value "
                        "of the disk throughput is computed and the levels for read "
                        "and write will be applied to the average instead of the current "
                        "value."
                    ),
                    custom_validate=(validators.NumberInRange(min_value=60),),
                    displayed_magnitudes=[TimeMagnitude.MINUTE],
                    prefill=DefaultValue(5 * 60),
                    migrate=_migrate_average_to_seconds,
                )
            ),
            "latency": DictElement(
                parameter_form=Levels(
                    title=Title("IO latency"),
                    form_spec_template=TimeSpan(displayed_magnitudes=[TimeMagnitude.MILLISECOND]),
                    level_direction=LevelDirection.UPPER,
                    prefill_fixed_levels=DefaultValue((0.08, 0.16)),
                    predictive=PredictiveLevels(
                        reference_metric="latency",
                        prefill_abs_diff=DefaultValue((0.0, 0.0)),
                    ),
                    migrate=migrate_to_upper_float_levels,
                ),
            ),
            "read_ql": DictElement(
                parameter_form=Levels(
                    title=Title("Read queue length"),
                    form_spec_template=Float(),
                    level_direction=LevelDirection.UPPER,
                    prefill_fixed_levels=DefaultValue((80.0, 90.0)),
                    predictive=PredictiveLevels(
                        reference_metric="read_ql",
                        prefill_abs_diff=DefaultValue((0.0, 0.0)),
                    ),
                    migrate=migrate_to_upper_float_levels,
                ),
            ),
            "write_ql": DictElement(
                parameter_form=Levels(
                    title=Title("Write queue length"),
                    form_spec_template=Float(),
                    level_direction=LevelDirection.UPPER,
                    prefill_fixed_levels=DefaultValue((80.0, 90.0)),
                    predictive=PredictiveLevels(
                        reference_metric="write_ql",
                        prefill_abs_diff=DefaultValue((0.0, 0.0)),
                    ),
                    migrate=migrate_to_upper_float_levels,
                ),
            ),
            "read_ios": DictElement(
                parameter_form=Levels(
                    title=Title("Read operations"),
                    form_spec_template=Float(unit_symbol="/s"),
                    level_direction=LevelDirection.UPPER,
                    prefill_fixed_levels=DefaultValue((400.0, 600.0)),
                    predictive=PredictiveLevels(
                        reference_metric="read_ios",
                        prefill_abs_diff=DefaultValue((0.0, 0.0)),
                    ),
                    migrate=migrate_to_upper_float_levels,
                ),
            ),
            "write_ios": DictElement(
                parameter_form=Levels(
                    title=Title("Write operations"),
                    form_spec_template=Float(unit_symbol="/s"),
                    level_direction=LevelDirection.UPPER,
                    prefill_fixed_levels=DefaultValue((300.0, 400.0)),
                    predictive=PredictiveLevels(
                        reference_metric="write_ios",
                        prefill_abs_diff=DefaultValue((0.0, 0.0)),
                    ),
                    migrate=migrate_to_upper_float_levels,
                ),
            ),
        },
    )


rule_spec_disk_io = CheckParameters(
    name="disk_io",
    title=Title("Disk IO levels (old style checks)"),
    topic=Topic.STORAGE,
    parameter_form=_parameter_form,
    condition=HostAndItemCondition(
        item_title=Title("Device"),
        item_form=String(
            help_text=Help(
                "For a summarized throughput of all disks, specify <tt>SUMMARY</tt>, for a "
                "sum of read or write throughput write <tt>read</tt> or <tt>write</tt> resp. "
                "A per-disk IO is specified by the drive letter, a colon and a slash on Windows "
                "(e.g. <tt>C:/</tt>) or by the device name on Linux/UNIX (e.g. <tt>/dev/sda</tt>)."
            ),
        ),
    ),
)


def _migrate(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        raise TypeError(value)
    return {
        k: v
        for k, v in value.items()
        if k
        in {
            "read_throughput",
            "write_throughput",
            "average",
            "latency",
            "read_ql",
            "write_ql",
            "read_ios",
            "write_ios",
        }
    }


def _migrate_average_to_seconds(value: object) -> float:
    if isinstance(value, float):
        return value
    if isinstance(value, int):
        return value * 60.0
    raise TypeError(value)
