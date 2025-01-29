#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    Integer,
    ServiceState,
    SingleChoice,
    SingleChoiceElement,
)
from cmk.rulesets.v1.form_specs.validators import NumberInRange
from cmk.rulesets.v1.rule_specs import CheckParameters, HostAndItemCondition, Topic


def get_common_elements() -> dict:
    return {
        "expect_active": DictElement(
            parameter_form=SingleChoice(
                title=Title("Warn on unexpected active interface"),
                elements=[
                    SingleChoiceElement("ignore", title=Title("ignore which one is active")),
                    SingleChoiceElement(
                        "primary", title=Title("require primary interface to be active")
                    ),
                    SingleChoiceElement(
                        "lowest", title=Title("require interface that sorts lowest alphabetically")
                    ),
                ],
                prefill=DefaultValue("ignore"),
            ),
        ),
        "ieee_302_3ad_agg_id_missmatch_state": DictElement(
            parameter_form=ServiceState(
                title=Title("State for mismatching Aggregator IDs for LACP"),
                prefill=DefaultValue(ServiceState.WARN),
            ),
        ),
        "expected_interfaces": DictElement(
            parameter_form=Dictionary(
                title=Title("Configure the number of expected interfaces"),
                elements={
                    "expected_number": DictElement(
                        required=True,
                        parameter_form=Integer(
                            title=Title("Lower limit of expected interfaces"),
                            prefill=DefaultValue(2),
                            custom_validate=(NumberInRange(min_value=0),),
                        ),
                    ),
                    "state": DictElement(
                        required=True,
                        parameter_form=ServiceState(
                            title=Title("State for unexpected number of interfaces"),
                            prefill=DefaultValue(ServiceState.OK),
                        ),
                    ),
                },
            ),
        ),
    }


def _make_lnx_parameter_form() -> Dictionary:
    return Dictionary(
        title=Title("Linux bonding"),
        elements={
            **get_common_elements(),
            "bonding_mode_states": DictElement(
                parameter_form=Dictionary(
                    title=Title("State for specific bonding modes"),
                    elements={
                        "mode_0": DictElement(
                            required=True,
                            parameter_form=ServiceState(
                                title=Title("balance-rr"), prefill=DefaultValue(ServiceState.OK)
                            ),
                        ),
                        "mode_1": DictElement(
                            required=True,
                            parameter_form=ServiceState(
                                title=Title("active-backup"), prefill=DefaultValue(ServiceState.OK)
                            ),
                        ),
                        "mode_2": DictElement(
                            required=True,
                            parameter_form=ServiceState(
                                title=Title("balance-xor"), prefill=DefaultValue(ServiceState.OK)
                            ),
                        ),
                        "mode_3": DictElement(
                            required=True,
                            parameter_form=ServiceState(
                                title=Title("broadcast"), prefill=DefaultValue(ServiceState.OK)
                            ),
                        ),
                        "mode_4": DictElement(
                            required=True,
                            parameter_form=ServiceState(
                                title=Title("802.3ad"), prefill=DefaultValue(ServiceState.OK)
                            ),
                        ),
                        "mode_5": DictElement(
                            required=True,
                            parameter_form=ServiceState(
                                title=Title("balance-tlb"), prefill=DefaultValue(ServiceState.OK)
                            ),
                        ),
                        "mode_6": DictElement(
                            required=True,
                            parameter_form=ServiceState(
                                title=Title("balance-alb"), prefill=DefaultValue(ServiceState.OK)
                            ),
                        ),
                    },
                    help_text=Help(
                        "Specify the monitoring state when the bonding mode is not as expected."
                    ),
                ),
            ),
        },
        ignored_elements=("primary",),
    )


def _make_ovs_parameter_form() -> Dictionary:
    return Dictionary(
        title=Title("OVS bonding"),
        elements=get_common_elements(),
        ignored_elements=("primary",),
    )


rule_spec_lnx_bonding = CheckParameters(
    name="bonding",
    title=Title("Linux bonding interface status"),
    topic=Topic.NETWORKING,
    parameter_form=_make_lnx_parameter_form,
    condition=HostAndItemCondition(item_title=Title("Name of the bonding interface")),
)

rule_spec_ovs_bonding = CheckParameters(
    name="ovs_bonding",
    title=Title("Linux bonding interface status"),
    topic=Topic.NETWORKING,
    parameter_form=_make_ovs_parameter_form,
    condition=HostAndItemCondition(item_title=Title("Name of the bonding interface")),
)
