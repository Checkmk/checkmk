#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.rulesets.v1 import Label, Title
from cmk.rulesets.v1.form_specs import (
    DataSize,
    DefaultValue,
    DictElement,
    Dictionary,
    LevelDirection,
    Levels,
    migrate_to_upper_integer_levels,
    PredictiveLevels,
    SIMagnitude,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostCondition, Topic


def _parameter_valuespec_proxmox_ve_disk_throughput():
    return Dictionary(
        elements={
            "read_levels": DictElement(
                required=True,
                parameter_form=Levels(
                    title=Title("Read levels (per second)"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=DataSize(
                        label=Label("/s"),
                        displayed_magnitudes=[SIMagnitude.MEGA],
                    ),
                    prefill_fixed_levels=DefaultValue(value=(50_000_000, 100_000_000)),
                    predictive=PredictiveLevels(
                        reference_metric="disk_read_throughput",
                        prefill_abs_diff=DefaultValue(value=(0.0, 0.0)),
                    ),
                    migrate=migrate_to_upper_integer_levels,
                ),
            ),
            "write_levels": DictElement(
                required=True,
                parameter_form=Levels(
                    title=Title("Write levels (per second)"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=DataSize(
                        label=Label("/s"),
                        displayed_magnitudes=[SIMagnitude.MEGA],
                    ),
                    prefill_fixed_levels=DefaultValue(value=(50_000_000, 100_000_000)),
                    predictive=PredictiveLevels(
                        reference_metric="disk_write_throughput",
                        prefill_abs_diff=DefaultValue(value=(0.0, 0.0)),
                    ),
                    migrate=migrate_to_upper_integer_levels,
                ),
            ),
        }
    )


rule_spec_proxmox_ve_disk_throughput = CheckParameters(
    name="proxmox_ve_disk_throughput",
    topic=Topic.VIRTUALIZATION,
    parameter_form=_parameter_valuespec_proxmox_ve_disk_throughput,
    title=Title("Proxmox VE disk throughput"),
    condition=HostCondition(),
)
