#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    DataSize,
    DictElement,
    Dictionary,
    InputHint,
    LevelDirection,
    SIMagnitude,
    SimpleLevels,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostCondition, Topic


def _make_form() -> Dictionary:
    return Dictionary(
        help_text=Help(
            "This ruleset allows you to configure levels for Azure Redis throughput monitoring"
        ),
        elements={
            "cache_read_upper": DictElement(
                required=False,
                parameter_form=SimpleLevels(
                    title=Title("Cache read throughput (/sec)"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=DataSize(
                        displayed_magnitudes=[
                            SIMagnitude.BYTE,
                            SIMagnitude.KILO,
                            SIMagnitude.MEGA,
                            SIMagnitude.GIGA,
                        ],
                    ),
                    prefill_fixed_levels=InputHint((0, 0)),
                ),
            ),
            "cache_write_upper": DictElement(
                required=False,
                parameter_form=SimpleLevels(
                    title=Title("Cache write throughput (/sec)"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=DataSize(
                        displayed_magnitudes=[
                            SIMagnitude.BYTE,
                            SIMagnitude.KILO,
                            SIMagnitude.MEGA,
                            SIMagnitude.GIGA,
                        ],
                    ),
                    prefill_fixed_levels=InputHint((0, 0)),
                ),
            ),
        },
    )


rule_spec_azure_redis_throughput = CheckParameters(
    name="azure_redis_throughput",
    title=Title("Azure Redis throughput"),
    topic=Topic.APPLICATIONS,
    parameter_form=_make_form,
    condition=HostCondition(),
)
