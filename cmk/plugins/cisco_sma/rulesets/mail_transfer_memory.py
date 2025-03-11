#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import DefaultValue, DictElement, Dictionary, ServiceState
from cmk.rulesets.v1.rule_specs import CheckParameters, HostCondition, Topic


def _mail_transfer_memory_form() -> Dictionary:
    return Dictionary(
        elements={
            "monitoring_status_memory_available": DictElement(
                parameter_form=ServiceState(
                    title=Title("Monitoring status if memory available"),
                    prefill=DefaultValue(ServiceState.OK),
                )
            ),
            "monitoring_status_memory_shortage": DictElement(
                parameter_form=ServiceState(
                    title=Title("Monitoring status if memory shortage"),
                    prefill=DefaultValue(ServiceState.WARN),
                )
            ),
            "monitoring_status_memory_full": DictElement(
                parameter_form=ServiceState(
                    title=Title("Monitoring status if memory full"),
                    prefill=DefaultValue(ServiceState.CRIT),
                )
            ),
        }
    )


rule_spec_dns_requests = CheckParameters(
    name="cisco_sma_mail_transfer_memory",
    title=Title("Cisco SMA mail transfer memory"),
    topic=Topic.APPLICATIONS,
    parameter_form=_mail_transfer_memory_form,
    condition=HostCondition(),
)
