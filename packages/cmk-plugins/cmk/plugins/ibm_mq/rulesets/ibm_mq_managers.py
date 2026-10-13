#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import Literal

from cmk.plugins.ibm_mq.rulesets.lib import migrate_mapped_states, version_form
from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import DefaultValue, DictElement, Dictionary, ServiceState
from cmk.rulesets.v1.rule_specs import CheckParameters, HostAndItemCondition, Topic

# Queue manager state: title and factory default service state
_MANAGER_STATES: Mapping[str, tuple[Title, Literal[0, 1, 2, 3]]] = {
    "starting": (Title("STARTING"), ServiceState.OK),
    "running": (Title("RUNNING"), ServiceState.OK),
    "running_as_standby": (Title("RUNNING AS STANDBY"), ServiceState.OK),
    "running_elsewhere": (Title("RUNNING ELSEWHERE"), ServiceState.OK),
    "quiescing": (Title("QUIESCING"), ServiceState.OK),
    "ending_immediately": (Title("ENDING IMMEDIATELY"), ServiceState.OK),
    "ending_pre_emptively": (Title("ENDING PRE-EMPTIVELY"), ServiceState.OK),
    "ended_normally": (Title("ENDED NORMALLY"), ServiceState.OK),
    "ended_immediately": (Title("ENDED IMMEDIATELY"), ServiceState.OK),
    "ended_unexpectedly": (Title("ENDED UNEXPECTEDLY"), ServiceState.CRIT),
    "ended_pre_emptively": (Title("ENDED PRE-EMPTIVELY"), ServiceState.WARN),
    "status_not_available": (Title("STATUS NOT AVAILABLE"), ServiceState.OK),
}


def _migrate(model: object) -> Mapping[str, object]:
    return migrate_mapped_states(model, tuple(_MANAGER_STATES))


def _parameter_form_ibm_mq_managers() -> Dictionary:
    return Dictionary(
        elements={
            "mapped_states": DictElement(
                parameter_form=Dictionary(
                    title=Title("Map manager state to service state"),
                    help_text=Help(
                        "The queue manager states you leave out keep their factory default"
                        " service state."
                    ),
                    elements={
                        name: DictElement(
                            parameter_form=ServiceState(
                                title=title, prefill=DefaultValue(factory_default)
                            )
                        )
                        for name, (title, factory_default) in _MANAGER_STATES.items()
                    },
                )
            ),
            "mapped_states_default": DictElement(
                parameter_form=ServiceState(
                    title=Title("Service state for unknown manager states"),
                    prefill=DefaultValue(ServiceState.UNKNOWN),
                )
            ),
            "version": DictElement(parameter_form=version_form()),
        },
        migrate=_migrate,
    )


rule_spec_ibm_mq_managers = CheckParameters(
    name="ibm_mq_managers",
    title=Title("IBM MQ managers"),
    topic=Topic.APPLICATIONS,
    parameter_form=_parameter_form_ibm_mq_managers,
    condition=HostAndItemCondition(item_title=Title("Name of queue manager")),
)
