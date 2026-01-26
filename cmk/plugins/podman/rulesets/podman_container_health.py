#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    ServiceState,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostCondition, Topic


def podman_container_health() -> Dictionary:
    return Dictionary(
        elements={
            "healthy": DictElement(
                parameter_form=ServiceState(
                    title=Title("Healthy"),
                    prefill=DefaultValue(ServiceState.OK),
                )
            ),
            "starting": DictElement(
                parameter_form=ServiceState(
                    title=Title("Starting"),
                    prefill=DefaultValue(ServiceState.OK),
                )
            ),
            "unhealthy": DictElement(
                parameter_form=ServiceState(
                    title=Title("Unhealthy"),
                    prefill=DefaultValue(ServiceState.CRIT),
                )
            ),
            "no_healthcheck": DictElement(
                parameter_form=ServiceState(
                    title=Title("No Health Check"),
                    prefill=DefaultValue(ServiceState.WARN),
                )
            ),
        }
    )


rule_spec_podman_container_health = CheckParameters(
    name="podman_container_health",
    title=Title("Podman container health"),
    topic=Topic.APPLICATIONS,
    parameter_form=podman_container_health,
    condition=HostCondition(),
)
