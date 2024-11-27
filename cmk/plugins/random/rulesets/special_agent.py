#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import FixedValue
from cmk.rulesets.v1.form_specs._composed import DictElement, Dictionary
from cmk.rulesets.v1.rule_specs import SpecialAgent, Topic


def _parameter_form() -> Dictionary:
    return Dictionary(
        title=Title("Create random monitoring data"),
        help_text=Help(
            "By configuring this rule for a host - instead of the normal "
            "Check_MK agent random monitoring data will be created."
        ),
        elements={
            "random": DictElement(
                required=True,
                parameter_form=FixedValue(value=None, title=Title("Create random monitoring data")),
            )
        },
        migrate=_migrate,
    )


def _migrate(params: object) -> dict[str, object]:
    match params:
        case {"random": random_value}:
            return {"random": random_value}
        case {}:
            return {"random": None}
    raise ValueError(f"Invalid parameters: {params!r}")


rule_spec_special_agent_random = SpecialAgent(
    name="random",
    title=Title("Create random monitoring data"),
    topic=Topic.APPLICATIONS,
    parameter_form=_parameter_form,
)
