#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    ServiceState,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostAndItemCondition, Topic


def _formspec_checkpoint_powersupply() -> Dictionary:
    return Dictionary(
        elements={
            "up": DictElement(
                required=False,
                parameter_form=ServiceState(
                    title=Title("State when reported device status is UP"), prefill=DefaultValue(0)
                ),
            ),
            "present": DictElement(
                required=False,
                parameter_form=ServiceState(
                    title=Title("State when reported device status is present"),
                    prefill=DefaultValue(2),
                ),
            ),
        }
    )


rule_spec_checkpoint_powersupply = CheckParameters(
    name="checkpoint_powersupply",
    title=Title("Check Point powersupply"),
    topic=Topic.POWER,
    parameter_form=_formspec_checkpoint_powersupply,
    condition=HostAndItemCondition(item_title=Title("Power supply name")),
)
