#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    ServiceState,
    SingleChoice,
    SingleChoiceElement,
)
from cmk.rulesets.v1.rule_specs import (
    CheckParameters,
    HostCondition,
    Topic,
)


def create_power_state_element() -> DictElement:
    return DictElement(
        parameter_form=Dictionary(
            title=Title("Power state mapping"),
            elements={
                "running": DictElement(
                    parameter_form=ServiceState(
                        title=Title("Running"),
                        prefill=DefaultValue(ServiceState.OK),
                    ),
                ),
                "off": DictElement(
                    parameter_form=ServiceState(
                        title=Title("Off"),
                        prefill=DefaultValue(ServiceState.CRIT),
                    ),
                ),
                "saved": DictElement(
                    parameter_form=ServiceState(
                        title=Title("Saved"),
                        prefill=DefaultValue(ServiceState.OK),
                    ),
                ),
                "paused": DictElement(
                    parameter_form=ServiceState(
                        title=Title("Paused"),
                        prefill=DefaultValue(ServiceState.WARN),
                    ),
                ),
                "starting": DictElement(
                    parameter_form=ServiceState(
                        title=Title("Starting"),
                        prefill=DefaultValue(ServiceState.WARN),
                    ),
                ),
            },
        ),
    )


def create_vm_generation_element() -> DictElement:
    return DictElement(
        parameter_form=Dictionary(
            title=Title("VM Generation"),
            elements={
                "expected_generation": DictElement(
                    parameter_form=SingleChoice(
                        title=Title("Expected VM Generation"),
                        elements=[
                            SingleChoiceElement(
                                name="generation_1",
                                title=Title("Generation 1"),
                            ),
                            SingleChoiceElement(
                                name="generation_2",
                                title=Title("Generation 2"),
                            ),
                        ],
                    ),
                ),
                "state_if_not_expected": DictElement(
                    parameter_form=ServiceState(
                        title=Title("State if not expected"),
                        prefill=DefaultValue(ServiceState.WARN),
                    ),
                ),
            },
        ),
    )


def _parameter_valuespec_hyperv_vm_general():
    return Dictionary(
        elements={
            "power_state": create_power_state_element(),
            "vm_generation": create_vm_generation_element(),
        }
    )


rule_spec_hyperv_vm_general = CheckParameters(
    name="hyperv_vm_general",
    title=Title("Hyper-V VM summary"),
    topic=Topic.APPLICATIONS,
    condition=HostCondition(),
    parameter_form=_parameter_valuespec_hyperv_vm_general,
)
