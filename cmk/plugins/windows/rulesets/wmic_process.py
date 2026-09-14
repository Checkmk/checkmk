#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    Float,
    LevelDirection,
    LevelsType,
    Percentage,
    SimpleLevels,
    String,
    validators,
)
from cmk.rulesets.v1.rule_specs import EnforcedService, HostAndItemCondition, Topic


def _make_form() -> Dictionary:
    return Dictionary(
        help_text=Help(
            "This rule monitors the accumulated memory, page file and CPU usage of all "
            "Windows processes sharing the configured name."
        ),
        elements={
            "name": DictElement(
                required=False,
                parameter_form=String(
                    title=Title("Name of the process"),
                    help_text=Help(
                        "The process name as reported by WMI, for example <tt>notepad.exe</tt>. "
                        "Matching is case insensitive."
                    ),
                    custom_validate=[validators.LengthInRange(min_value=1)],
                ),
            ),
            "mem_levels": DictElement(
                required=False,
                parameter_form=SimpleLevels(
                    title=Title("Levels on memory usage"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Float(unit_symbol="MB"),
                    prefill_levels_type=DefaultValue(LevelsType.NONE),
                    prefill_fixed_levels=DefaultValue((1024.0, 2048.0)),
                ),
            ),
            "page_levels": DictElement(
                required=False,
                parameter_form=SimpleLevels(
                    title=Title("Levels on page file usage"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Float(unit_symbol="MB"),
                    prefill_levels_type=DefaultValue(LevelsType.NONE),
                    prefill_fixed_levels=DefaultValue((1024.0, 2048.0)),
                ),
            ),
            "cpu_levels": DictElement(
                required=False,
                parameter_form=SimpleLevels(
                    title=Title("Levels on CPU usage"),
                    help_text=Help(
                        "The sum of user and kernel mode CPU usage, averaged over all logical "
                        "processors of the host: 100% means that every core is fully busy with "
                        "the matching processes."
                    ),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Percentage(),
                    prefill_levels_type=DefaultValue(LevelsType.NONE),
                    prefill_fixed_levels=DefaultValue((80.0, 90.0)),
                ),
            ),
        },
    )


rule_spec_wmic_process = EnforcedService(
    name="wmic_process",
    title=Title("Memory and CPU of processes on Windows"),
    topic=Topic.APPLICATIONS,
    parameter_form=_make_form,
    condition=HostAndItemCondition(item_title=Title("Process name used in the service name")),
)
