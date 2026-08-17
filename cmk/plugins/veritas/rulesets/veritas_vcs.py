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


def _parameter_form_veritas_vcs() -> Dictionary:
    return Dictionary(
        elements={
            "map_states": DictElement(
                parameter_form=Dictionary(
                    title=Title("Map attribute 'State'"),
                    elements={
                        "ONLINE": _state(Title("ONLINE"), ServiceState.OK),
                        "RUNNING": _state(Title("RUNNING"), ServiceState.OK),
                        "OK": _state(Title("OK"), ServiceState.OK),
                        "OFFLINE": _state(Title("OFFLINE"), ServiceState.WARN),
                        "EXITED": _state(Title("EXITED"), ServiceState.WARN),
                        "PARTIAL": _state(Title("PARTIAL"), ServiceState.WARN),
                        "FAULTED": _state(Title("FAULTED"), ServiceState.CRIT),
                        "UNKNOWN": _state(Title("UNKNOWN"), ServiceState.UNKNOWN),
                        "default": _state(Title("States other than the above"), ServiceState.WARN),
                    },
                ),
            ),
            "map_frozen": DictElement(
                parameter_form=Dictionary(
                    title=Title("Map attribute 'Frozen'"),
                    elements={
                        "tfrozen": _state(Title("Temporarily frozen"), ServiceState.WARN),
                        "frozen": _state(Title("Frozen"), ServiceState.CRIT),
                    },
                ),
            ),
        },
    )


rule_spec_veritas_vcs = CheckParameters(
    name="veritas_vcs",
    title=Title("Veritas Cluster Server"),
    topic=Topic.APPLICATIONS,
    parameter_form=_parameter_form_veritas_vcs,
    condition=HostAndItemCondition(
        item_title=Title("Cluster name"),
        item_form=String(),
    ),
)
