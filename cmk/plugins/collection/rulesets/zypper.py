#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import DefaultValue, DictElement, Dictionary, ServiceState
from cmk.rulesets.v1.rule_specs import CheckParameters, HostCondition, Topic


def _parameter_form_zypper() -> Dictionary:
    return Dictionary(
        elements={
            "security": DictElement(
                parameter_form=ServiceState(
                    title=Title("State when security updates are pending"),
                    prefill=DefaultValue(ServiceState.CRIT),
                ),
            ),
            "recommended": DictElement(
                parameter_form=ServiceState(
                    title=Title("State when recommended updates are pending"),
                    prefill=DefaultValue(ServiceState.WARN),
                ),
            ),
            "other": DictElement(
                parameter_form=ServiceState(
                    title=Title(
                        "State when updates are pending, which are neither recommended or a "
                        "security update"
                    ),
                    prefill=DefaultValue(ServiceState.OK),
                ),
            ),
            "locks": DictElement(
                parameter_form=ServiceState(
                    title=Title("State when packages are locked"),
                    prefill=DefaultValue(ServiceState.WARN),
                ),
            ),
        },
    )


rule_spec_zypper = CheckParameters(
    name="zypper",
    topic=Topic.OPERATING_SYSTEM,
    parameter_form=_parameter_form_zypper,
    title=Title("Zypper Updates"),
    condition=HostCondition(),
)
