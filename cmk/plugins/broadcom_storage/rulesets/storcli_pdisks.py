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
        title=Title("Evaluation of PDisk states"),
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
            "good": DictElement(
                required=False,
                parameter_form=ServiceState(
                    title=Title("State for StorCLI2 status <i>Good</i>"),
                    prefill=DefaultValue(ServiceState.OK),
                ),
            ),
            "online": DictElement(
                required=False,
                parameter_form=ServiceState(
                    title=Title("State for StorCLI2 status <i>Online</i>"),
                    prefill=DefaultValue(ServiceState.OK),
                ),
            ),
            "various": DictElement(
                required=False,
                parameter_form=ServiceState(
                    title=Title("State for StorCLI2 status <i>Various</i>"),
                    prefill=DefaultValue(ServiceState.WARN),
                ),
            ),
            "replace": DictElement(
                required=False,
                parameter_form=ServiceState(
                    title=Title("State for StorCLI2 status <i>Replace</i>"),
                    prefill=DefaultValue(ServiceState.CRIT),
                ),
            ),
            "missing": DictElement(
                required=False,
                parameter_form=ServiceState(
                    title=Title("State for StorCLI2 status <i>Missing</i>"),
                    prefill=DefaultValue(ServiceState.CRIT),
                ),
            ),
            "unusable": DictElement(
                required=False,
                parameter_form=ServiceState(
                    title=Title("State for StorCLI2 status <i>Unusable</i>"),
                    prefill=DefaultValue(ServiceState.CRIT),
                ),
            ),
            "bad": DictElement(
                required=False,
                parameter_form=ServiceState(
                    title=Title("State for StorCLI2 status <i>Bad</i>"),
                    prefill=DefaultValue(ServiceState.CRIT),
                ),
            ),
            "offline": DictElement(
                required=False,
                parameter_form=ServiceState(
                    title=Title("State for StorCLI2 status <i>Offline</i>"),
                    prefill=DefaultValue(ServiceState.CRIT),
                ),
            ),
            "failed": DictElement(
                required=False,
                parameter_form=ServiceState(
                    title=Title("State for StorCLI2 status <i>Failed</i>"),
                    prefill=DefaultValue(ServiceState.CRIT),
                ),
            ),
            "unknown": DictElement(
                required=False,
                parameter_form=ServiceState(
                    title=Title("State for StorCLI2 status <i>Unknown</i>"),
                    prefill=DefaultValue(ServiceState.UNKNOWN),
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
