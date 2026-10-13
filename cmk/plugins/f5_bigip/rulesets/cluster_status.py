#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    ServiceState,
    SingleChoice,
    SingleChoiceElement,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostCondition, Topic

# The rule used to be keyed by the failover status code the device reports. Form spec
# element names have to be Python identifiers, so the codes are renamed to the status they
# stand for; see V11_2_STATE_KEYS in the check plugin.
_RENAMED_KEYS: Mapping[str, str] = {
    "0": "unknown",
    "1": "offline",
    "2": "forced_offline",
    "3": "standby",
    "4": "active",
}


def _migrate_v11_2_states(model: object) -> Mapping[str, int]:
    if not isinstance(model, dict):
        raise TypeError(f"Expected a mapping of failover states, got {model!r}")
    return {_RENAMED_KEYS.get(key, key): value for key, value in model.items()}


def _parameter_form_cluster_status() -> Dictionary:
    return Dictionary(
        elements={
            "type": DictElement(
                required=True,
                parameter_form=SingleChoice(
                    title=Title("Cluster type"),
                    help_text=Help("Expected cluster type."),
                    elements=[
                        SingleChoiceElement(name="active_standby", title=Title("active / standby")),
                        SingleChoiceElement(name="active_active", title=Title("active / active")),
                    ],
                    prefill=DefaultValue("active_standby"),
                ),
            ),
            "v11_2_states": DictElement(
                parameter_form=Dictionary(
                    title=Title("Interpretation of failover cluster state"),
                    help_text=Help(
                        "Here, you can set the failover state for BIG-IP system of version 11.2.0"
                    ),
                    elements={
                        "unknown": DictElement(
                            parameter_form=ServiceState(
                                title=Title("Unknown"),
                                prefill=DefaultValue(ServiceState.UNKNOWN),
                            )
                        ),
                        "offline": DictElement(
                            parameter_form=ServiceState(
                                title=Title("Offline"),
                                prefill=DefaultValue(ServiceState.CRIT),
                            )
                        ),
                        "forced_offline": DictElement(
                            parameter_form=ServiceState(
                                title=Title("Forced offline"),
                                prefill=DefaultValue(ServiceState.CRIT),
                            )
                        ),
                        "standby": DictElement(
                            parameter_form=ServiceState(
                                title=Title("Standby"),
                                prefill=DefaultValue(ServiceState.OK),
                            )
                        ),
                        "active": DictElement(
                            parameter_form=ServiceState(
                                title=Title("Active"),
                                prefill=DefaultValue(ServiceState.OK),
                            )
                        ),
                    },
                    migrate=_migrate_v11_2_states,
                )
            ),
        },
    )


rule_spec_cluster_status = CheckParameters(
    name="cluster_status",
    topic=Topic.APPLICATIONS,
    parameter_form=_parameter_form_cluster_status,
    title=Title("Cluster status"),
    condition=HostCondition(),
)
