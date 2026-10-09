#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    ServiceState,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostAndItemCondition, Topic


def _make_form() -> Dictionary:
    return Dictionary(
        help_text=Help(
            "The RAID controllers of HPE ProLiant servers report a condition, a "
            "board condition and a board status. Each of these can take the value "
            "<i>other</i>, meaning the instrument agent does not recognize the "
            "status. HPE ProLiant Gen11 / iLO 6 firmware reports the board "
            "condition as <i>other</i> for perfectly healthy controllers, which "
            "makes the service WARN permanently. Here you can remap the monitoring "
            "state used for the <i>other</i> value of each field independently."
        ),
        elements={
            "condition_other_state": DictElement(
                required=False,
                parameter_form=ServiceState(
                    title=Title("State when the controller condition is <i>other</i>"),
                    prefill=DefaultValue(ServiceState.WARN),
                ),
            ),
            "board_condition_other_state": DictElement(
                required=False,
                parameter_form=ServiceState(
                    title=Title("State when the board condition is <i>other</i>"),
                    prefill=DefaultValue(ServiceState.WARN),
                ),
            ),
            "board_status_other_state": DictElement(
                required=False,
                parameter_form=ServiceState(
                    title=Title("State when the board status is <i>other</i>"),
                    prefill=DefaultValue(ServiceState.WARN),
                ),
            ),
        },
    )


rule_spec_hp_proliant_da_cntlr = CheckParameters(
    name="hp_proliant_da_cntlr",
    title=Title("HPE ProLiant RAID controller"),
    topic=Topic.STORAGE,
    parameter_form=_make_form,
    condition=HostAndItemCondition(item_title=Title("Controller index")),
)
