#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
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
from cmk.rulesets.v1.rule_specs import CheckParameters, HostCondition, Topic


def _make_form() -> Dictionary:
    return Dictionary(
        help_text=Help(
            "This check monitors number of active and inactive terminal server sessions."
        ),
        elements={
            "active": DictElement(
                required=False,
                parameter_form=SimpleLevels(
                    title=Title("Number of active sessions"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Integer(),
                    migrate=migrate_to_integer_simple_levels,
                    prefill_fixed_levels=DefaultValue((100, 200)),
                ),
            ),
            "inactive": DictElement(
                required=False,
                parameter_form=SimpleLevels(
                    title=Title("Number of inactive sessions"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Integer(),
                    migrate=migrate_to_integer_simple_levels,
                    prefill_fixed_levels=DefaultValue((10, 20)),
                ),
            ),
        },
    )


rule_spec_winperf_ts_sessions = CheckParameters(
    name="winperf_ts_sessions",
    title=Title("Windows Terminal Server Sessions"),
    topic=Topic.APPLICATIONS,
    parameter_form=_make_form,
    condition=HostCondition(),
)
