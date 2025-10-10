#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"
from cmk.gui.form_specs.generators.age import Age
from cmk.gui.form_specs.unstable.legacy_converter import Tuple
from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostAndItemCondition, Topic


def _parameter_form_spec_azure_ad():
    return Dictionary(
        elements={
            "age": DictElement(
                required=False,
                parameter_form=Tuple(
                    title=Title("Time since last AD Connect sync"),
                    elements=[Age(prefill=DefaultValue(1800)), Age(prefill=DefaultValue(3600))],
                ),
            )
        }
    )


rule_spec_azure_ad = CheckParameters(
    name="azure_ad",
    title=Title("Azure AD Connect (deprecated)"),
    topic=Topic.NETWORKING,
    parameter_form=_parameter_form_spec_azure_ad,
    condition=HostAndItemCondition(item_title=Title("Accounts display name")),
)
