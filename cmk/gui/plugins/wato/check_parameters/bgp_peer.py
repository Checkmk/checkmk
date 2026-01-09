#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import (
    DictElement,
    Dictionary,
    ServiceState,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostAndItemCondition, Topic


def _parameter_form_spec_bgp_peer() -> Dictionary:
    return Dictionary(
        elements={
            "admin_state_mapping": DictElement(
                required=False,
                parameter_form=Dictionary(
                    title=Title("Admin states"),
                    elements={
                        "halted": DictElement(
                            required=True, parameter_form=ServiceState(title=Title("halted"))
                        ),
                        "running": DictElement(
                            required=True, parameter_form=ServiceState(title=Title("running"))
                        ),
                    },
                ),
            ),
            "peer_state_mapping": DictElement(
                required=False,
                parameter_form=Dictionary(
                    title=Title("Peer states"),
                    elements={
                        "idle": DictElement(
                            required=True, parameter_form=ServiceState(title=Title("idle"))
                        ),
                        "connect": DictElement(
                            required=True, parameter_form=ServiceState(title=Title("connect"))
                        ),
                        "active": DictElement(
                            required=True, parameter_form=ServiceState(title=Title("active"))
                        ),
                        "opensent": DictElement(
                            required=True, parameter_form=ServiceState(title=Title("opensent"))
                        ),
                        "openconfirm": DictElement(
                            required=True, parameter_form=ServiceState(title=Title("openconfirm"))
                        ),
                        "established": DictElement(
                            required=True, parameter_form=ServiceState(title=Title("established"))
                        ),
                    },
                ),
            ),
        }
    )


rule_spec_bgp_peer = CheckParameters(
    name="bgp_peer",
    title=Title("BGP Peer State Mapping"),
    topic=Topic.NETWORKING,
    parameter_form=_parameter_form_spec_bgp_peer,
    condition=HostAndItemCondition(
        item_title=Title("Remote IP address"),
    ),
)
