#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import (
    DictElement,
    Dictionary,
    Float,
    InputHint,
    LevelDirection,
    SimpleLevels,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostCondition, Topic


def _make_form() -> Dictionary:
    return Dictionary(
        title=Title("Levels storage"),
        elements={
            "io_consumption": DictElement(
                parameter_form=SimpleLevels(
                    title=Title("Storage IO"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Float(unit_symbol="%"),
                    prefill_fixed_levels=InputHint((90.0, 80.0)),
                ),
            ),
            "storage": DictElement(
                parameter_form=SimpleLevels(
                    title=Title("Storage"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Float(unit_symbol="%"),
                    prefill_fixed_levels=InputHint((90.0, 80.0)),
                ),
            ),
            "serverlog_storage": DictElement(
                parameter_form=SimpleLevels(
                    title=Title("Server log storage"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Float(unit_symbol="%"),
                    prefill_fixed_levels=InputHint((90.0, 80.0)),
                ),
            ),
        },
    )


rule_spec_azure_db_storage = CheckParameters(
    name="azure_v2_db_storage",
    title=Title("Azure DB Storage"),
    topic=Topic.APPLICATIONS,
    parameter_form=_make_form,
    condition=HostCondition(),
)
