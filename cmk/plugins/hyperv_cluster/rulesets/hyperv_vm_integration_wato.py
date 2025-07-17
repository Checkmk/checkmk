#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Thanks to Andreas Döhler for the contribution.

# -*- encoding: utf-8; py-indent-offset: 4 -*-
from collections.abc import Sequence
from typing import Any

from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    List,
    SingleChoice,
    SingleChoiceElement,
    String,
)
from cmk.rulesets.v1.form_specs.validators import LengthInRange
from cmk.rulesets.v1.rule_specs import (
    CheckParameters,
    HostCondition,
    Topic,
)


def _migrate_tuple(value: object) -> Sequence[Any]:
    """
    Convert a list of tuple to a list of dictionary with keys 'service_name' and 'state'.
    """
    if isinstance(value, list):
        if all(isinstance(item, dict) for item in value):
            return value
        return [
            {
                "service_name": item[0],
                "expected_state": item[1],
            }
            for item in value
            if isinstance(item, tuple) and len(item) == 2
        ]
    return []


def create_default_status_element() -> DictElement:
    return DictElement(
        parameter_form=SingleChoice(
            title=Title("Default State"),
            elements=[
                SingleChoiceElement(
                    name="active",
                    title=Title("active"),
                ),
                SingleChoiceElement(
                    name="inactive",
                    title=Title("inactive"),
                ),
            ],
            prefill=DefaultValue("active"),
        ),
    )


def create_match_services_element() -> DictElement:
    return DictElement(
        parameter_form=List(
            title=Title("Special States"),
            migrate=_migrate_tuple,
            element_template=Dictionary(
                elements={
                    "service_name": DictElement(
                        required=True,
                        parameter_form=String(
                            title=Title("Service name"),
                            custom_validate=(LengthInRange(min_value=1),),
                        ),
                    ),
                    "expected_state": DictElement(
                        required=True,
                        parameter_form=SingleChoice(
                            title=Title("State"),
                            elements=[
                                SingleChoiceElement(
                                    name="active",
                                    title=Title("active"),
                                ),
                                SingleChoiceElement(
                                    name="inactive",
                                    title=Title("inactive"),
                                ),
                            ],
                        ),
                    ),
                }
            ),
        ),
    )


def _parameter_valuespec_hyperv_vm_integration():
    return Dictionary(
        elements={
            "default_status": create_default_status_element(),
            "match_services": create_match_services_element(),
        }
    )


rule_spec_hyperv_vm_integration = CheckParameters(
    name="hyperv_vm_integration",
    title=Title("Hyper-V Integration Services Status"),
    topic=Topic.APPLICATIONS,
    condition=HostCondition(),
    parameter_form=_parameter_valuespec_hyperv_vm_integration,
)
