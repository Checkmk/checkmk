#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import DefaultValue, DictElement, Dictionary, ServiceState
from cmk.rulesets.v1.rule_specs import CheckParameters, HostCondition, Topic

rule_spec_check_parameters = CheckParameters(
    title=Title("Splunk Health"),
    topic=Topic.APPLICATIONS,
    parameter_form=lambda: Dictionary(
        elements={
            "green": DictElement(
                parameter_form=ServiceState(
                    title=Title("Status: green"),
                    prefill=DefaultValue(ServiceState.OK),
                )
            ),
            "yellow": DictElement(
                parameter_form=ServiceState(
                    title=Title("Status: yellow"),
                    prefill=DefaultValue(ServiceState.WARN),
                )
            ),
            "red": DictElement(
                parameter_form=ServiceState(
                    title=Title("Status: red"),
                    prefill=DefaultValue(ServiceState.CRIT),
                )
            ),
        },
    ),
    name="splunk_health",
    condition=HostCondition(),
)
