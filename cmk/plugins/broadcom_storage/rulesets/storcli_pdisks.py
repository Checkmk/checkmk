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
from cmk.rulesets.v1.rule_specs import CheckParameters, HostAndItemCondition, Topic


def _make_form() -> Dictionary:
    return Dictionary(
        title=Title("Evaluation of PDisk States"),
        elements={
            "dhs": DictElement(
                required=False,
                parameter_form=ServiceState(
                    title=Title("State for <i>Dedicated Hot Spare</i>"),
                    prefill=DefaultValue(ServiceState.OK),
                ),
            ),
            "ghs": DictElement(
                required=False,
                parameter_form=ServiceState(
                    title=Title("State for <i>Global Hot Spare</i>"),
                    prefill=DefaultValue(ServiceState.OK),
                ),
            ),
            "ugood": DictElement(
                required=False,
                parameter_form=ServiceState(
                    title=Title("State for <i>Unconfigured Good</i>"),
                    prefill=DefaultValue(ServiceState.OK),
                ),
            ),
            "ubad": DictElement(
                required=False,
                parameter_form=ServiceState(
                    title=Title("State for <i>Unconfigured Bad</i>"),
                    prefill=DefaultValue(ServiceState.OK),
                ),
            ),
            "onln": DictElement(
                required=False,
                parameter_form=ServiceState(
                    title=Title("State for <i>Online</i>"), prefill=DefaultValue(ServiceState.OK)
                ),
            ),
            "ofln": DictElement(
                required=False,
                parameter_form=ServiceState(
                    title=Title("State for <i>Offline</i>"), prefill=DefaultValue(ServiceState.CRIT)
                ),
            ),
            "jbod": DictElement(
                required=False,
                parameter_form=ServiceState(
                    title=Title("State for <i>JBOD</i>"),
                    prefill=DefaultValue(ServiceState.OK),
                ),
            ),
        },
    )


rule_spec_storcli_pdisks = CheckParameters(
    name="storcli_pdisks",
    title=Title("Broadcom RAID physical disks"),
    topic=Topic.STORAGE,
    parameter_form=_make_form,
    condition=HostAndItemCondition(item_title=Title("PDisk EID:Slot-Device")),
)
