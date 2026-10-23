#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import DefaultValue, DictElement, Dictionary, ServiceState
from cmk.rulesets.v1.rule_specs import CheckParameters, HostAndItemCondition, Topic


def _parameter_form_veeam_managed_servers() -> Dictionary:
    return Dictionary(
        help_text=Help("Any other status, or no status at all, always makes the service UNKNOWN."),
        elements={
            "status_available": DictElement(
                parameter_form=ServiceState(
                    title=Title("Status: Available"),
                    prefill=DefaultValue(ServiceState.OK),
                ),
            ),
            "status_unavailable": DictElement(
                parameter_form=ServiceState(
                    title=Title("Status: Unavailable"),
                    prefill=DefaultValue(ServiceState.CRIT),
                ),
            ),
        },
    )


rule_spec_veeam_managed_servers = CheckParameters(
    name="veeam_managed_servers",
    title=Title("Veeam: Managed server"),
    topic=Topic.APPLICATIONS,
    parameter_form=_parameter_form_veeam_managed_servers,
    condition=HostAndItemCondition(item_title=Title("Managed server name")),
)
