#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Literal

from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    ServiceState,
    String,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostAndItemCondition, Topic


def _state_element(title: Title, prefill: Literal[0, 1, 2, 3]) -> DictElement[Literal[0, 1, 2, 3]]:
    return DictElement(
        required=True,
        parameter_form=ServiceState(title=title, prefill=DefaultValue(prefill)),
    )


def _parameter_form_ibm_svc_mdisk() -> Dictionary:
    return Dictionary(
        elements={
            "online_state": _state_element(
                Title("Resulting state if disk is online"), ServiceState.OK
            ),
            "degraded_state": _state_element(
                Title("Resulting state if disk is degraded"), ServiceState.WARN
            ),
            "offline_state": _state_element(
                Title("Resulting state if disk is offline"), ServiceState.CRIT
            ),
            "excluded_state": _state_element(
                Title("Resulting state if disk is excluded"), ServiceState.CRIT
            ),
            "managed_mode": _state_element(
                Title("Resulting state if disk is in managed mode"), ServiceState.OK
            ),
            "array_mode": _state_element(
                Title("Resulting state if disk is in array mode"), ServiceState.OK
            ),
            "image_mode": _state_element(
                Title("Resulting state if disk is in image mode"), ServiceState.OK
            ),
            "unmanaged_mode": _state_element(
                Title("Resulting state if disk is in unmanaged mode"), ServiceState.WARN
            ),
        },
    )


rule_spec_ibm_svc_mdisk = CheckParameters(
    name="ibm_svc_mdisk",
    title=Title("IBM SVC disk"),
    topic=Topic.STORAGE,
    parameter_form=_parameter_form_ibm_svc_mdisk,
    condition=HostAndItemCondition(
        item_title=Title("IBM SVC disk"),
        item_form=String(help_text=Help("Name of the disk, e.g. mdisk0")),
    ),
)
