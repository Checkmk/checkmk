#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import DefaultValue, DictElement, Dictionary, ServiceState
from cmk.rulesets.v1.rule_specs import CheckParameters, HostAndItemCondition, Topic


def _parameter_form_veeam_proxies() -> Dictionary:
    return Dictionary(
        elements={
            "disabled_state": DictElement(
                parameter_form=ServiceState(
                    title=Title("State when the proxy is disabled"),
                    prefill=DefaultValue(ServiceState.WARN),
                ),
            ),
        },
    )


rule_spec_veeam_proxies = CheckParameters(
    name="veeam_proxies",
    title=Title("Veeam: Backup proxy"),
    topic=Topic.APPLICATIONS,
    parameter_form=_parameter_form_veeam_proxies,
    condition=HostAndItemCondition(item_title=Title("Proxy name")),
)
