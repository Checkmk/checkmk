#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import Dictionary
from cmk.rulesets.v1.rule_specs import SpecialAgent, Topic


def _parameter_form() -> Dictionary:
    return Dictionary(
        elements={},
        help_text=Help(
            "This rule activates an agent which connects to an ACME Session Border Controller (SBC). "
            "This agent uses SSH, so you have to exchange an SSH key to make a passwordless connect possible."
        ),
    )


rule_spec_special_agent_acme_sbc = SpecialAgent(
    name="acme_sbc",
    title=Title("ACME Session Border Controller"),
    topic=Topic.SERVER_HARDWARE,
    parameter_form=_parameter_form,
)
