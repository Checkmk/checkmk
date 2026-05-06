#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    Integer,
    LevelDirection,
    migrate_to_integer_simple_levels,
    SimpleLevels,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostAndItemCondition, Topic


def _migrate(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        raise TypeError(f"Cannot migrate jvm_queue parameters: {value!r}")
    if "levels_upper" in value:
        return value
    return {"levels_upper": value["levels"]}


def _parameter_form_jvm_queue() -> Dictionary:
    return Dictionary(
        elements={
            "levels_upper": DictElement(
                required=True,
                parameter_form=SimpleLevels(
                    title=Title("Upper levels"),
                    help_text=Help(
                        "The BEA application servers have 'Execute Queues' in "
                        "which requests are processed. This rule allows to set "
                        "warn and crit levels for the number of requests that "
                        "are being queued for processing."
                    ),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Integer(),
                    prefill_fixed_levels=DefaultValue(value=(20, 50)),
                    migrate=migrate_to_integer_simple_levels,
                ),
            ),
        },
        migrate=_migrate,
    )


rule_spec_jvm_queue = CheckParameters(
    name="jvm_queue",
    title=Title("JVM Execute Queue Count"),
    topic=Topic.APPLICATIONS,
    parameter_form=_parameter_form_jvm_queue,
    condition=HostAndItemCondition(item_title=Title("Name of the virtual machine")),
)
