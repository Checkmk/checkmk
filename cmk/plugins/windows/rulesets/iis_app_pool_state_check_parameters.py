#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Literal

from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import DefaultValue, DictElement, Dictionary, ServiceState, String
from cmk.rulesets.v1.rule_specs import CheckParameters, HostAndItemCondition, Topic


def _state(title: Title, default: Literal[0, 1, 2, 3]) -> DictElement[Literal[0, 1, 2, 3]]:
    return DictElement(
        required=True,
        parameter_form=ServiceState(title=title, prefill=DefaultValue(default)),
    )


def _parameter_form_iis_app_pool_state() -> Dictionary:
    return Dictionary(
        elements={
            "state_mapping": DictElement(
                required=True,
                parameter_form=Dictionary(
                    title=Title("Map of Application Pool States to Service States"),
                    elements={
                        "Uninitialized": _state(Title("Uninitialized"), ServiceState.CRIT),
                        "Initialized": _state(Title("Initialized"), ServiceState.WARN),
                        "Running": _state(Title("Running"), ServiceState.OK),
                        "Disabling": _state(Title("Disabling"), ServiceState.CRIT),
                        "Disabled": _state(Title("Disabled"), ServiceState.CRIT),
                        "ShutdownPending": _state(Title("ShutdownPending"), ServiceState.CRIT),
                        "DeletePending": _state(Title("DeletePending"), ServiceState.CRIT),
                    },
                ),
            ),
        },
    )


rule_spec_iis_app_pool_state_check_parameters = CheckParameters(
    name="iis_app_pool_state",
    title=Title("IIS application pool state settings"),
    topic=Topic.APPLICATIONS,
    parameter_form=_parameter_form_iis_app_pool_state,
    condition=HostAndItemCondition(
        item_title=Title("Application pool name"),
        item_form=String(),
    ),
)
