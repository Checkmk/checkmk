#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Literal

from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import DefaultValue, DictElement, Dictionary, ServiceState
from cmk.rulesets.v1.rule_specs import CheckParameters, HostCondition, Topic


def _state(title: Title, default: Literal[0, 1, 2, 3]) -> DictElement[Literal[0, 1, 2, 3]]:
    return DictElement(
        required=True,
        parameter_form=ServiceState(title=title, prefill=DefaultValue(default)),
    )


def _parameter_form_citrix_state() -> Dictionary:
    return Dictionary(
        elements={
            "registrationstate": DictElement(
                parameter_form=Dictionary(
                    title=Title("Interpretation of registration states"),
                    elements={
                        "Unregistered": _state(Title("Unregistered"), ServiceState.CRIT),
                        "Initializing": _state(Title("Initializing"), ServiceState.WARN),
                        "Registered": _state(Title("Registered"), ServiceState.OK),
                        "AgentError": _state(Title("Agent error"), ServiceState.CRIT),
                    },
                ),
            ),
            "vmtoolsstate": DictElement(
                parameter_form=Dictionary(
                    title=Title("Interpretation of VM tools states"),
                    elements={
                        "NotPresent": _state(Title("Not present"), ServiceState.CRIT),
                        "Unknown": _state(Title("Unknown"), ServiceState.UNKNOWN),
                        "NotStarted": _state(Title("Not started"), ServiceState.WARN),
                        "Running": _state(Title("Running"), ServiceState.OK),
                    },
                ),
            ),
        },
    )


rule_spec_citrix_state = CheckParameters(
    name="citrix_state",
    title=Title("Citrix VM state"),
    topic=Topic.APPLICATIONS,
    parameter_form=_parameter_form_citrix_state,
    condition=HostCondition(),
)
