#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.rulesets.v1 import Help, Label, Title
from cmk.rulesets.v1.form_specs import DictElement, Dictionary, List, String, validators
from cmk.rulesets.v1.rule_specs import SpecialAgent, Topic


def _parameter_form() -> Dictionary:
    return Dictionary(
        title=Title("Salesforce"),
        help_text=Help("This rule selects the special agent for Salesforce."),
        elements={
            "instances": DictElement(
                required=True,
                parameter_form=List(
                    title=Title("Instances"),
                    custom_validate=(validators.LengthInRange(min_value=1),),
                    element_template=String(),
                    add_element_label=Label("Add Instance"),
                    remove_element_label=Label("Remove Instance"),
                ),
            )
        },
    )


rule_spec_special_agent_salesforce = SpecialAgent(
    name="salesforce",
    title=Title("Salesforce"),
    topic=Topic.CLOUD,
    parameter_form=_parameter_form,
    help_text=Help("This rule selects the special agent for Salesforce."),
)
