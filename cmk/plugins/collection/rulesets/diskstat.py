#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import Final

from cmk.rulesets.v1 import Help, Label, Title
from cmk.rulesets.v1.form_specs import (
    BooleanChoice,
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
    SingleChoice,
    SingleChoiceElement,
    String,
    TimeMagnitude,
    TimeSpan,
)
from cmk.rulesets.v1.form_specs.validators import NumberInRange
from cmk.rulesets.v1.rule_specs import (
    CheckParameters,
    DiscoveryParameters,
    HostAndItemCondition,
    Topic,
)

_MB = 1000**2


def migrate_diskstat_inventory(value: object) -> Mapping[str, object]:
    if not isinstance(value, dict):
        raise TypeError(value)

    if isinstance((physical := value.get("physical")), str):
        return value

    return {
        **{f: f in value and value[f] for f in ("summary", "lvm", "vxvm", "diskless")},
        **({} if physical is None else {"physical": "name"}),
    }


def _valuespec_diskstat_inventory() -> Dictionary:
    return Dictionary(
        elements={
            "summary": DictElement(
                required=True,
                parameter_form=BooleanChoice(
                    prefill=DefaultValue(True),
                    title=Title("Summary"),
                    label=Label("Create a summary over all physical disks"),
                ),
            ),
            "physical": DictElement(
                required=False,
                parameter_form=SingleChoice(
                    title=Title("Create a separate check for each physical disk"),
                    elements=[
                        SingleChoiceElement(
                            name="wwn",
                            title=Title("Use World Wide Name (WWN) as service name"),
                        ),
                        SingleChoiceElement(
                            name="name",
                            title=Title("Use device name as service name"),
                        ),
                    ],
                    prefill=DefaultValue("wwn"),
                    help_text=Help(
                        "Using device name as service name isn't recommended. "
                        "Device names aren't persistent and can change after a reboot or an update. "
                        "In case WWN is not available, device name will be used."
                    ),
                ),
            ),
            "lvm": DictElement(
                required=True,
                parameter_form=BooleanChoice(
                    prefill=DefaultValue(False),
                    title=Title("LVM volumes (Linux)"),
                    label=Label("Create a separate check for each LVM volume (Linux)"),
                ),
            ),
            "vxvm": DictElement(
                required=True,
                parameter_form=BooleanChoice(
                    prefill=DefaultValue(False),
                    title=Title("VxVM volumes (Linux)"),
                    label=Label("Create a separate check for each VxVM volume (Linux)"),
                ),
            ),
            "diskless": DictElement(
                required=True,
                parameter_form=BooleanChoice(
                    prefill=DefaultValue(False),
                    title=Title("Partitions (XEN)"),
                    label=Label("Create a separate check for each partition (XEN)"),
                ),
            ),
        },
        migrate=migrate_diskstat_inventory,
    )


rule_spec_diskstat_inventory = DiscoveryParameters(
    topic=Topic.GENERAL,
    name="diskstat_inventory",
    title=Title("Disk IO discovery"),
    parameter_form=_valuespec_diskstat_inventory,
)


def _item_spec_diskstat() -> String:
    return String(
        help_text=Help(
            "For a summarized throughput of all disks, specify <tt>SUMMARY</tt>,  "
            "a per-disk IO is specified by the drive letter, a colon and a slash on Windows "
            "(e.g. <tt>C:/</tt>) or by the device name on Linux/UNIX (e.g. <tt>/dev/sda</tt>)."
        ),
    )


_KEY_MAP: Final = {
    "read": "read_throughput",
    "write": "write_throughput",
    "read_wait": "average_read_wait",
    "write_wait": "average_write_wait",
}


def rename_amd_remove_conversion_arg(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        raise TypeError(f"Invalid value {value!r}")

    value.pop("_NEEDS_CONVERSION", None)

    return {_KEY_MAP.get(k, k): v for k, v in value.items() if isinstance(k, str)}


def migrate_to_float(value: object) -> float:
    match value:
        case int(value) | float(value):
            return float(value)
    raise ValueError(value)


def _parameter_valuespec_diskstat() -> Dictionary:
    return Dictionary(
        elements={
            "read_throughput": DictElement(
                required=False,
                parameter_form=Levels(
                    title=Title("Read throughput"),
                    form_spec_template=DataSize(
                        label=Label("/sec"),
                        displayed_magnitudes=[SIMagnitude.MEGA],
                    ),
                    level_direction=LevelDirection.UPPER,
                    prefill_fixed_levels=DefaultValue((50 * _MB, 100 * _MB)),
                    predictive=PredictiveLevels(
                        reference_metric="disk_read_throughput",
                        prefill_abs_diff=DefaultValue((0.0, 0.0)),
                    ),
                    migrate=migrate_to_upper_integer_levels,
                ),
            ),
            "write_throughput": DictElement(
                required=False,
                parameter_form=Levels(
                    title=Title("Write throughput"),
                    form_spec_template=DataSize(
                        label=Label("/sec"),
                        displayed_magnitudes=[SIMagnitude.MEGA],
                    ),
                    level_direction=LevelDirection.UPPER,
                    prefill_fixed_levels=DefaultValue((50 * _MB, 100 * _MB)),
                    predictive=PredictiveLevels(
                        reference_metric="disk_write_throughput",
                        prefill_abs_diff=DefaultValue((0.0, 0.0)),
                    ),
                    migrate=migrate_to_upper_integer_levels,
                ),
            ),
            "utilization": DictElement(
                required=False,
                parameter_form=Levels(
                    title=Title("Disk Utilization"),
                    form_spec_template=Float(
                        custom_validate=(NumberInRange(min_value=0.0, max_value=1.0),),
                    ),
                    level_direction=LevelDirection.UPPER,
                    prefill_fixed_levels=DefaultValue((0.8, 0.9)),
                    predictive=PredictiveLevels(
                        reference_metric="disk_utilization",
                        prefill_abs_diff=DefaultValue((0.0, 0.0)),
                    ),
                    migrate=migrate_to_upper_float_levels,
                ),
            ),
            "latency": DictElement(
                required=False,
                parameter_form=Levels(
                    title=Title("Disk Latency"),
                    form_spec_template=TimeSpan(displayed_magnitudes=[TimeMagnitude.MILLISECOND]),
                    level_direction=LevelDirection.UPPER,
                    prefill_fixed_levels=DefaultValue((0.08, 0.16)),
                    predictive=PredictiveLevels(
                        reference_metric="disk_latency",
                        prefill_abs_diff=DefaultValue((0.0, 0.0)),
                    ),
                    migrate=migrate_to_upper_float_levels,
                ),
            ),
            "read_latency": DictElement(
                required=False,
                parameter_form=Levels(
                    title=Title("Disk Read Latency"),
                    form_spec_template=TimeSpan(displayed_magnitudes=[TimeMagnitude.MILLISECOND]),
                    level_direction=LevelDirection.UPPER,
                    prefill_fixed_levels=DefaultValue((0.08, 0.16)),
                    predictive=PredictiveLevels(
                        reference_metric="disk_read_latency",
                        prefill_abs_diff=DefaultValue((0.0, 0.0)),
                    ),
                    migrate=migrate_to_upper_float_levels,
                ),
            ),
            "write_latency": DictElement(
                required=False,
                parameter_form=Levels(
                    title=Title("Disk Write Latency"),
                    form_spec_template=TimeSpan(displayed_magnitudes=[TimeMagnitude.MILLISECOND]),
                    level_direction=LevelDirection.UPPER,
                    prefill_fixed_levels=DefaultValue((0.08, 0.16)),
                    predictive=PredictiveLevels(
                        reference_metric="disk_write_latency",
                        prefill_abs_diff=DefaultValue((0.0, 0.0)),
                    ),
                    migrate=migrate_to_upper_float_levels,
                ),
            ),
            "average_read_wait": DictElement(
                required=False,
                parameter_form=Levels(
                    title=Title("Read wait"),
                    form_spec_template=TimeSpan(displayed_magnitudes=[TimeMagnitude.MILLISECOND]),
                    level_direction=LevelDirection.UPPER,
                    prefill_fixed_levels=DefaultValue((0.03, 0.05)),
                    predictive=PredictiveLevels(
                        reference_metric="disk_average_read_wait",
                        prefill_abs_diff=DefaultValue((0.0, 0.0)),
                    ),
                    migrate=migrate_to_upper_float_levels,
                ),
            ),
            "average_write_wait": DictElement(
                required=False,
                parameter_form=Levels(
                    title=Title("Write wait"),
                    form_spec_template=TimeSpan(displayed_magnitudes=[TimeMagnitude.MILLISECOND]),
                    level_direction=LevelDirection.UPPER,
                    prefill_fixed_levels=DefaultValue((0.03, 0.05)),
                    predictive=PredictiveLevels(
                        reference_metric="disk_average_write_wait",
                        prefill_abs_diff=DefaultValue((0.0, 0.0)),
                    ),
                    migrate=migrate_to_upper_float_levels,
                ),
            ),
            "average": DictElement(
                required=False,
                parameter_form=TimeSpan(
                    title=Title("Averaging"),
                    displayed_magnitudes=[
                        TimeMagnitude.DAY,
                        TimeMagnitude.HOUR,
                        TimeMagnitude.MINUTE,
                        TimeMagnitude.SECOND,
                    ],
                    help_text=Help(
                        "When averaging is set, then all of the disk's metrics are averaged "
                        "over the selected interval - rather then the check interval. This allows "
                        "you to make your monitoring less reactive to short peaks. But it will also "
                        "introduce a loss of accuracy in your graphs. "
                    ),
                    prefill=DefaultValue(300.0),
                    migrate=migrate_to_float,
                ),
            ),
            "read_ios": DictElement(
                required=False,
                parameter_form=Levels(
                    title=Title("Read operations"),
                    form_spec_template=Float(unit_symbol="1/s"),
                    level_direction=LevelDirection.UPPER,
                    prefill_fixed_levels=DefaultValue((400.0, 600.0)),
                    predictive=PredictiveLevels(
                        reference_metric="disk_read_ios",
                        prefill_abs_diff=DefaultValue((0.0, 0.0)),
                    ),
                    migrate=migrate_to_upper_float_levels,
                ),
            ),
            "write_ios": DictElement(
                required=False,
                parameter_form=Levels(
                    title=Title("Write operations"),
                    form_spec_template=Float(unit_symbol="1/s"),
                    level_direction=LevelDirection.UPPER,
                    prefill_fixed_levels=DefaultValue((300.0, 400.0)),
                    predictive=PredictiveLevels(
                        reference_metric="disk_write_ios",
                        prefill_abs_diff=DefaultValue((0.0, 0.0)),
                    ),
                    migrate=migrate_to_upper_float_levels,
                ),
            ),
        },
        migrate=rename_amd_remove_conversion_arg,
    )


rule_spec_diskstat = CheckParameters(
    name="diskstat",
    title=Title("Disk IO levels"),
    topic=Topic.STORAGE,
    parameter_form=_parameter_valuespec_diskstat,
    condition=HostAndItemCondition(item_title=Title("Device"), item_form=_item_spec_diskstat()),
)
