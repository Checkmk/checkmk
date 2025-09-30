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


def _parameter_form_spec_apt() -> Dictionary:
    return Dictionary(
        elements={
            "normal": DictElement(
                required=False,
                parameter_form=ServiceState(
                    title=Title("State when normal updates are pending"), prefill=DefaultValue(1)
                ),
            ),
            "security": DictElement(
                required=False,
                parameter_form=ServiceState(
                    title=Title("State when security updates are pending"), prefill=DefaultValue(2)
                ),
            ),
            "removals": DictElement(
                required=False,
                parameter_form=ServiceState(
                    title=Title("State when removals are pending"), prefill=DefaultValue(1)
                ),
            ),
        }
    )


rule_spec_apt = CheckParameters(
    name="apt",
    title=Title("APT Updates"),
    topic=Topic.OPERATING_SYSTEM,
    parameter_form=_parameter_form_spec_apt,
    condition=HostCondition(),
)
