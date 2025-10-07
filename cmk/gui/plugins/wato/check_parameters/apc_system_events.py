#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    ServiceState,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostCondition, Topic


def _parameter_form_spec_apc_system_events() -> Dictionary:
    return Dictionary(
        title=Title("System Events on APX Inrow Devices"),
        elements={
            "state": DictElement(
                required=False,
                parameter_form=ServiceState(
                    title=Title("State during active system events"), prefill=DefaultValue(2)
                ),
            )
        },
    )


rule_spec_apc_system_events = CheckParameters(
    name="apc_system_events",
    title=Title("APC Inrow System Events"),
    topic=Topic.ENVIRONMENTAL,
    parameter_form=_parameter_form_spec_apc_system_events,
    condition=HostCondition(),
)
