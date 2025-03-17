#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import Dictionary, String
from cmk.rulesets.v1.rule_specs import CheckParameters, HostAndItemCondition, Topic

rule_spec_mytest = CheckParameters(
    name="test",
    title=Title("Test"),
    topic=Topic.SERVER_HARDWARE,
    parameter_form=lambda: Dictionary(elements={}),
    condition=HostAndItemCondition(
        item_title=Title("Item"),
        item_form=String(),
    ),
)
