#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import DefaultValue, DictElement, Dictionary, ServiceState
from cmk.rulesets.v1.rule_specs import CheckParameters, HostCondition, Topic

rule_spec_check_parameters = CheckParameters(
    title=Title("Gerrit Version"),
    topic=Topic.APPLICATIONS,
    parameter_form=lambda: Dictionary(
        elements={
            "major": DictElement(
                parameter_form=ServiceState(
                    title=Title("Alert when a major version release is available"),
                    help_text=Help("Version will only appear in summary if non-OK state set."),
                    prefill=DefaultValue(ServiceState.WARN),
                )
            ),
            "minor": DictElement(
                parameter_form=ServiceState(
                    title=Title("Alert when a minor version release is available"),
                    help_text=Help("Version will only appear in summary if non-OK state set."),
                    prefill=DefaultValue(ServiceState.WARN),
                )
            ),
            "patch": DictElement(
                parameter_form=ServiceState(
                    title=Title("Alert when a patch version release is available"),
                    help_text=Help("Version will only appear in summary if non-OK state set."),
                    prefill=DefaultValue(ServiceState.WARN),
                )
            ),
        },
    ),
    name="gerrit_version",
    condition=HostCondition(),
)
