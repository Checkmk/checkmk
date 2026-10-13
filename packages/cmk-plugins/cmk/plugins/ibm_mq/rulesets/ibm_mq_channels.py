#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import Literal

from cmk.plugins.ibm_mq.rulesets.lib import migrate_mapped_states
from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import DefaultValue, DictElement, Dictionary, ServiceState
from cmk.rulesets.v1.rule_specs import CheckParameters, HostAndItemCondition, Topic

# Channel state: title and factory default service state
_CHANNEL_STATES: Mapping[str, tuple[Title, Literal[0, 1, 2, 3]]] = {
    "inactive": (Title("INACTIVE"), ServiceState.OK),
    "initializing": (Title("INITIALIZING"), ServiceState.OK),
    "binding": (Title("BINDING"), ServiceState.OK),
    "starting": (Title("STARTING"), ServiceState.OK),
    "running": (Title("RUNNING"), ServiceState.OK),
    "retrying": (Title("RETRYING"), ServiceState.WARN),
    "stopping": (Title("STOPPING"), ServiceState.OK),
    "stopped": (Title("STOPPED"), ServiceState.CRIT),
}


def _migrate(model: object) -> Mapping[str, object]:
    return migrate_mapped_states(model, tuple(_CHANNEL_STATES))


def _parameter_form_ibm_mq_channels() -> Dictionary:
    return Dictionary(
        elements={
            "mapped_states": DictElement(
                parameter_form=Dictionary(
                    title=Title("Map channel state to service state"),
                    help_text=Help(
                        "The channel states you leave out keep their factory default service state."
                    ),
                    elements={
                        name: DictElement(
                            parameter_form=ServiceState(
                                title=title, prefill=DefaultValue(factory_default)
                            )
                        )
                        for name, (title, factory_default) in _CHANNEL_STATES.items()
                    },
                )
            ),
            "mapped_states_default": DictElement(
                parameter_form=ServiceState(
                    title=Title("Service state for unknown channel states"),
                    prefill=DefaultValue(ServiceState.UNKNOWN),
                )
            ),
        },
        migrate=_migrate,
    )


rule_spec_ibm_mq_channels = CheckParameters(
    name="ibm_mq_channels",
    title=Title("IBM MQ channels"),
    topic=Topic.APPLICATIONS,
    parameter_form=_parameter_form_ibm_mq_channels,
    condition=HostAndItemCondition(item_title=Title("Name of channel")),
)
