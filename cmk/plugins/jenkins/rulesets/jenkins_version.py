#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import DefaultValue, DictElement, Dictionary, ServiceState
from cmk.rulesets.v1.rule_specs import CheckParameters, HostCondition, Topic


def _parameter_valuespec_jenkins_version() -> Dictionary:
    return Dictionary(
        elements={
            "diff_state": DictElement(
                parameter_form=ServiceState(
                    title=Title("Service state on version difference"),
                    help_text=Help("If a version difference is detected this state will be used."),
                    prefill=DefaultValue(ServiceState.WARN),
                ),
            ),
        }
    )


rule_spec_jenkins_version = CheckParameters(
    name="jenkins_version",
    topic=Topic.APPLICATIONS,
    condition=HostCondition(),
    parameter_form=_parameter_valuespec_jenkins_version,
    title=Title("Jenkins version"),
)
