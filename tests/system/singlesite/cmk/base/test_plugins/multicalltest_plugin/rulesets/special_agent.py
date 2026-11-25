#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import Dictionary
from cmk.rulesets.v1.rule_specs import SpecialAgent, Topic


def _valuespec_special_agent_multicalltest() -> Dictionary:
    return Dictionary(
        title=Title("Multicall special agent test"),
        elements={},
    )


rule_spec_multicalltest = SpecialAgent(
    name="multicalltest",
    title=Title("Multicall special agent test"),
    topic=Topic.APPLICATIONS,
    parameter_form=_valuespec_special_agent_multicalltest,
)
