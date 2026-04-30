#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
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


def _parameter_form_kube_collector_info() -> Dictionary:
    return Dictionary(
        elements={
            "machine_metrics": DictElement(
                required=True,
                parameter_form=ServiceState(
                    title=Title(
                        "Monitoring state if the cluster collector reports no machine metrics"
                    ),
                    prefill=DefaultValue(ServiceState.CRIT),
                ),
            ),
        },
    )


rule_spec_kube_collector_info = CheckParameters(
    name="kube_collector_info",
    topic=Topic.APPLICATIONS,
    parameter_form=_parameter_form_kube_collector_info,
    title=Title("Kubernetes Collector info"),
    condition=HostCondition(),
)
