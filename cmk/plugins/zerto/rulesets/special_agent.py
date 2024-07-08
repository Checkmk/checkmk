#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    DictElement,
    Dictionary,
    migrate_to_password,
    Password,
    SingleChoice,
    SingleChoiceElement,
    String,
    validators,
)
from cmk.rulesets.v1.rule_specs import SpecialAgent, Topic


def _form_spec_special_agents_zerto():
    return Dictionary(
        title=Title("Zerto"),
        help_text=Help(
            "Monitor if your VMs are properly protected by the "
            "disaster recovery software Zerto (compatible with Zerto v9.x)."
        ),
        elements={
            "authentication": DictElement(
                required=False,
                parameter_form=SingleChoice(
                    title=Title("Authentication method"),
                    elements=[
                        SingleChoiceElement(name="windows", title=Title("Windows authentication")),
                        SingleChoiceElement(name="vcenter", title=Title("VCenter authentication")),
                    ],
                    help_text=Help("Default is Windows authentication"),
                ),
            ),
            "username": DictElement(
                required=True,
                parameter_form=String(
                    title=Title("Username"),
                    custom_validate=(validators.LengthInRange(min_value=1),),
                ),
            ),
            "password": DictElement(
                required=True,
                parameter_form=Password(
                    title=Title("Password"),
                    custom_validate=(validators.LengthInRange(min_value=1),),
                    migrate=migrate_to_password,
                ),
            ),
        },
    )


rule_spec_special_agent_zerto = SpecialAgent(
    name="zerto",
    title=Title("Zerto"),
    topic=Topic.APPLICATIONS,
    parameter_form=_form_spec_special_agents_zerto,
)
