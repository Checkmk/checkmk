#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    ServiceState,
    SingleChoice,
    SingleChoiceElement,
    String,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostAndItemCondition, Topic


def create_connection_state_element() -> DictElement:
    return DictElement(
        parameter_form=Dictionary(
            title=Title("Connection state configuration"),
            elements={
                "connected": DictElement(
                    parameter_form=SingleChoice(
                        title=Title("Expected connection state"),
                        elements=[
                            SingleChoiceElement(
                                name="true",
                                title=Title("Connected"),
                            ),
                            SingleChoiceElement(
                                name="false",
                                title=Title("Disconnected"),
                            ),
                        ],
                        prefill=DefaultValue("true"),
                    ),
                    required=True,
                ),
                "state_if_not_expected": DictElement(
                    parameter_form=ServiceState(
                        title=Title("State if not expected"),
                        prefill=DefaultValue(ServiceState.WARN),
                    ),
                    required=True,
                ),
            },
        ),
    )


def create_mac_configuration_element() -> DictElement:
    return DictElement(
        parameter_form=Dictionary(
            title=Title("MAC configuration"),
            elements={
                "dynamic_mac_enabled": DictElement(
                    parameter_form=SingleChoice(
                        title=Title("Dynamic MAC enabled"),
                        elements=[
                            SingleChoiceElement(
                                name="true",
                                title=Title("True"),
                            ),
                            SingleChoiceElement(
                                name="false",
                                title=Title("False"),
                            ),
                        ],
                        prefill=DefaultValue("true"),
                    ),
                    required=True,
                ),
                "state_if_not_expected": DictElement(
                    parameter_form=ServiceState(
                        title=Title("State if not expected"),
                        prefill=DefaultValue(ServiceState.WARN),
                    ),
                    required=True,
                ),
            },
        ),
    )


def create_expected_vswitch_element() -> DictElement:
    return DictElement(
        parameter_form=Dictionary(
            title=Title("Expected virtual switch"),
            elements={
                "name": DictElement(
                    parameter_form=String(
                        title=Title("Virtual switch name"),
                        help_text=Help("Expected virtual switch name"),
                        prefill=DefaultValue(""),
                    ),
                    required=True,
                ),
                "state_if_not_expected": DictElement(
                    parameter_form=ServiceState(
                        title=Title("State if not expected"),
                        prefill=DefaultValue(ServiceState.WARN),
                    ),
                    required=True,
                ),
            },
        ),
    )


def _parameter_valuespec_hyperv_vm_nic() -> Dictionary:
    return Dictionary(
        elements={
            "connection_state": create_connection_state_element(),
            "dynamic_mac": create_mac_configuration_element(),
            "expected_vswitch": create_expected_vswitch_element(),
        },
        help_text=Help(
            "Configure expected states for Hyper-V VM network interfaces. "
            "You can set expected connection state, MAC configuration, "
            "and expected virtual switch assignment."
        ),
    )


rule_spec_hyperv_vm_nic = CheckParameters(
    name="hyperv_vm_nic",
    title=Title("Hyper-V VM Network Adapter"),
    topic=Topic.NETWORKING,
    condition=HostAndItemCondition(
        item_title=Title("Network Adapter"),
    ),
    parameter_form=_parameter_valuespec_hyperv_vm_nic,
)
