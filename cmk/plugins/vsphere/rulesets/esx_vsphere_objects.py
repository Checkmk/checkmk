#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import re

from cmk.rulesets.v1 import Help, Label, Message, Title
from cmk.rulesets.v1.form_specs import (
    BooleanChoice,
    DefaultValue,
    DictElement,
    Dictionary,
    ServiceState,
    String,
    validators,
)
from cmk.rulesets.v1.form_specs.validators import ValidationError
from cmk.rulesets.v1.rule_specs import (
    CheckParameters,
    DiscoveryParameters,
    HostAndItemCondition,
    Topic,
)

ITEM_PATTERN = re.compile("(^VM|HostSystem) (.*)$")


def _validate_item(value: str) -> str:
    if not ITEM_PATTERN.match(value):
        raise ValidationError(
            Message("The name of the system must begin with <tt>VM</tt> or <tt>HostSystem</tt>.")
        )

    return value


def _parameter_form_esx_vsphere_objects():
    return Dictionary(
        help_text=Help(
            "Usually the check goes to WARN if a VM or host is powered off and OK otherwise. "
            "You can change this behaviour on a per-state-basis here."
        ),
        elements={
            "states": DictElement(
                required=True,
                parameter_form=Dictionary(
                    title=Title("Target states"),
                    elements={
                        "standBy": DictElement(
                            required=True,
                            parameter_form=ServiceState(
                                title=Title("Stand by"),
                                help_text=Help("Check result if the host or VM is in stand by"),
                                prefill=DefaultValue(ServiceState.WARN),
                            ),
                        ),
                        "poweredOn": DictElement(
                            required=True,
                            parameter_form=ServiceState(
                                title=Title("Powered ON"),
                                help_text=Help("Check result if the host or VM is powered on"),
                                prefill=DefaultValue(ServiceState.OK),
                            ),
                        ),
                        "poweredOff": DictElement(
                            required=True,
                            parameter_form=ServiceState(
                                title=Title("Powered OFF"),
                                help_text=Help("Check result if the host or VM is powered off"),
                                prefill=DefaultValue(ServiceState.WARN),
                            ),
                        ),
                        "suspended": DictElement(
                            required=True,
                            parameter_form=ServiceState(
                                title=Title("Suspended"),
                                help_text=Help("Check result if the host or VM is suspended"),
                                prefill=DefaultValue(ServiceState.WARN),
                            ),
                        ),
                        "unknown": DictElement(
                            required=True,
                            parameter_form=ServiceState(
                                title=Title("Unknown"),
                                help_text=Help(
                                    "Check result if the host or VM state is reported as <i>unknown</i>"
                                ),
                                prefill=DefaultValue(ServiceState.UNKNOWN),
                            ),
                        ),
                    },
                ),
            ),
        },
    )


rule_spec_esx_vsphere_objects = CheckParameters(
    name="esx_vsphere_objects",
    title=Title("ESX host and virtual machine states"),
    topic=Topic.APPLICATIONS,
    parameter_form=_parameter_form_esx_vsphere_objects,
    condition=HostAndItemCondition(
        item_title=Title("Name of the VM/HostSystem"),
        item_form=String(
            help_text=Help(
                "Please do not forget to specify either <tt>VM</tt> or <tt>HostSystem</tt>. "
                "Example: <tt>VM abcsrv123</tt>. Also note, that we match the <i>beginning</i> of "
                "the name. This rule cannot be applied to templates as those are always in state OK."
            ),
            custom_validate=(validators.LengthInRange(min_value=1), _validate_item),
        ),
    ),
)


def _parameter_form_discovery() -> Dictionary:
    return Dictionary(
        elements={
            "templates": DictElement(
                required=True,
                parameter_form=BooleanChoice(
                    label=Label("Discover templates"),
                    help_text=Help(
                        "Control whether VM templates should be monitored. "
                        "Check this box to create services for VM templates."
                    ),
                    prefill=DefaultValue(True),
                ),
            )
        },
    )


rule_spec_esx_vsphere_objects_discovery = DiscoveryParameters(
    name="esx_vsphere_objects_discovery",
    title=Title("ESX VM template discovery"),
    topic=Topic.APPLICATIONS,
    parameter_form=_parameter_form_discovery,
)
