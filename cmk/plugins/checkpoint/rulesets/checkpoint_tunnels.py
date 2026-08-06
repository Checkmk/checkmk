#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Literal

from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    ServiceState,
    String,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostAndItemCondition, Topic


def _tunnel_state(title: Title, default: Literal[0, 1, 2, 3]) -> DictElement[Literal[0, 1, 2, 3]]:
    return DictElement(
        required=False,
        parameter_form=ServiceState(title=title, prefill=DefaultValue(default)),
    )


def _parameter_form_checkpoint_tunnels() -> Dictionary:
    return Dictionary(
        elements={
            "Active": _tunnel_state(Title("State when VPN status is Active"), 0),
            "Destroy": _tunnel_state(Title("State when VPN status is Destroy"), 1),
            "Idle": _tunnel_state(Title("State when VPN status is Idle"), 0),
            "Phase1": _tunnel_state(Title("State when VPN status is Phase1"), 2),
            "Down": _tunnel_state(Title("State when VPN status is Down"), 2),
            "Init": _tunnel_state(Title("State when VPN status is Init"), 1),
        },
    )


rule_spec_checkpoint_tunnels = CheckParameters(
    name="checkpoint_tunnels",
    # weblate-flags: read-only, vendor-name
    title=Title("Check Point tunnel status"),
    topic=Topic.NETWORKING,
    parameter_form=_parameter_form_checkpoint_tunnels,
    condition=HostAndItemCondition(
        item_title=Title("Name of VPN tunnel"),
        item_form=String(),
    ),
)
