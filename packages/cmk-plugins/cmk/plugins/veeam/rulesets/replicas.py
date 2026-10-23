#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from typing import Literal

from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import DefaultValue, DictElement, Dictionary, ServiceState
from cmk.rulesets.v1.rule_specs import CheckParameters, HostAndItemCondition, Topic

_STATES: Sequence[tuple[str, Literal[0, 1, 2, 3]]] = (
    ("Ready", ServiceState.OK),
    ("Processing", ServiceState.OK),
    ("SureBackup", ServiceState.OK),
    ("Failover", ServiceState.WARN),
    ("FailedFailover", ServiceState.CRIT),
    ("PermanentFailover", ServiceState.WARN),
    ("Failback", ServiceState.WARN),
    ("ReadyToSwitch", ServiceState.WARN),
)


def _parameter_form_veeam_replicas() -> Dictionary:
    return Dictionary(
        help_text=Help(
            "The monitoring state for each replica state reported by Veeam. A replica "
            "state not listed here is always UNKNOWN."
        ),
        elements={
            state: DictElement(
                parameter_form=ServiceState(
                    title=Title("State when the replica is %(state)s") % {"state": state},
                    prefill=DefaultValue(default),
                ),
            )
            for state, default in _STATES
        },
    )


rule_spec_veeam_replicas = CheckParameters(
    name="veeam_replicas",
    title=Title("Veeam: Replica"),
    topic=Topic.APPLICATIONS,
    parameter_form=_parameter_form_veeam_replicas,
    condition=HostAndItemCondition(item_title=Title("Replica name")),
)
