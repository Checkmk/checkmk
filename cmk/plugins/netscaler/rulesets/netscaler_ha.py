#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    CascadingSingleChoice,
    CascadingSingleChoiceElement,
    DefaultValue,
    DictElement,
    Dictionary,
    FixedValue,
    SingleChoice,
    SingleChoiceElement,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostCondition, Topic


def _parameter_netscaler_ha() -> Dictionary:
    return Dictionary(
        elements={
            "failover_monitoring": DictElement(
                required=True,
                parameter_form=CascadingSingleChoice(
                    title=Title("Failover monitoring"),
                    elements=[
                        CascadingSingleChoiceElement(
                            name="disabled",
                            title=Title("Do not monitor failovers"),
                            parameter_form=FixedValue(
                                value=None,
                            ),
                        ),
                        CascadingSingleChoiceElement(
                            name="use_discovered_failover_mode",
                            title=Title("Compare against failover mode at discovery time"),
                            parameter_form=FixedValue(
                                value=None,
                                help_text=Help(
                                    "Compare the current failover mode against the one at discovery time to detect and alert on failovers. "
                                    "Note that using this option might require a service re-discovery. "
                                    "You will be informed if this is the case."
                                ),
                            ),
                        ),
                        CascadingSingleChoiceElement(
                            name="explicit_failover_mode",
                            title=Title("Set explicit failover mode"),
                            parameter_form=SingleChoice(
                                elements=[
                                    SingleChoiceElement(name="primary", title=Title("Primary")),
                                    SingleChoiceElement(name="secondary", title=Title("Secondary")),
                                ],
                                help_text=Help(
                                    "Alert if failover mode is different from the value configured here."
                                ),
                            ),
                        ),
                    ],
                    prefill=DefaultValue("disabled"),
                ),
            ),
            "discovered_failover_mode": DictElement(
                render_only=True,
                parameter_form=SingleChoice(
                    title=Title("Discovered failover mode"),
                    elements=[
                        SingleChoiceElement(name="primary", title=Title("Primary")),
                        SingleChoiceElement(name="secondary", title=Title("Secondary")),
                    ],
                ),
            ),
        }
    )


rule_spec_netscaler_ha = CheckParameters(
    name="netscaler_ha",
    title=Title("Citrix Netscaler load balancer HA"),
    topic=Topic.APPLICATIONS,
    parameter_form=_parameter_netscaler_ha,
    condition=HostCondition(),
)
